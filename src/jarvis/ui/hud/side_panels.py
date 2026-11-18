"""The smaller panel bodies: Vitals (live system stats), Tools (every tool + its risk tier) and
the Approval pop-up.
"""

import gc
import subprocess
import sys
import threading
from html import escape

import psutil
from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jarvis.ui import theme
from jarvis.ui.hud.style import MONO, TIER_COLORS, TIER_LABELS, rgba

# ---------------------------------------------------------------------------------- Vitals

SAMPLE_SECONDS = 2.0


class VitalsSampler:
    """Reads system stats on a background thread every couple of seconds.

    Why a thread: brightness goes through WMI and VRAM through `nvidia-smi`, and either can take
    100+ ms - long enough to stutter the reactor's 60 fps if done on the UI thread. Same
    "thread writes, UI timer reads" pattern as AudioLevel: `values` is replaced as a whole dict,
    so the UI never sees a half-updated one.
    """

    def __init__(self) -> None:
        self.values: dict[str, tuple[float, str] | None] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._has_nvidia_smi = True

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)  # let _run's COM cleanup finish before Python exits
            self._thread = None

    def _run(self) -> None:
        # Imported here: these modules touch Windows COM/WMI, only needed on this thread.
        import pythoncom

        from jarvis.tools.brightness import get_brightness
        from jarvis.tools.volume import get_volume

        # COM objects (brightness goes through WMI) belong to the thread that made them. Without
        # our own init + cleanup, they get released at exit after this thread is gone, and
        # Windows prints "Win32 exception occurred releasing IUnknown" for each one.
        pythoncom.CoInitialize()
        try:
            psutil.cpu_percent(None)  # the first call only starts the measurement
            while not self._stop.wait(SAMPLE_SECONDS):
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(None)
                self.values = {
                    "CPU": (cpu / 100, f"{cpu:.0f}%"),
                    "RAM": (
                        memory.percent / 100,
                        f"{memory.used / 2**30:.1f} / {memory.total / 2**30:.0f} GB",
                    ),
                    "VRAM": self._vram(),
                    "VOLUME": _percent(get_volume),
                    "BRIGHT": _percent(get_brightness),
                }
        finally:
            gc.collect()  # release this thread's COM objects *now*, while COM is still up
            pythoncom.CoUninitialize()

    def _vram(self) -> tuple[float, str] | None:
        if not self._has_nvidia_smi:
            return None
        try:
            out = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                # Without this flag Windows flashes a console window every 2 seconds.
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            ).stdout
            used, total = (float(part) for part in out.splitlines()[0].split(","))
        except FileNotFoundError:
            self._has_nvidia_smi = False  # no NVIDIA driver tools - stop trying
            return None
        except (ValueError, IndexError, subprocess.SubprocessError, OSError):
            return None
        return used / total, f"{used / 1024:.1f} / {total / 1024:.0f} GB"


def _percent(tool) -> tuple[float, str] | None:
    try:
        value = int(tool.invoke({}))
    except Exception:  # noqa: BLE001 - a missing device just shows "n/a"
        return None
    return value / 100, f"{value}%"


class _Bar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(6)
        self.value = 0.0

    def set_value(self, value: float) -> None:
        self.value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ARG002
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 229, 255, 30))
        p.drawRoundedRect(QRectF(self.rect()), 3, 3)
        if self.value > 0:
            color = QColor(theme.TOOL if self.value > 0.85 else theme.ACCENT)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(0, 0, self.width() * self.value, self.height()), 3, 3)
        p.end()


class VitalsView(QWidget):
    NAMES = ["CPU", "RAM", "VRAM", "VOLUME", "BRIGHT"]

    def __init__(self, sampler: VitalsSampler) -> None:
        super().__init__()
        self._sampler = sampler
        grid = QGridLayout(self)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        self._rows: dict[str, tuple[_Bar, QLabel]] = {}
        for row, name in enumerate(self.NAMES):
            bar = _Bar()
            value = QLabel("…", objectName="vitalValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setMinimumWidth(96)
            grid.addWidget(QLabel(name, objectName="vitalName"), row, 0)
            grid.addWidget(bar, row, 1)
            grid.addWidget(value, row, 2)
            self._rows[name] = (bar, value)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)

    def _refresh(self) -> None:
        values = self._sampler.values
        if not values:
            return
        for name, (bar, label) in self._rows.items():
            sample = values.get(name)
            if sample is None:
                bar.set_value(0)
                label.setText("n/a")
            else:
                bar.set_value(sample[0])
                label.setText(sample[1])


