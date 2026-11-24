"""Cartoon AI entry point.  `Cartoon.exe --selftest [outdir]` runs a headless smoke test."""
from __future__ import annotations

import os
import sys
import traceback


def _selftest(outdir: str | None) -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["CARTOONAI_NO_AUDIO"] = "1"      # headless test: never touch sound devices
    lines: list[str] = []
    code = 0
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        from cartoon.context import Context
        from cartoon.media import make_sample_clip, probe, tmp_path, ffmpeg_exe
        from cartoon.providers.demo import DemoProvider
        from cartoon.ui.mainwindow import NAV, MainWindow

        lines.append("ffmpeg: " + ffmpeg_exe())
        ctx = Context()
        win = MainWindow(ctx)
        win.show()
        for i, (_ic, name) in enumerate(NAV):
            win.go(i)
            app.processEvents()
            pm = win.stack.currentWidget().grab()
            assert not pm.isNull(), "page did not render: " + name
            if outdir:
                os.makedirs(outdir, exist_ok=True)
                pm.save(os.path.join(outdir, f"{i}_{name.replace(' ', '_')}.png"))
            lines.append("page ok: " + name)
        clip = tmp_path(".mp4")
        make_sample_clip(clip)
        info = probe(clip)
        lines.append("probe ok: " + info.summary())
        out = DemoProvider().generate(clip, None, "", "", {}, lambda p, m: None, lambda: False)
        lines.append("demo generate ok: " + str(probe(out).duration) + " s")
        lines.append("SELFTEST PASSED")
    except Exception:
        code = 1
        lines.append("SELFTEST FAILED\n" + traceback.format_exc())
    text = "\n".join(lines)
    try:
        with open(os.path.join(outdir or os.getcwd(), "selftest_result.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass
    print(text)
    return code


def main() -> int:
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        return _selftest(sys.argv[i + 1] if len(sys.argv) > i + 1 else None)

    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Cartoon AI")
    try:
        from cartoon.context import Context
        from cartoon.media import ffmpeg_exe
        from cartoon.ui.mainwindow import MainWindow
        ffmpeg_exe()
        ctx = Context()
        win = MainWindow(ctx)
    except Exception as e:
        QMessageBox.critical(None, "Cartoon AI could not start", f"{e}\n\n{traceback.format_exc()[-1200:]}")
        return 1
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
