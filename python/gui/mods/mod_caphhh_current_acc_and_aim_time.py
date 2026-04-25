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
    import gambiter.flash as gambiter_flash_module
    from gambiter.flash import COMPONENT_TYPE
    _GUIFLASH_IMPORT_ERROR = None
except Exception as exc:
    _GUIFLASH_IMPORT_ERROR = repr(exc)
    g_guiFlash = None
    gambiter_flash_module = None
    COMPONENT_TYPE = None

try:
    from Avatar import PlayerAvatar
except ImportError:
    class PlayerAvatar(object):
        pass

try:
    from AvatarInputHandler import AvatarInputHandler
except ImportError:
    AvatarInputHandler = None

try:
    from gui import InputHandler
except ImportError:
    InputHandler = None

try:
    import Keys
except ImportError:
    Keys = None

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
                    if v is None:
                        v = _caphhh_get_value(gun, key)
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
        base = _caphhh_get_value(gun, 'shotDispersionAngle')
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
_DRAG_DEBUG_LAST_TIME = -9999.0

# Minimum spacing between HUD refreshes; actual value is SETTINGS['display_update_interval'].
_last_display_update_time = None

# Last values shown on HUD (for repositioning during Ctrl+drag without a fresh dispersion sample).
_last_hud_dispersion = 0.0
_last_hud_aim_time = 0.0


def _now_display_clock():
    if BigWorld is not None:
        try:
            return BigWorld.time()
        except Exception:
            pass
    import time
    return time.time()


def _reset_aiming_runtime():
    global _last_display_update_time
    AIMING_RUNTIME['vehicle_id'] = None
    AIMING_RUNTIME['ideal_dispersion'] = None
    AIMING_RUNTIME['aiming_time'] = 0.0
    _last_display_update_time = None


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


def _drag_debug_log(message, force=False):
    if not SETTINGS.get('debug_drag_logging', False):
        return
    global _DRAG_DEBUG_LAST_TIME
    try:
        now = BigWorld.time() if BigWorld is not None else 0.0
    except Exception:
        now = 0.0
    if not force and now - _DRAG_DEBUG_LAST_TIME < 0.25:
        return
    _DRAG_DEBUG_LAST_TIME = now
    log('[DRAG_DEBUG] %s' % message)


MOD_ID = 'caphhh.realtimeDispersionAimTimeRemaining'
MOD_NAME = 'Realtime Dispersion & Aim Time Remaining'
MOD_VERSION = '1.1.4'
CONFIG_FOLDER_NAME = 'RealtimeDispersion&AimTimeRemaining'
CONFIG_RELATIVE_PATH = os.path.join('mods', 'configs', CONFIG_FOLDER_NAME, 'config.json')
LEGACY_CONFIG_RELATIVE_PATHS = (
    os.path.join('mods', 'configs', 'currentAccAndAimTime', 'config.json'),
    os.path.join('mods', 'configs', 'caphhh.current_acc_and_aim_time', 'config.json'),
)
DEFAULT_FONT_CHOICES = (
    'default_small.font',
    'default_medium.font',
    'default_large.font',
)

# Seconds between HUD text updates; 0 = no throttle (every getOwnVehicleShotDispersionAngle call).
DEFAULT_DISPLAY_UPDATE_INTERVAL = 0.033

DEFAULT_SETTINGS = {
    'enabled': True,
    'show_dispersion': True,
    'show_aim_time': True,
    'debug_aim_logging': False,
    'debug_drag_logging': False,
    'font_size': 24.0,
    'font_name': DEFAULT_FONT_CHOICES[1],
    'decimal_dispersion': 3,
    'decimal_aim_time': 2,
    'offset_x': 0.0,
    'offset_y': 0.0,
    'offset_x_arcade': 0.0,
    'offset_y_arcade': 0.0,
    'offset_x_sniper': 0.0,
    'offset_y_sniper': 0.0,
    'line_spacing': 0.02,
    'display_update_interval': DEFAULT_DISPLAY_UPDATE_INTERVAL,
    'color': [235, 248, 255, 255],
    # Mirrors DistanceMarker-style ModsSettingsAPI: ColorChoice + alpha slider + shadow checkbox.
    'text_color_hex': 'EBF8FF',
    'text_alpha': 1.0,
    'text_shadow': False,
    'text_shadow_alpha': 0.45,
}
POSITION_SETTING_KEYS = (
    'offset_x',
    'offset_y',
    'offset_x_arcade',
    'offset_y_arcade',
    'offset_x_sniper',
    'offset_y_sniper',
)


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
    'offset_x_arcade': _build_float_range(-0.30, 0.30, 0.01),
    'offset_y_arcade': _build_float_range(-0.30, 0.30, 0.01),
    'offset_x_sniper': _build_float_range(-0.30, 0.30, 0.01),
    'offset_y_sniper': _build_float_range(-0.30, 0.30, 0.01),
    'line_spacing': _build_float_range(0.00, 0.10, 0.005),
    'display_update_interval': (
        0.0,
        1.0 / 120.0,
        1.0 / 60.0,
        1.0 / 30.0,
        DEFAULT_DISPLAY_UPDATE_INTERVAL,
        0.25,
        0.5,
        1.0,
        2.0,
    ),
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


