---
name: wot-mod-version-update
description: >-
  Maintains World of Tanks Python mods after a client patch. Covers comparing
  decompiled sources from izeberg/wot-src, updating hooks and private attribute
  indices, and diagnosing issues via python.log with optional [AIM_DEBUG] traces.
  Use when the game version changes, dispersion or targeting APIs break, or
  when the user asks how to debug WoT mod breakage after an update.
---

# WoT mod maintenance after a game version update

## When to apply

- The user bumped `game.version` in `build.json` or reports the mod broke after a WoT patch.
- Hooks fail, dispersion or aim time show wrong values, or tracebacks appear in `python.log`.
- The user needs a repeatable workflow: **source diff → code fix → log verification**.

## 1. Align the decompiled reference (wot-src)

1. Open **[izeberg/wot-src](https://github.com/izeberg/wot-src)** (typically **EU** branch matching the live client region/build you target).

2. Clone or download the tree locally. Focus on Python sources under **`sources/`** (paths mirror the client’s `scripts/client` layout).

3. Locate the classes your mod patches, for example:
   - `PlayerAvatar` — methods such as `updateTargetingInfo`, `getOwnVehicleShotDispersionAngle`, lifecycle (`onBecomePlayer`, `destroy`).
   - Any module that defines dispersion or gun descriptors you read.

4. **Diff against your mental model or previous wot-src revision**: method signatures, parameter order, and **private fields** (e.g. `_PlayerAvatar__dispersionInfo`, `_PlayerAvatar__aimingInfo`) often change between major versions.

5. Update your mod to match:
   - **Hook targets**: same class and method names; fix `*args` / `**kwargs` forwarding if the signature changed.
   - **Tuple/list indices** for internal structures: re-verify indices against the current decompiled method body that fills those structures.
   - **Fallbacks**: keep a safe order (e.g. try index A, then B) when multiple client builds need support.

## 2. Rebuild and install the `.wotmod`

1. Set **`build.json` → `game.version`** to the new folder name under `WorldOfTanks/mods/<version>/`.

2. Run `python build.py` (add `--distribute` or `--ingame` as needed).

3. Ensure the packaged **`meta.xml`** `id` matches **`MOD_ID`** in the mod and that config paths match the shipped **`resources/out`** tree.

## 3. Debug with `python.log`

1. **Log file location** (typical Windows install):  
   `Documents/World_of_Tanks/<region>/python.log`  
   (exact folder name may vary by region and edition.)

2. Reproduce the issue in a short session (training room or garage test if applicable).

3. Search the log for:
   - **Tracebacks** mentioning your mod file or `PlayerAvatar`.
   - Your mod’s **`LOG_WARNING`** prefix (e.g. `[Current Accuracy & Aim Time]`).
   - Optional **`[AIM_DEBUG]`** lines if **`debug_aim_logging`** is enabled in `mods/configs/currentAccAndAimTime/config.json`.

4. **Enable structured aim/dispersion debugging** (for this project):
   - Set **`debug_aim_logging`** to **`true`** in **`mods/configs/currentAccAndAimTime/config.json`**.
   - Restart the client. **`[AIM_DEBUG]`** output is **throttled** (about once per second) to avoid flooding the log.

5. Interpret **`[AIM_DEBUG]`** (conceptually):
   - Compare **dispersion info tuples** (`di=...`) with what the current `PlayerAvatar.updateTargetingInfo` / related code assigns in wot-src.
   - Check **cached aiming time**, **ideal dispersion**, **turret rotation**, and **`with_shot`** when remaining aim time looks wrong.
   - If **`ideal<=0`** or **`aiming_time<=0`** while `di` looks valid, the stationary-ideal derivation or gun descriptor path likely needs adjustment for the new client.

6. After fixing, set **`debug_aim_logging`** back to **`false`** for normal play.

## 4. Checklist before closing

- [ ] wot-src methods and private-field usage match the new client revision you support.
- [ ] No new tracebacks in `python.log` during a smoke test.
- [ ] In-game overlay values look sane (stationary/moving, different tanks).
- [ ] Default config under **`resources/out`** documents any new keys (if added).
- [ ] **`README.md`** or **`build.json`** version strings updated if you ship a release.

## 5. Notes

- Do not rely on undocumented indices forever: leave **comments in code** at hook sites noting **which wot-src file/line** was used when the index was verified.
- Prefer **defensive reads** (`try`/`except` or length checks) around decompiler-shaped tuples so a partial client change fails gracefully in the UI.
