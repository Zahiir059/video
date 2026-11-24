PURPLE = "#5425D6"
VIOLET = "#8B5CF6"
BLUE = "#3B82F6"
CYAN = "#22D3EE"
PINK = "#EC4899"


def colors(dark: bool) -> dict:
    if dark:
        return dict(bg="#10111B", card="#1C1D2B", text="#FFFFFF", sub="#A9A8C0",
                    border="#2B2D42", input="#14151F", side="#0C0D15", hover="#26283B")
    return dict(bg="#F4F2FF", card="#FFFFFF", text="#1B1633", sub="#5B5878",
                border="#E2DDF5", input="#F1EEFB", side="#FFFFFF", hover="#ECE8FB")


def stylesheet(dark: bool) -> str:
    c = colors(dark)
    grad = f"qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {PURPLE}, stop:1 {VIOLET})"
    grad2 = f"qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {VIOLET}, stop:1 {PINK})"
    return f"""
* {{ font-family: "Segoe UI", "Inter", "Noto Sans", "DejaVu Sans", sans-serif; font-size: 13px; }}
QMainWindow, QDialog, QWidget#Page, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {c['bg']}; color: {c['text']}; }}
QLabel {{ color: {c['text']}; background: transparent; }}
QLabel#Heading {{ font-size: 24px; font-weight: 700; }}
QLabel#SubHeading {{ font-size: 17px; font-weight: 700; }}
QLabel#Sub {{ color: {c['sub']}; }}
QLabel#Chip {{ border-radius: 10px; padding: 3px 10px; font-weight: 600; background: {c['hover']}; }}
QLabel#ChipOk {{ border-radius: 10px; padding: 3px 10px; font-weight: 600; background: #14532D; color: #BBF7D0; }}
QLabel#ChipWarn {{ border-radius: 10px; padding: 3px 10px; font-weight: 600; background: #7C2D12; color: #FED7AA; }}
QLabel#ChipBad {{ border-radius: 10px; padding: 3px 10px; font-weight: 600; background: #7F1D1D; color: #FECACA; }}
QLabel#DemoBadge {{ border-radius: 12px; padding: 5px 12px; font-weight: 700; color: white; background: {PINK}; }}
QLabel#LiveBadge {{ border-radius: 12px; padding: 5px 12px; font-weight: 700; color: white; background: #16A34A; }}
QLabel#Drop {{ border: 2px dashed {VIOLET}; border-radius: 16px; color: {c['sub']}; padding: 18px; background: {c['input']}; }}
QFrame#Sidebar {{ background: {c['side']}; border-right: 1px solid {c['border']}; }}
QFrame#Header {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}
QFrame#Card {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 16px; }}
QFrame#CardSel {{ background: {c['card']}; border: 2px solid {CYAN}; border-radius: 16px; }}
QPushButton {{ background: {c['hover']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 8px 16px; }}
QPushButton:hover {{ border-color: {VIOLET}; }}
QPushButton:disabled {{ color: {c['sub']}; background: {c['input']}; }}
QPushButton#Primary {{ background: {grad}; color: white; border: none; font-weight: 700; padding: 11px 24px; border-radius: 12px; }}
QPushButton#Primary:hover {{ background: {grad2}; }}
QPushButton#Primary:disabled {{ background: {c['hover']}; color: {c['sub']}; }}
QPushButton#Hero {{ background: white; color: {PURPLE}; border: none; font-weight: 800; font-size: 15px; padding: 13px 28px; border-radius: 14px; }}
QPushButton#Hero:hover {{ background: #F0E9FF; }}
QPushButton#Icon {{ background: transparent; border: none; font-size: 18px; padding: 6px 10px; border-radius: 10px; }}
QPushButton#Icon:hover {{ background: {c['hover']}; }}
QPushButton#NavButton {{ text-align: left; padding: 12px 16px; border: none; border-radius: 12px; background: transparent; color: {c['sub']}; font-size: 14px; font-weight: 600; border-left: 4px solid transparent; }}
QPushButton#NavButton:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#NavButton:checked {{ background: {grad}; color: white; border-left: 4px solid {CYAN}; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {c['input']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 7px 10px; selection-background-color: {VIOLET}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 1px solid {VIOLET}; }}
QComboBox QAbstractItemView {{ background: {c['card']}; color: {c['text']}; selection-background-color: {VIOLET}; border: 1px solid {c['border']}; }}
QSlider::groove:horizontal {{ height: 6px; background: {c['border']}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {grad}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: white; border: 2px solid {VIOLET}; width: 14px; height: 14px; margin: -6px 0; border-radius: 9px; }}
QProgressBar {{ background: {c['input']}; border: none; border-radius: 6px; height: 10px; text-align: center; }}
QProgressBar::chunk {{ background: {grad2}; border-radius: 6px; }}
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 12px; background: {c['card']}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {c['sub']}; padding: 9px 14px; border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: 600; }}
QTabBar::tab:selected {{ color: {c['text']}; background: {c['card']}; border: 1px solid {c['border']}; border-bottom: none; }}
QCheckBox, QRadioButton {{ color: {c['text']}; spacing: 8px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; min-width: 30px; }}
QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {VIOLET}; padding: 4px; }}
QMessageBox, QProgressDialog {{ background: {c['bg']}; }}
"""
