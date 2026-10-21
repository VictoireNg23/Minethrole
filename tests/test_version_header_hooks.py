import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('version_headers', Path(__file__).resolve().parents[1] / 'scripts/prepare-chromium71-version-headers.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class VersionHooks(unittest.TestCase):
    def test_selects_only_two_original_hooks_without_execution(self):
        hooks = [dict(name='gpu_lists_version', action=['python', 'gpu']), dict(name='lastchange_skia', action=['python', 'skia']), dict(name='landmines', action=['do not run'])]
        self.assertEqual(set(m.selected_hooks('raise Exception()\nhooks = ' + repr(hooks))), {'gpu_lists_version', 'lastchange_skia'})
        with self.assertRaises(ValueError):
            m.selected_hooks('hooks = []')