def _rgb_tuple_to_hex_upper(rgb):
    try:
        return '%02X%02X%02X' % (
            int(_clamp(_to_int(rgb[0], 255), 0, 255)),
            int(_clamp(_to_int(rgb[1], 255), 0, 255)),
            int(_clamp(_to_int(rgb[2], 255), 0, 255)),
        )
    except Exception:
        return DEFAULT_SETTINGS['text_color_hex']


def _hex_string_to_rgb_three(value):
    if value is None:
        return None
    if isinstance(value, STRING_TYPES):
        s = value.strip().lstrip('#').upper()
        if len(s) >= 6:
            s = s[:6]
            try:
                return (
                    int(s[0:2], 16),
                    int(s[2:4], 16),
                    int(s[4:6], 16),
                )
            except Exception:
                return None
    return None


def sanitize_settings(raw_settings):
    data = copy.deepcopy(DEFAULT_SETTINGS)
    raw_keys = set(raw_settings.keys()) if isinstance(raw_settings, dict) else set()
    if isinstance(raw_settings, dict):
        data.update(raw_settings)

    data['enabled'] = _to_bool(data.get('enabled'), DEFAULT_SETTINGS['enabled'])
    data['show_dispersion'] = _to_bool(data.get('show_dispersion'), DEFAULT_SETTINGS['show_dispersion'])
    data['show_aim_time'] = _to_bool(data.get('show_aim_time'), DEFAULT_SETTINGS['show_aim_time'])
    data['debug_aim_logging'] = _to_bool(data.get('debug_aim_logging'), DEFAULT_SETTINGS['debug_aim_logging'])
    data['debug_drag_logging'] = _to_bool(data.get('debug_drag_logging'), DEFAULT_SETTINGS['debug_drag_logging'])
    data['font_size'] = _clamp(_to_float(data.get('font_size'), DEFAULT_SETTINGS['font_size']), 8.0, 48.0)
    data['font_name'] = data.get('font_name')
    if data['font_name'] not in DEFAULT_FONT_CHOICES:
        data['font_name'] = DEFAULT_SETTINGS['font_name']
    data['decimal_dispersion'] = _clamp(_to_int(data.get('decimal_dispersion'), DEFAULT_SETTINGS['decimal_dispersion']), 0, 6)
    data['decimal_aim_time'] = _clamp(_to_int(data.get('decimal_aim_time'), DEFAULT_SETTINGS['decimal_aim_time']), 0, 4)
    data['offset_x'] = _clamp(_to_float(data.get('offset_x'), DEFAULT_SETTINGS['offset_x']), -0.5, 0.5)
    data['offset_y'] = _clamp(_to_float(data.get('offset_y'), DEFAULT_SETTINGS['offset_y']), -0.5, 0.5)
    data['offset_x_arcade'] = _clamp(_to_float(data.get('offset_x_arcade'), data['offset_x']), -0.5, 0.5)
    data['offset_y_arcade'] = _clamp(_to_float(data.get('offset_y_arcade'), data['offset_y']), -0.5, 0.5)
    data['offset_x_sniper'] = _clamp(_to_float(data.get('offset_x_sniper'), data['offset_x']), -0.5, 0.5)
    data['offset_y_sniper'] = _clamp(_to_float(data.get('offset_y_sniper'), data['offset_y']), -0.5, 0.5)
    data['line_spacing'] = _clamp(_to_float(data.get('line_spacing'), DEFAULT_SETTINGS['line_spacing']), 0.0, 0.2)
    interval = _to_float(data.get('display_update_interval'), DEFAULT_SETTINGS['display_update_interval'])
    if interval <= 0.0:
        data['display_update_interval'] = 0.0
    else:
        data['display_update_interval'] = _clamp(interval, 1.0 / 360.0, 10.0)
    data['color'] = _normalize_color(data.get('color'))

    if 'text_alpha' not in raw_keys:
        data['text_alpha'] = _clamp(float(data['color'][3]) / 255.0, 0.0, 1.0)
    else:
        data['text_alpha'] = _clamp(_to_float(data.get('text_alpha'), DEFAULT_SETTINGS['text_alpha']), 0.0, 1.0)
    data['text_shadow'] = _to_bool(data.get('text_shadow'), DEFAULT_SETTINGS['text_shadow'])
    data['text_shadow_alpha'] = _clamp(_to_float(data.get('text_shadow_alpha'), DEFAULT_SETTINGS['text_shadow_alpha']), 0.0, 1.0)
    try:
        data['color'][3] = int(round(data['text_alpha'] * 255.0))
    except Exception:
        data['color'][3] = int(round(DEFAULT_SETTINGS['text_alpha'] * 255.0))

    if 'text_color_hex' in raw_keys:
        hex_in = data.get('text_color_hex', '')
        if isinstance(hex_in, STRING_TYPES):
            rgb = _hex_string_to_rgb_three(hex_in)
            if rgb is not None:
                data['color'][0], data['color'][1], data['color'][2] = rgb
    data['text_color_hex'] = _rgb_tuple_to_hex_upper(data['color'])

    # Keep legacy keys in sync with current mode defaults for backward compatibility.
    data['offset_x'] = data['offset_x_arcade']
    data['offset_y'] = data['offset_y_arcade']

    return data


def _without_position_settings(raw_settings):
    if not isinstance(raw_settings, dict):
        return {}
    filtered = copy.deepcopy(raw_settings)
    for key in POSITION_SETTING_KEYS:
        filtered.pop(key, None)
    return filtered


