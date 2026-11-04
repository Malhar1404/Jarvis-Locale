"""The HUD color palette and stylesheet, kept separate from main_window.py so the look can be
swapped without touching any widget logic. Qt's stylesheet language is CSS-like but limited -
notably no box-shadow - so the glow around panels comes from QGraphicsDropShadowEffect in
main_window.py instead, not from this stylesheet.
"""

BG = "#05080f"
PANEL = "#0b1726"
BORDER = "#00c3e0"
ACCENT = "#00e5ff"
TEXT = "#bdf4ff"
MUTED = "#5c7a8a"
TOOL = "#ffb300"
OK = "#00e676"
ERROR = "#ff5252"
APPROVAL = "#e040fb"

MONO_FONT = 'Consolas, "Cascadia Mono", monospace'

STYLESHEET = f"""
QMainWindow, QWidget#central {{
    background-color: {BG};
}}
QLabel#title {{
    color: {ACCENT};
    font-size: 22px;
    font-weight: 600;
}}
QLabel#status {{
    color: {MUTED};
    font-size: 12px;
    font-family: {MONO_FONT};
}}
QScrollArea#timeline {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QWidget#timelineContent {{
    background-color: {PANEL};
}}
QLineEdit#inputLine {{
    background-color: {PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 10px;
    font-family: {MONO_FONT};
    font-size: 13px;
}}
QLineEdit#inputLine:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit#inputLine:disabled {{
    color: {MUTED};
    border-color: {MUTED};
}}
QPushButton#sendButton {{
    background-color: transparent;
    color: {ACCENT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 600;
}}
QPushButton#sendButton:hover {{
    background-color: rgba(0, 229, 255, 40);
    border-color: {ACCENT};
}}
QPushButton#sendButton:disabled {{
    color: {MUTED};
    border-color: {MUTED};
}}
QPushButton#approvalYes {{
    background-color: transparent;
    color: {OK};
    border: 1px solid {OK};
    border-radius: 4px;
    padding: 4px 18px;
    font-weight: 600;
}}
QPushButton#approvalYes:hover {{
    background-color: rgba(0, 230, 118, 40);
}}
QPushButton#approvalYes:disabled {{
    color: {MUTED};
    border-color: {MUTED};
}}
QPushButton#approvalNo {{
    background-color: transparent;
    color: {ERROR};
    border: 1px solid {ERROR};
    border-radius: 4px;
    padding: 4px 18px;
    font-weight: 600;
}}
QPushButton#approvalNo:hover {{
    background-color: rgba(255, 82, 82, 40);
}}
QPushButton#approvalNo:disabled {{
    color: {MUTED};
    border-color: {MUTED};
}}
QStatusBar {{
    background-color: {BG};
    border-top: 1px solid {BORDER};
    color: {MUTED};
    font-family: {MONO_FONT};
    font-size: 12px;
}}
QStatusBar QLabel {{
    color: {MUTED};
    font-family: {MONO_FONT};
    font-size: 12px;
    padding: 2px 8px;
}}
QStatusBar::item {{
    border: none;
}}
"""
