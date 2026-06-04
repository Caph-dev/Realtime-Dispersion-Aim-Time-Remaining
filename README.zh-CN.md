# 实时散布与剩余缩圈时间（Realtime Dispersion & Aim Time Remaining）

**英文文档:** [README.md](README.md)

**GitHub 链接:** [github.com/Walaxy/WOT-Current-Accuracy-Aim-Time](https://github.com/Walaxy/WOT-Current-Accuracy-Aim-Time)

**WGMODS 链接:** [wgmods.net/7612/](https://wgmods.net/7612/)

## 简介

《坦克世界》客户端模组，在准星附近显示**实时火炮散布**与**剩余缩圈时间（秒）**。可选 **ModSettingsAPI**。

---

## 使用方法

### 安装

将 **`release/caphhh.RealtimeDispersion&AimTimeRemaining-<版本>.wotmod`** 复制到游戏目录：

`WorldOfTanks/mods/<游戏版本号>/`

### 从源码构建

使用与客户端一致的 **Python 2.7**。在 **`build.json` → `software.python`** 或环境变量 **`WOT_PYTHON27`** 中指定解释器；可选设置 **`game.version`** / **`WOT_VERSION`** 以配合 `--ingame`。

```powershell
python build.py --distribute
```

产物输出到 **`release/`**（`.wotmod`，以及 `--distribute` 时的发布 **`.zip`**）。使用 **`python build.py --ingame`** 可将模组与 `resources/out` 复制到已配置的游戏目录。

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

## 依赖、致谢与参考

感谢以下项目的作者与维护者：

- **[ModsSettingsAPI](https://github.com/izeberg/modssettingsapi)** — WoT 模组游戏内设置框架
- **[Mods List](https://gitlab.com/wot-public-mods/mods-list)** — 公共模组栈的 ModsList API 入口
- **[OpenWG Gameface](https://gitlab.com/openwg/wot.gameface/)** — Mods List 使用的 Gameface UI 层
- **[true-server-reticle](https://github.com/Archie-osu/true-server-reticle)** — 实时散布与缩圈时间实现参考
- **[wot-src](https://github.com/izeberg/wot-src)** — 客户端反编译参考（EU 分支）

## 许可证

本程序为自由软件：您可以在遵循 **GNU 通用公共许可证第 3 版（GPL-3.0）** 的前提下再发布和/或修改。完整条款见仓库根目录的 [`LICENSE`](LICENSE)。

**Copyright (C) 2026 Walaxy** \<wlx0414@foxmail.com\>
