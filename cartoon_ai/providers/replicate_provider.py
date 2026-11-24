"""Replicate (https://replicate.com) adapter: real upload, async prediction, real polling,
real result download. Default model: luma/modify-video (video-to-video style transfer).

IMPORTANT: Replicate models differ in their input field names. The mapping lives in the
"input template" setting (JSON). Open the model's API tab on replicate.com and edit the
template in Settings if the field names differ. The defaults were NOT verified against a live
account while this app was written."""
from __future__ import annotations

import json
import os
import re
import time

import requests

from .. import paths
from .. import secrets_store
from .base import Cancelled, JobRequest, Provider, ProviderError

API = os.environ.get("CARTOON_REPLICATE_API", "https://api.replicate.com/v1")  # env override is for tests
POLL_SECONDS = float(os.environ.get("CARTOON_POLL_SECONDS", "3"))
QUALITY_SUFFIX = ", clean line art, consistent character design, smooth motion, high detail"


def _fill(obj, values: dict):
    if isinstance(obj, str):
        for k, v in values.items():
            obj = obj.replace("{" + k + "}", str(v))
        return obj
    if isinstance(obj, list):
        return [_fill(x, values) for x in obj]
    if isinstance(obj, dict):
        return {k: _fill(v, values) for k, v in obj.items()}
    return obj


def intensity_to_mode(intensity: int) -> str:
    """Low = stay close to the original, high = reimagine more."""
    if intensity < 34:
        return "adhere_2"
    if intensity < 67:
        return "flex_2"
    return "reimagine_2"


class ReplicateProvider(Provider):
    id = "replicate"
    name = "Replicate - cloud AI video-to-video"
    capabilities = {"prompt", "intensity", "auto_enhance"}
    notes = ("Needs internet and a Replicate API key (pay per use). Style Intensity chooses how "
             "strongly the model may change the video. Other controls are not offered by this model.")

    def __init__(self, cfg) -> None:
        self.cfg = cfg

    def _key(self) -> str | None:
        return secrets_store.get_key("replicate")

    def model(self) -> str:
        return str(self.cfg.get("model")).strip()

    def configured(self) -> bool:
        return bool(self._key()) and bool(re.fullmatch(r"[\w.-]+/[\w.-]+", self.model()))

    # ---- HTTP with retry ---------------------------------------------------
    def _request(self, method, url, key, file_path=None, **kw):
        headers = {"Authorization": f"Bearer {key}"}
        last = None
        for attempt in range(3):
            try:
                if file_path:
                    with open(file_path, "rb") as f:
                        r = requests.request(
                            method, url, headers=headers, timeout=(15, 300),
                            files={"content": (os.path.basename(file_path), f, "video/mp4")})
                else:
                    r = requests.request(method, url, headers=headers, timeout=(15, 60), **kw)
            except (requests.ConnectionError, requests.Timeout) as e:
                last = ProviderError(f"Network problem: {e.__class__.__name__}. Check your internet.", True)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = ProviderError(f"Service busy (HTTP {r.status_code}).", True)
                try:
                    wait = float(r.headers.get("Retry-After", 2 * (attempt + 1)))
                except ValueError:
                    wait = 2 * (attempt + 1)
                time.sleep(min(wait, 20))
                continue
            if r.status_code in (401, 403):
                raise ProviderError("The API key was rejected. Check it in Settings.")
            if r.status_code == 402:
                raise ProviderError("Your Replicate account has no credit / billing is not set up.")
            if r.status_code == 404:
                raise ProviderError(f"Model or resource not found: {self.model()}")
            if r.status_code >= 400:
                detail = ""
                try:
                    detail = r.json().get("detail", "") or r.text[:300]
                except Exception:
                    detail = r.text[:300]
                raise ProviderError(f"The service rejected the request (HTTP {r.status_code}): {detail}")
            return r
        raise last or ProviderError("Request failed.", True)

    def test_connection(self) -> str:
        key = self._key()
        if not key:
            raise ProviderError("No API key saved.")
        r = self._request("GET", f"{API}/account", key)
        who = r.json().get("username") or r.json().get("name") or "account"
        return f"Connected as {who}."

    # ---- main job ------------------------------------------------------------
    def run(self, req: JobRequest, report, cancelled) -> str:
        key = self._key()
        if not key:
            raise ProviderError("No API key. Add one in Settings.")
        try:
            template = json.loads(str(self.cfg.get("template")))
        except Exception:
            raise ProviderError("The input template in Settings is not valid JSON.")

        prompt = req.style_prompt
        if req.prompt.strip():
            prompt += ". " + req.prompt.strip()
        if req.auto_enhance:
            prompt += QUALITY_SUFFIX

        report("Uploading video to the AI service...")
        up = self._request("POST", f"{API}/files", key, file_path=req.video_path).json()
        video_url = (up.get("urls") or {}).get("get")
        if not video_url:
            raise ProviderError("Upload succeeded but no file URL was returned.")
        if cancelled():
            raise Cancelled()

        inputs = _fill(template, {"video": video_url, "prompt": prompt,
                                  "mode": intensity_to_mode(req.intensity)})
        report("Starting AI job...")
        pred = self._request("POST", f"{API}/models/{self.model()}/predictions", key,
                             json={"input": inputs}).json()
        get_url = (pred.get("urls") or {}).get("get")
        cancel_url = (pred.get("urls") or {}).get("cancel")
        if not get_url:
            raise ProviderError("The service did not return a job URL.")

        started = time.time()
        while True:
            if cancelled():
                try:
                    if cancel_url:
                        self._request("POST", cancel_url, key)
                except Exception:
                    pass
                raise Cancelled()
            if time.time() - started > 25 * 60:
                raise ProviderError("The AI job took longer than 25 minutes.", True)
            time.sleep(POLL_SECONDS)
            pred = self._request("GET", get_url, key).json()
            status = pred.get("status", "")
            report(f"AI service status: {status} ({int(time.time() - started)} s)")
            if status == "succeeded":
                break
            if status in ("failed", "canceled"):
                raise ProviderError(f"AI job {status}: {pred.get('error') or 'no details given'}")

        out = pred.get("output")
        if isinstance(out, list) and out:
            out = out[0]
        if not isinstance(out, str) or not out.startswith("http"):
            raise ProviderError("The job finished but returned no video URL.")

        report("Downloading the generated video...")
        dst = paths.work_file(f"ai_{int(time.time() * 1000)}.mp4")
        last = None
        for attempt in range(3):
            try:
                with requests.get(out, stream=True, timeout=(15, 120)) as r:
                    r.raise_for_status()
                    with open(dst, "wb") as f:
                        for chunk in r.iter_content(1 << 16):
                            if cancelled():
                                raise Cancelled()
                            f.write(chunk)
                if os.path.getsize(dst) > 0:
                    return dst
            except Cancelled:
                raise
            except Exception as e:
                last = e
                time.sleep(2)
        raise ProviderError(f"Could not download the result: {last}", True)
