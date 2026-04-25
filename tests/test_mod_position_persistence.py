import importlib.util
import os
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
MODULE_PATH = os.path.join(
    REPO_ROOT,
    'python',
    'gui',
    'mods',
    'mod_caphhh_current_acc_and_aim_time.py',
)


def load_mod_module():
    temp_dir = tempfile.TemporaryDirectory()
    old_cwd = os.getcwd()
    os.chdir(temp_dir.name)
    try:
        spec = importlib.util.spec_from_file_location('test_mod_under_test', MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.CONFIG_RELATIVE_PATH = os.path.join(temp_dir.name, module.CONFIG_RELATIVE_PATH)
        module.LEGACY_CONFIG_RELATIVE_PATHS = tuple(
            os.path.join(temp_dir.name, path) for path in module.LEGACY_CONFIG_RELATIVE_PATHS
        )
    finally:
        os.chdir(old_cwd)
    return module, temp_dir


class _FakeModsSettingsApi(object):
    def __init__(self, saved_settings=None):
        self.saved_settings = saved_settings
        self.callbacks = []
        self.templates = []

    def getModSettings(self, mod_id, template):
        self.templates.append((mod_id, template))
        return self.saved_settings

    def registerCallback(self, mod_id, callback):
        self.callbacks.append((mod_id, callback))

    def setModTemplate(self, mod_id, template, callback):
        self.templates.append((mod_id, template))
        self.callbacks.append((mod_id, callback))
        return None


class _FakeRenderer(object):
    def __init__(self):
        self.destroy_calls = 0
        self.update_calls = []

    def destroy(self):
        self.destroy_calls += 1

    def update(self, dispersion, aim_time_remaining):
        self.update_calls.append((dispersion, aim_time_remaining))

    def ensure(self):
        pass

    def hide(self):
        pass

    def apply_settings(self):
        pass


class _FakeBigWorld(object):
    def __init__(self, player):
        self._player = player

    def player(self):
        return self._player

    def time(self):
        return 1.0


class _FakeAvatar(object):
    def __init__(self, vehicle_id=7, alive=True):
        self.playerVehicleID = vehicle_id
        self.isVehicleAlive = alive


class PositionPersistenceTests(unittest.TestCase):
    def test_default_offsets_start_centered(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        self.assertEqual(module.DEFAULT_SETTINGS['offset_x'], 0.0)
        self.assertEqual(module.DEFAULT_SETTINGS['offset_y'], 0.0)
        self.assertEqual(module.DEFAULT_SETTINGS['offset_x_arcade'], 0.0)
        self.assertEqual(module.DEFAULT_SETTINGS['offset_y_arcade'], 0.0)
        self.assertEqual(module.DEFAULT_SETTINGS['offset_x_sniper'], 0.0)
        self.assertEqual(module.DEFAULT_SETTINGS['offset_y_sniper'], 0.0)

    def test_settings_change_callback_ignores_position_fields(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        module.SETTINGS = module.sanitize_settings({
            'offset_x_arcade': 0.18,
            'offset_y_arcade': -0.09,
            'offset_x_sniper': 0.11,
            'offset_y_sniper': -0.07,
            'font_size': 24.0,
        })

        module.on_settings_changed(module.MOD_ID, {
            'offset_x_arcade': 0.33,
            'offset_y_arcade': 0.22,
            'font_size': 31.0,
        })

        self.assertEqual(module.SETTINGS['font_size'], 31.0)
        self.assertEqual(module.SETTINGS['offset_x_arcade'], 0.18)
        self.assertEqual(module.SETTINGS['offset_y_arcade'], -0.09)
        self.assertEqual(module.SETTINGS['offset_x_sniper'], 0.11)
        self.assertEqual(module.SETTINGS['offset_y_sniper'], -0.07)

    def test_register_mod_settings_preserves_dragged_offsets(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        module.SETTINGS = module.sanitize_settings({
            'offset_x_arcade': 0.14,
            'offset_y_arcade': -0.06,
            'offset_x_sniper': 0.09,
            'offset_y_sniper': -0.04,
            'font_size': 24.0,
        })
        module.templates = object()
        module.build_settings_template = lambda: {'enabled': True}
        module.g_modsSettingsApi = _FakeModsSettingsApi({
            'offset_x_arcade': 0.02,
            'offset_y_arcade': 0.03,
            'offset_x_sniper': 0.04,
            'offset_y_sniper': 0.05,
            'font_size': 28.0,
        })

        module.register_mod_settings()

        self.assertEqual(module.SETTINGS['font_size'], 28.0)
        self.assertEqual(module.SETTINGS['offset_x_arcade'], 0.14)
        self.assertEqual(module.SETTINGS['offset_y_arcade'], -0.06)
        self.assertEqual(module.SETTINGS['offset_x_sniper'], 0.09)
        self.assertEqual(module.SETTINGS['offset_y_sniper'], -0.04)

    def test_settings_template_hides_position_controls(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        def fake_control(_title, variable_name, *_args, **_kwargs):
            return {'varName': variable_name}

        module.make_checkbox = fake_control
        module.make_option_dropdown = fake_control
        module.make_mods_color_choice = fake_control
        module.make_mods_slider_dict = fake_control
        module.make_mods_checkbox_dict = fake_control

        template = module.build_settings_template()
        variable_names = [control['varName'] for control in template['column1'] + template['column2']]

        self.assertNotIn('offset_x_arcade', variable_names)
        self.assertNotIn('offset_y_arcade', variable_names)
        self.assertNotIn('offset_x_sniper', variable_names)
        self.assertNotIn('offset_y_sniper', variable_names)


class DestroyedVehicleHudTests(unittest.TestCase):
    def test_vehicle_death_health_update_clears_hud_before_original(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        avatar = _FakeAvatar(vehicle_id=7, alive=True)
        renderer = _FakeRenderer()
        module.BigWorld = _FakeBigWorld(avatar)
        module.RENDERER = renderer
        module.AIMING_RUNTIME['vehicle_id'] = 7
        module.AIMING_RUNTIME['ideal_dispersion'] = 0.3
        module.AIMING_RUNTIME['aiming_time'] = 2.0
        calls = []

        def original(self, vehicle_id, health, death_reason_id, is_crew_active, is_respawn):
            calls.append((self, vehicle_id, health, death_reason_id, is_crew_active, is_respawn, renderer.destroy_calls))
            return 'original-result'

        result = module.hook_update_vehicle_health(original, avatar, 7, 0, 1, True, False)

        self.assertEqual(result, 'original-result')
        self.assertEqual(renderer.destroy_calls, 1)
        self.assertEqual(calls[0][-1], 1)
        self.assertIsNone(module.AIMING_RUNTIME['vehicle_id'])
        self.assertIsNone(module.AIMING_RUNTIME['ideal_dispersion'])
        self.assertEqual(module.AIMING_RUNTIME['aiming_time'], 0.0)

    def test_update_display_does_not_restore_hud_after_death(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        avatar = _FakeAvatar(vehicle_id=7, alive=False)
        renderer = _FakeRenderer()
        module.BigWorld = _FakeBigWorld(avatar)
        module.RENDERER = renderer

        module.update_display(avatar, 12.5, 0.75)

        self.assertEqual(renderer.update_calls, [])
        self.assertEqual(renderer.destroy_calls, 1)

    def test_dispersion_hook_does_not_restore_hud_after_death(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        avatar = _FakeAvatar(vehicle_id=7, alive=False)
        renderer = _FakeRenderer()
        module.BigWorld = _FakeBigWorld(avatar)
        module.RENDERER = renderer

        result = module.hook_get_own_vehicle_shot_dispersion_angle(
            lambda _self, _turret_rotation_speed, _with_shot=0: (0.12, 0.12),
            avatar,
            0.0,
            0,
        )

        self.assertEqual(result, (0.12, 0.12))
        self.assertEqual(renderer.update_calls, [])
        self.assertEqual(renderer.destroy_calls, 1)


if __name__ == '__main__':
    unittest.main()
