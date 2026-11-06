"""The validated handoff from raw screen perception to Jarvis's conversational model."""

from typing import Literal

from pydantic import BaseModel, Field

from jarvis.vision.screen_capture import ScreenCapture


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
