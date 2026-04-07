# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Walaxy <wlx0414@foxmail.com>
import copy
import json
import math
import os

try:
    import BigWorld
except ImportError:
    BigWorld = None

try:
    import GUI
except ImportError:
    GUI = None

try:
    from gambiter import g_guiFlash
    from gambiter.flash import COMPONENT_TYPE
except ImportError:
    g_guiFlash = None
    COMPONENT_TYPE = None

try:
    from Avatar import PlayerAvatar
except ImportError:
    class PlayerAvatar(object):
        pass

try:
    from debug_utils import LOG_CURRENT_EXCEPTION, LOG_WARNING
except ImportError:
    def LOG_WARNING(message):
        print(message)

    def LOG_CURRENT_EXCEPTION():
        import traceback
        traceback.print_exc()

try:
    from gui.modsSettingsApi import g_modsSettingsApi, templates
except ImportError:
    g_modsSettingsApi = None
    templates = None

def _caphhh_get_dispersion_info(avatar):
    """Read _PlayerAvatar__dispersionInfo (list of >= 1 element)."""
    if avatar is None:
        return None
    try:
        di = getattr(avatar, '_PlayerAvatar__dispersionInfo', None)
        if di is not None and hasattr(di, '__len__') and len(di) >= 1:
            return di
    except Exception:
        pass
    return None


def _caphhh_resolve_aiming_time_seconds(avatar):
    """
    aimingTime from __dispersionInfo. Try index [5] first (EU Avatar.py structure:
    [mult, turretRot, move, rot, afterShot, aimingTime]), then [4] (wotstat / some
    clients pack it differently). Fallback to gun descriptor.
    """
    di = _caphhh_get_dispersion_info(avatar)
    if di is not None:
        for idx in (5, 4):
            try:
                if len(di) > idx:
                    v = float(di[idx])
                    if v > 0.0:
                        return v
            except Exception:
                pass

    descr = getattr(avatar, 'vehicleTypeDescriptor', None)
    if descr is not None:
        try:
            gun = getattr(descr, 'gun', None)
            if gun is not None:
                for key in ('aimingTime', 'aimTime'):
                    v = getattr(gun, key, None)
                    if v is None and hasattr(gun, 'get'):
                        v = gun.get(key)
                    if v is not None:
                        fv = float(v)
                        if fv > 0.0:
                            return fv
        except Exception:
            pass
    return 0.0


def _caphhh_ideal_dispersion(avatar):
    """
    Stationary ideal dispersion angle (wotstat-style):
      vehicleTypeDescriptor.gun.shotDispersionAngle * dispersionInfo[0]
    dispersionInfo[0] is shotDispMultiplierFactor from updateTargetingInfo.
    """
    if avatar is None:
        return None
    try:
        descr = getattr(avatar, 'vehicleTypeDescriptor', None)
        if descr is None:
            return None
        gun = getattr(descr, 'gun', None)
        if gun is None:
            return None
        if hasattr(gun, 'get'):
            base = gun.get('shotDispersionAngle')
        elif isinstance(gun, dict):
            base = gun.get('shotDispersionAngle')
        else:
            base = getattr(gun, 'shotDispersionAngle', None)
        if base is None:
            return None
        base = float(base)
        if base <= 0.0:
            return None
    except Exception:
        return None

    di = _caphhh_get_dispersion_info(avatar)
    if di is None:
        return base

    try:
        mult = float(di[0])
        if mult > 0.0:
            return base * mult
    except Exception:
        pass
    return base


def _caphhh_get_value(obj, key):
    try:
        if obj is None:
            return None
        if hasattr(obj, 'get'):
            return obj.get(key)
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)
    except Exception:
        return None


def _caphhh_get_additive_dispersion_factor(descr):
    try:
        misc = getattr(descr, 'miscAttrs', None)
        if misc is None:
            return 1.0
        value = _caphhh_get_value(misc, 'additiveShotDispersionFactor')
        if value is None:
            return 1.0
        value = float(value)
        if value > 0.0:
            return value
    except Exception:
        pass
    return 1.0


