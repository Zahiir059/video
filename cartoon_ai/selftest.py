"""`Cartoon.exe --selftest report.txt` : builds every screen, runs FFmpeg operations, runs the
AI-provider flow against a local mock server, and writes PASS/FAIL lines to the report."""
from __future__ import annotations

import http.server
import json
import os
import shutil
import tempfile
import threading
import traceback

RESULTS: list[str] = []
FAILS = 0


def check(name: str, fn):
    global FAILS
    try:
        extra = fn()
        RESULTS.append(f"PASS  {name}" + (f"  ({extra})" if extra else ""))
    except Exception as e:
        FAILS += 1
        RESULTS.append(f"FAIL  {name}: {e}\n" + traceback.format_exc(limit=3))


def _mock_server(video_bytes: bytes, fail: bool):
    state = {"polls": 0, "uploads": 0, "inputs": None}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n)
            base = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Authorization") != "Bearer test-key":
                return self._json(401, {"detail": "bad key"})
            if self.path.endswith("/files"):
                state["uploads"] += 1
                return self._json(201, {"urls": {"get": base + "/files/1"}})
            if "/predictions" in self.path:
                state["inputs"] = json.loads(body)["input"]
                return self._json(201, {"status": "starting", "urls": {
                    "get": base + "/predictions/1", "cancel": base + "/predictions/1/cancel"}})
            self._json(404, {"detail": "nope"})

        def do_GET(self):
            base = f"http://127.0.0.1:{self.server.server_port}"
            if self.path == "/predictions/1":
                state["polls"] += 1
                if state["polls"] < 2:
                    return self._json(200, {"status": "processing"})
                if fail:
                    return self._json(200, {"status": "failed", "error": "mock model exploded"})
                return self._json(200, {"status": "succeeded", "output": base + "/out.mp4"})
            if self.path == "/out.mp4":
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(len(video_bytes)))
                self.end_headers()
                self.wfile.write(video_bytes)
                return
            if self.path == "/account":
                return self._json(200, {"username": "tester"})
            self._json(404, {"detail": "nope"})

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, state


