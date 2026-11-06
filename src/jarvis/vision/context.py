"""The validated handoff from raw screen perception to Jarvis's conversational model."""

from typing import Literal

from pydantic import BaseModel, Field

from jarvis.vision.screen_capture import ScreenCapture


class MonitorInspection(BaseModel):
    """Qwen3-VL's observations about one physical monitor."""

    monitor_index: int = Field(ge=1)
    image_size: tuple[int, int]
    screen_position: tuple[int, int]
    visual_analysis: str


class ScreenInspection(BaseModel):
    """Small, serializable context the text model can safely use to answer the user."""

    mode: Literal["active_window", "full_desktop"]
    question: str = Field(description="The user's question about the captured screen.")
    image_size: tuple[int, int] = Field(description="Screenshot width and height in pixels.")
    screen_position: tuple[int, int] = Field(
        description="Screenshot origin in virtual-desktop pixels."
    )
    monitor_count: int = Field(ge=1)
    active_window_title: str | None = None
    visual_analysis: str = Field(description="Qwen3-VL's observations about the screenshot.")
    monitors: list[MonitorInspection] = Field(default_factory=list)

    @classmethod
    def from_capture(cls, capture: ScreenCapture, *, question: str, visual_analysis: str):
        """Create the model-facing context without exposing the temporary image path."""
        return cls(
            mode=capture.mode,
            question=question,
            image_size=(capture.width, capture.height),
            screen_position=(capture.left, capture.top),
            monitor_count=capture.monitor_count,
            active_window_title=capture.window.title if capture.window else None,
            visual_analysis=visual_analysis,
        )

    @classmethod
    def from_monitor_captures(
        cls, captures: list[ScreenCapture], *, question: str, analyses: list[str]
    ):
        """Build a whole-desktop context from one independently analyzed image per monitor."""
        if len(captures) != len(analyses):
            raise ValueError("Each monitor capture must have exactly one visual analysis.")
        left = min(capture.left for capture in captures)
        top = min(capture.top for capture in captures)
        right = max(capture.left + capture.width for capture in captures)
        bottom = max(capture.top + capture.height for capture in captures)
        monitors = [
            MonitorInspection(
                monitor_index=capture.monitor_index or index,
                image_size=(capture.width, capture.height),
                screen_position=(capture.left, capture.top),
                visual_analysis=analysis,
            )
            for index, (capture, analysis) in enumerate(
                zip(captures, analyses, strict=True), start=1
            )
        ]
        return cls(
            mode="full_desktop",
            question=question,
            image_size=(right - left, bottom - top),
            screen_position=(left, top),
            monitor_count=len(captures),
            visual_analysis="Each monitor was analyzed separately; see monitors for observations.",
            monitors=monitors,
        )
