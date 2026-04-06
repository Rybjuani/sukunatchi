from __future__ import annotations

import time
from dataclasses import dataclass

from .constants import ANIMATION_INTERVALS_MS, NON_LOOPING_ANIMATIONS


@dataclass
class AnimationDecision:
    name: str
    loop: bool
    interval_ms: int


class AnimationClock:
    def __init__(self) -> None:
        self._current = ""
        self._started_at = time.monotonic()

    def frame_index(self, animation_name: str, frame_count: int, interval_ms: int, loop: bool) -> int:
        if frame_count <= 1:
            self._current = animation_name
            return 0
        if animation_name != self._current:
            self._current = animation_name
            self._started_at = time.monotonic()
            return 0

        elapsed_ms = int((time.monotonic() - self._started_at) * 1000)
        frame = elapsed_ms // max(1, interval_ms)
        if loop:
            return frame % frame_count
        return min(frame_count - 1, frame)


def choose_animation(state: object, transient_animation: str | None) -> AnimationDecision:
    if not getattr(state, "alive"):
        name = "dead"
    elif transient_animation:
        name = transient_animation
    elif getattr(state, "stage") == "egg":
        name = "egg"
    elif getattr(state, "asleep"):
        name = "lights_off" if getattr(state, "lights_off") else "sleep"
    elif getattr(state, "sick"):
        name = "sick"
    elif getattr(state, "attention"):
        name = "attention"
    elif getattr(state, "poop_count") > 0:
        name = "poop"
    else:
        name = "idle"

    return AnimationDecision(
        name=name,
        loop=name not in NON_LOOPING_ANIMATIONS,
        interval_ms=ANIMATION_INTERVALS_MS.get(name, 240),
    )
