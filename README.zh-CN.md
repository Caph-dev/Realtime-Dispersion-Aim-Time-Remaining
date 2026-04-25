# 实时散布与剩余缩圈时间（Realtime Dispersion & Aim Time Remaining）

**英文文档:** [README.md](README.md)

**GitHub 链接:** [github.com/Walaxy/WOT-Current-Accuracy-Aim-Time](https://github.com/Walaxy/WOT-Current-Accuracy-Aim-Time)

**WGMODS 链接:** [wgmods.net/7612/](https://wgmods.net/7612/)

## 简介

本模组在准星附近显示两行文字：**实时火炮散布**与**剩余缩圈时间（秒）**。可选接入 **ModSettingsAPI**，配置保存在 `mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`。构建产物为 **`caphhh.RealtimeDispersion&AimTimeRemaining-<版本号>.wotmod`**（模组版本见 `build.json` 的 `info.version`，例如 **`caphhh.RealtimeDispersion&AimTimeRemaining-1.1.4.wotmod`**），并放在仓库的 **`release/`** 目录中随 Git 发布。

---

## 使用方法

### 安装

1. 将 **`release/`** 下的 **`caphhh.RealtimeDispersion&AimTimeRemaining-<版本>.wotmod`** 复制到游戏目录：  
   `WorldOfTanks/mods/<游戏版本号>/`

2. 首次运行会在游戏可执行文件旁自动生成 **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`**；也可手动放置仓库中的默认配置：  
   `resources/out/mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`

3. 若使用 **WoT 2.2.1.1+** 下的推荐完整栈：将 **`release/RealtimeDispersion&AimTimeRemaining-<版本>.zip`** 内（或 **`release/`** 目录中已解压的）**五个** `.wotmod` 全部拷贝到 `mods/<游戏版本>/` —— 本模组、**GUIFlash**（`gambiter.guiflash_0.6.3.wotmod`）、**ModsSettingsAPI**（`izeberg`）、**Mods List**（`me.poliroid.modslistapi`）、**Gameface**（`net.openwg`）。然后在游戏内打开模组设置；选项会写回同一 JSON。

在 **WoT 2.2.1.1** 上，强烈建议安装 **`gambiter.guiflash_0.6.3.wotmod`**。检测到该依赖时，本模组会优先走 GUIFlash 渲染路径，而不是旧的 `GUI.Text` 回退方案；这可以避开近期 2.2.1.x 更新后战斗 HUD 不显示的问题。

### 从源码构建

1. 安装与《坦克世界》客户端兼容的 **Python 2.7**（主版本需与游戏内嵌 Python 一致）。

2. 在 **`build.json` → `software.python`** 中填写 `python.exe` 完整路径，或设置环境变量 **`WOT_PYTHON27`**。本仓库默认指向 `tools/python27/python.exe`，若本机 Python 2.7 在其他位置请自行修改。

3. 可选：设置 **`build.json` → `game.version`**（以及用于 `--ingame` 的 `game.folder`），或使用 **`WOT_VERSION`** / **`WOT_FOLDER`**。

4. 执行：

```powershell
cd "d:\GAME\Current Accuracy and Aim Time"
python build.py --distribute
```

构建输出（版本后缀来自 `build.json` → `info.version`）：

- `release/caphhh.RealtimeDispersion&AimTimeRemaining-1.1.4.wotmod`
- 使用 `--distribute` 时还会生成 **`release/RealtimeDispersion&AimTimeRemaining-1.1.4.zip`**：扁平 zip，内含 **五个** `.wotmod` —— 本模组、**`gambiter.guiflash_0.6.3.wotmod`**、**`izeberg.modssettingsapi_1.7.0.wotmod`**、**`me.poliroid.modslistapi_1.7.8.wotmod`**、**`net.openwg.gameface_1.1.5.wotmod`**（路径见 **`build.json`** 的 **`packaging.distribute_bundle_extra_wotmods`**）。构建前请先将上述第三方 **`release/`** 文件放好。该 zip 为面向 GitHub 的**发布包**。可选：将 **`packaging.distribute_resources_zip`** 设为 `true`，额外生成 **`*-<版本>-resources.zip`**（mods 目录 + `resources/out` 布局）。

**`release/` 目录约定：** 共 **六** 个文件 —— 上述五个 `.wotmod` 加上 **`.zip`**（zip 内为同样的五个 `.wotmod`；保留解压后的 loose 文件便于不解压直接拷贝）。

使用 **`python build.py --ingame`** 可将 `.wotmod` 与 `resources/out` 复制到已配置的游戏目录。

**GitHub Releases：** 仅上传 distribute 生成的 **`.zip`**（可用 **`scripts/publish-github-release.ps1`**），不要单独上传裸 `.wotmod` 作为 Release 资源。

---

## 配置说明

配置文件路径：**`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`**

全新安装默认在屏幕正中（`0.0`，`0.0`）。战斗中可拖动 HUD 调整位置并保存；ModSettings 不再提供位置相关选项。

| 键 | 类型 | 说明 |
|----|------|------|
| `enabled` | bool | 总开关；为 `false` 时不显示文字。 |
| `show_dispersion` | bool | 是否显示「当前散布/精度」一行。 |
| `show_aim_time` | bool | 是否显示「剩余缩圈时间」一行。 |
| `debug_aim_logging` | bool | 为 `true` 时在 **`python.log`** 中输出限频的 **`[AIM_DEBUG]`** 日志，用于版本更新后排查；默认关闭。 |
| `font_size` | float | 字号（与游戏内字体档位对应）。 |
| `font_name` | string | 字体预设：`default_small.font`、`default_medium.font`、`default_large.font` 三选一。 |
| `decimal_dispersion` | int | 散布数值小数位数（0–6）。 |
| `decimal_aim_time` | int | 缩圈时间小数位数（0–4）。 |
| `color` | `[R,G,B,A]` | 文字颜色，RGBA 各 0–255。 |

### 旧路径迁移

若曾使用 **`mods/configs/currentAccAndAimTime/config.json`** 或 **`mods/configs/caphhh.current_acc_and_aim_time/config.json`**，请将文件复制到 **`mods/configs/RealtimeDispersion&AimTimeRemaining/config.json`**，并视情况补全新增键。

## 更新记录

### 1.1.4

- 玩家坦克被摧毁或乘员失效时，立即隐藏并清理 HUD。
- 防止坦克已被击毁后，后续散布刷新回调再次重建 HUD。
- 将目标游戏版本更新为 WoT `2.2.1.1`。

### 1.1.3

- 面向 WoT `2.2.1.0` 重新用 Python 2.7 字节码构建，修复更新后客户端不再正确加载的问题。
- 不再依赖旧式物品组件包装器上的直接 `gun.get(...)` 读取 `shotDispersionAngle` / 缩圈时间，规避 `SoftException('Operation is not allowed')`。
- 在 `python.log` 中增加一次性渲染后端诊断日志，便于后续版本更新后快速排查。
- 将 **`gambiter.guiflash_0.6.3.wotmod`** 纳入发布 zip，并在 WoT `2.2.1.0+` 上推荐 GUIFlash 渲染后端，以规避旧 `GUI.Text` 回退路径下战斗 HUD 不显示的问题。

### 1.1.2

- 修复在存在旧 ModSettings 数据时，战斗结束或退出游戏后 HUD 位置不保存的问题。
- 全新安装默认 HUD 位置为屏幕正中。
- 从 ModSettings 中移除位置相关选项；位置仅通过拖动调整。

### 1.1.1

- 已跳过。

### 1.1.0

- 模组显示名称改为 **Realtime Dispersion & Aim Time Remaining**。
- 战斗中支持 **Ctrl + 鼠标左键** 拖动 HUD。
- 增加文字颜色、透明度、阴影等显示选项。
- 通过清除默认标签阴影滤镜，修复 Gambiter 默认光晕问题。
- 归一化光标与备用起始路径，提升多客户端下拖动稳定性。
- 修正拖动 Y 轴方向与速度，使文字更精确跟随鼠标。
- 为 **街机**与**狙击**模式分别保存 HUD 偏移。
- 可选 **`debug_drag_logging`**（`[DRAG_DEBUG]`）便于在 `python.log` 中排查拖动问题。

---

## 工程结构

- `python/gui/mods/mod_caphhh_current_acc_and_aim_time.py` — 主模组（挂钩、界面、设置）
- `resources/out/mods/configs/RealtimeDispersion&AimTimeRemaining/config.json` — 默认配置（手动复制或启用 **`packaging.distribute_resources_zip`**）
- `build.py` / `build.json` — 编译 `.pyc` 并打包 **`release/caphhh.RealtimeDispersion&AimTimeRemaining-<版本>.wotmod`**
- `release/` — **`caphhh.RealtimeDispersion&AimTimeRemaining-<版本>.wotmod`**、第三方 **gambiter / izeberg / Mods List / Gameface** 的 `.wotmod`，以及 **`RealtimeDispersion&AimTimeRemaining-<版本>.zip`**（zip 内含五个 `.wotmod`）；随 Git 发布

## 依赖与致谢

本模组对 **ModSettingsAPI** 的接入依赖上游项目维护的通用设置栈，感谢相关作者与维护者提供的接口与文档。

- **[ModsSettingsAPI](https://github.com/izeberg/modssettingsapi)** — 游戏内模组设置框架（[izeberg](https://github.com/izeberg) 维护）；本仓库发布 zip 中附带 **`izeberg.modssettingsapi_1.7.0.wotmod`**（与上游发布文件名一致）。
- **[Mods List](https://gitlab.com/wot-public-mods/mods-list)** — **ModsList API** 聚合入口（WoT public mods / Poliroid）；ModsSettingsAPI 说明中要求依赖 ModsList 以打开设置界面。
- **[OpenWG Gameface](https://gitlab.com/openwg/wot.gameface/)** — Mods List 使用的 Gameface UI 层；使用 Mods List 时需同时安装 **`net.openwg.gameface_*.wotmod`**。

## 许可证

本程序为自由软件：您可以在遵循 **GNU 通用公共许可证第 3 版（GPL-3.0）** 的前提下再发布和/或修改。完整条款见仓库根目录的 [`LICENSE`](LICENSE)。

**Copyright (C) 2026 Walaxy** \<wlx0414@foxmail.com\>

## 参考

实现思路参考 [true-server-reticle](https://github.com/Archie-osu/true-server-reticle) 的实时散布与缩圈时间表现。

客户端 API 变更可参考反编译仓库 [izeberg/wot-src](https://github.com/izeberg/wot-src)（EU 分支）。
