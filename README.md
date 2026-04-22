# Realtime Dispersion & Aim Time Remaining

**中文文档:** [README.zh-CN.md](README.zh-CN.md)

**GitHub Link:** [github.com/Walaxy/WOT-Current-Accuracy-Aim-Time](https://github.com/Walaxy/WOT-Current-Accuracy-Aim-Time)

**WGMODS Link:** [wgmods.net/7612/](https://wgmods.net/7612/)

## Description

A World of Tanks client mod that draws two lines near the crosshair: **realtime gun dispersion** and **aim time remaining** (seconds). It works with **ModSettingsAPI** (optional), and stores settings in JSON under `mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`. The built package is **`caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`** (mod version from `build.json` → `info.version`, e.g. **`caphhh.RealtimeDispersion&AimTimeRemaining-1.1.3.wotmod`**), committed under **`release/`**.

---

## Usage

### Install

1. Copy **`release/caphhh.RealtimeDispersion&AimTimeRemaining-1.1.3.wotmod`** (or the matching **`caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`** from **`release/`**) into your game folder:  
   `WorldOfTanks/mods/<game_version>/`

2. On first run, the mod creates **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`** next to the game executable if it does not exist. You can also ship the default from this repo:  
   `resources/out/mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`

3. For the recommended full stack on **WoT 2.2.1.0+**: copy **all five** `.wotmod` files from **`release/RealtimeDispersion&AimTimeRemaining-<version>.zip`** (or the loose copies in **`release/`**) into `WorldOfTanks/mods/<game_version>/` — this mod, **GUIFlash** (`gambiter.guiflash_0.6.3.wotmod`), **ModsSettingsAPI** (`izeberg`), **Mods List** (`me.poliroid.modslistapi`), and **Gameface** (`net.openwg`). Then open the mod settings panel in-game; changes are written back to the same JSON file.

On **WoT 2.2.1.0**, installing **`gambiter.guiflash_0.6.3.wotmod`** is strongly recommended. When available, this mod renders through GUIFlash instead of the legacy `GUI.Text` fallback, which avoids the missing battle HUD issue observed after the 2.2.1.0 update.

### Build from source

1. Install a **Python 2.7** interpreter compatible with the WoT client (same major version as the game’s embedded Python).

2. Point the build to that interpreter via **`build.json` → `software.python`** (full path to `python.exe`), or set environment variable **`WOT_PYTHON27`**. This repo currently defaults to `tools/python27/python.exe`; change it if your Python 2.7 lives elsewhere.

3. Optional: set **`build.json` → `game.version`** (and `game.folder` for `--ingame`) or **`WOT_VERSION`** / **`WOT_FOLDER`**.

4. Run:

```powershell
cd "d:\GAME\Current Accuracy and Aim Time"
python build.py --distribute
```

Outputs (mod version suffix comes from `build.json` → `info.version`):

- `release/caphhh.RealtimeDispersion&AimTimeRemaining-1.1.3.wotmod`
- `release/RealtimeDispersion&AimTimeRemaining-1.1.3.zip` when using `--distribute`: a flat zip with **five** `.wotmod` files — this mod, **`gambiter.guiflash_0.6.3.wotmod`**, **`izeberg.modssettingsapi_1.7.0.wotmod`**, **`me.poliroid.modslistapi_1.7.8.wotmod`**, **`net.openwg.gameface_1.1.5.wotmod`** (paths listed in **`packaging.distribute_bundle_extra_wotmods`** in **`build.json`**). Vendor files must already sit under **`release/`** before building. This is the **published release** zip for GitHub. Optional: set **`packaging.distribute_resources_zip`** to `true` to also build **`*-<version>-resources.zip`** (mods folder + `resources/out` layout).

**Tracked under `release/`:** six artifacts — the five `.wotmod` files above plus the **`.zip`** (the zip contains the same five `.wotmod` entries; keep loose copies for direct installs without unpacking).

Use **`python build.py --ingame`** to copy the `.wotmod` and `resources/out` into a configured game folder.

**GitHub Releases:** publish **only** the distribute **`.zip`** (via **`scripts/publish-github-release.ps1`**), not a separate `.wotmod` download.

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

### Migrating from older paths

If you previously used **`mods/configs/currentAccAndAimTime/config.json`** or **`mods/configs/caphhh.current_acc_and_aim_time/config.json`**, copy that file to **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`** and add missing new keys if needed.

## Changelog

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

## Project layout

- `python/gui/mods/mod_caphhh_current_acc_and_aim_time.py` — main mod (hooks, UI, settings)
- `resources/out/mods/configs/RealtimeDispersion&AimTimeRemaining/config.json` — default config (copy manually or use **`packaging.distribute_resources_zip`**)
- `build.py` / `build.json` — compile `.pyc` and pack **`release/caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`**
- `release/` — **`caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`**, vendor **`gambiter` / `izeberg` / Mods List / Gameface** `.wotmod` files, and **`RealtimeDispersion&AimTimeRemaining-<version>.zip`** (zip = five `.wotmod`); tracked in Git for releases

## Dependencies & acknowledgments

Optional **ModSettingsAPI** integration in this mod relies on upstream projects that maintain the shared settings stack. Thanks to their authors and maintainers for the APIs and documentation.

- **[ModsSettingsAPI](https://github.com/izeberg/modssettingsapi)** — in-game settings framework for World of Tanks mods (maintained by [izeberg](https://github.com/izeberg)); this repo bundles **`izeberg.modssettingsapi_1.7.0.wotmod`** in distribute zips (upstream release asset naming).
- **[Mods List](https://gitlab.com/wot-public-mods/mods-list)** — **ModsList API** hub (WoT public mods / Poliroid); ModsSettingsAPI [documents](https://github.com/izeberg/modssettingsapi) ModsList as a required dependency for opening the settings window.
- **[OpenWG Gameface](https://gitlab.com/openwg/wot.gameface/)** — Gameface UI layer used by Mods List; install **`net.openwg.gameface_*.wotmod`** alongside Mods List when using that stack.

## License

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License v3.0** as published by the Free Software Foundation. See the [`LICENSE`](LICENSE) file.

**Copyright (C) 2026 Walaxy** \<wlx0414@foxmail.com\>

## Reference

Implementation draws on ideas from [true-server-reticle](https://github.com/Archie-osu/true-server-reticle) for live dispersion and aim-time behavior.

Decompiled client reference for API changes: [izeberg/wot-src](https://github.com/izeberg/wot-src) (EU branch).
