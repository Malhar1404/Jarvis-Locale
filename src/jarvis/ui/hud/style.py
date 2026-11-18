"""HUD colours, fonts and the Qt stylesheet - kept apart from widget code so the look can change
without touching behaviour (same idea as ui/theme.py, which the old window uses).

Note: these rules only use object names and widget types, never "QWidget#hud QLabel"-style
descendant rules. A descendant rule with an ID beats a plain "QLabel#name" rule in Qt's
specificity math, which would silently override every per-label colour below.
"""

from PySide6.QtGui import QColor

from jarvis.ui import theme

TEXT_DIM = "#8fb3c2"  # brighter than theme.MUTED so small labels stay readable on the dark bg
TITLE_FONT = "Bahnschrift"  # ships with Windows 10/11: squared, technical, nothing to bundle
BODY_FONT = "Segoe UI"
MONO = theme.MONO_FONT
# Mostly opaque: a hint of the grid shows through, but text on a panel behind never does.
PANEL_BG = "rgba(9, 20, 34, 236)"
EDGE_MARGIN = 40  # px between the screen edge and the top bar / panels

# Arc reactor colour per state. "speaking" is detected from the voice itself (see reactor.py).
STATE_COLORS = {
    "idle": "#4f8a9c",
    "listening": theme.ACCENT,
    "thinking": theme.TOOL,
    "speaking": theme.ACCENT,
    "waiting": theme.APPROVAL,
}
STATE_LABELS = {
    "idle": "STANDBY",
    "listening": "LISTENING",
    "thinking": "THINKING",
    "speaking": "SPEAKING",
    "waiting": "AWAITING APPROVAL",
}

TIER_COLORS = {
    "auto": theme.OK,
    "ask_once": theme.TOOL,
    "always_ask": theme.APPROVAL,
    "never": theme.ERROR,
}
TIER_LABELS = {
    "auto": "AUTO",
    "ask_once": "ASK ONCE",
    "always_ask": "ALWAYS ASK",
    "never": "NEVER",
}


def rgba(hex_color: str, alpha: int) -> str:
    """'#00e5ff', 64 -> 'rgba(0, 229, 255, 64)' for stylesheets that need a see-through colour."""
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


