from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from .constants import HATCH_MINUTES, MENU_ITEMS, STAGE_ORDER, STAGE_THRESHOLDS


def now_local() -> datetime:
    return datetime.now().astimezone()


def clamp(value: int, lower: int = 0, upper: int = 100) -> int:
    return max(lower, min(upper, value))


def parse_dt(raw: str | None, fallback: datetime | None = None) -> datetime:
    if not raw:
        return fallback or now_local()
    return datetime.fromisoformat(raw)


def iso(dt: datetime) -> str:
    return dt.astimezone().isoformat(timespec="seconds")


@dataclass
class PetState:
    created_at: str
    last_update: str
    stage: str = "egg"
    age_minutes: int = 0
    stage_minutes: int = 0
    hunger: int = 82
    happiness: int = 78
    health: int = 100
    discipline: int = 42
    sick: bool = False
    asleep: bool = False
    lights_off: bool = False
    poop_count: int = 0
    alive: bool = True
    attention: bool = False
    attention_reason: str = ""
    pending_discipline: bool = False
    neglect_points: int = 0
    snack_abuse: int = 0
    transient_animation: str = ""
    animation_until: str = ""
    message: str = ""
    message_until: str = ""
    last_action: str = ""

    @classmethod
    def fresh(cls, now: datetime | None = None) -> "PetState":
        current = now or now_local()
        return cls(created_at=iso(current), last_update=iso(current))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PetState":
        base = cls.fresh()
        values = asdict(base)
        values.update(payload)
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def level(self) -> int:
        if self.stage == "egg":
            return 1
        base = 1 + (self.age_minutes // 24)
        care_bonus = max(0, (self.hunger + self.happiness + self.health + self.discipline - 280) // 55)
        return min(99, base + care_bonus)

    @property
    def stage_index(self) -> int:
        return STAGE_ORDER.index(self.stage)

    @property
    def display_age(self) -> str:
        hours, minutes = divmod(self.age_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"


class PetGame:
    def __init__(self, state: PetState | None = None) -> None:
        self.state = state or PetState.fresh()

    def serialize(self) -> dict[str, Any]:
        return self.state.to_dict()

    def reset(self, current: datetime | None = None) -> None:
        self.state = PetState.fresh(current)

    def tick(self, current: datetime | None = None) -> bool:
        now = current or now_local()
        changed = self._expire_transients(now)
        last_update = parse_dt(self.state.last_update, now)
        elapsed_minutes = int((now - last_update).total_seconds() // 60)
        if elapsed_minutes <= 0:
            self._refresh_attention(now)
            return changed

        for minute in range(elapsed_minutes):
            self._advance_one_minute(last_update + timedelta(minutes=minute + 1))
            changed = True

        self.state.last_update = iso(last_update + timedelta(minutes=elapsed_minutes))
        self._expire_transients(now)
        self._refresh_attention(now)
        return changed

    def perform(self, action: str, current: datetime | None = None) -> bool:
        now = current or now_local()
        self.tick(now)

        if not self.state.alive:
            if action == "RESET":
                self.reset(now)
                self._set_message("NEW EGG", now, 5)
                return True
            self._set_message("GAME OVER", now, 4)
            return True

        if action == "STATUS":
            self._set_message("STATUS", now, 3)
            return True

        if self.state.stage == "egg" and action not in {"STATUS"}:
            self._set_message("WAIT", now, 3)
            return True

        if self.state.asleep and action not in {"LIGHT", "MED", "CLEAN"}:
            self._set_message("ZZZ", now, 3)
            return True

        if action == "MEAL":
            self.state.hunger = clamp(self.state.hunger + 34)
            self.state.health = clamp(self.state.health + 5)
            self.state.last_action = action
            self._set_animation("meal", now, 4)
            self._set_message("MEAL", now, 3)
        elif action == "SNACK":
            self.state.happiness = clamp(self.state.happiness + 22)
            self.state.hunger = clamp(self.state.hunger + 6)
            self.state.snack_abuse += 1
            if self.state.snack_abuse > 2:
                self.state.health = clamp(self.state.health - 7)
                self.state.discipline = clamp(self.state.discipline - 4)
            self.state.last_action = action
            self._set_animation("snack", now, 4)
            self._set_message("SNACK", now, 3)
        elif action == "GAME":
            self.state.happiness = clamp(self.state.happiness + 24)
            self.state.discipline = clamp(self.state.discipline + 4)
            self.state.hunger = clamp(self.state.hunger - 4)
            self.state.last_action = action
            self._set_animation("play", now, 4)
            self._set_message("GAME", now, 3)
        elif action == "CLEAN":
            if self.state.poop_count > 0:
                self.state.poop_count = 0
                self.state.health = clamp(self.state.health + 4)
                self._set_animation("clean", now, 4)
                self._set_message("CLEAN", now, 3)
            else:
                self._set_message("CLEAR", now, 3)
        elif action == "MED":
            if self.state.sick:
                self.state.sick = False
                self.state.health = clamp(self.state.health + 18)
                self._set_animation("medicine", now, 4)
                self._set_message("MED OK", now, 3)
            else:
                self._set_message("FINE", now, 3)
        elif action == "DISC":
            if self.state.pending_discipline:
                self.state.pending_discipline = False
                self.state.discipline = clamp(self.state.discipline + 14)
                self.state.happiness = clamp(self.state.happiness - 5)
                self._set_animation("discipline", now, 4)
                self._set_message("DISC", now, 3)
            else:
                self.state.happiness = clamp(self.state.happiness - 8)
                self._set_message("NO CALL", now, 3)
        elif action == "LIGHT":
            if self.state.asleep:
                self.state.lights_off = True
                self._set_animation("lights_off", now, 4)
                self._set_message("LIGHT OFF", now, 3)
            else:
                self._set_message("AWAKE", now, 3)

        self._refresh_attention(now)
        return True

    def status_rows(self) -> tuple[str, ...]:
        hearts = lambda value: max(0, min(4, round(value / 25)))
        return (
            f"HUN {hearts(self.state.hunger)}/4   JOY {hearts(self.state.happiness)}/4",
            f"HLT {hearts(self.state.health)}/4   DIS {hearts(self.state.discipline)}/4",
            f"POOP {self.state.poop_count}     AGE {self.state.display_age}",
            f"LV  {self.state.level:02d}     STG {self.state.stage.upper()}",
        )

    def _advance_one_minute(self, current: datetime) -> None:
        if not self.state.alive:
            return

        self.state.age_minutes += 1
        self.state.stage_minutes += 1

        should_sleep = self._is_sleep_time(current)
        if self.state.stage != "egg":
            if should_sleep and not self.state.asleep:
                self.state.asleep = True
                self.state.lights_off = False
            elif not should_sleep and self.state.asleep:
                self.state.asleep = False
                self.state.lights_off = False

        if self.state.stage == "egg":
            if self.state.age_minutes >= HATCH_MINUTES:
                self.state.stage = "baby"
                self.state.stage_minutes = 0
                self._set_animation("hatch", current, 7)
                self._set_message("BORN", current, 5)
            return

        hunger_rate = {"baby": 1, "child": 1, "teen": 2, "adult": 2}.get(self.state.stage, 1)
        joy_rate = {"baby": 1, "child": 1, "teen": 1, "adult": 2}.get(self.state.stage, 1)

        if self.state.age_minutes % 5 == 0:
            self.state.hunger = clamp(self.state.hunger - hunger_rate)
        if self.state.age_minutes % 7 == 0:
            self.state.happiness = clamp(self.state.happiness - joy_rate)
        if self.state.age_minutes % 18 == 0 and self.state.poop_count < 4:
            self.state.poop_count += 1
        if self.state.age_minutes % 12 == 0 and self.state.snack_abuse > 0:
            self.state.snack_abuse -= 1

        if self.state.poop_count > 0 and self.state.age_minutes % 6 == 0:
            self.state.happiness = clamp(self.state.happiness - self.state.poop_count)
        if self.state.poop_count >= 2 and self.state.age_minutes % 8 == 0:
            self.state.sick = True
        if self.state.hunger <= 25 and self.state.age_minutes % 4 == 0:
            self.state.health = clamp(self.state.health - 3)
        if self.state.happiness <= 25 and self.state.age_minutes % 5 == 0:
            self.state.health = clamp(self.state.health - 2)
        if self.state.sick and self.state.age_minutes % 4 == 0:
            self.state.health = clamp(self.state.health - 4)
        if self.state.pending_discipline and self.state.age_minutes % 6 == 0:
            self.state.discipline = clamp(self.state.discipline - 3)
            self.state.happiness = clamp(self.state.happiness - 2)
        if self.state.asleep and not self.state.lights_off and self.state.age_minutes % 3 == 0:
            self.state.health = clamp(self.state.health - 2)
            self.state.happiness = clamp(self.state.happiness - 2)

        if (
            self.state.stage in {"child", "teen", "adult"}
            and not self.state.pending_discipline
            and not self.state.sick
            and not self.state.asleep
            and self.state.hunger > 35
            and self.state.happiness > 35
            and self.state.age_minutes % 27 == 0
        ):
            self.state.pending_discipline = True

        if self._is_neglected() and self.state.age_minutes % 9 == 0:
            self.state.neglect_points += 1
        if self.state.health <= 0 or self.state.neglect_points >= 12:
            self._die(current)
            return

        self._maybe_evolve(current)

    def _maybe_evolve(self, current: datetime) -> None:
        threshold = None
        next_stage = None
        if self.state.stage == "baby":
            threshold = STAGE_THRESHOLDS["baby"] + (8 if self.state.neglect_points > 2 else 0)
            next_stage = "child"
        elif self.state.stage == "child":
            threshold = STAGE_THRESHOLDS["child"] + (10 if self.state.discipline < 35 else 0)
            next_stage = "teen"
        elif self.state.stage == "teen":
            threshold = STAGE_THRESHOLDS["teen"] + (12 if self.state.health < 60 else 0)
            next_stage = "adult"

        if threshold is None or next_stage is None:
            return
        if self.state.stage_minutes < threshold:
            return

        self.state.stage = next_stage
        self.state.stage_minutes = 0
        self.state.health = clamp(self.state.health + 8)
        self.state.happiness = clamp(self.state.happiness + 6)
        self._set_animation("evolution", current, 6)
        self._set_message("EVOLVE", current, 4)

    def _die(self, current: datetime) -> None:
        self.state.alive = False
        self.state.sick = False
        self.state.asleep = False
        self.state.attention = False
        self.state.attention_reason = ""
        self.state.pending_discipline = False
        self._set_animation("dead", current, 20)
        self._set_message("GAME OVER", current, 20)

    def _is_neglected(self) -> bool:
        return (
            self.state.hunger <= 10
            or self.state.health <= 25
            or self.state.poop_count >= 3
            or (self.state.sick and self.state.health <= 55)
            or (self.state.asleep and not self.state.lights_off)
        )

    def _is_sleep_time(self, current: datetime) -> bool:
        return current.hour >= 22 or current.hour < 8

    def _refresh_attention(self, current: datetime) -> None:
        if not self.state.alive:
            self.state.attention = False
            self.state.attention_reason = ""
            return

        reason = ""
        if self.state.sick:
            reason = "SICK"
        elif self.state.asleep and not self.state.lights_off:
            reason = "LIGHT"
        elif self.state.poop_count > 0:
            reason = "DIRTY"
        elif self.state.hunger <= 30:
            reason = "HUNGRY"
        elif self.state.happiness <= 30:
            reason = "BORED"
        elif self.state.pending_discipline:
            reason = "DISC"

        self.state.attention = bool(reason)
        self.state.attention_reason = reason

        if not reason and self.state.message == "STATUS" and parse_dt(self.state.message_until, current) < current:
            self.state.message = ""

    def _expire_transients(self, current: datetime) -> bool:
        changed = False
        if self.state.transient_animation and parse_dt(self.state.animation_until, current) <= current:
            self.state.transient_animation = ""
            self.state.animation_until = ""
            changed = True
        if self.state.message and parse_dt(self.state.message_until, current) <= current:
            self.state.message = ""
            self.state.message_until = ""
            changed = True
        return changed

    def _set_animation(self, name: str, current: datetime, seconds: int) -> None:
        self.state.transient_animation = name
        self.state.animation_until = iso(current + timedelta(seconds=seconds))

    def _set_message(self, message: str, current: datetime, seconds: int) -> None:
        self.state.message = message
        self.state.message_until = iso(current + timedelta(seconds=seconds))