def run(app, report_path: str) -> int:
    tmp = tempfile.mkdtemp(prefix="cartoon_selftest_")
    os.environ["CARTOON_DATA"] = os.path.join(tmp, "data")
    os.environ["CARTOON_POLL_SECONDS"] = "0.2"
    os.environ["REPLICATE_API_TOKEN"] = "test-key"
    shots = os.path.join(os.path.dirname(os.path.abspath(report_path)), "selftest_screens")
    os.makedirs(shots, exist_ok=True)

    from . import ffmpeg_tools as ff
    from . import paths
    from .providers import JobRequest, ReplicateProvider
    from .providers import replicate_provider as rp
    from .providers.base import ProviderError

    ctx_box: dict = {}

    # ---------------- FFmpeg --------------------------------------------------
    clip = os.path.join(tmp, "clip.mp4")
    long_clip = os.path.join(tmp, "long.mp4")
    audio = os.path.join(tmp, "beep.wav")

    def make_media():
        code, err = ff.run_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=4",
                                   "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
                                   *ff.ENCODE, "-shortest", clip])
        assert code == 0, err[-300:]
        code, err = ff.run_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=12",
                                   "-c:v", "libx264", "-pix_fmt", "yuv420p", long_clip])
        assert code == 0, err[-300:]
        code, err = ff.run_ffmpeg(["-f", "lavfi", "-i", "sine=frequency=880:duration=2", audio])
        assert code == 0, err[-300:]
        return f"ffmpeg at {ff.ffmpeg_exe()}"

    check("FFmpeg runs and creates test media", make_media)

    def t_probe():
        i = ff.probe(clip)
        assert (i.width, i.height) == (640, 360), i
        assert 3.5 < i.duration < 4.5 and i.has_audio and i.fps > 20
        return i.summary()

    check("Probe detects duration/resolution/fps/audio", t_probe)

    def t_probe_bad():
        bad = os.path.join(tmp, "bad.mp4")
        with open(bad, "w") as f:
            f.write("not a video")
        try:
            ff.probe(bad)
        except ff.VideoError:
            return "rejected invalid file"
        raise AssertionError("invalid file accepted")

    check("Invalid video is rejected", t_probe_bad)

    def t_trim10():
        info = ff.probe(long_clip)
        assert info.duration > 10.05  # would force the trim dialog
        out = ff.trim(long_clip, os.path.join(tmp, "t10.mp4"), 1.0, 10.0)
        d = ff.probe(out).duration
        assert d <= 10.2, d
        return f"12 s -> {d:.1f} s"

    check("10-second limit: long video trimmed to 10 s", t_trim10)

    def t_edits():
        from . import textimg
        png = textimg.render_text_png("Hello: it's a test", 36, "white", 560)
        assert os.path.getsize(png) > 200
        out = os.path.join(tmp, "edited.mp4")
        ff.apply_edits(clip, out, dict(
            start=0.5, end=3.5, crop=("ratio", 1, 1), rotate=90, flip_h=True, speed=1.5,
            brightness=0.1, contrast=1.1, saturation=1.3, volume=0.8,
            overlays=[dict(png=png, pos="bottom", start=0, end=2)],
            music=dict(path=audio, volume=0.7, offset=0.5)))
        i = ff.probe(out)
        assert i.has_audio and i.width == i.height or i.width < i.height + 2
        return i.summary()

    check("Editor: trim+crop+rotate+flip+speed+colour+text+volume+music", t_edits)

    def t_mute_sub():
        if not ff.has_filter("subtitles"):
            return "SKIPPED: this FFmpeg build has no subtitles filter (the app disables that button)"
        srt = os.path.join(tmp, "s.srt")
        with open(srt, "w") as f:
            f.write("1\n00:00:00,000 --> 00:00:02,000\nSubtitle test\n")
        out = os.path.join(tmp, "mute.mp4")
        ff.apply_edits(clip, out, dict(mute=True, subtitles=srt, speed=0.5))
        assert not ff.probe(out).has_audio
        return "muted + subtitles + slow motion"

    check("Editor: remove audio + subtitles + slow motion", t_mute_sub)

    def t_split():
        a, b = ff.split_at(clip, 2.0, os.path.join(tmp, "a.mp4"), os.path.join(tmp, "b.mp4"))
        return f"{ff.probe(a).duration:.1f} s + {ff.probe(b).duration:.1f} s"

    check("Editor: split", t_split)

    def t_export():
        for h, asp in ((480, None), (720, (16, 9)), (1080, (9, 16)), (None, (1, 1))):
            o = os.path.join(tmp, f"exp_{h}_{asp[0] if asp else 0}.mp4")
            ff.export_video(clip, o, h, asp)
            i = ff.probe(o)
            if h:
                assert i.height == h, (h, i.height)
            if asp:
                assert abs(i.width / i.height - asp[0] / asp[1]) < 0.02, (i.width, i.height)
        return "480p / 720p 16:9 / 1080p 9:16 / 1:1 verified"

    check("Export: resolutions and aspect ratios", t_export)

    def t_thumb():
        t = os.path.join(tmp, "th.jpg")
        assert ff.make_thumbnail(clip, t)
        return f"{os.path.getsize(t)} bytes"

    check("Thumbnail creation", t_thumb)

    # ---------------- providers ------------------------------------------------
    from .providers import DemoProvider

    def t_demo():
        req = JobRequest(clip, "anime", "Japanese Anime", "anime style")
        msgs = []
        out = DemoProvider().run(req, msgs.append, lambda: False)
        assert os.path.getsize(out) > 1000
        d = DemoProvider()
        assert d.is_demo and d.label_png and os.path.exists(d.label_png), "DEMO label image missing"
        return "demo filter output created, flagged is_demo"

    check("Demo Mode provider (flagged as not AI)", t_demo)

    video_bytes = open(clip, "rb").read()

    def t_replicate_ok():
        srv, st = _mock_server(video_bytes, fail=False)
        rp.API = f"http://127.0.0.1:{srv.server_port}"
        rp.POLL_SECONDS = 0.2
        from .config import Config
        cfg = Config()
        prov = ReplicateProvider(cfg)
        assert prov.configured()
        msgs = []
        req = JobRequest(clip, "anime", "Japanese Anime", "anime style", prompt="golden hour", intensity=80)
        out = prov.run(req, msgs.append, lambda: False)
        srv.shutdown()
        assert st["uploads"] == 1 and st["polls"] >= 2
        assert st["inputs"]["mode"] == "reimagine_2", st["inputs"]
        assert "golden hour" in st["inputs"]["prompt"] and st["inputs"]["video"].endswith("/files/1")
        assert os.path.getsize(out) == len(video_bytes)
        assert any("Uploading" in m for m in msgs) and any("status" in m for m in msgs)
        return "upload -> job -> polling -> download OK"

    check("AI provider flow (mock server): upload, async job, polling, download", t_replicate_ok)

    def t_replicate_fail():
        srv, _ = _mock_server(video_bytes, fail=True)
        rp.API = f"http://127.0.0.1:{srv.server_port}"
        from .config import Config
        prov = ReplicateProvider(Config())
        try:
            prov.run(JobRequest(clip, "anime", "A", "p"), lambda m: None, lambda: False)
        except ProviderError as e:
            srv.shutdown()
            assert "mock model exploded" in str(e)
            return "failure message surfaced"
        raise AssertionError("failure not reported")

    check("AI provider: job failure is reported", t_replicate_fail)

    def t_replicate_badkey():
        srv, _ = _mock_server(video_bytes, fail=False)
        rp.API = f"http://127.0.0.1:{srv.server_port}"
        os.environ["REPLICATE_API_TOKEN"] = "wrong"
        from .config import Config
        try:
            ReplicateProvider(Config()).run(JobRequest(clip, "a", "A", "p"), lambda m: None, lambda: False)
        except ProviderError as e:
            assert "rejected" in str(e)
            return "401 handled"
        finally:
            os.environ["REPLICATE_API_TOKEN"] = "test-key"
            srv.shutdown()
        raise AssertionError("bad key accepted")

    check("AI provider: wrong API key handled", t_replicate_badkey)

    def t_mapping():
        assert rp.intensity_to_mode(10) == "adhere_2" and rp.intensity_to_mode(50) == "flex_2"
        assert rp._fill({"a": ["{x}"]}, {"x": 5}) == {"a": ["5"]}

    check("Intensity->mode mapping and template fill", t_mapping)

    # ---------------- database / context -----------------------------------------
    def t_db():
        from .context import Ctx
        ctx = Ctx()
        ctx_box["ctx"] = ctx
        pid = ctx.db.add(name="Test", style="Japanese Anime", status="Processing", output_path=clip)
        ctx.db.update(pid, favorite=1, status="Completed")
        assert len(ctx.db.list("Test", "Favorites")) == 1
        assert len(ctx.db.list("zzz")) == 0
        ctx.db.delete(pid)
        return "add/update/search/filter/delete"

    check("SQLite project history", t_db)

    # ---------------- UI --------------------------------------------------------------
    def t_ui():
        from PySide6.QtWidgets import QApplication
        from .app import MainWindow, NAV
        ctx = ctx_box["ctx"]
        for dark in (True, False):
            ctx.cfg.set("theme", "dark" if dark else "light")
            win = MainWindow(ctx)
            win.show()
            for i, (_, name) in enumerate(NAV):
                win.go(i, animate=False)
                QApplication.processEvents()
                win.grab().save(os.path.join(shots, f"{'dark' if dark else 'light'}_{i}_{name.replace(' ', '_')}.png"))
            if dark:
                # real flow through the Studio page with the demo filter (no key => demo)
                os.environ.pop("REPLICATE_API_TOKEN", None)
                win.update_badge()
                assert win.studio.ctx.active_provider().is_demo
                win.studio.refresh_controls()
                assert win.studio.load_video(clip)
                assert win.studio.gen_b.isEnabled()
                win.studio.generate()
                for _ in range(400):
                    QApplication.processEvents()
                    if win.studio.output:
                        break
                    import time
                    time.sleep(0.05)
                assert win.studio.output, "demo generation did not finish"
                row = ctx.db.list()[0]
                assert row["status"] == "Completed" and row["is_demo"] == 1
                win.go(1, animate=False)
                QApplication.processEvents()
                win.grab().save(os.path.join(shots, "dark_studio_after_demo.png"))
                win.go(0, animate=False)
                win.go(4, animate=False)
                QApplication.processEvents()
                win.grab().save(os.path.join(shots, "dark_creations_with_item.png"))
                assert win.editor.open_video(clip)
                win.editor.add_overlay()
                os.environ["REPLICATE_API_TOKEN"] = "test-key"
            win.studio.shutdown()
            win.editor.shutdown()
            win.close()
        return f"7 screens x dark/light rendered, studio demo flow OK, screenshots in {shots}"

    check("UI: all screens render (dark + light) and Studio flow runs", t_ui)

    def t_ui_long():
        from PySide6.QtWidgets import QApplication
        from .app import MainWindow
        from .dialogs import TrimDialog
        ctx = ctx_box["ctx"]
        win = MainWindow(ctx)
        info = ff.probe(long_clip)
        d = TrimDialog(info, win)
        d.show()
        QApplication.processEvents()
        assert d.start.maximum() == int((info.duration - 10) * 10)
        d.player.clear()
        d.close()
        win.close()
        return "trim dialog opens for a 12 s video, start range correct"

    check("UI: trim dialog for >10 s video", t_ui_long)

    paths.clear_work()
    shutil.rmtree(tmp, ignore_errors=True)
    head = "CARTOON AI SELFTEST\n" + "=" * 60 + "\n"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(RESULTS) + f"\n\n{len(RESULTS) - FAILS} passed, {FAILS} failed\n")
    return 1 if FAILS else 0
