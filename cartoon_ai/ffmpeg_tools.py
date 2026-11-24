"""All video work goes through FFmpeg (bundled via imageio-ffmpeg, no install needed)."""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass

from . import paths


class VideoError(Exception):
    pass


_NOWIN = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


def ffmpeg_exe() -> str:
    env = os.environ.get("CARTOON_FFMPEG")
    if env and os.path.exists(env):
        return env
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args, timeout: int = 900) -> tuple[int, str]:
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-y", *[str(a) for a in args]]
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace",
            timeout=timeout, creationflags=_NOWIN,
        )
    except subprocess.TimeoutExpired:
        raise VideoError("Video processing took too long and was stopped.")
    except OSError as e:
        raise VideoError(f"Could not start FFmpeg: {e}")
    return p.returncode, p.stderr


def _tail(err: str) -> str:
    lines = [l for l in err.strip().splitlines() if l.strip()]
    return "\n".join(lines[-4:])


@dataclass
class VideoInfo:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool
    size_bytes: int
    codec: str

    def summary(self) -> str:
        return (f"{self.width}x{self.height} | {self.fps:.0f} fps | {self.duration:.1f} s | "
                f"{self.size_bytes / 1048576:.1f} MB | {self.codec}")


def probe(path: str) -> VideoInfo:
    if not os.path.isfile(path):
        raise VideoError("File not found.")
    size = os.path.getsize(path)
    if size == 0:
        raise VideoError("The file is empty.")
    _, err = run_ffmpeg(["-i", path], timeout=60)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    v = re.search(r"Video:\s*([^\s,(]+)[^\n]*?,\s*(\d{2,5})x(\d{2,5})", err)
    if not v or not m:
        raise VideoError("This file is not a readable video (unsupported or damaged).")
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    w, h = int(v.group(2)), int(v.group(3))
    rot = re.search(r"rotation of (-?\d+(?:\.\d+)?) degrees", err)
    if rot and int(abs(float(rot.group(1)))) % 180 == 90:
        w, h = h, w
    fps_m = re.search(r"(\d+(?:\.\d+)?)\s*fps", err) or re.search(r"(\d+(?:\.\d+)?)\s*tbr", err)
    fps = float(fps_m.group(1)) if fps_m else 0.0
    if dur <= 0:
        raise VideoError("The video has no duration.")
    return VideoInfo(path, dur, w, h, fps, "Audio:" in err, size, v.group(1))


def esc_path(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


ENCODE = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"]


def make_thumbnail(src: str, dst: str, width: int = 320) -> bool:
    try:
        code, _ = run_ffmpeg(["-ss", "0.3", "-i", src, "-frames:v", "1", "-vf", f"scale={width}:-2", dst], 60)
        if code != 0 or not os.path.exists(dst):
            code, _ = run_ffmpeg(["-i", src, "-frames:v", "1", "-vf", f"scale={width}:-2", dst], 60)
        return code == 0 and os.path.exists(dst)
    except VideoError:
        return False


def trim(src: str, dst: str, start: float, duration: float) -> str:
    code, err = run_ffmpeg(["-ss", f"{start:.3f}", "-i", src, "-t", f"{duration:.3f}", *ENCODE, dst])
    if code != 0 or not os.path.exists(dst):
        raise VideoError("Trimming failed.\n" + _tail(err))
    return dst


def split_at(src: str, t: float, dst_a: str, dst_b: str) -> tuple[str, str]:
    info = probe(src)
    if not (0.2 < t < info.duration - 0.2):
        raise VideoError("Choose a split time inside the video.")
    trim(src, dst_a, 0, t)
    trim(src, dst_b, t, info.duration - t)
    return dst_a, dst_b


def _atempo_chain(speed: float) -> list[str]:
    out, s = [], speed
    while s > 2.0:
        out.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        out.append("atempo=0.5")
        s /= 0.5
    out.append(f"atempo={s:.4f}")
    return out


_FILTERS_CACHE: dict = {}


def has_filter(name: str) -> bool:
    """True if the bundled FFmpeg contains this filter (e.g. 'subtitles' needs libass)."""
    if "out" not in _FILTERS_CACHE:
        try:
            p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-filters"], capture_output=True, text=True,
                               errors="replace", timeout=30, creationflags=_NOWIN)
            _FILTERS_CACHE["out"] = p.stdout
        except Exception:
            _FILTERS_CACHE["out"] = ""
    return re.search(rf"\s{re.escape(name)}\s", _FILTERS_CACHE["out"]) is not None


