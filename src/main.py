from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .assets import AssetCatalog
from .constants import APP_NAME, SAVE_PATH, SAVE_VERSION
from .pet import PetGame, PetState
from .storage import SaveStore
from .ui import TamagotchiWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--screenshot", type=str, default="")
    parser.add_argument("--delay-ms", type=int, default=1200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    store = SaveStore(SAVE_PATH)
    payload = store.load()
    if payload and payload.get("save_version") == SAVE_VERSION:
        state = PetState.from_dict(payload)
    else:
        state = None
    game = PetGame(state)
    assets = AssetCatalog()
    window = TamagotchiWindow(assets, game, store)
    window.show()

    if args.screenshot:
        def capture() -> None:
            window.grab().save(args.screenshot)
            window.close()
            app.quit()

        QTimer.singleShot(max(1, args.delay_ms), capture)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