def _get_ctrl_mode_name():
    if BigWorld is None:
        return ''
    try:
        avatar = BigWorld.player()
    except Exception:
        return ''
    if avatar is None:
        return ''
    try:
        handler = getattr(avatar, 'inputHandler', None)
        mode_name = getattr(handler, 'ctrlModeName', '') if handler is not None else ''
        return str(mode_name or '').lower()
    except Exception:
        return ''


def _is_sniper_mode():
    mode_name = _get_ctrl_mode_name()
    return 'sniper' in mode_name


def _get_active_offset_keys():
    if _is_sniper_mode():
        return 'offset_x_sniper', 'offset_y_sniper'
    return 'offset_x_arcade', 'offset_y_arcade'


def _get_active_offsets():
    x_key, y_key = _get_active_offset_keys()
    return (
        _clamp(_to_float(SETTINGS.get(x_key, SETTINGS.get('offset_x', DEFAULT_SETTINGS['offset_x'])), DEFAULT_SETTINGS['offset_x']), -0.5, 0.5),
        _clamp(_to_float(SETTINGS.get(y_key, SETTINGS.get('offset_y', DEFAULT_SETTINGS['offset_y'])), DEFAULT_SETTINGS['offset_y']), -0.5, 0.5),
    )


def _set_offsets_for_keys(x_key, y_key, offset_x, offset_y):
    SETTINGS[x_key] = _clamp(_to_float(offset_x, SETTINGS.get(x_key, 0.0)), -0.5, 0.5)
    SETTINGS[y_key] = _clamp(_to_float(offset_y, SETTINGS.get(y_key, 0.0)), -0.5, 0.5)
    # legacy mirror
    SETTINGS['offset_x'] = SETTINGS[x_key]
    SETTINGS['offset_y'] = SETTINGS[y_key]


