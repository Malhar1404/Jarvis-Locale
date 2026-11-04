"""The right-hand sidebar: every tool the agent can call, with whichever one is currently
running highlighted. Purely a display - it never calls a tool itself.
"""

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget


class ToolsPanel(QScrollArea):
    def __init__(self, tool_names: list[str]) -> None:
        super().__init__()
        self.setObjectName("toolsPanel")
        self.setWidgetResizable(True)
        self.setFixedWidth(220)

        content = QWidget(objectName="toolsPanelContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        heading = QLabel("TOOLS")
        heading.setObjectName("toolsPanelHeading")
        layout.addWidget(heading)

        self._rows: dict[str, QLabel] = {}
        for name in tool_names:
            row = QLabel(name)
            row.setObjectName("toolRow")
            row.setProperty("active", False)
            row.setWordWrap(True)
            layout.addWidget(row)
            self._rows[name] = row

        layout.addStretch()
        self.setWidget(content)

    def set_active(self, name: str | None) -> None:
        for tool_name, row in self._rows.items():
            is_active = tool_name == name
            if row.property("active") == is_active:
                continue
            row.setProperty("active", is_active)
            style = row.style()
            style.unpolish(row)
            style.polish(row)
