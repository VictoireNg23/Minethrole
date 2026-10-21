import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('original_patch_application', Path(__file__).resolve().parents[1] / 'scripts/apply-chromium71-original-patches.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OriginalPatchApplication(unittest.TestCase):
    def test_authors_patch_paths_and_content_prefix(self):
        root = Path(__file__).resolve().parents[1]
        for name, relative, revision, checksum, options in m.PATCHES:
            paths = m.affected_paths((root / 'patches' / name).read_bytes(), 'content' if name == 'content.patch' else '')
            self.assertTrue(paths)
            if name == 'content.patch':
                self.assertEqual(paths, ['content/renderer/render_frame_impl.cc'])
    def test_parent_traversal_refused(self):
        with self.assertRaises(ValueError):
            m.affected_paths(b'+++ b/../../outside\n')
