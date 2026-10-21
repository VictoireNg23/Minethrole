import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('gn_configuration', Path(__file__).resolve().parents[1] / 'scripts/configure-chromium71.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class GnConfiguration(unittest.TestCase):
    def test_explicit_root_survives_launcher_working_directory(self):
        workspace = Path('/tmp/workspace with spaces')
        command = m.gn_command(workspace, workspace / 'src/out/new')
        self.assertIn('--root=/tmp/workspace with spaces/src', command)
        self.assertIn('--args=cc_wrapper="ccache" use_jumbo_build=true is_debug=false enable_nacl=false', command)
        self.assertEqual(command[2], 'gen')