def _set_active_offsets(offset_x, offset_y):
    x_key, y_key = _get_active_offset_keys()
    _set_offsets_for_keys(x_key, y_key, offset_x, offset_y)


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
    source_path = config_path
    if not os.path.isfile(config_path):
        source_path = None
        for legacy_path in LEGACY_CONFIG_RELATIVE_PATHS:
            if os.path.isfile(legacy_path):
                source_path = legacy_path
                break
        if source_path is None:
            SETTINGS = sanitize_settings(DEFAULT_SETTINGS)
            save_config()
            return

    try:
        config_file = open(source_path, 'r')
        try:
            SETTINGS = sanitize_settings(json.load(config_file))
        finally:
            config_file.close()
        if source_path != config_path:
            save_config()
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
        self._backend_logged = False
        self._first_update_logged = False
        self._guiflash_failure_logged = False
        self._label_aliases = {
            'dispersion': 'caphhhCurrentDispersionLabel',
            'aim_time': 'caphhhAimTimeLabel',
        }

    def _is_guiflash_ready(self):
        return g_guiFlash is not None and COMPONENT_TYPE is not None

    def _log_backend_once(self):
        if self._backend_logged:
            return
        self._backend_logged = True
        screen_width = 1920
        screen_height = 1080
        if BigWorld is not None:
            try:
                screen_width = max(1, int(BigWorld.screenWidth()))
                screen_height = max(1, int(BigWorld.screenHeight()))
            except Exception:
                pass
        offset_x, offset_y = _get_active_offsets()
        backend = 'gambiter.guiflash' if self._is_guiflash_ready() else 'GUI.Text'
        guiflash_ui = None
        guiflash_cache_size = None
        if gambiter_flash_module is not None:
            try:
                guiflash_ui = getattr(getattr(gambiter_flash_module, 'g_guiViews', None), 'ui', None) is not None
            except Exception:
                guiflash_ui = None
            try:
                cache = getattr(gambiter_flash_module, 'g_guiCache', None)
                if cache is not None and hasattr(cache, 'getKeys'):
                    guiflash_cache_size = len(cache.getKeys())
            except Exception:
                guiflash_cache_size = None
        log('Renderer backend=%s gui=%r guiflash=%r component_type=%r import_error=%r screen=%dx%d offsets=(%.4f, %.4f) line_spacing=%.4f' % (
            backend,
            GUI is not None,
            g_guiFlash is not None,
            COMPONENT_TYPE is not None,
            _GUIFLASH_IMPORT_ERROR,
            screen_width,
            screen_height,
            offset_x,
            offset_y,
            float(SETTINGS.get('line_spacing', 0.0)),
        ))
        log('Renderer backend state guiflash_ui=%r guiflash_cache_size=%r' % (
            guiflash_ui,
            guiflash_cache_size,
        ))

    def _log_first_update_once(self, visible_texts):
        if self._first_update_logged:
            return
        self._first_update_logged = True
        positions = []
        line_index = 0
        for kind, _text in visible_texts:
            if self._is_guiflash_ready():
                positions.append((kind, self._pixel_position_for_line(line_index)))
            else:
                screen_width = 1920
                screen_height = 1080
                if BigWorld is not None:
                    try:
                        screen_width = max(1, int(BigWorld.screenWidth()))
                        screen_height = max(1, int(BigWorld.screenHeight()))
                    except Exception:
                        pass
                offset_x, offset_y = _get_active_offsets()
                positions.append((kind, (
                    int((screen_width * 0.5) + (offset_x * screen_width)),
                    int((screen_height * 0.5) + (offset_y * screen_height) + (SETTINGS['line_spacing'] * screen_height * line_index)),
                )))
            line_index += 1
        log('Renderer first update backend=%s texts=%r positions=%r' % (
            'gambiter.guiflash' if self._is_guiflash_ready() else 'GUI.Text',
            [kind for kind, _text in visible_texts],
            positions,
        ))

    def _color_to_html(self):
        color = SETTINGS['color']
        return '#%02X%02X%02X' % (color[0], color[1], color[2])

    def _make_html_text(self, text):
        return "<font size='%d' color='%s'>%s</font>" % (
            int(round(SETTINGS['font_size'])),
            self._color_to_html(),
            text,
        )

    def _make_html_shadow_layer(self, text):
        return "<font size='%d' color='#000000'>%s</font>" % (
            int(round(SETTINGS['font_size'])),
            text,
        )

    def _guiflash_base_props(self, html, x_position, y_position, alpha_override=None, z_index=None):
        # Gambiter LabelEx applies a default DropShadowFilter on the TextField (gray, blurred),
        # which reads as a colored halo around white text. Passing shadow=None clears filters.
        props = {
            'text': html,
            'x': x_position,
            'y': y_position,
            'alignX': 'center',
            'alignY': 'center',
            'visible': True,
            'shadow': None,
        }
        if z_index is not None:
            props['index'] = int(z_index)
        try:
            if alpha_override is None:
                alpha = _clamp(_to_float(SETTINGS.get('text_alpha', 1.0), 1.0), 0.0, 1.0)
            else:
                alpha = _clamp(_to_float(alpha_override, 1.0), 0.0, 1.0)
            props['alpha'] = alpha
        except Exception:
            pass
        return props

    def _pixel_position_for_line(self, line_index):
        screen_width = 1920
        screen_height = 1080
        if BigWorld is not None:
            try:
                screen_width = max(1, int(BigWorld.screenWidth()))
                screen_height = max(1, int(BigWorld.screenHeight()))
            except Exception:
                pass
        offset_x, offset_y = _get_active_offsets()
        x_position = int(offset_x * screen_width)
        y_position = int((offset_y * screen_height) + (SETTINGS['line_spacing'] * screen_height * line_index))
        return x_position, y_position

    def _put_guiflash_component(self, alias, props):
        if not self._is_guiflash_ready():
            return
        if alias in self._guiflash_created:
            try:
                g_guiFlash.updateComponent(alias, props, None)
                return
            except Exception:
                if not self._guiflash_failure_logged:
                    self._guiflash_failure_logged = True
                    log('GUIFlash updateComponent failed alias=%s props=%r' % (alias, props))
                    LOG_CURRENT_EXCEPTION()
                try:
                    g_guiFlash.deleteComponent(alias)
                except Exception:
                    pass
                self._guiflash_created.discard(alias)
        try:
            g_guiFlash.createComponent(alias, COMPONENT_TYPE.LABEL, props)
            self._guiflash_created.add(alias)
        except Exception:
            if not self._guiflash_failure_logged:
                self._guiflash_failure_logged = True
                log('GUIFlash createComponent failed alias=%s props=%r' % (alias, props))
                LOG_CURRENT_EXCEPTION()

    def _delete_guiflash_one(self, alias):
        if not self._is_guiflash_ready():
            return
        if alias not in self._guiflash_created:
            return
        try:
            g_guiFlash.deleteComponent(alias)
        except Exception:
            pass
        self._guiflash_created.discard(alias)

    def _create_or_update_guiflash_label(self, alias, text, line_index):
        if not self._is_guiflash_ready():
            return

        x_position, y_position = self._pixel_position_for_line(line_index)
        shadow_dx = 2
        shadow_dy = 2
        base_index = 300 + (line_index * 10)

        if SETTINGS.get('text_shadow', True):
            shadow_alias = alias + '_shadow'
            shadow_alpha = _clamp(
                _to_float(SETTINGS.get('text_alpha', 1.0), 1.0) * _to_float(SETTINGS.get('text_shadow_alpha', 0.45), 0.45),
                0.0, 1.0
            )
            shadow_props = self._guiflash_base_props(
                self._make_html_shadow_layer(text),
                x_position + shadow_dx,
                y_position + shadow_dy,
                alpha_override=shadow_alpha,
                z_index=base_index,
            )
            self._put_guiflash_component(shadow_alias, shadow_props)
        else:
            self._delete_guiflash_one(alias + '_shadow')

        main_props = self._guiflash_base_props(
            self._make_html_text(text),
            x_position,
            y_position,
            z_index=base_index + 1,
        )
        self._put_guiflash_component(alias, main_props)

    def _delete_guiflash_label(self, alias):
        self._delete_guiflash_one(alias)
        self._delete_guiflash_one(alias + '_shadow')

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
        self._safe_set(label, 'shadow', SETTINGS.get('text_shadow', True))

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
        self._log_backend_once()
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
            self._safe_set(label, 'shadow', SETTINGS.get('text_shadow', True))

    def _hud_label_centers_pixels(self):
        """Screen pixel centers for each visible line (matches update() layout)."""
        sw = 1920
        sh = 1080
        if BigWorld is not None:
            try:
                sw = max(1, int(BigWorld.screenWidth()))
                sh = max(1, int(BigWorld.screenHeight()))
            except Exception:
                pass
        centers = []
        line_index = 0
        offset_x, offset_y = _get_active_offsets()
        if SETTINGS.get('show_dispersion', True):
            # Mouse position from GUI.mcursor() is in absolute screen pixels.
            # Guiflash LabelEx with alignX/alignY='center' also ends up centered on screen with
            # x/y used as offsets, so hit-test centers must be absolute (center + offset).
            cx = int((sw * 0.5) + (offset_x * sw))
            cy = int((sh * 0.5) + (offset_y * sh) + (SETTINGS['line_spacing'] * sh * line_index))
            centers.append((cx, cy))
            line_index += 1
        if SETTINGS.get('show_aim_time', True):
            cx = int((sw * 0.5) + (offset_x * sw))
            cy = int((sh * 0.5) + (offset_y * sh) + (SETTINGS['line_spacing'] * sh * line_index))
            centers.append((cx, cy))
        return centers

    def is_point_over_hud(self, mx, my):
        if not SETTINGS.get('enabled', True):
            return False
        centers = self._hud_label_centers_pixels()
        if not centers:
            return False
        fs = float(SETTINGS.get('font_size', 28))
        # Generous box: HTML label width varies; guiflash shadow layer extends past main text.
        half_w = max(120.0, fs * 6.5)
        half_h = max(18.0, fs * 0.9)
        if self._is_guiflash_ready():
            half_w *= 1.4
            half_h *= 1.4
        ys = [c[1] for c in centers]
        cx = centers[0][0]
        top = min(ys) - half_h
        bottom = max(ys) + half_h
        left = cx - half_w
        right = cx + half_w
        return left <= mx <= right and top <= my <= bottom

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

        offset_x, offset_y = _get_active_offsets()
        x_position = int((screen_width * 0.5) + (offset_x * screen_width))
        y_position = int((screen_height * 0.5) + (offset_y * screen_height) + (SETTINGS['line_spacing'] * screen_height * line_index))

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

        self._log_first_update_once(visible_texts)

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


