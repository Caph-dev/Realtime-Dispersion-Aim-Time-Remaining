import importlib.util
import os
import sys
import tempfile
import types
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
    finally:
        os.chdir(old_cwd)
    return module, temp_dir


class _FakeModsListApi(object):
    """Mirrors the parameter validation of poliroid ModsListApi 1.7.x."""

    MANDATORY = ('name', 'description', 'enabled', 'login', 'lobby', 'callback')

    def __init__(self):
        self.modifications = {}
        self.errors = []

    def addModification(self, id=None, name=None, description=None, icon=None,
                        enabled=None, login=None, lobby=None, callback=None):
        arguments = {
            'id': id, 'name': name, 'description': description, 'icon': icon,
            'enabled': enabled, 'login': login, 'lobby': lobby, 'callback': callback,
        }
        if any(arguments[key] is None for key in self.MANDATORY):
            self.errors.append(
                'Method @addModification requires mandatory parameters [%s]' % ', '.join(self.MANDATORY)
            )
            return
        self.modifications[id] = arguments


def install_fake_mods_list_api(test_case):
    api = _FakeModsListApi()
    package = types.ModuleType('gui')
    package.__path__ = []
    submodule = types.ModuleType('gui.modsListApi')
    submodule.g_modsListApi = api
    package.modsListApi = submodule

    saved = {name: sys.modules.get(name) for name in ('gui', 'gui.modsListApi')}

    def restore():
        for name, value in saved.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

    test_case.addCleanup(restore)
    sys.modules['gui'] = package
    sys.modules['gui.modsListApi'] = submodule
    return api


class ModsListRegistrationTests(unittest.TestCase):
    def test_registration_passes_all_mandatory_parameters(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)
        api = install_fake_mods_list_api(self)

        module.register_mods_list()

        self.assertEqual(api.errors, [])
        self.assertIn(module.MOD_ID, api.modifications)
        registered = api.modifications[module.MOD_ID]
        self.assertEqual(registered['name'], module.MOD_NAME)
        self.assertTrue(registered['lobby'])
        self.assertTrue(callable(registered['callback']))

    def test_missing_mods_list_api_is_ignored(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        module.register_mods_list()

    def test_init_only_runs_once(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        calls = []
        module.register_mods_list = lambda: calls.append('registered')
        module.MOD_INITIALIZED = False

        module.init()
        module.init()

        self.assertEqual(calls, ['registered'])

    def test_fini_only_runs_once(self):
        module, temp_dir = load_mod_module()
        self.addCleanup(temp_dir.cleanup)

        calls = []
        module.RENDERER.destroy = lambda: calls.append('destroyed')
        module.MOD_INITIALIZED = True

        module.fini()
        module.fini()

        self.assertEqual(calls, ['destroyed'])


if __name__ == '__main__':
    unittest.main()
