---
name: wot-mod-version-update
description: >-
  Maintains World of Tanks Python mods after a client patch. Covers comparing
  decompiled sources from izeberg/wot-src, updating hooks and private attribute
  indices, diagnosing issues via python.log with optional [AIM_DEBUG] traces, and
  versioned release artifact naming (release/<base>-<mod_version>.wotmod from
  build.json). Use when the game version changes, dispersion or targeting APIs
  break, when shipping a new mod version, or when the user asks how to debug WoT
  mod breakage after an update.
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

2. Run `python build.py` (add `--distribute` or `--ingame` as needed). **Bytecode** in `release/*.wotmod` must be produced with **Python 2.7** (set `build.json` → `software.python` or `WOT_PYTHON27` to the game-matching `python.exe`). To ship **`.py` source** instead (no local Python 2.7), use `python build.py --source` or set `packaging.ship_python_source` to `true` in `build.json`.

3. Ensure the packaged **`meta.xml`** `id` matches **`MOD_ID`** in the mod and that config paths match the shipped **`resources/out`** tree.

### Artifact filename rules (this project)

The build script derives **final on-disk names** from **`build.json` → `info`**. The **mod’s own version** is **`info.version`** (e.g. `1.0.0`). It is **not** the WoT client folder version in `game.version`.

| Role | `build.json` field | How it is used |
|------|---------------------|----------------|
| Base name for `.wotmod` | **`info.package_name`** | Must end with **`.wotmod`**. Take the **stem** (path without `.wotmod`). |
| Mod version suffix | **`info.version`** | Appended to the stem, before **`.wotmod`**. |
| Output path | — | **`release/<stem>-<info.version>.wotmod`** |

**Examples**

- `package_name`: `Caphhh.currentAccAndAimTime.wotmod`, `version`: `1.0.0` → **`release/Caphhh.currentAccAndAimTime-1.0.0.wotmod`**.

**Distribute zip (`--distribute`)**

- **`info.archive_name`** must end with **`.zip`**. Take the stem (without `.zip`), then: **`release/<stem>-<info.version>.zip`** (e.g. `caphhh.RealtimeDispersion&AimTimeRemaining-1.1.2.zip`).

- That zip is the **published release archive**: **exactly two** `.wotmod` files — **`caphhh.RealtimeDispersion&AimTimeRemaining-<info.version>.wotmod`** (same as the built mod) and **`caphhh.modssettingsapi_<apiVersion>.wotmod`**, where **`apiVersion`** defaults to **`1.7.0`** (`packaging.modssettingsapi_version` in **`build.json`**). Source file on disk: **`release/caphhh.modssettingsapi_<apiVersion>.wotmod`**, unless overridden by **`packaging.github_release_bundle_wotmod`**. Toggle the two-file bundle with **`packaging.github_release_bundle`**.

- Optional: **`packaging.distribute_resources_zip`** → **`release/<package_stem>-<info.version>-resources.zip`** (mods folder + `resources/out`), separate from the release zip.

**Git / GitHub**

- **`release/`** holds the versioned **`.wotmod`** and the **`<stem>-<info.version>.zip`** (two mods only) when using **`--distribute`**, and is **tracked** so releases ship with the repo. After bumping **`info.version`**, rebuild, then commit the new files under **`release/`**.

- **GitHub Releases:** attach **only** the **`<stem>-<info.version>.zip`** file. Do **not** upload a standalone `.wotmod` as a release asset. Use **`scripts/publish-github-release.ps1`** (it uploads the zip and strips stray `.wotmod` attachments).

**`--ingame`**

- The same **versioned filename** is copied into **`WorldOfTanks/mods/<game.version>/`**. WoT loads any **`*.wotmod`** filename; the version suffix is for humans and release hygiene only.

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
- [ ] **`info.version`** in **`build.json`** matches the release you intend; **`README.md`** updated if user-facing version text changed.
- [ ] Rebuilt artifacts are present under **`release/`** with versioned names per **Artifact filename rules** above (and matching **`.zip`** if using **`--distribute`**), and committed when publishing to GitHub.

## 5. Notes

- Do not rely on undocumented indices forever: leave **comments in code** at hook sites noting **which wot-src file/line** was used when the index was verified.
- Prefer **defensive reads** (`try`/`except` or length checks) around decompiler-shaped tuples so a partial client change fails gracefully in the UI.
