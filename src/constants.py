from __future__ import annotations

from pathlib import Path

APP_NAME = "Sukunatchi"
BASE_SIZE = 1024
DEFAULT_WINDOW_SCALE = 0.45
SAVE_VERSION = 2

ROOT_DIR = Path(__file__).resolve().parents[1]
CARCASA_PATH = ROOT_DIR / "carcaza.jpeg"
SPRITE_SHEET_PATH = ROOT_DIR / "sukunas.jpg"
SAVE_PATH = ROOT_DIR / "save" / "state.json"

LCD_RECT = (304, 306, 413, 390)
LCD_INSET = 14
LCD_RADIUS = 30

BUTTON_CENTERS = {
    "A": (376, 785),
    "B": (512, 794),
    "C": (649, 783),
}
BUTTON_RADIUS = 52

MENU_ITEMS = ("STATUS", "MEAL", "SNACK", "GAME", "CLEAN", "MED", "DISC", "LIGHT")

ANIMATION_INTERVALS_MS = {
    "egg": 260,
    "hatch": 180,
    "idle": 340,
    "meal": 220,
    "snack": 220,
    "play": 200,
    "poop": 280,
    "clean": 220,
    "sick": 320,
    "medicine": 220,
    "sleep": 550,
    "lights_off": 900,
    "attention": 180,
    "discipline": 260,
    "evolution": 180,
    "dead": 420,
}

NON_LOOPING_ANIMATIONS = {"dead"}

LCD_BACKGROUND = (233, 231, 205, 255)
LCD_LINE = (210, 208, 182, 32)
LCD_TEXT = (39, 39, 39)
LCD_PANEL = (226, 223, 196, 232)
LCD_PANEL_BORDER = (103, 98, 73, 130)
LCD_MESSAGE = (236, 231, 202, 238)

HATCH_MINUTES = 1
STAGE_THRESHOLDS = {
    "baby": 18,
    "child": 55,
    "teen": 110,
}

STAGE_ORDER = ("egg", "baby", "child", "teen", "adult")
