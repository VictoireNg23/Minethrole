import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('header_guard_repair', Path(__file__).resolve().parents[1] / 'scripts/repair-chromium71-header-guards.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HeaderGuards(unittest.TestCase):
    def test_detects_temp_path_hyphens(self):
        self.assertFalse(m.valid_guards('#ifndef _TMP_MINETHROTTLE71-WORK_HEADER_H_\n#define _TMP_MINETHROTTLE71-WORK_HEADER_H_\n'))
        self.assertTrue(m.valid_guards('#ifndef SRC_GPU_CONFIG_GPU_LISTS_VERSION_H_\n#define SRC_GPU_CONFIG_GPU_LISTS_VERSION_H_\n#define GPU_LISTS_VERSION "revision"\n#endif\n'))
