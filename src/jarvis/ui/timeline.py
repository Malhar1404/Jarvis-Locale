"""A scrollable, top-to-bottom list of cards - the live activity timeline. A QVBoxLayout can only
grow downward, so we keep one trailing stretch at the bottom and always insert new cards just
above it, which is what keeps everything pinned to the top with blank space absorbed below.
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget


class Timeline(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("timeline")
        self.setWidgetResizable(True)

        content = QWidget(objectName="timelineContent")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(8)
        self._layout.addStretch()
        self.setWidget(content)

    def add(self, widget: QWidget) -> None:
        self._layout.insertWidget(self._layout.count() - 1, widget)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def remove(self, widget: QWidget) -> None:
        self._layout.removeWidget(widget)
        widget.deleteLater()

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
