import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('node_hooks', Path(__file__).resolve().parents[1] / 'scripts/download-chromium71-node.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NodeHooks(unittest.TestCase):
    def test_extract_exact_hooks_without_executing_deps(self):
        hooks = [dict(name='node_linux', action=['python', '--bucket', 'chromium-nodejs/8.9.1', '-s', 'src/third_party/node/linux/node-linux-x64.tar.gz.sha1']),
                 dict(name='webui_node_modules', action=['python', '--bucket', 'chromium-nodejs', '-s', 'src/third_party/node/node_modules.tar.gz.sha1'])]
        data = m.hook_artifacts('raise RuntimeError("must not execute")\nhooks = ' + repr(hooks))
        self.assertEqual(len(data), 2)
        hooks[0]['action'][2] = 'unexpected'
        with self.assertRaises(ValueError):
            m.hook_artifacts('hooks = ' + repr(hooks))
