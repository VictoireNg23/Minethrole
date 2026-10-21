import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('experiment_directory', Path(__file__).resolve().parents[1] / 'scripts/prepare-experiment-directory.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ExperimentDirectory(unittest.TestCase):
    def test_separate_runs_and_unchanged_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            dataset = parent / 'dataset'
            dataset.mkdir()
            fixture = dataset / 'keep.wasm'
            fixture.write_bytes(b'unchanged')
            code = Path(__file__).resolve().parents[1]
            first, manifest = m.prepare(dataset, parent / 'results', code)
            second, _ = m.prepare(dataset, parent / 'results', code)
            self.assertNotEqual(first, second)
            self.assertEqual(fixture.read_bytes(), b'unchanged')
            self.assertFalse(manifest['browser_started'])
            self.assertTrue((first / 'provenance/original.json').is_file())
            with self.assertRaises(ValueError):
                m.prepare(dataset, dataset / 'results', code)
