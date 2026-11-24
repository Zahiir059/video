"""FFmpeg helpers: probing, validation, editing, export."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import AUDIO_EXTS, MAX_FILE_MB, TMP_DIR, VIDEO_EXTS


class MediaError(Exception):
    pass


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    p = shutil.which("ffmpeg")
    if p:
        return p
    raise MediaError("The bundled FFmpeg could not be found.")


def _flags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def run_ffmpeg(args: list[str], cwd: str | None = None, timeout: int = 1200) -> None:
    cmd = [ffmpeg_exe(), "-hide_banner", "-y", "-loglevel", "error"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=cwd, timeout=timeout, creationflags=_flags())
    except subprocess.TimeoutExpired:
        raise MediaError("FFmpeg took too long and was stopped.")
    if r.returncode != 0:
        tail = "\n".join(r.stderr.strip().splitlines()[-3:]) or "unknown error"
        raise MediaError("FFmpeg failed:\n" + tail)


@dataclass
class VideoInfo:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool
    size_bytes: int

    def summary(self) -> str:
        return (f"{self.width}x{self.height}  |  {self.fps:.2f} fps  |  {self.duration:.1f} s  |  "
                f"{self.size_bytes / 1_048_576:.1f} MB  |  audio: {'yes' if self.has_audio else 'no'}")


def probe(path: str) -> VideoInfo:
    p = Path(path)
    if not p.is_file():
        raise MediaError("File not found.")
    try:
        r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(p)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", creationflags=_flags(), timeout=60)
    except subprocess.TimeoutExpired:
        raise MediaError("Reading the file took too long.")
    err = r.stderr
    v = re.search(r"Stream #\d+:\d+.*?: Video: (.*)", err)
    if not v:
        raise MediaError("This file does not contain a readable video stream.")
    d = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if not d:
        raise MediaError("The video has no readable duration (is it a still image or a broken file?).")
    dur = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))
    if dur <= 0:
        raise MediaError("The video has zero length.")
    vline = v.group(1)
    res = re.search(r"\b(\d{2,5})x(\d{2,5})\b", vline)
    if not res:
        raise MediaError("Could not read the video resolution.")
    fps_m = re.search(r"(\d+(?:\.\d+)?)\s*fps", vline) or re.search(r"(\d+(?:\.\d+)?)\s*tbr", vline)
    return VideoInfo(str(p), dur, int(res.group(1)), int(res.group(2)),
                     float(fps_m.group(1)) if fps_m else 0.0,
                     bool(re.search(r"Stream #\d+:\d+.*?: Audio:", err)), p.stat().st_size)


def validate_video(path: str) -> VideoInfo:
    p = Path(path)
    if p.suffix.lower() not in VIDEO_EXTS:
        raise MediaError("Unsupported format '" + p.suffix + "'. Use: " +
                         ", ".join(sorted(e.strip('.') for e in VIDEO_EXTS)) + ".")
    if not p.is_file():
        raise MediaError("File not found.")
    if p.stat().st_size > MAX_FILE_MB * 1_048_576:
        raise MediaError(f"File is larger than {MAX_FILE_MB} MB.")
    return probe(path)


def validate_audio(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() not in AUDIO_EXTS | VIDEO_EXTS:
        raise MediaError("Unsupported audio format.")
    return str(p)


def tmp_path(suffix: str = ".mp4") -> str:
    return str(TMP_DIR / (uuid.uuid4().hex[:10] + suffix))


_ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"]


def cut_segment(src: str, start: float, dur: float, out: str) -> None:
    run_ffmpeg(["-ss", f"{start:.3f}", "-i", src, "-t", f"{dur:.3f}", "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2"] + _ENC + [out])


def make_thumbnail(src: str, out: str, at: float = 0.4) -> bool:
    try:
        run_ffmpeg(["-ss", f"{at:.2f}", "-i", src, "-frames:v", "1", "-vf", "scale=360:-2", out])
        if not Path(out).exists():
            run_ffmpeg(["-i", src, "-frames:v", "1", "-vf", "scale=360:-2", out])
        return Path(out).exists()
    except MediaError:
        return False


def make_sample_clip(out: str) -> None:
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=6",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-shortest"] + _ENC + [out])


def demo_stylize(src: str, out: str) -> None:
    """DEMO ONLY: plain FFmpeg edge/colour filter. This is NOT AI."""
    run_ffmpeg(["-i", src, "-vf",
                "scale=-2:480,hue=s=1.6,edgedetect=mode=colormix:high=0,scale=trunc(iw/2)*2:trunc(ih/2)*2"]
               + _ENC + [out])


# ------------------------------------------------------------------ editing
@dataclass
class EditSpec:
    trim_start: float = 0.0
    trim_end: float | None = None
    crop: tuple | None = None          # fractions (x, y, w, h)
    rotate: int = 0                    # 0 / 90 / 180 / 270
    flip_h: bool = False
    flip_v: bool = False
    speed: float = 1.0
    brightness: float = 0.0            # -1 .. 1
    contrast: float = 1.0
    saturation: float = 1.0
    text: str = ""
    text_pos: str = "bottom"
    text_size: int = 36
    text_color: str = "white"
    subtitles: str | None = None
    mute: bool = False
    volume: float = 1.0
    music: str | None = None
    music_volume: float = 0.5
    music_start: float = 0.0
    music_dur: float | None = None
    voice: str | None = None
    voice_volume: float = 1.0
    sfx: str | None = None
    sfx_at: float = 0.0
    sfx_volume: float = 1.0


def find_font() -> str | None:
    for p in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"):
        if os.path.exists(p):
            return p
    return None


def _atempo(speed: float) -> str:
    parts = []
    s = speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


def _ff_font(path: str) -> str:
    return path.replace("\\", "/").replace(":", "\\:")


def build_edit(src: str, out: str, s: EditSpec, info: VideoInfo) -> tuple[list[str], str]:
    """Returns (ffmpeg args, cwd). Text/subtitle files are placed in TMP_DIR (the cwd)."""
    cwd = str(TMP_DIR)
    src, out = str(Path(src).resolve()), str(Path(out).resolve())
    args: list[str] = []
    if s.trim_start > 0:
        args += ["-ss", f"{s.trim_start:.3f}"]
    if s.trim_end and s.trim_end > s.trim_start:
        args += ["-t", f"{s.trim_end - s.trim_start:.3f}"]
    args += ["-i", src]
    idx = 1
    music_i = voice_i = sfx_i = None
    for kind, path in (("music", s.music), ("voice", s.voice), ("sfx", s.sfx)):
        if path:
            args += ["-i", str(Path(path).resolve())]
            if kind == "music":
                music_i = idx
            elif kind == "voice":
                voice_i = idx
            else:
                sfx_i = idx
            idx += 1

    vf: list[str] = []
    if s.crop:
        x, y, w, h = s.crop
        cw = max(2, int(info.width * w) // 2 * 2)
        ch = max(2, int(info.height * h) // 2 * 2)
        cx = min(int(info.width * x), info.width - cw)
        cy = min(int(info.height * y), info.height - ch)
        vf.append(f"crop={cw}:{ch}:{cx}:{cy}")
    if s.rotate == 90:
        vf.append("transpose=1")
    elif s.rotate == 180:
        vf += ["hflip", "vflip"]
    elif s.rotate == 270:
        vf.append("transpose=2")
    if s.flip_h:
        vf.append("hflip")
    if s.flip_v:
        vf.append("vflip")
    if s.brightness != 0 or s.contrast != 1 or s.saturation != 1:
        vf.append(f"eq=brightness={s.brightness:.3f}:contrast={s.contrast:.3f}:saturation={s.saturation:.3f}")
    if s.speed != 1.0:
        vf.append(f"setpts=PTS/{s.speed:.4f}")
    if s.text.strip():
        (TMP_DIR / "overlay_text.txt").write_text(s.text, encoding="utf-8")
        y = {"top": "h*0.06", "center": "(h-text_h)/2"}.get(s.text_pos, "h-text_h-h*0.06")
        font = find_font()
        ff = f"fontfile='{_ff_font(font)}':" if font else ""
        vf.append(f"drawtext={ff}textfile=overlay_text.txt:expansion=none:fontsize={int(s.text_size)}:"
                  f"fontcolor={s.text_color}:x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.45:boxborderw=10")
    if s.subtitles:
        shutil.copyfile(s.subtitles, TMP_DIR / "subs.srt")
        vf.append("subtitles=subs.srt")
    vf.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

    fc = ["[0:v]" + ",".join(vf) + "[v]"]
    labels: list[str] = []
    if info.has_audio and not s.mute:
        f = []
        if s.volume != 1.0:
            f.append(f"volume={s.volume:.3f}")
        if s.speed != 1.0:
            f.append(_atempo(s.speed))
        fc.append("[0:a]" + (",".join(f) if f else "anull") + "[a0]")
        labels.append("[a0]")
    if music_i is not None:
        f = []
        if s.music_start > 0 or s.music_dur:
            tr = f"atrim=start={s.music_start:.3f}"
            if s.music_dur:
                tr += f":duration={s.music_dur:.3f}"
            f += [tr, "asetpts=PTS-STARTPTS"]
        f.append(f"volume={s.music_volume:.3f}")
        fc.append(f"[{music_i}:a]" + ",".join(f) + "[am]")
        labels.append("[am]")
    if voice_i is not None:
        fc.append(f"[{voice_i}:a]volume={s.voice_volume:.3f}[avo]")
        labels.append("[avo]")
    if sfx_i is not None:
        ms = int(s.sfx_at * 1000)
        fc.append(f"[{sfx_i}:a]adelay={ms}|{ms},volume={s.sfx_volume:.3f}[afx]")
        labels.append("[afx]")

    maps = ["-map", "[v]"]
    if len(labels) == 1:
        maps += ["-map", labels[0]]
    elif len(labels) > 1:
        fc.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0[aout]")
        maps += ["-map", "[aout]"]
    else:
        maps += ["-an"]
    args += ["-filter_complex", ";".join(fc)] + maps
    if len(labels) > 0 and idx > 1:
        args += ["-shortest"]
    args += _ENC + [out]
    return args, cwd


def apply_edit(src: str, out: str, s: EditSpec) -> None:
    info = probe(src)
    args, cwd = build_edit(src, out, s, info)
    run_ffmpeg(args, cwd=cwd)


def split_at(src: str, t: float, out1: str, out2: str) -> None:
    info = probe(src)
    if not (0.2 < t < info.duration - 0.2):
        raise MediaError("Choose a split point inside the video.")
    cut_segment(src, 0, t, out1)
    cut_segment(src, t, info.duration - t, out2)


ASPECTS = {"Original aspect ratio": None, "16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0}


def export_video(src: str, out: str, height: int | None, aspect: float | None) -> None:
    info = probe(src)
    h = height or info.height
    h = h // 2 * 2
    if aspect is None:
        vf = f"scale=-2:{h}"
    else:
        w = int(round(h * aspect / 2)) * 2
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black")
    run_ffmpeg(["-i", src, "-vf", vf + ",setsar=1"] + _ENC + [out])