def _caphhh_get_stationary_ideal_from_result(avatar, dispersion_result, turret_rotation_speed, with_shot):
    """
    Reconstruct stationary ideal angle without direct shotDispersionAngle access.
    Avatar.py formula:
      idealFactor = mult * sqrt(1 + additiveSqr)
      result[1] = shotDispersionAngle * idealFactor
    therefore:
      stationaryIdeal = result[1] / sqrt(1 + additiveSqr)
    """
    di = _caphhh_get_dispersion_info(avatar)
    if di is None or len(di) < 5 or dispersion_result is None:
        return None
    try:
        current_ideal = float(dispersion_result[1])
        if current_ideal <= 0.0:
            return None

        vehicle_speed, vehicle_rspeed = avatar.getOwnVehicleSpeeds(True)
        vehicle_movement_factor = float(vehicle_speed) * float(di[2])
        vehicle_movement_factor *= vehicle_movement_factor

        vehicle_rotation_factor = float(vehicle_rspeed) * float(di[3])
        vehicle_rotation_factor *= vehicle_rotation_factor

        turret_rotation_factor = float(turret_rotation_speed) * float(di[1])
        turret_rotation_factor *= turret_rotation_factor

        shot_factor = 0.0
        if with_shot:
            try:
                shot_factor = float(di[4])
            except Exception:
                shot_factor = 0.0
        shot_factor *= shot_factor

        additive_sqr = vehicle_movement_factor + vehicle_rotation_factor + turret_rotation_factor + shot_factor
        descr = getattr(avatar, 'vehicleTypeDescriptor', None)
        additive_factor = _caphhh_get_additive_dispersion_factor(descr)
        additive_sqr *= additive_factor * additive_factor

        ratio = math.sqrt(1.0 + additive_sqr)
        if ratio <= 0.0:
            return None
        return current_ideal / ratio
    except Exception:
        return None


def _caphhh_compute_aim_time(aiming_time, current_angles, ideal_angle):
    """time = aimingTime * ln(current / ideal) for each current angle; return max."""
    if aiming_time <= 0.0 or ideal_angle is None or ideal_angle <= 1e-12:
        return 0.0
    best = 0.0
    for ca in current_angles:
        try:
            cur = float(ca)
        except Exception:
            continue
        if cur <= 0.0:
            continue
        if cur <= ideal_angle * 1.000000001:
            continue
        ratio = cur / ideal_angle
        if ratio > 1.0:
            best = max(best, aiming_time * math.log(ratio))
    return max(best, 0.0)


def reset_floor_tracker():
    pass


AIMING_RUNTIME = {
    'vehicle_id': None,
    'ideal_dispersion': None,
    'aiming_time': 0.0,
}
_AIMING_DEBUG_LAST_TIME = -9999.0


def _reset_aiming_runtime():
    AIMING_RUNTIME['vehicle_id'] = None
    AIMING_RUNTIME['ideal_dispersion'] = None
    AIMING_RUNTIME['aiming_time'] = 0.0


def _aiming_debug_log(message):
    if not SETTINGS.get('debug_aim_logging', False):
        return
    global _AIMING_DEBUG_LAST_TIME
    try:
        now = BigWorld.time() if BigWorld is not None else 0.0
    except Exception:
        now = 0.0
    if now - _AIMING_DEBUG_LAST_TIME < 1.0:
        return
    _AIMING_DEBUG_LAST_TIME = now
    log('[AIM_DEBUG] %s' % message)


MOD_ID = 'caphhh.currentAccAndAimTime'
MOD_NAME = 'Current Accuracy & Aim Time'
MOD_VERSION = '1.0.0'
CONFIG_FOLDER_NAME = 'currentAccAndAimTime'
CONFIG_RELATIVE_PATH = os.path.join('mods', 'configs', CONFIG_FOLDER_NAME, 'config.json')
DEFAULT_FONT_CHOICES = (
    'default_small.font',
    'default_medium.font',
    'default_large.font',
)
DEFAULT_SETTINGS = {
    'enabled': True,
    'show_dispersion': True,
    'show_aim_time': True,
    'debug_aim_logging': False,
    'font_size': 28.0,
    'font_name': DEFAULT_FONT_CHOICES[1],
    'decimal_dispersion': 3,
    'decimal_aim_time': 1,
    'offset_x': 0.05,
    'offset_y': 0.05,
    'line_spacing': 0.02,
    'color': [255, 255, 255, 255],
}


def _build_float_range(start, stop, step):
    values = []
    current = int(round(start / step))
    finish = int(round(stop / step))
    while current <= finish:
        values.append(round(current * step, 3))
        current += 1
    return values


SETTING_OPTIONS = {
    'font_size': [float(value) for value in range(8, 49)],
    'font_name': list(DEFAULT_FONT_CHOICES),
    'decimal_dispersion': [value for value in range(0, 7)],
    'decimal_aim_time': [value for value in range(0, 5)],
    'offset_x': _build_float_range(-0.30, 0.30, 0.01),
    'offset_y': _build_float_range(-0.30, 0.30, 0.01),
    'line_spacing': _build_float_range(0.00, 0.10, 0.005),
}

