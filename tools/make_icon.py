"""Creates assets/cartoon.ico from the in-app logo (run during the build)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from cartoon_ai import art  # noqa: E402

app = QGuiApplication([])
os.makedirs("assets", exist_ok=True)
ok = art.logo_pixmap(256).save("assets/cartoon.ico", "ICO")
print("icon written" if ok else "icon NOT written (build continues without it)")
