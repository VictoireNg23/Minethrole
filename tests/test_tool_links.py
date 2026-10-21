import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('tool_links', Path(__file__).resolve().parents[1] / 'scripts/link-chromium71-tools.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ToolLinks(unittest.TestCase):
    def test_link_is_idempotent_and_never_replaces_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'tool'
            source.write_text('fixture')
            destination = root / 'bin/tool'
            self.assertEqual(m.link_new(source, destination), 'created')
            self.assertEqual(m.link_new(source, destination), 'existing_matching_link')
            occupied = root / 'occupied'
            occupied.write_text('preserve')
            with self.assertRaises(ValueError):
                m.link_new(source, occupied)
            self.assertEqual(occupied.read_text(), 'preserve')
