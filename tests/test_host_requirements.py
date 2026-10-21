import importlib.util
import csv
import tempfile
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('host_requirements', Path(__file__).resolve().parents[1] / 'scripts/analyze-wasm-hosts.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HostRequirements(unittest.TestCase):
    def row(self, imports):
        return {'relative_path': 'sample.wasm', 'status': 'metadata_parsed_not_validated', 'imports': imports, 'exports': []}

    def test_env_alone_is_not_emscripten_proof(self):
        result = m.describe(self.row([{'module': 'env', 'name': 'custom_host', 'kind': 0}]))
        self.assertEqual(result['host_requirements'], ['unresolved_host_namespace'])
        self.assertEqual(result['mining_entry_point'], 'not established')

    def test_mixed_wasi_and_binding_requirements_preserved(self):
        result = m.describe(self.row([{'module': 'wasi_snapshot_preview1', 'name': 'fd_write', 'kind': 0}, {'module': 'wbg', 'name': '__wbindgen_throw', 'kind': 0}]))
        self.assertEqual(set(result['host_requirements']), {'wasi_host_required', 'javascript_bindings_required'})

    def test_no_import_does_not_imply_executable(self):
        result = m.describe(self.row([]))
        self.assertEqual(result['host_requirements'], ['no_imports_observed'])
        self.assertIn('not established', result['execution_readiness'])

    def test_reference_csv_larger_than_default_field_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.csv'
            with path.open('w', newline='') as output:
                writer = csv.writer(output)
                writer.writerow(['sha256', 'exports'])
                writer.writerow(['abc', 'x' * 200000])
                writer.writerow(['abc', 'other'])
            previous = csv.field_size_limit()
            self.assertEqual(m.reference_hash_counts(path), {'abc': 2})
            self.assertEqual(csv.field_size_limit(), previous)
