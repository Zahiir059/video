"""Real cloud video-to-video generation through the Replicate HTTP API.

Default model: philz1337x/video-style-transfer (AnimateDiff based). Its documented inputs are
video, prompt, negative_prompt, cfg_scale, num_inference_steps, target_fps and input/output
width+height - so those are the only controls shown. It has NO face-consistency / motion /
lighting / palette inputs, so the app does not pretend to offer them.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import requests

from ..media import MediaError, probe, tmp_path
from .base import Capability, Provider, ProviderError

API = "https://api.replicate.com/v1"


class ReplicateProvider(Provider):
    id = "replicate"
    name = "Replicate (cloud AI)"
    supports_prompt = True
    supports_negative = True
    description = "Cloud AI video-to-video. Needs internet and a Replicate account with billing enabled."

    capabilities = [
        Capability("cfg_scale", "Style Intensity", "slider", 3.0, 1.0, 10.0, 0.5,
                   help="Guidance scale: higher follows the style prompt more strongly."),
        Capability("num_inference_steps", "Detail / Quality", "int", 10, 4, 30, 1,
                   help="More steps give more detail but take longer and cost more."),
        Capability("target_fps", "Frame rate", "choice", 0, choices=[("Same as original", 0), ("12 fps", 12), ("24 fps", 24)],
                   help="Output frame rate."),
        Capability("size", "Output size (longest side)", "choice", 768,
                   choices=[("512 px", 512), ("768 px", 768), ("1024 px", 1024)],
                   help="Resolution requested from the model."),
    ]

    def __init__(self, api_key: str, model: str):
        self.key = api_key
        self.model = model.strip()
        self.http = requests.Session()
        self.http.headers["Authorization"] = "Bearer " + api_key
        self.http.headers["User-Agent"] = "CartoonAI/1.0"

    def configured(self) -> bool:
        return bool(self.key)

    # ---------------------------------------------------------------- HTTP
    def _req(self, method: str, path: str, **kw):
        url = path if path.startswith("http") else API + path
        timeout = kw.pop("timeout", 60)
        last = "network error"
        upload = kw.pop("upload", None)      # (filename, mime, path): re-opened on every retry
        for attempt in range(4):
            fh = None
            call = dict(kw)
            if upload:
                fh = open(upload[2], "rb")
                call["files"] = {"content": (upload[0], fh, upload[1])}
            try:
                r = self.http.request(method, url, timeout=timeout, **call)
            except requests.RequestException as e:
                last = "Network problem: " + str(e).split("\n")[0][:160]
                time.sleep(1.5 * (attempt + 1))
                continue
            finally:
                if fh:
                    fh.close()
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"Server busy (HTTP {r.status_code})"
                time.sleep(float(r.headers.get("Retry-After", 2 * (attempt + 1))))
                continue
            if r.status_code == 401:
                raise ProviderError("Invalid API key. Check it in Settings.")
            if r.status_code == 402:
                raise ProviderError("Replicate says payment is required. Add billing/credit to your account.")
            if r.status_code == 404:
                raise ProviderError("Not found. Check the model name in Settings (owner/name).")
            if r.status_code >= 400:
                try:
                    detail = r.json().get("detail") or r.text
                except Exception:
                    detail = r.text
                raise ProviderError(f"Replicate error {r.status_code}: {str(detail)[:300]}")
            return r
        raise ProviderError(last + ". Please try again.", retryable=True)

    def test_connection(self) -> str:
        r = self._req("GET", "/account", timeout=20)
        name = r.json().get("username", "?")
        self._latest_version()
        return f"Connected as '{name}'. Model '{self.model}' is available."

    def _latest_version(self) -> str:
        if ":" in self.model:
            return self.model.split(":", 1)[1]
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", self.model):
            raise ProviderError("Model must look like owner/name.")
        r = self._req("GET", f"/models/{self.model}", timeout=30)
        v = (r.json().get("latest_version") or {}).get("id")
        if not v:
            raise ProviderError("This model has no published version.")
        return v

    def _upload(self, path: str) -> str:
        name = Path(path).name
        r = self._req("POST", "/files", timeout=300, upload=(name, "video/mp4", path))
        url = (r.json().get("urls") or {}).get("get")
        if not url:
            raise ProviderError("Upload failed: no file URL returned.")
        return url

    # ------------------------------------------------------------ generate
    def generate(self, video, style, prompt, negative, params, report, cancelled):
        try:
            info = probe(video)
        except MediaError as e:
            raise ProviderError(str(e))
        longest = int(params.get("size", 768))
        scale = longest / max(info.width, info.height)
        w = max(64, int(round(info.width * scale / 8)) * 8)
        h = max(64, int(round(info.height * scale / 8)) * 8)

        report(4, "Preparing request")
        version = self._latest_version()
        if cancelled():
            raise ProviderError("Cancelled.")
        report(8, "Uploading video to Replicate...")
        url = self._upload(video)
        if cancelled():
            raise ProviderError("Cancelled.")

        body = {"version": version, "input": {
            "video": url,
            "prompt": prompt,
            "negative_prompt": negative,
            "cfg_scale": float(params.get("cfg_scale", 3)),
            "num_inference_steps": int(params.get("num_inference_steps", 10)),
            "target_fps": int(params.get("target_fps", 0)),
            "input_width": w, "input_height": h, "output_width": w, "output_height": h,
        }}
        report(15, "Starting AI job...")
        pred = self._req("POST", "/predictions", json=body, timeout=60).json()
        pid, get_url = pred["id"], pred["urls"]["get"]
        cancel_url = pred["urls"].get("cancel")
        t0 = time.time()

        while True:
            if cancelled():
                if cancel_url:
                    try:
                        self.http.post(cancel_url, timeout=20)
                    except requests.RequestException:
                        pass
                raise ProviderError("Cancelled.")
            time.sleep(3)
            pred = self._req("GET", get_url, timeout=30).json()
            status = pred.get("status")
            elapsed = int(time.time() - t0)
            if status == "starting":
                report(-1, f"AI server is starting (model may be cold-booting)... {elapsed}s")
            elif status == "processing":
                report(-1, f"AI is generating your video... {elapsed}s")
            elif status == "succeeded":
                break
            elif status in ("failed", "canceled"):
                err = pred.get("error") or "The AI job did not complete."
                raise ProviderError(f"AI job {status}: {str(err)[:300]}", retryable=True)
            if elapsed > 1800:
                raise ProviderError("The AI job took too long (30 min).", retryable=True)

        out = pred.get("output")
        if isinstance(out, list) and out:
            out = out[0]
        if isinstance(out, dict):
            out = next(iter(out.values()), None)
        if not isinstance(out, str) or not out.startswith("http"):
            raise ProviderError("The AI returned no video file.", retryable=True)

        report(92, "Downloading the generated video...")
        dest = tmp_path(".mp4")
        try:
            with requests.get(out, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        except requests.RequestException as e:
            raise ProviderError("Download failed: " + str(e)[:160], retryable=True)
        report(100, "Done")
        return dest
