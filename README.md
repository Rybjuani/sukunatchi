# Sukunatchi

Tamagotchi clasico de escritorio basado en la carcasa rosa del repo y en la sprite sheet de Sukuna.

## Requisitos

- Python 3.12
- PySide6
- Pillow

## Ejecutar

```bash
./run.sh
```

O directo:

```bash
python3 -m src.main
```

## Instalar Comando Global

```bash
./scripts/install.sh
```

Eso crea el comando `sukunatchi` en `~/.local/bin`, para abrirlo desde cualquier lugar:

```bash
sukunatchi
```

## Controles

- `A` o `Left`: navegar acciones
- `Tab`: navegar acciones
- `B` o `Enter` o `Space`: confirmar / ejecutar
- `C` o `Backspace` o `Esc`: cancelar / volver
- Click en los botones fisicos `A`, `B`, `C`: igual que el teclado
- Arrastrar con mouse sobre la carcasa: mover la ventana
- Click derecho sobre la app: cerrar
- `Ctrl+Q` o `Ctrl+W`: cerrar rapido

## Menu

- `STATUS`
- `MEAL`
- `SNACK`
- `GAME`
- `CLEAN`
- `MED`
- `DISC`
- `LIGHT`

## Persistencia

El estado se guarda automaticamente en `save/state.json`.
Si no existe save previo compatible, la partida comienza desde huevo.

## Screenshot offscreen

```bash
QT_QPA_PLATFORM=offscreen python3 -m src.main --screenshot /tmp/sukunatchi.png --delay-ms 1200
```
