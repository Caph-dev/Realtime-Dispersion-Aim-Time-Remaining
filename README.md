# Realtime Dispersion & Aim Time Remaining

**中文文档:** [README.zh-CN.md](README.zh-CN.md)

**WGMODS Link:** [wgmods.net/7612/](https://wgmods.net/7612/)

## Description

A World of Tanks client mod that shows **realtime gun dispersion** and **aim time remaining** (seconds) near the crosshair. Optional **ModSettingsAPI** integration.

---

## Usage

### Install

Copy **`release/caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`** into your game folder:

`WorldOfTanks/mods/<game_version>/`

### Build from source

Use **Python 2.7** (same major version as the game’s embedded Python). Set **`build.json` → `software.python`** or **`WOT_PYTHON27`**; optionally set **`game.version`** / **`WOT_VERSION`** for `--ingame`.

```powershell
python build.py --distribute
```

Artifacts land in **`release/`** (`.wotmod` and, with `--distribute`, the release **`.zip`**). Use **`python build.py --ingame`** to copy the mod and `resources/out` into a configured game folder.

---

## Configuration

File path: **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`**

Fresh installs start centered on screen (`0.0`, `0.0`). Position is adjusted by dragging the HUD in battle and saved to this file; ModSettings no longer exposes position controls.

| Key | Type | Description |
|-----|------|-------------|
| `enabled` | bool | Master switch; when `false`, the overlay is hidden and hooks stay minimal. |
| `show_dispersion` | bool | Show the line with current dispersion / accuracy value. |
| `show_aim_time` | bool | Show the line with remaining aim time (seconds). |
| `debug_aim_logging` | bool | When `true`, writes throttled **`[AIM_DEBUG]`** lines to **`python.log`** for troubleshooting after game updates. Default `false`. |
| `font_size` | float | Text size (see in-game font presets). |
| `font_name` | string | One of: `default_small.font`, `default_medium.font`, `default_large.font`. |
| `decimal_dispersion` | int | Decimal places for dispersion (0–6). |
| `decimal_aim_time` | int | Decimal places for aim time (0–4). |
| `color` | `[R,G,B,A]` | Text color, each channel 0–255. |

## Changelog

### 1.1.4

- Hide and tear down the HUD immediately when the player's vehicle is destroyed or crew is deactivated.
- Prevent later dispersion refresh callbacks from recreating the HUD while the player vehicle is dead.
- Update the target game version to WoT `2.2.1.1`.

### 1.1.3

- Fix WoT `2.2.1.0` compatibility by rebuilding the package as Python 2.7 bytecode for the new game version.
- Avoid `SoftException('Operation is not allowed')` from legacy item component wrappers by no longer depending on direct `gun.get(...)` access for `shotDispersionAngle` / aiming time reads.
- Add one-time renderer backend diagnostics to `python.log` to speed up post-update troubleshooting.
- Bundle **`gambiter.guiflash_0.6.3.wotmod`** in the release zip and recommend the GUIFlash backend on WoT `2.2.1.0+`, where the legacy `GUI.Text` fallback can fail to show the in-battle HUD.

### 1.1.2

- Fix HUD position not persisting after battle/game exit when old ModSettings data exists.
- Set the default HUD position for fresh installs to the screen center.
- Remove position options from ModSettings; HUD position is now drag-only.

### 1.1.1

- Skipped.

### 1.1.0

- Rename mod display name to **Realtime Dispersion & Aim Time Remaining**.
- Add HUD drag support during battle with **Ctrl + Left Mouse**.
- Add visual options: text color, alpha, and shadow toggle.
- Fix Gambiter default halo issue by clearing default label shadow filter.
- Improve drag reliability across clients with normalized-cursor handling and fallback start path.
- Fix drag Y-axis direction and drag speed matching (text now follows mouse movement precisely).
- Add independent HUD offsets for **Arcade** and **Sniper** modes.
- Add optional **`debug_drag_logging`** (`[DRAG_DEBUG]`) for troubleshooting in `python.log`.

---

## Dependencies, acknowledgments & reference

Thanks to the authors and maintainers of these projects:

- **[ModsSettingsAPI](https://github.com/izeberg/modssettingsapi)** — in-game settings framework for WoT mods
- **[Mods List](https://gitlab.com/wot-public-mods/mods-list)** — ModsList API hub for the public mod stack
- **[OpenWG Gameface](https://gitlab.com/openwg/wot.gameface/)** — Gameface UI layer for Mods List
- **[true-server-reticle](https://github.com/Archie-osu/true-server-reticle)** — live dispersion and aim-time behavior
- **[wot-src](https://github.com/izeberg/wot-src)** — decompiled client reference (EU branch)

## License

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License v3.0** as published by the Free Software Foundation. See the [`LICENSE`](LICENSE) file.

**Copyright (C) 2026 Walaxy** \<wlx0414@foxmail.com\>
