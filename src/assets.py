from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtGui import QPixmap

from .constants import CARCASA_PATH, SPRITE_SHEET_PATH


ForegroundThreshold = 68


@dataclass(frozen=True)
class AnimationSpec:
    region: tuple[int, int, int, int]
    groups: tuple[tuple[int, ...], ...]
    min_area: int = 200


@dataclass
class Component:
    area: int
    box: tuple[int, int, int, int]
    image: Image.Image


ANIMATION_SPECS: dict[str, AnimationSpec] = {
    "egg": AnimationSpec((0, 35, 360, 135), ((0,), (1,), (2,))),
    "hatch": AnimationSpec((400, 35, 1000, 135), ((0,), (1,), (2,), (3, 4), (5,))),
    "idle": AnimationSpec((0, 170, 360, 265), ((0,), (1,), (2,))),
    "meal": AnimationSpec((400, 170, 1000, 265), ((0,), (1,), (2, 3), (4,), (5,))),
    "snack": AnimationSpec((0, 300, 360, 370), ((0,), (1, 3), (2,))),
    "play": AnimationSpec((620, 295, 930, 385), ((0, 1), (2, 3))),
    "poop": AnimationSpec((0, 420, 360, 515), ((0, 2), (1, 2))),
    "clean": AnimationSpec((420, 420, 1000, 515), ((0,), (1,), (2, 3), (4,))),
    "sick": AnimationSpec((0, 550, 360, 640), ((0,), (1,), (2, 3))),
    "medicine": AnimationSpec((420, 550, 940, 645), ((0,), (1, 2, 3), (4,))),
    "sleep": AnimationSpec((0, 690, 400, 770), ((0,), (1,), (2,))),
    "lights_off": AnimationSpec((430, 690, 620, 770), ((0,),)),
    "attention": AnimationSpec((620, 690, 1010, 770), ((0,), (1, 2))),
    "discipline": AnimationSpec((0, 810, 400, 895), ((0,), (2,), (3,))),
    "evolution": AnimationSpec((420, 810, 1010, 895), ((0,), (1,), (2,), (3,))),
    "dead": AnimationSpec((0, 935, 760, 1024), ((0,), (1,), (2,), (3,), (4, 5), (6,), (7,))),
}


class AssetCatalog:
    def __init__(self) -> None:
        self.casing = QPixmap(str(CARCASA_PATH))
        self.sheet = Image.open(SPRITE_SHEET_PATH).convert("RGB")
        self.sheet_bg = self.sheet.getpixel((0, 0))
        self.animations: dict[str, list[QPixmap]] = {}
        self.icons: dict[str, QPixmap] = {}
        self._components: dict[str, list[Component]] = {}
        self._load_all()

    def frames(self, name: str) -> list[QPixmap]:
        return self.animations.get(name) or self.animations["idle"]

    def _load_all(self) -> None:
        for name, spec in ANIMATION_SPECS.items():
            components = self._extract_components(spec)
            self._components[name] = components
            self.animations[name] = self._compose_animation_frames(spec, components)

        poop_components = self._components["poop"]
        self.icons["poop"] = self._pixmap_from_pil(poop_components[2].image)

    def _compose_animation_frames(self, spec: AnimationSpec, components: list[Component]) -> list[QPixmap]:
        frames: list[QPixmap] = []
        frame_layouts: list[list[tuple[Component, int, int]]] = []
        union_left: int | None = None
        union_top: int | None = None
        union_right: int | None = None
        union_bottom: int | None = None

        anchor_x, anchor_y = self._primary_center([components[index] for index in spec.groups[0]])

        for group in spec.groups:
            subset = [components[index] for index in group]
            primary_x, primary_y = self._primary_center(subset)
            delta_x = anchor_x - primary_x
            delta_y = anchor_y - primary_y
            layout: list[tuple[Component, int, int]] = []
            for component in subset:
                left, top, right, bottom = component.box
                dest_x = left + delta_x
                dest_y = top + delta_y
                layout.append((component, dest_x, dest_y))
                union_left = dest_x if union_left is None else min(union_left, dest_x)
                union_top = dest_y if union_top is None else min(union_top, dest_y)
                union_right = right + delta_x if union_right is None else max(union_right, right + delta_x)
                union_bottom = bottom + delta_y if union_bottom is None else max(union_bottom, bottom + delta_y)
            frame_layouts.append(layout)

        union_left = union_left or 0
        union_top = union_top or 0
        union_right = union_right or 1
        union_bottom = union_bottom or 1
        width = max(1, union_right - union_left)
        height = max(1, union_bottom - union_top)

        for layout in frame_layouts:
            frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            for component, dest_x, dest_y in layout:
                frame.alpha_composite(component.image, (dest_x - union_left, dest_y - union_top))
            frames.append(self._pixmap_from_pil(frame))
        return frames

    def _extract_components(self, spec: AnimationSpec) -> list[Component]:
        crop = self.sheet.crop(spec.region)
        pixels = crop.load()
        width, height = crop.size
        seen = [[False for _ in range(width)] for _ in range(height)]
        components: list[Component] = []

        for y in range(height):
            for x in range(width):
                if seen[y][x]:
                    continue
                seen[y][x] = True
                if not self._is_foreground(pixels[x, y]):
                    continue

                queue = deque([(x, y)])
                cells: list[tuple[int, int]] = []
                min_x = max_x = x
                min_y = max_y = y

                while queue:
                    cx, cy = queue.popleft()
                    cells.append((cx, cy))
                    min_x = min(min_x, cx)
                    max_x = max(max_x, cx)
                    min_y = min(min_y, cy)
                    max_y = max(max_y, cy)

                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < width and 0 <= ny < height and not seen[ny][nx]:
                            seen[ny][nx] = True
                            if self._is_foreground(pixels[nx, ny]):
                                queue.append((nx, ny))

                if len(cells) < spec.min_area:
                    continue

                box = (min_x, min_y, max_x + 1, max_y + 1)
                component = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
                for cx, cy in cells:
                    component.putpixel((cx - box[0], cy - box[1]), (*pixels[cx, cy], 255))
                components.append(Component(area=len(cells), box=box, image=component))

        components.sort(key=lambda item: item.box[0])
        return components

    def _primary_center(self, components: list[Component]) -> tuple[int, int]:
        primary = max(components, key=lambda item: item.area)
        left, top, right, bottom = primary.box
        return (left + right) // 2, (top + bottom) // 2

    def _is_foreground(self, pixel: tuple[int, int, int]) -> bool:
        distance = sum(abs(channel - base) for channel, base in zip(pixel, self.sheet_bg))
        return distance >= ForegroundThreshold

    def _pixmap_from_pil(self, image: Image.Image) -> QPixmap:
        return QPixmap.fromImage(ImageQt(image))