def apply_edits(src: str, dst: str, o: dict) -> str:
    """o keys: start,end,crop,rotate,flip_h,flip_v,speed,brightness,contrast,saturation,
    overlays[{png,pos,start,end}],subtitles,volume,mute,music{path,volume,offset}.
    Text overlays are PNG images (see textimg.py) so FFmpeg's drawtext is not needed."""
    info = probe(src)
    pre: list[str] = []
    af: list[str] = []

    crop = o.get("crop")
    if crop:
        if crop[0] == "ratio":
            a, b = crop[1], crop[2]
            pre.append(f"crop='min(iw,ih*{a}/{b})':'min(ih,iw*{b}/{a})'")
        elif crop[0] == "rect":
            _, x, y, w, h = crop
            pre.append(f"crop={int(w)}:{int(h)}:{int(x)}:{int(y)}")
    rot = int(o.get("rotate", 0)) % 360
    if rot == 90:
        pre.append("transpose=1")
    elif rot == 180:
        pre += ["hflip", "vflip"]
    elif rot == 270:
        pre.append("transpose=2")
    if o.get("flip_h"):
        pre.append("hflip")
    if o.get("flip_v"):
        pre.append("vflip")

    br, co, sa = o.get("brightness", 0.0), o.get("contrast", 1.0), o.get("saturation", 1.0)
    if abs(br) > 1e-6 or abs(co - 1) > 1e-6 or abs(sa - 1) > 1e-6:
        pre.append(f"eq=brightness={br:.3f}:contrast={co:.3f}:saturation={sa:.3f}")

    speed = float(o.get("speed", 1.0) or 1.0)
    if abs(speed - 1.0) > 1e-6:
        pre.append(f"setpts=PTS/{speed:.4f}")
        af += _atempo_chain(speed)

    overlays = o.get("overlays", [])
    for ov in overlays:
        if not ov.get("png") or not os.path.exists(ov["png"]):
            raise VideoError("A text overlay has no image. Please add it again.")

    post: list[str] = []
    if o.get("subtitles"):
        if not has_filter("subtitles"):
            raise VideoError("This FFmpeg build cannot burn in subtitles. Use text overlays instead.")
        post.append(f"subtitles='{esc_path(o['subtitles'])}'")
    post.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

    mute = bool(o.get("mute"))
    vol = float(o.get("volume", 1.0))
    if abs(vol - 1.0) > 1e-6:
        af.append(f"volume={vol:.3f}")

    pre_in: list[str] = []
    start = float(o.get("start", 0) or 0)
    end = o.get("end")
    if start > 0:
        pre_in += ["-ss", f"{start:.3f}"]
    out_opts: list[str] = []
    if end is not None and float(end) > start:
        out_opts += ["-t", f"{float(end) - start:.3f}"]

    cmd = [*pre_in, "-i", src]
    for ov in overlays:
        cmd += ["-i", ov["png"]]
    music = o.get("music")
    mus_idx = 1 + len(overlays)
    if music and music.get("path"):
        cmd += ["-i", music["path"]]

    parts = [f"[0:v]{','.join(pre) if pre else 'null'}[v0]"]
    cur = "v0"
    for i, ov in enumerate(overlays):
        y = {"top": "H*0.08", "center": "(H-h)/2"}.get(ov.get("pos", "bottom"), "H-h-H*0.08")
        s_, e_ = float(ov.get("start", 0)), float(ov.get("end", 9999))
        parts.append(f"[{cur}][{i + 1}:v]overlay=x=(W-w)/2:y={y}:enable='between(t,{s_:.2f},{e_:.2f})'[v{i + 1}]")
        cur = f"v{i + 1}"
    parts.append(f"[{cur}]{','.join(post)}[v]")

    has_music = bool(music and music.get("path"))
    map_a: list[str] = []
    if has_music:
        ms = int(float(music.get("offset", 0)) * 1000)
        mus = f"[{mus_idx}:a]volume={float(music.get('volume', 1.0)):.3f},adelay={ms}|{ms}"
        if info.has_audio and not mute:
            parts.append(f"[0:a]{','.join(af) if af else 'anull'}[a0]")
            parts.append(mus + "[m]")
            parts.append("[a0][m]amix=inputs=2:duration=first:dropout_transition=0[a]")
        else:
            parts.append(mus + "[a]")
        map_a = ["-map", "[a]", "-shortest"]
    elif info.has_audio and not mute:
        parts.append(f"[0:a]{','.join(af) if af else 'anull'}[a]")
        map_a = ["-map", "[a]"]
    else:
        map_a = ["-an"]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]", *map_a, *out_opts, *ENCODE, dst]
    code, err = run_ffmpeg(cmd)
    if code != 0 or not os.path.exists(dst):
        raise VideoError("Editing failed.\n" + _tail(err))
    return dst


def export_video(src: str, dst: str, height: int | None, aspect: tuple[int, int] | None) -> str:
    """Local re-scaling / padding. (The AI service decides the generated size itself.)"""
    info = probe(src)
    h = height or info.height
    h -= h % 2
    if aspect:
        w = int(round(h * aspect[0] / aspect[1]))
        w -= w % 2
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1")
    elif height:
        vf = f"scale=-2:{h}"
    else:
        vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    args = ["-i", src, "-vf", vf, *ENCODE, dst]
    code, err = run_ffmpeg(args)
    if code != 0 or not os.path.exists(dst):
        raise VideoError("Export failed.\n" + _tail(err))
    return dst


def demo_filter(src: str, dst: str, label_png: str | None = None) -> str:
    """DEMO ONLY: a plain local colour/posterize filter. This is NOT AI."""
    base = ("hue=s=1.7,eq=contrast=1.15:saturation=1.5,"
            "lutyuv=y='floor(val/40)*40':u='floor(val/28)*28':v='floor(val/28)*28'")
    even = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    if label_png and os.path.exists(label_png):
        graph = (f"[0:v]{base}[b];[b][1:v]overlay=x=W*0.03:y=H*0.03,{even}[v]")
        args = ["-i", src, "-i", label_png, "-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
                *ENCODE, dst]
    else:
        args = ["-i", src, "-vf", f"{base},{even}", *ENCODE, dst]
    code, err = run_ffmpeg(args)
    if code != 0 or not os.path.exists(dst):
        raise VideoError("Demo preview failed.\n" + _tail(err))
    return dst