# ----------------------------------------------------------------------------------- Tools

_TIER_ORDER = ["auto", "ask_once", "always_ask", "never"]


def _chip_style(color: str, active: bool) -> str:
    base = f"border: 1px solid {color}; border-radius: 5px; padding: 4px 8px; font-family: {MONO};"
    base += " font-size: 11px;"
    if active:
        return base + f" background: {color}; color: {theme.BG}; font-weight: 700;"
    return base + f" background: {rgba(color, 18)}; color: {color};"


class ToolsView(QWidget):
    """Every tool, coloured by risk tier; the one running right now is filled in."""

    def __init__(self, tool_tiers: dict[str, str]) -> None:
        super().__init__()
        self._tiers = tool_tiers
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(6)
        ordered = sorted(tool_tiers, key=lambda n: (_TIER_ORDER.index(tool_tiers[n]), n))
        self._chips: dict[str, QLabel] = {}
        for index, name in enumerate(ordered):
            chip = QLabel(name)
            chip.setStyleSheet(_chip_style(TIER_COLORS[tool_tiers[name]], False))
            grid.addWidget(chip, index // 2, index % 2)
            self._chips[name] = chip
        layout.addLayout(grid)
        layout.addStretch()

        legend = QHBoxLayout()
        legend.setSpacing(14)
        for tier in ("auto", "ask_once", "always_ask"):
            label = QLabel(f"■ {TIER_LABELS[tier]}", objectName="legend")
            label.setStyleSheet(f"color: {TIER_COLORS[tier]};")
            legend.addWidget(label)
        legend.addStretch()
        layout.addLayout(legend)

    def set_active(self, name: str | None) -> None:
        for tool_name, chip in self._chips.items():
            chip.setStyleSheet(_chip_style(TIER_COLORS[self._tiers[tool_name]], tool_name == name))


# -------------------------------------------------------------------------------- Approval


class ApprovalView(QWidget):
    """The body of the pop-up shown while the graph is paused on an ApprovalRequest."""

    decided = Signal(str)  # "yes" or "no" - the exact strings Agent.resume() expects

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        top = QHBoxLayout()
        self._headline = QLabel(objectName="approvalHeadline")
        self._headline.setTextFormat(Qt.TextFormat.RichText)
        self._tier = QLabel(objectName="approvalTier")
        top.addWidget(self._headline, 1)
        top.addWidget(self._tier)
        self._args = QLabel(objectName="approvalArgs")
        self._args.setTextFormat(Qt.TextFormat.PlainText)
        self._args.setWordWrap(True)

        self._allow = QPushButton("Allow", objectName="approvalAllow")
        self._deny = QPushButton("Deny", objectName="approvalDeny")
        self._allow.clicked.connect(lambda: self._decide("yes"))
        self._deny.clicked.connect(lambda: self._decide("no"))
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addWidget(self._allow)
        buttons.addWidget(self._deny)

        layout.addLayout(top)
        layout.addWidget(self._args)
        layout.addStretch()
        layout.addLayout(buttons)

    def show_request(self, name: str, args: dict, tier: str) -> None:
        self._headline.setText(f'Jarvis wants to run <b style="color:#f08cff">{escape(name)}</b>')
        self._tier.setText(TIER_LABELS.get(tier, tier.upper()))
        self._args.setText(", ".join(f"{k}={v!r}" for k, v in args.items()) or "(no arguments)")
        self._allow.setEnabled(True)
        self._deny.setEnabled(True)

    def _decide(self, decision: str) -> None:
        self._allow.setEnabled(False)
        self._deny.setEnabled(False)
        self.decided.emit(decision)