try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)

try:
    INTEGER_TYPES = (int, long)
except NameError:
    INTEGER_TYPES = (int,)


SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
SETTINGS_TEMPLATE = None
HOOKS_INSTALLED = False


def log(message):
    LOG_WARNING('[%s] %s' % (MOD_NAME, message))


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _to_bool(value, default):
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return default


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_color(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return list(DEFAULT_SETTINGS['color'])
    result = []
    for channel in value:
        result.append(int(_clamp(_to_int(channel, 255), 0, 255)))
    return result


def sanitize_settings(raw_settings):
    data = copy.deepcopy(DEFAULT_SETTINGS)
    if isinstance(raw_settings, dict):
        data.update(raw_settings)

    data['enabled'] = _to_bool(data.get('enabled'), DEFAULT_SETTINGS['enabled'])
    data['show_dispersion'] = _to_bool(data.get('show_dispersion'), DEFAULT_SETTINGS['show_dispersion'])
    data['show_aim_time'] = _to_bool(data.get('show_aim_time'), DEFAULT_SETTINGS['show_aim_time'])
    data['debug_aim_logging'] = _to_bool(data.get('debug_aim_logging'), DEFAULT_SETTINGS['debug_aim_logging'])
    data['font_size'] = _clamp(_to_float(data.get('font_size'), DEFAULT_SETTINGS['font_size']), 8.0, 48.0)
    data['font_name'] = data.get('font_name')
    if data['font_name'] not in DEFAULT_FONT_CHOICES:
        data['font_name'] = DEFAULT_SETTINGS['font_name']
    data['decimal_dispersion'] = _clamp(_to_int(data.get('decimal_dispersion'), DEFAULT_SETTINGS['decimal_dispersion']), 0, 6)
    data['decimal_aim_time'] = _clamp(_to_int(data.get('decimal_aim_time'), DEFAULT_SETTINGS['decimal_aim_time']), 0, 4)
    data['offset_x'] = _clamp(_to_float(data.get('offset_x'), DEFAULT_SETTINGS['offset_x']), -0.5, 0.5)
    data['offset_y'] = _clamp(_to_float(data.get('offset_y'), DEFAULT_SETTINGS['offset_y']), -0.5, 0.5)
    data['line_spacing'] = _clamp(_to_float(data.get('line_spacing'), DEFAULT_SETTINGS['line_spacing']), 0.0, 0.2)
    data['color'] = _normalize_color(data.get('color'))
    return data


def get_config_path():
    return CONFIG_RELATIVE_PATH


def ensure_config_directory():
    config_path = get_config_path()
    config_dir = os.path.dirname(config_path)
    if config_dir and not os.path.isdir(config_dir):
        os.makedirs(config_dir)


def load_config():
    global SETTINGS
    config_path = get_config_path()
    if not os.path.isfile(config_path):
        SETTINGS = sanitize_settings(DEFAULT_SETTINGS)
        save_config()
        return

    try:
        config_file = open(config_path, 'r')
        try:
            SETTINGS = sanitize_settings(json.load(config_file))
        finally:
            config_file.close()
    except Exception:
        LOG_CURRENT_EXCEPTION()
        SETTINGS = sanitize_settings(DEFAULT_SETTINGS)


def save_config():
    config_path = get_config_path()
    try:
        ensure_config_directory()
        config_file = open(config_path, 'w')
        try:
            json.dump(SETTINGS, config_file, indent=4, sort_keys=True)
        finally:
            config_file.close()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def detour(original, hook):
    def wrapper(*args, **kwargs):
        return hook(original, *args, **kwargs)

    wrapper._caphhh_wrapped = True
    wrapper._caphhh_original = original
    return wrapper


def install_hook(target, attribute_name, hook):
    original = getattr(target, attribute_name, None)
    if not callable(original):
        log('Skipped missing hook target %s.%s' % (target.__name__, attribute_name))
        return False
    if getattr(original, '_caphhh_wrapped', False):
        return True
    setattr(target, attribute_name, detour(original, hook))
    return True


class CrosshairTextRenderer(object):
    def __init__(self):
        self._dispersion_label = None
        self._aim_time_label = None
        self._guiflash_created = set()
        self._label_aliases = {
            'dispersion': 'caphhhCurrentDispersionLabel',
            'aim_time': 'caphhhAimTimeLabel',
        }

    def _is_guiflash_ready(self):
        return g_guiFlash is not None and COMPONENT_TYPE is not None

    def _color_to_html(self):
        color = SETTINGS['color']
        return '#%02X%02X%02X' % (color[0], color[1], color[2])

    def _make_html_text(self, text):
        return "<font size='%d' color='%s'>%s</font>" % (
            int(round(SETTINGS['font_size'])),
            self._color_to_html(),
            text,
        )

    def _create_or_update_guiflash_label(self, alias, text, line_index):
        if not self._is_guiflash_ready():
            return

        screen_width = 1920
        screen_height = 1080
        if BigWorld is not None:
            try:
                screen_width = max(1, int(BigWorld.screenWidth()))
                screen_height = max(1, int(BigWorld.screenHeight()))
            except Exception:
                pass

        x_position = int(SETTINGS['offset_x'] * screen_width)
        y_position = int((SETTINGS['offset_y'] * screen_height) + (SETTINGS['line_spacing'] * screen_height * line_index))

        props = {
            'text': self._make_html_text(text),
            'x': x_position,
            'y': y_position,
            'alignX': 'center',
            'alignY': 'center',
            'visible': True,
        }

        if alias in self._guiflash_created:
            try:
                g_guiFlash.updateComponent(alias, props, None)
                return
            except Exception:
                try:
                    g_guiFlash.deleteComponent(alias)
                except Exception:
                    pass
                self._guiflash_created.discard(alias)

        g_guiFlash.createComponent(alias, COMPONENT_TYPE.LABEL, props)
        self._guiflash_created.add(alias)

    def _delete_guiflash_label(self, alias):
        if not self._is_guiflash_ready():
            return
        if alias not in self._guiflash_created:
            return
        try:
            g_guiFlash.deleteComponent(alias)
        except Exception:
            pass
        self._guiflash_created.discard(alias)

    def _create_label(self):
        if self._is_guiflash_ready():
            return True
        if GUI is None:
            return None
        try:
            label = GUI.Text('')
        except Exception:
            LOG_CURRENT_EXCEPTION()
            return None

        self._safe_set(label, 'visible', False)
        self._safe_set(label, 'horizontalAnchor', 'CENTER')
        self._safe_set(label, 'verticalAnchor', 'CENTER')
        self._safe_set(label, 'horizontalPositionMode', 'PIXEL')
        self._safe_set(label, 'verticalPositionMode', 'PIXEL')
        self._safe_set(label, 'colourFormatting', True)
        self._safe_set(label, 'explicitSize', (400, 40))
        self._safe_set(label, 'text', '')
        self._safe_set(label, 'font', SETTINGS['font_name'])
        self._safe_set(label, 'scale', SETTINGS['font_size'] / 16.0)
        self._safe_set(label, 'position', (0, 0, 0.75))
        self._safe_set(label, 'colour', tuple(SETTINGS['color']))

        try:
            GUI.addRoot(label)
        except Exception:
            LOG_CURRENT_EXCEPTION()
            return None
        return label

    def _safe_set(self, target, attribute_name, value):
        try:
            setattr(target, attribute_name, value)
        except Exception:
            pass

    def _remove_label(self, label):
        if self._is_guiflash_ready():
            return
        if label is None or GUI is None:
            return
        try:
            GUI.delRoot(label)
        except Exception:
            pass

    def ensure(self):
        if self._is_guiflash_ready():
            return
        if self._dispersion_label is None:
            self._dispersion_label = self._create_label()
        if self._aim_time_label is None:
            self._aim_time_label = self._create_label()

    def destroy(self):
        for alias in self._label_aliases.values():
            self._delete_guiflash_label(alias)
        self._remove_label(self._dispersion_label)
        self._remove_label(self._aim_time_label)
        self._dispersion_label = None
        self._aim_time_label = None

    def apply_settings(self):
        if self._is_guiflash_ready():
            return
        for label in (self._dispersion_label, self._aim_time_label):
            if label is None:
                continue
            self._safe_set(label, 'font', SETTINGS['font_name'])
            self._safe_set(label, 'scale', SETTINGS['font_size'] / 16.0)
            self._safe_set(label, 'colour', tuple(SETTINGS['color']))

    def _set_label_state(self, label, text, line_index):
        if label is None:
            return

        screen_width = 1920
        screen_height = 1080
        if BigWorld is not None:
            try:
                screen_width = max(1, int(BigWorld.screenWidth()))
                screen_height = max(1, int(BigWorld.screenHeight()))
            except Exception:
                pass

        x_position = int((screen_width * 0.5) + (SETTINGS['offset_x'] * screen_width))
        y_position = int((screen_height * 0.5) + (SETTINGS['offset_y'] * screen_height) + (SETTINGS['line_spacing'] * screen_height * line_index))

        self._safe_set(label, 'text', text)
        self._safe_set(label, 'position', (x_position, y_position, 0.75))
        self._safe_set(label, 'visible', True)

    def hide(self):
        if self._is_guiflash_ready():
            for alias in self._label_aliases.values():
                self._delete_guiflash_label(alias)
            return
        for label in (self._dispersion_label, self._aim_time_label):
            if label is not None:
                self._safe_set(label, 'visible', False)

    def update(self, dispersion, aim_time_remaining):
        if GUI is None and not self._is_guiflash_ready():
            return

        self.ensure()
        self.apply_settings()

        if not SETTINGS['enabled']:
            self.hide()
            return

        visible_texts = []
        if SETTINGS['show_dispersion']:
            visible_texts.append(('dispersion', ('%%.%df' % SETTINGS['decimal_dispersion']) % dispersion))
        if SETTINGS['show_aim_time']:
            visible_texts.append(('aim_time', ('%%.%df' % SETTINGS['decimal_aim_time']) % aim_time_remaining + 's'))

        if not visible_texts:
            self.hide()
            return

        shown_kinds = set()
        line_index = 0
        for kind, text in visible_texts:
            shown_kinds.add(kind)
            if self._is_guiflash_ready():
                self._create_or_update_guiflash_label(self._label_aliases[kind], text, line_index)
            elif kind == 'dispersion':
                self._set_label_state(self._dispersion_label, text, line_index)
            elif kind == 'aim_time':
                self._set_label_state(self._aim_time_label, text, line_index)
            line_index += 1

        for kind in ('dispersion', 'aim_time'):
            if kind in shown_kinds:
                continue
            if self._is_guiflash_ready():
                self._delete_guiflash_label(self._label_aliases[kind])
            elif kind == 'dispersion' and self._dispersion_label is not None:
                self._safe_set(self._dispersion_label, 'visible', False)
            elif kind == 'aim_time' and self._aim_time_label is not None:
                self._safe_set(self._aim_time_label, 'visible', False)


RENDERER = CrosshairTextRenderer()


def apply_runtime_settings():
    try:
        RENDERER.apply_settings()
        RENDERER.hide()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _try_get_player():
    if BigWorld is None:
        return None
    try:
        return BigWorld.player()
    except Exception:
        return None


def calculate_aim_time_remaining(avatar, dispersion_result, turret_rotation_speed, with_shot):
    """
    Remaining aim time (wotstat-style, all inlined — no external module):
      ideal = vehicleTypeDescriptor.gun.shotDispersionAngle * dispersionInfo[0]
      time  = aimingTime * ln(current_dispersion_angle / ideal)
    """
    if BigWorld is None or avatar is None or dispersion_result is None:
        return 0.0

    try:
        vehicle_id = getattr(avatar, 'playerVehicleID', None)
        ideal = AIMING_RUNTIME['ideal_dispersion']
        aiming_time = AIMING_RUNTIME['aiming_time']
        if AIMING_RUNTIME['vehicle_id'] != vehicle_id or aiming_time <= 0.0:
            aiming_time = _caphhh_resolve_aiming_time_seconds(avatar)
        if aiming_time <= 0.0:
            _aiming_debug_log('aiming_time<=0 di=%r runtime=%r' % (_caphhh_get_dispersion_info(avatar), AIMING_RUNTIME))
            return 0.0

        ideal = _caphhh_get_stationary_ideal_from_result(avatar, dispersion_result, turret_rotation_speed, with_shot)
        if ideal is None or ideal <= 0.0:
            ideal = AIMING_RUNTIME['ideal_dispersion']
        if ideal is None or ideal <= 0.0:
            _aiming_debug_log('ideal<=0 di=%r runtime=%r' % (_caphhh_get_dispersion_info(avatar), AIMING_RUNTIME))
            return 0.0

        r = dispersion_result
        currents = [float(r[0])]
        if len(r) > 3:
            try:
                currents.append(float(r[2]))
            except Exception:
                pass

        aim_remaining = _caphhh_compute_aim_time(aiming_time, currents, ideal)
        _aiming_debug_log('di=%r ideal=%r aiming_time=%r currents=%r remain=%r turret=%r with_shot=%r runtime=%r' % (
            _caphhh_get_dispersion_info(avatar),
            ideal,
            aiming_time,
            currents,
            aim_remaining,
            turret_rotation_speed,
            with_shot,
            AIMING_RUNTIME
        ))
        return aim_remaining
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0.0


def update_display(avatar, dispersion, aim_time_remaining):
    if avatar is None:
        return

    player = _try_get_player()
    if player is not None and avatar is not player:
        return

    RENDERER.update(dispersion, aim_time_remaining)


def hook_get_own_vehicle_shot_dispersion_angle(original, self, turret_rotation_speed, with_shot=0):
    result = original(self, turret_rotation_speed, with_shot)
    try:
        current_dispersion = float(result[0]) * 100.0
        aim_time_remaining = calculate_aim_time_remaining(self, result, turret_rotation_speed, with_shot)
        update_display(self, current_dispersion, aim_time_remaining)
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return result


def hook_update_targeting_info(
    original,
    self,
    entityId,
    turretYaw,
    gunPitch,
    maxTurretRotationSpeed,
    maxGunRotationSpeed,
    shotDispMultiplierFactor,
    gunShotDispersionFactorsTurretRotation,
    chassisShotDispersionFactorsMovement,
    chassisShotDispersionFactorsRotation,
    gunShotDispersionFactorsAfterShot,
    aimingTime
):
    result = original(
        self,
        entityId,
        turretYaw,
        gunPitch,
        maxTurretRotationSpeed,
        maxGunRotationSpeed,
        shotDispMultiplierFactor,
        gunShotDispersionFactorsTurretRotation,
        chassisShotDispersionFactorsMovement,
        chassisShotDispersionFactorsRotation,
        gunShotDispersionFactorsAfterShot,
        aimingTime
    )
    try:
        if entityId != getattr(self, 'playerVehicleID', None):
            return result
        di = _caphhh_get_dispersion_info(self)
        descr = getattr(self, 'vehicleTypeDescriptor', None)
        gun = getattr(descr, 'gun', None) if descr is not None else None
        if gun is None:
            _aiming_debug_log('updateTargetingInfo gun=None di=%r entityId=%r playerVehicleID=%r' % (
                di,
                entityId,
                getattr(self, 'playerVehicleID', None)
            ))
            return result
        if hasattr(gun, 'get'):
            base = gun.get('shotDispersionAngle')
        elif isinstance(gun, dict):
            base = gun.get('shotDispersionAngle')
        else:
            base = getattr(gun, 'shotDispersionAngle', None)
        if base is None:
            _aiming_debug_log('updateTargetingInfo base=None di=%r gun=%r' % (di, gun))
            return result
        base = float(base)
        mult = None
        atime = None
        if di is not None:
            try:
                if len(di) > 0:
                    mult = float(di[0])
            except Exception:
                mult = None
            for idx in (5, 4):
                try:
                    if len(di) > idx:
                        candidate = float(di[idx])
                        if candidate > 0.0:
                            atime = candidate
                            break
                except Exception:
                    continue
        if mult is None:
            try:
                mult = float(shotDispMultiplierFactor)
            except Exception:
                mult = None
        if atime is None:
            try:
                atime = float(aimingTime)
            except Exception:
                atime = None
        if base > 0.0 and mult is not None and mult > 0.0 and atime is not None and atime > 0.0:
            AIMING_RUNTIME['vehicle_id'] = entityId
            AIMING_RUNTIME['ideal_dispersion'] = base * mult
            AIMING_RUNTIME['aiming_time'] = atime
        _aiming_debug_log('updateTargetingInfo di=%r base=%r arg_mult=%r arg_aim=%r cached_mult=%r cached_aim=%r runtime=%r' % (
            di,
            base,
            shotDispMultiplierFactor,
            aimingTime,
            mult,
            atime,
            AIMING_RUNTIME
        ))
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return result


def hook_on_become_player(original, self):
    result = original(self)
    try:
        _reset_aiming_runtime()
        reset_floor_tracker()
        RENDERER.ensure()
        RENDERER.hide()
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return result


def hook_on_become_non_player(original, self):
    try:
        _reset_aiming_runtime()
        reset_floor_tracker()
        RENDERER.destroy()
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return original(self)


def hook_destroy(original, self):
    try:
        player = _try_get_player()
        if self is player:
            _reset_aiming_runtime()
            reset_floor_tracker()
            RENDERER.destroy()
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return original(self)


def make_checkbox(title, variable_name, default_value, tooltip=''):
    if templates is None:
        return None
    try:
        return templates.createCheckbox(title, variable_name, default_value, tooltip=tooltip)
    except Exception:
        return None


def make_dropdown(title, variable_name, options, default_value, tooltip=''):
    if templates is None:
        return None
    try:
        return templates.createDropdown(title, variable_name, options, default_value, tooltip=tooltip)
    except Exception:
        return None


def _try_template_calls(method_name, variants, kwargs=None):
    if templates is None or not hasattr(templates, method_name):
        return None
    method = getattr(templates, method_name)
    kwargs = kwargs or {}
    for args in variants:
        try:
            return method(*args, **kwargs)
        except Exception:
            continue
    return None


def make_slider(title, variable_name, default_value, minimum, maximum, step, tooltip=''):
    format_string = '%.2f' if step < 1 else '%d'
    variants = (
        (title, variable_name, minimum, maximum, default_value, step),
        (title, variable_name, default_value, minimum, maximum, step),
        (title, variable_name, minimum, maximum, step, default_value),
        (title, variable_name, minimum, maximum, default_value),
    )
    return _try_template_calls(
        'createSlider',
        variants,
        {'format': format_string, 'tooltip': tooltip}
    )


def _make_option_label(value):
    if isinstance(value, float):
        if abs(value) < 0.0005:
            value = 0.0
        if abs(value - int(round(value))) < 0.0005:
            return str(int(round(value)))
        return ('%.3f' % value).rstrip('0').rstrip('.')
    return str(value)


def _find_option_index(options, current_value):
    for index, option in enumerate(options):
        if isinstance(option, float):
            if abs(option - float(current_value)) < 0.0005:
                return index
        elif option == current_value:
            return index
    return 0


def make_option_dropdown(title, variable_name, current_value, tooltip=''):
    options = SETTING_OPTIONS.get(variable_name, [])
    labels = [_make_option_label(value) for value in options]
    default_index = _find_option_index(options, current_value)
    return make_dropdown(title, variable_name, labels, default_index, tooltip=tooltip)


def make_stepper(title, variable_name, default_value, minimum, maximum, step, tooltip=''):
    variants = (
        (title, variable_name, default_value, minimum, maximum, step),
        (title, variable_name, minimum, maximum, default_value, step),
        (title, variable_name, range(minimum, maximum + 1, step), default_value),
    )
    control = _try_template_calls('createStepper', variants, {'tooltip': tooltip})
    if control is None:
        options = [str(value) for value in range(minimum, maximum + 1, step)]
        default_index = int(_clamp(default_value - minimum, 0, len(options) - 1))
        control = make_dropdown(title, variable_name, options, default_index, tooltip=tooltip)
    return control


def build_settings_template():
    controls = []
    controls.append(make_checkbox('Enable mod (master switch)', 'enabled', SETTINGS['enabled']))
    controls.append(make_checkbox('Show current accuracy (dispersion line)', 'show_dispersion', SETTINGS['show_dispersion']))
    controls.append(make_checkbox('Show remaining aim time (seconds line)', 'show_aim_time', SETTINGS['show_aim_time']))
    controls.append(make_checkbox('Debug aim logging ([AIM_DEBUG] in python.log, throttled)', 'debug_aim_logging', SETTINGS.get('debug_aim_logging', False)))
    controls.append(make_option_dropdown('Font size (text size)', 'font_size', SETTINGS['font_size']))
    controls.append(make_option_dropdown('Font (game font preset)', 'font_name', SETTINGS['font_name']))
    controls.append(make_option_dropdown('Dispersion decimals (digits after dot)', 'decimal_dispersion', SETTINGS['decimal_dispersion']))
    controls.append(make_option_dropdown('Aim time decimals (digits after dot)', 'decimal_aim_time', SETTINGS['decimal_aim_time']))
    controls.append(make_option_dropdown('Horizontal offset (move text left/right)', 'offset_x', SETTINGS['offset_x']))
    controls.append(make_option_dropdown('Vertical offset (move text up/down)', 'offset_y', SETTINGS['offset_y']))
    controls.append(make_option_dropdown('Line spacing (gap between the 2 lines)', 'line_spacing', SETTINGS['line_spacing']))

    filtered_controls = [control for control in controls if control is not None]
    mid = (len(filtered_controls) + 1) // 2
    return {
        'modDisplayName': MOD_NAME,
        'enabled': SETTINGS['enabled'],
        'column1': filtered_controls[:mid],
        'column2': filtered_controls[mid:],
    }


def _resolve_font_name(new_settings):
    font_value = new_settings.get('font_name', SETTINGS['font_name'])
    if isinstance(font_value, INTEGER_TYPES):
        font_index = int(_clamp(font_value, 0, len(DEFAULT_FONT_CHOICES) - 1))
        return DEFAULT_FONT_CHOICES[font_index]
    if isinstance(font_value, STRING_TYPES) and font_value in DEFAULT_FONT_CHOICES:
        return font_value
    return SETTINGS['font_name']


def normalize_settings_payload(raw_settings):
    normalized = copy.deepcopy(raw_settings) if isinstance(raw_settings, dict) else {}
    for variable_name, options in SETTING_OPTIONS.items():
        if variable_name not in normalized:
            continue
        raw_value = normalized[variable_name]
        if variable_name == 'font_name':
            normalized['font_name'] = _resolve_font_name(normalized)
            continue
        if isinstance(raw_value, INTEGER_TYPES):
            option_index = int(_clamp(raw_value, 0, len(options) - 1))
            normalized[variable_name] = options[option_index]
    if 'font_name' in normalized:
        normalized['font_name'] = _resolve_font_name(normalized)
    return normalized


def on_settings_changed(linkage, new_settings):
    global SETTINGS
    if linkage != MOD_ID or not isinstance(new_settings, dict):
        return

    patched_settings = copy.deepcopy(SETTINGS)
    patched_settings.update(normalize_settings_payload(new_settings))
    SETTINGS = sanitize_settings(patched_settings)
    save_config()
    apply_runtime_settings()


def register_mod_settings():
    global SETTINGS
    global SETTINGS_TEMPLATE
    if g_modsSettingsApi is None or templates is None:
        return

    SETTINGS_TEMPLATE = build_settings_template()
    try:
        saved_settings = g_modsSettingsApi.getModSettings(MOD_ID, SETTINGS_TEMPLATE)
    except Exception:
        saved_settings = None

    if saved_settings:
        SETTINGS = sanitize_settings(normalize_settings_payload(saved_settings))
        save_config()
        apply_runtime_settings()
        try:
            g_modsSettingsApi.registerCallback(MOD_ID, on_settings_changed)
        except Exception:
            pass
        log('ModSettingsAPI settings loaded.')
        return

    try:
        api_settings = g_modsSettingsApi.setModTemplate(MOD_ID, SETTINGS_TEMPLATE, on_settings_changed)
        if api_settings:
            SETTINGS = sanitize_settings(normalize_settings_payload(api_settings))
            save_config()
            apply_runtime_settings()
        log('ModSettingsAPI template registered.')
    except Exception:
        LOG_CURRENT_EXCEPTION()


def register_mods_list():
    metadata = {
        'id': MOD_ID,
        'name': MOD_NAME,
        'description': 'Shows live dispersion and remaining aim time near the crosshair.',
        'version': MOD_VERSION,
    }
    candidates = (
        ('gui.modsListApi', 'g_modsListApi'),
        ('gui.modsListApi', 'g_modsListAPI'),
        ('gui.modsListApi.api', 'g_modsListApi'),
        ('gui.mods.mod_mods_gui', 'g_modsListApi'),
    )
    for module_name, attribute_name in candidates:
        try:
            module = __import__(module_name, globals(), locals(), [attribute_name], 0)
            api = getattr(module, attribute_name, None)
        except Exception:
            api = None
        if api is None:
            continue

        for method_name in ('addModification', 'addMod', 'registerMod', 'appendMod'):
            method = getattr(api, method_name, None)
            if not callable(method):
                continue
            try:
                method(metadata)
                log('ModsListAPI registered via %s.%s' % (module_name, method_name))
                return
            except TypeError:
                try:
                    method(MOD_ID, MOD_NAME, metadata['description'])
                    log('ModsListAPI registered via %s.%s' % (module_name, method_name))
                    return
                except Exception:
                    continue
            except Exception:
                continue


def install_hooks():
    global HOOKS_INSTALLED
    if HOOKS_INSTALLED:
        return

    install_hook(PlayerAvatar, 'getOwnVehicleShotDispersionAngle', hook_get_own_vehicle_shot_dispersion_angle)
    install_hook(PlayerAvatar, 'updateTargetingInfo', hook_update_targeting_info)
    install_hook(PlayerAvatar, 'onBecomePlayer', hook_on_become_player)
    install_hook(PlayerAvatar, 'onBecomeNonPlayer', hook_on_become_non_player)
    install_hook(PlayerAvatar, 'destroy', hook_destroy)
    HOOKS_INSTALLED = True


def init():
    load_config()
    install_hooks()
    register_mod_settings()
    register_mods_list()
    apply_runtime_settings()
    log('Loaded successfully.')


def fini():
    try:
        _reset_aiming_runtime()
        RENDERER.destroy()
    finally:
        log('Unloaded.')


init()