class _HudDragController(object):
    """Battle-only HUD drag: Ctrl + left mouse on text, same idea as DistanceMarker."""

    def __init__(self):
        self._dragging = False
        self._keys_registered = False
        self._drag_start_px = None
        self._drag_start_py = None
        self._drag_start_offset_x = 0.0
        self._drag_start_offset_y = 0.0
        self._drag_offset_x_key = 'offset_x_arcade'
        self._drag_offset_y_key = 'offset_y_arcade'

    def install(self):
        if InputHandler is None or Keys is None or GUI is None:
            return
        if self._keys_registered:
            return
        try:
            InputHandler.g_instance.onKeyDown += self._on_key_down
            InputHandler.g_instance.onKeyUp += self._on_key_up
            self._keys_registered = True
        except Exception:
            pass

    def uninstall(self):
        self.end_drag(save=True)
        if not self._keys_registered:
            return
        try:
            InputHandler.g_instance.onKeyDown -= self._on_key_down
            InputHandler.g_instance.onKeyUp -= self._on_key_up
        except Exception:
            pass
        self._keys_registered = False

    @staticmethod
    def _is_left_mouse(event):
        try:
            return event.isMouseButton() and event.key == Keys.KEY_LEFTMOUSE
        except Exception:
            return False

    @staticmethod
    def _is_key_down(key_code):
        if BigWorld is None or key_code is None:
            return False
        try:
            return bool(BigWorld.isKeyDown(key_code))
        except Exception:
            return False

    def _is_ctrl_pressed(self):
        left = getattr(Keys, 'KEY_LCONTROL', None)
        right = getattr(Keys, 'KEY_RCONTROL', None)
        generic = getattr(Keys, 'KEY_CONTROL', None)
        return self._is_key_down(left) or self._is_key_down(right) or self._is_key_down(generic)

    def _is_left_pressed(self):
        return self._is_key_down(getattr(Keys, 'KEY_LEFTMOUSE', None))

    def _begin_drag(self, mx, my, reason, dx, dy):
        px, py = self._cursor_to_screen_pixels(mx, my)
        self._drag_start_px = px
        self._drag_start_py = py
        self._drag_offset_x_key, self._drag_offset_y_key = _get_active_offset_keys()
        self._drag_start_offset_x = _clamp(
            _to_float(SETTINGS.get(self._drag_offset_x_key, SETTINGS.get('offset_x', DEFAULT_SETTINGS['offset_x'])),
                     DEFAULT_SETTINGS['offset_x']),
            -0.5, 0.5
        )
        self._drag_start_offset_y = _clamp(
            _to_float(SETTINGS.get(self._drag_offset_y_key, SETTINGS.get('offset_y', DEFAULT_SETTINGS['offset_y'])),
                     DEFAULT_SETTINGS['offset_y']),
            -0.5, 0.5
        )
        self._dragging = True
        _drag_debug_log(
            'drag start by %s raw=(%.2f, %.2f) px=(%.1f, %.1f) dx=%.3f dy=%.3f mode_keys=(%s,%s) start_offset=(%.4f,%.4f)' % (
                reason, mx, my, px, py, dx, dy,
                self._drag_offset_x_key, self._drag_offset_y_key,
                self._drag_start_offset_x, self._drag_start_offset_y
            ),
            force=True
        )

    @staticmethod
    def _cursor_to_screen_pixels(mx, my):
        """
        Normalize GUI.mcursor() position to absolute screen pixels.
        Some clients return clip-space (-1..1), others return pixel coords.
        """
        if BigWorld is None:
            return float(mx), float(my)
        try:
            sw = max(1.0, float(BigWorld.screenWidth()))
            sh = max(1.0, float(BigWorld.screenHeight()))
        except Exception:
            return float(mx), float(my)

        fx = float(mx)
        fy = float(my)
        if -1.5 <= fx <= 1.5 and -1.5 <= fy <= 1.5:
            px = (fx + 1.0) * 0.5 * sw
            # GUI.mcursor normalized Y is client-dependent; on CN client it behaves as +Y up.
            # Convert to screen pixels where +Y is down.
            py = (1.0 - fy) * 0.5 * sh
            return px, py
        return fx, fy

    def _on_key_down(self, event):
        if not SETTINGS.get('enabled', True):
            return
        if not event.isCtrlDown():
            return
        if not self._is_left_mouse(event):
            return
        try:
            cursor = GUI.mcursor()
        except Exception:
            return
        # Do not require inFocus: with Gambiter/Scaleform the cursor is often "out of focus" for the
        # main GUI while the battle view still receives mouse — DistanceMarker used inFocus too, but
        # that blocks drag start on many setups. inWindow is enough.
        if not cursor.inWindow:
            return
        try:
            mx, my = cursor.position
        except Exception:
            return
        px, py = self._cursor_to_screen_pixels(mx, my)
        if not RENDERER.is_point_over_hud(px, py):
            _drag_debug_log('keydown miss: ctrl=1 lmb=1 raw=(%.2f, %.2f) px=(%.1f, %.1f)' % (mx, my, px, py))
            return
        self._begin_drag(mx, my, 'keydown(hit)', 0.0, 0.0)

    def _on_key_up(self, event):
        if not self._dragging:
            return
        # Stop dragging either on left mouse release or when CTRL is no longer held.
        if self._is_left_mouse(event):
            _drag_debug_log('drag end by keyup(lmb)', force=True)
            self.end_drag(save=True)
            return
        try:
            if not event.isCtrlDown():
                _drag_debug_log('drag end by keyup(ctrl)', force=True)
                self.end_drag(save=True)
        except Exception:
            pass

    def end_drag(self, save=True):
        if not self._dragging:
            return
        self._dragging = False
        _drag_debug_log('drag end save=%r offset=(%.4f, %.4f)' % (save, SETTINGS.get('offset_x', 0.0), SETTINGS.get('offset_y', 0.0)), force=True)
        if save:
            try:
                save_config()
            except Exception:
                LOG_CURRENT_EXCEPTION()
            # Do not call apply_runtime_settings() here: it invokes RENDERER.hide(), which deletes
            # guiflash labels; update_display may be throttled so the HUD stays gone until the next
            # unthrottled tick — looks like drag broke and blocks further drags.
            global _last_display_update_time
            _last_display_update_time = None
            try:
                RENDERER.apply_settings()
                RENDERER.update(_last_hud_dispersion, _last_hud_aim_time)
            except Exception:
                LOG_CURRENT_EXCEPTION()
        self._drag_start_px = None
        self._drag_start_py = None

    def on_mouse_delta(self, dx, dy):
        if not SETTINGS.get('enabled', True):
            return
        if BigWorld is None:
            return
        try:
            cursor = GUI.mcursor()
        except Exception:
            _drag_debug_log('delta skipped: GUI.mcursor unavailable')
            return
        if not cursor.inWindow:
            _drag_debug_log('delta skipped: cursor not in window')
            return

        # Fallback path: some clients don't dispatch left-mouse onKeyDown to InputHandler.
        # In such case we bootstrap drag from continuous mouse delta while Ctrl+LMB is pressed.
        if not self._dragging:
            if not self._is_ctrl_pressed() or not self._is_left_pressed():
                return
            try:
                mx, my = cursor.position
            except Exception:
                _drag_debug_log('delta skipped: cursor.position unavailable')
                return
            px, py = self._cursor_to_screen_pixels(mx, my)
            if RENDERER.is_point_over_hud(px, py):
                self._begin_drag(mx, my, 'delta(hit)', dx, dy)
            else:
                # Compatibility fallback: in some clients cursor/HUD coordinate spaces drift slightly,
                # making hit-test unreliable. When Ctrl+LMB is physically held and we already receive
                # battle mouse deltas, allow drag start anyway.
                self._begin_drag(mx, my, 'delta(fallback-no-hit)', dx, dy)

        # Keep drag only while left mouse is physically held.
        if not self._is_left_pressed():
            _drag_debug_log('drag end by physical lmb up', force=True)
            self.end_drag(save=True)
            return

        try:
            sw = max(1, int(BigWorld.screenWidth()))
            sh = max(1, int(BigWorld.screenHeight()))
        except Exception:
            return
        try:
            mx_now, my_now = cursor.position
            px_now, py_now = self._cursor_to_screen_pixels(mx_now, my_now)
            if self._drag_start_px is None or self._drag_start_py is None:
                self._drag_start_px = px_now
                self._drag_start_py = py_now
            delta_px = px_now - self._drag_start_px
            delta_py = py_now - self._drag_start_py
            new_x = self._drag_start_offset_x + (delta_px / float(sw))
            new_y = self._drag_start_offset_y + (delta_py / float(sh))
        except Exception:
            # Fallback to delta integration when cursor absolute position is unavailable.
            new_x = _to_float(SETTINGS.get(self._drag_offset_x_key, SETTINGS.get('offset_x', 0.0)), 0.0) + (float(dx) / float(sw))
            new_y = _to_float(SETTINGS.get(self._drag_offset_y_key, SETTINGS.get('offset_y', 0.0)), 0.0) + (float(dy) / float(sh))
        _set_offsets_for_keys(self._drag_offset_x_key, self._drag_offset_y_key, new_x, new_y)
        _drag_debug_log('delta move dx=%.3f dy=%.3f -> offset=(%.4f, %.4f)' % (
            dx, dy, SETTINGS.get(self._drag_offset_x_key, 0.0), SETTINGS.get(self._drag_offset_y_key, 0.0)
        ))
        try:
            RENDERER.update(_last_hud_dispersion, _last_hud_aim_time)
        except Exception:
            LOG_CURRENT_EXCEPTION()


