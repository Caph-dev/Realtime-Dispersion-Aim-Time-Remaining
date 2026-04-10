# Realtime Dispersion & Aim Time Remaining

**Repository:** [github.com/Walaxy/WOT-Current-Accuracy-Aim-Time](https://github.com/Walaxy/WOT-Current-Accuracy-Aim-Time)

## Description / 简介

**English:** A World of Tanks client mod that draws two lines near the crosshair: **realtime gun dispersion** and **aim time remaining** (seconds). It hooks `PlayerAvatar` dispersion and targeting updates, works with **ModSettingsAPI** (optional) and **ModsListAPI** (optional), and stores settings in JSON under `mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`. The built package is **`caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`** (mod version from `build.json` → `info.version`, e.g. **`caphhh.RealtimeDispersion&AimTimeRemaining-1.1.2.wotmod`**), committed under **`release/`**.

**中文：** 本模组在准星附近显示两行文字：**实时火炮散布**与**剩余缩圈时间（秒）**。通过挂钩 `PlayerAvatar` 的散布与瞄准信息实现，可选接入 **ModSettingsAPI** 与 **ModsListAPI**，配置保存在 `mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`。构建产物为 **`caphhh.RealtimeDispersion&AimTimeRemaining-<版本号>.wotmod`**（模组版本见 `build.json` 的 `info.version`，例如 **`caphhh.RealtimeDispersion&AimTimeRemaining-1.1.2.wotmod`**），并放在仓库的 **`release/`** 目录中随 Git 发布。

---

## Usage / 使用方法

### Install / 安装

1. Copy **`release/caphhh.RealtimeDispersion&AimTimeRemaining-1.1.2.wotmod`** (or the matching **`caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`** from **`release/`**) into your game folder:  
   `WorldOfTanks/mods/<game_version>/`  
   （将 **`release/`** 下的 **`caphhh.RealtimeDispersion&AimTimeRemaining-<版本>.wotmod`** 复制到游戏目录下的 `mods/<游戏版本号>/`。）

2. On first run, the mod creates **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`** next to the game executable if it does not exist. You can also ship the default from this repo:  
   `resources/out/mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`  
   （首次运行会自动生成配置；也可手动放置仓库中的默认 `config.json`。）

3. If you use **ModSettingsAPI**, open the mod settings panel in-game to change options; changes are written back to the same JSON file.  
   （若安装了 **ModSettingsAPI**，可在游戏内模组设置中修改选项，会写回同一 JSON。）

### Build from source / 从源码构建

1. Install a **Python 2.7** interpreter compatible with the WoT client (same major version as the game’s embedded Python).

2. Point the build to that interpreter via **`build.json` → `software.python`** (full path to `python.exe`), or set environment variable **`WOT_PYTHON27`**. This repo currently defaults to `tools/python27/python.exe`; change it if your Python 2.7 lives elsewhere.

3. Optional: set **`build.json` → `game.version`** (and `game.folder` for `--ingame`) or **`WOT_VERSION`** / **`WOT_FOLDER`**.

4. Run:

```powershell
cd "d:\GAME\Current Accuracy and Aim Time"
python build.py --distribute
```

Outputs (mod version suffix comes from `build.json` → `info.version`):

- `release/caphhh.RealtimeDispersion&AimTimeRemaining-1.1.2.wotmod`
- `release/caphhh.RealtimeDispersion&AimTimeRemaining-1.1.2.zip` when using `--distribute`: **only two** `.wotmod` files — **`caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`** and **`caphhh.modssettingsapi_<version>.wotmod`** (ModSettingsAPI; default version **`1.7.0`** via `packaging.modssettingsapi_version` in **`build.json`**). This is the **published release** zip for GitHub. Optional: set **`packaging.distribute_resources_zip`** to `true` to also build **`*-<version>-resources.zip`** (mods folder + `resources/out` layout).

Use **`python build.py --ingame`** to copy the `.wotmod` and `resources/out` into a configured game folder.

---

## Configuration / 配置说明

File path: **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`**

Fresh installs start centered on screen (`0.0`, `0.0`). Position is adjusted by dragging the HUD in battle and saved to this file; ModSettings no longer exposes position controls.

| Key | Type | Description (EN) | 说明（中文） |
|-----|------|------------------|--------------|
| `enabled` | bool | Master switch; when `false`, the overlay is hidden and hooks stay minimal. | 总开关；为 `false` 时不显示文字。 |
| `show_dispersion` | bool | Show the line with current dispersion / accuracy value. | 是否显示“当前散布/精度”一行。 |
| `show_aim_time` | bool | Show the line with remaining aim time (seconds). | 是否显示“剩余缩圈时间”一行。 |
| `debug_aim_logging` | bool | When `true`, writes throttled **`[AIM_DEBUG]`** lines to **`python.log`** for troubleshooting after game updates. Default `false`. | 为 `true` 时在 **`python.log`** 中输出限频的 **`[AIM_DEBUG]`** 日志，用于版本更新后排查；默认关闭。 |
| `font_size` | float | Text size (see in-game font presets). | 字号（与游戏内字体档位对应）。 |
| `font_name` | string | One of: `default_small.font`, `default_medium.font`, `default_large.font`. | 字体预设，三选一。 |
| `decimal_dispersion` | int | Decimal places for dispersion (0–6). | 散布数值小数位数（0–6）。 |
| `decimal_aim_time` | int | Decimal places for aim time (0–4). | 缩圈时间小数位数（0–4）。 |
| `offset_x` | float | Horizontal offset of the text block (normalized, negative = left). | 文字块水平偏移（归一化，负值为左移）。 |
| `offset_y` | float | Vertical offset (negative = down). | 垂直偏移（负值为下移）。 |
| `line_spacing` | float | Extra gap between the two lines. | 两行之间的额外间距。 |
| `color` | `[R,G,B,A]` | Text color, each channel 0–255. | 文字颜色，RGBA 各 0–255。 |

### Migrating from older paths / 旧路径迁移

If you previously used **`mods/configs/currentAccAndAimTime/config.json`** or **`mods/configs/caphhh.current_acc_and_aim_time/config.json`**, copy that file to **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`** and add missing new keys if needed.

## Changelog / 更新记录

### 1.1.2

- Fix HUD position not persisting after battle/game exit when old ModSettings data exists.
- Set the default HUD position for fresh installs to the screen center.
- Remove position options from ModSettings; HUD position is now drag-only.

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

## Project layout / 工程结构

- `python/gui/mods/mod_caphhh_current_acc_and_aim_time.py` — main mod (hooks, UI, settings)
- `resources/out/mods/configs/RealtimeDispersion&AimTimeRemaining/config.json` — default config (copy manually or use **`packaging.distribute_resources_zip`**)
- `build.py` / `build.json` — compile `.pyc` and pack **`release/caphhh.RealtimeDispersion&AimTimeRemaining-<version>.wotmod`**
- `release/` — versioned `.wotmod` and **`caphhh.RealtimeDispersion&AimTimeRemaining-<version>.zip`** (this mod + `caphhh.modssettingsapi_<version>.wotmod`); tracked in Git for releases

## License / 许可证

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License v3.0** as published by the Free Software Foundation. See the [`LICENSE`](LICENSE) file.

本程序为自由软件：您可以在遵循 **GNU 通用公共许可证第 3 版（GPL-3.0）** 的前提下再发布和/或修改。完整条款见仓库根目录的 [`LICENSE`](LICENSE)。

**Copyright (C) 2026 Walaxy** \<wlx0414@foxmail.com\>

## Reference / 参考

Implementation draws on ideas from [true-server-reticle](https://github.com/Archie-osu/true-server-reticle) for live dispersion and aim-time behavior.

Decompiled client reference for API changes: [izeberg/wot-src](https://github.com/izeberg/wot-src) (EU branch).