STYLESHEET = f"""
QLabel {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QWidget#scrollContent {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {rgba(theme.ACCENT, 70)}; border-radius: 3px; min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QToolTip {{
    color: {theme.TEXT}; background-color: {theme.PANEL}; border: 1px solid {theme.BORDER};
}}

QLabel#hudTitle {{
    color: {theme.ACCENT}; font-family: "{TITLE_FONT}"; font-size: 22px; font-weight: 700;
}}
QLabel#hudStatus, QLabel#hudDate {{ color: {TEXT_DIM}; font-family: {MONO}; font-size: 12px; }}
QLabel#hudOnlineDot {{ color: {theme.OK}; font-size: 12px; }}
QLabel#hudCamera {{
    color: {theme.ERROR}; font-family: {MONO}; font-size: 12px; font-weight: 600;
}}
QLabel#hudClock {{ color: {theme.TEXT}; font-family: "{TITLE_FONT}"; font-size: 20px; }}
QPushButton#topButton {{
    background: transparent; color: {TEXT_DIM}; border: 1px solid transparent;
    border-radius: 6px; font-size: 16px; min-width: 32px; min-height: 32px;
}}
QPushButton#topButton:hover {{ border-color: {rgba(theme.ACCENT, 110)}; color: {theme.TEXT}; }}

QLabel#reactorState {{
    font-family: "{TITLE_FONT}"; font-size: 17px; font-weight: 600;
}}
QLabel#reactorCaption {{ color: {TEXT_DIM}; font-size: 13px; }}

QFrame#hudDock {{
    background-color: rgba(9, 20, 34, 220);
    border: 1px solid {rgba(theme.ACCENT, 64)};
    border-radius: 12px;
}}
QFrame#dockDivider {{ background: {rgba(theme.ACCENT, 64)}; border: none; }}
QPushButton#dockButton, QPushButton#dockInteractive {{
    background-color: transparent; color: {TEXT_DIM};
    border: 1px solid {rgba(theme.ACCENT, 64)}; border-radius: 8px;
    padding: 8px 14px; font-family: {MONO}; font-size: 12px;
}}
QPushButton#dockButton:hover, QPushButton#dockInteractive:hover {{ border-color: {theme.ACCENT}; }}
QPushButton#dockButton:checked {{
    background-color: {rgba(theme.ACCENT, 36)}; color: {theme.TEXT}; border-color: {theme.ACCENT};
}}
QPushButton#dockInteractive:checked {{
    background-color: {rgba(theme.ERROR, 40)}; color: {theme.TEXT}; border-color: {theme.ERROR};
}}

QPushButton#panelHide {{
    background: transparent; color: {TEXT_DIM}; border: 1px solid transparent;
    border-radius: 6px; font-size: 15px; min-width: 28px; min-height: 26px;
}}
QPushButton#panelHide:hover {{ border-color: {rgba(theme.ACCENT, 110)}; color: {theme.TEXT}; }}
QLabel#panelSubtitle {{ color: {TEXT_DIM}; font-family: {MONO}; font-size: 11px; }}

QLabel#bubbleUser {{
    color: {theme.TEXT}; background-color: {rgba(theme.ACCENT, 30)};
    border: 1px solid {rgba(theme.ACCENT, 80)}; border-radius: 10px; padding: 8px 11px;
    font-size: 13px;
}}
QLabel#bubbleName {{
    color: {theme.ACCENT}; font-family: {MONO}; font-size: 11px; font-weight: 600;
}}
QLabel#bubbleJarvis {{ color: {theme.TEXT}; font-size: 13px; }}
QLabel#bubbleNote {{ color: {TEXT_DIM}; font-family: {MONO}; font-size: 11px; }}
QLabel#bubbleError {{ color: {theme.ERROR}; font-family: {MONO}; font-size: 12px; }}
QLineEdit#commsInput {{
    background-color: rgba(5, 8, 15, 180); color: {theme.TEXT};
    border: 1px solid {rgba(theme.ACCENT, 90)}; border-radius: 8px;
    padding: 0 10px; min-height: 40px; font-family: {MONO}; font-size: 12px;
}}
QLineEdit#commsInput:focus {{ border-color: {theme.ACCENT}; }}
QLineEdit#commsInput:disabled {{ color: {TEXT_DIM}; border-color: {rgba(theme.MUTED, 120)}; }}
QPushButton#commsMic {{
    background: transparent; color: {theme.ACCENT}; border: 1px solid {theme.ACCENT};
    border-radius: 8px; min-width: 52px; min-height: 40px; font-family: {MONO};
    font-size: 11px; font-weight: 600;
}}
QPushButton#commsMic[recording="true"] {{
    background: {theme.ERROR}; color: {theme.BG}; border-color: {theme.ERROR};
}}
QPushButton#commsSend {{
    background: {theme.ACCENT}; color: {theme.BG}; border: 1px solid {theme.ACCENT};
    border-radius: 8px; min-width: 60px; min-height: 40px; font-family: {MONO};
    font-size: 11px; font-weight: 700;
}}
QPushButton#commsMic:disabled, QPushButton#commsSend:disabled {{
    background: transparent; color: {theme.MUTED}; border-color: {theme.MUTED};
}}

QLabel#mindTitle {{ font-family: {MONO}; font-size: 11px; font-weight: 600; }}
QLabel#mindMeta, QLabel#mindFooter, QLabel#thumbCaption {{
    color: {TEXT_DIM}; font-family: {MONO}; font-size: 11px;
}}
QLabel#mindText {{ color: {theme.TEXT}; font-size: 12px; }}
QLabel#mindMono {{ color: {theme.TEXT}; font-family: {MONO}; font-size: 12px; }}
QLabel#mindBox {{
    color: #cdeef7; background-color: {rgba(theme.ACCENT, 16)};
    border: 1px solid {rgba(theme.ACCENT, 56)}; border-radius: 6px; padding: 7px 9px;
    font-size: 12px;
}}
QLabel#thumb {{ border: 1px solid {rgba(theme.ACCENT, 140)}; border-radius: 4px; }}

QLabel#vitalName, QLabel#vitalValue {{ color: {TEXT_DIM}; font-family: {MONO}; font-size: 12px; }}
QLabel#vitalValue {{ color: {theme.TEXT}; }}
QLabel#legend {{ color: {TEXT_DIM}; font-family: {MONO}; font-size: 10px; }}

QLabel#approvalHeadline {{ color: {theme.TEXT}; font-size: 14px; }}
QLabel#approvalArgs {{ color: #d9c2e0; font-family: {MONO}; font-size: 12px; }}
QLabel#approvalTier {{
    color: #f08cff; border: 1px solid {theme.APPROVAL}; border-radius: 4px;
    padding: 2px 8px; font-family: {MONO}; font-size: 10px;
}}
QPushButton#approvalAllow, QPushButton#approvalDeny {{
    border-radius: 8px; min-height: 40px; font-weight: 600; font-size: 13px;
}}
QPushButton#approvalAllow {{
    background: {theme.APPROVAL}; color: #1a0420; border: 1px solid {theme.APPROVAL};
}}
QPushButton#approvalDeny {{
    background: transparent; color: #f08cff; border: 1px solid {rgba(theme.APPROVAL, 160)};
}}
QPushButton#approvalAllow:disabled, QPushButton#approvalDeny:disabled {{
    background: transparent; color: {theme.MUTED}; border-color: {theme.MUTED};
}}
"""