_HUD_DRAG = _HudDragController()


def apply_runtime_settings():
    global _last_display_update_time
    try:
        _last_display_update_time = None
        RENDERER.apply_settings()
        if not _HUD_DRAG._dragging:
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


def _get_bigworld_entity(entity_id):
    if BigWorld is None or entity_id is None:
        return None
    try:
        entity_getter = getattr(BigWorld, 'entity', None)
        if callable(entity_getter):
            return entity_getter(entity_id)
    except Exception:
        pass
    try:
        entities = getattr(BigWorld, 'entities', None)
        if entities is not None:
            return entities.get(entity_id)
    except Exception:
        pass
    return None


def _is_avatar_vehicle_alive(avatar):
    if avatar is None:
        return False
    try:
        alive = getattr(avatar, 'isVehicleAlive', None)
        if alive is not None:
            if callable(alive):
                return bool(alive())
            return bool(alive)
    except Exception:
        pass
    try:
        vehicle = _get_bigworld_entity(getattr(avatar, 'playerVehicleID', None))
        if vehicle is not None:
            is_alive = getattr(vehicle, 'isAlive', None)
            if callable(is_alive):
                return bool(is_alive())
            health = getattr(vehicle, 'health', None)
            if health is not None:
                return float(health) > 0.0
    except Exception:
        pass
    return True


def _health_update_means_dead(health, is_crew_active):
    try:
        if float(health) <= 0.0:
            return True
    except Exception:
        pass
    return is_crew_active in (False, 0)


def _is_player_vehicle_update(avatar, vehicle_id):
    try:
        return vehicle_id == getattr(avatar, 'playerVehicleID', None)
    except Exception:
        return False


def _clear_own_vehicle_hud():
    try:
        _HUD_DRAG.end_drag(save=True)
        _reset_aiming_runtime()
        reset_floor_tracker()
        RENDERER.destroy()
    except Exception:
        LOG_CURRENT_EXCEPTION()


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
    if not _is_avatar_vehicle_alive(avatar):
        _clear_own_vehicle_hud()
        return

    interval = SETTINGS.get('display_update_interval', DEFAULT_SETTINGS['display_update_interval'])
    if interval <= 0.0:
        RENDERER.update(dispersion, aim_time_remaining)
        return

    global _last_display_update_time
    now = _now_display_clock()
    if _last_display_update_time is not None:
        if now - _last_display_update_time < interval:
            return
    _last_display_update_time = now

    RENDERER.update(dispersion, aim_time_remaining)


def hook_get_own_vehicle_shot_dispersion_angle(original, self, turret_rotation_speed, with_shot=0):
    result = original(self, turret_rotation_speed, with_shot)
    try:
        if not _is_avatar_vehicle_alive(self):
            _clear_own_vehicle_hud()
            return result
        current_dispersion = float(result[0]) * 100.0
        aim_time_remaining = calculate_aim_time_remaining(self, result, turret_rotation_speed, with_shot)
        global _last_hud_dispersion, _last_hud_aim_time
        _last_hud_dispersion = current_dispersion
        _last_hud_aim_time = aim_time_remaining
        update_display(self, current_dispersion, aim_time_remaining)
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return result


def hook_update_vehicle_health(original, self, vehicleID, health, deathReasonID, isCrewActive, isRespawn):
    try:
        if _is_player_vehicle_update(self, vehicleID) and _health_update_means_dead(health, isCrewActive):
            _clear_own_vehicle_hud()
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return original(self, vehicleID, health, deathReasonID, isCrewActive, isRespawn)


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
        base = _caphhh_get_value(gun, 'shotDispersionAngle')
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
        _clear_own_vehicle_hud()
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return original(self)


def hook_destroy(original, self):
    try:
        player = _try_get_player()
        if self is player:
            _clear_own_vehicle_hud()
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return original(self)


def hook_avatar_handle_mouse_event(original, self, dx, dy, dz):
    result = original(self, dx, dy, dz)
    try:
        _drag_debug_log('handleMouseEvent dx=%.3f dy=%.3f dz=%.3f dragging=%r ctrl=%r lmb=%r' % (
            dx, dy, dz, _HUD_DRAG._dragging, _HUD_DRAG._is_ctrl_pressed(), _HUD_DRAG._is_left_pressed()
        ))
        _HUD_DRAG.on_mouse_delta(dx, dy)
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return result


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


def make_mods_color_choice(title, variable_name, default_hex, tooltip=''):
    return {
        'type': 'ColorChoice',
        'text': title,
        'varName': variable_name,
        'value': default_hex,
        'tooltip': tooltip,
    }


def make_mods_slider_dict(title, variable_name, default_value, minimum, maximum, step, tooltip=''):
    return {
        'type': 'Slider',
        'text': title,
        'varName': variable_name,
        'value': default_value,
        'minimum': minimum,
        'maximum': maximum,
        'snapInterval': step,
        'format': '{{value}}',
        'tooltip': tooltip,
    }


def make_mods_checkbox_dict(title, variable_name, default_value, tooltip=''):
    return {
        'type': 'CheckBox',
        'text': title,
        'varName': variable_name,
        'value': default_value,
        'tooltip': tooltip,
    }


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
    controls.append(make_checkbox('Debug drag logging ([DRAG_DEBUG] in python.log, throttled)', 'debug_drag_logging', SETTINGS.get('debug_drag_logging', False)))
    controls.append(make_option_dropdown('Font size (text size)', 'font_size', SETTINGS['font_size']))
    controls.append(make_option_dropdown('Font (game font preset)', 'font_name', SETTINGS['font_name']))
    controls.append(make_option_dropdown('Dispersion decimals (digits after dot)', 'decimal_dispersion', SETTINGS['decimal_dispersion']))
    controls.append(make_option_dropdown('Aim time decimals (digits after dot)', 'decimal_aim_time', SETTINGS['decimal_aim_time']))
    controls.append(make_option_dropdown('Line spacing (gap between the 2 lines)', 'line_spacing', SETTINGS['line_spacing']))
    controls.append(make_option_dropdown(
        'HUD update interval (seconds; 0 = every frame)',
        'display_update_interval',
        SETTINGS.get('display_update_interval', DEFAULT_SETTINGS['display_update_interval']),
    ))
    controls.append(make_mods_color_choice(
        'Text color',
        'text_color_hex',
        SETTINGS.get('text_color_hex', DEFAULT_SETTINGS['text_color_hex']),
        tooltip='RGB color of the HUD text (use Text alpha for opacity).',
    ))
    controls.append(make_mods_slider_dict(
        'Text alpha',
        'text_alpha',
        SETTINGS.get('text_alpha', DEFAULT_SETTINGS['text_alpha']),
        0.0,
        1.0,
        0.01,
        tooltip='Opacity: 0 = invisible, 1 = fully opaque.',
    ))
    controls.append(make_mods_checkbox_dict(
        'Draw text shadow',
        'text_shadow',
        SETTINGS.get('text_shadow', DEFAULT_SETTINGS['text_shadow']),
        tooltip='When enabled, draws a dark offset copy behind the text (gambiter HUD only).',
    ))
    controls.append(make_mods_slider_dict(
        'Text shadow alpha',
        'text_shadow_alpha',
        SETTINGS.get('text_shadow_alpha', DEFAULT_SETTINGS['text_shadow_alpha']),
        0.0,
        1.0,
        0.01,
        tooltip='Shadow opacity multiplier (0 = no visible shadow, 1 = strongest).',
    ))

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
    if 'text_color_hex' in normalized:
        v = normalized['text_color_hex']
        if isinstance(v, STRING_TYPES):
            if _hex_string_to_rgb_three(v) is None:
                del normalized['text_color_hex']
        elif isinstance(v, INTEGER_TYPES):
            del normalized['text_color_hex']
    if 'text_alpha' in normalized:
        try:
            normalized['text_alpha'] = float(normalized['text_alpha'])
        except Exception:
            del normalized['text_alpha']
    if 'text_shadow_alpha' in normalized:
        try:
            normalized['text_shadow_alpha'] = float(normalized['text_shadow_alpha'])
        except Exception:
            del normalized['text_shadow_alpha']
    if 'text_shadow' in normalized:
        normalized['text_shadow'] = _to_bool(normalized['text_shadow'], DEFAULT_SETTINGS['text_shadow'])
    return normalized


def on_settings_changed(linkage, new_settings):
    global SETTINGS
    if linkage != MOD_ID or not isinstance(new_settings, dict):
        return

    patched_settings = copy.deepcopy(SETTINGS)
    patched_settings.update(_without_position_settings(normalize_settings_payload(new_settings)))
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
        patched_settings = copy.deepcopy(SETTINGS)
        patched_settings.update(_without_position_settings(normalize_settings_payload(saved_settings)))
        SETTINGS = sanitize_settings(patched_settings)
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
            patched_settings = copy.deepcopy(SETTINGS)
            patched_settings.update(_without_position_settings(normalize_settings_payload(api_settings)))
            SETTINGS = sanitize_settings(patched_settings)
            save_config()
            apply_runtime_settings()
        log('ModSettingsAPI template registered.')
    except Exception:
        LOG_CURRENT_EXCEPTION()


def register_mods_list():
    metadata = {
        'id': MOD_ID,
        'name': MOD_NAME,
        'description': 'Shows realtime dispersion and aim time remaining near the crosshair.',
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
    install_hook(PlayerAvatar, 'updateVehicleHealth', hook_update_vehicle_health)
    install_hook(PlayerAvatar, 'onBecomePlayer', hook_on_become_player)
    install_hook(PlayerAvatar, 'onBecomeNonPlayer', hook_on_become_non_player)
    install_hook(PlayerAvatar, 'destroy', hook_destroy)
    if AvatarInputHandler is not None:
        install_hook(AvatarInputHandler, 'handleMouseEvent', hook_avatar_handle_mouse_event)
    HOOKS_INSTALLED = True


def init():
    load_config()
    install_hooks()
    _HUD_DRAG.install()
    register_mod_settings()
    register_mods_list()
    apply_runtime_settings()
    log('Loaded successfully.')


def fini():
    try:
        _HUD_DRAG.uninstall()
        _reset_aiming_runtime()
        RENDERER.destroy()
    finally:
        log('Unloaded.')


init()
