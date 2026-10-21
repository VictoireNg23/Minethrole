import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('seed_deps', ROOT / 'scripts/seed-chromium71-deps.py')
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


class SeedTests(unittest.TestCase):
    def test_platform_and_cipd_are_deferred(self):
        sha = 'a' * 40
        rows = []
        for name, definition in [('one', 'https://example.invalid/one@' + sha),
                ('two', {'url': 'https://example.invalid/two@' + sha, 'condition': 'checkout_linux'}),
                ('three', {'dep_type': 'cipd', 'packages': []})]:
            rows.append({'group': 'deps', 'path': 'src/' + name, 'definition': definition,
                         'candidates': [{'repository': '/example', 'status': 'commit_present'}]})
        plan = seed.plan_rows({'chromium_revision': seed.CHROMIUM, 'dependencies': rows})
        self.assertEqual([x['status'] for x in plan], ['candidate', 'not_a_pinned_git_dependency', 'condition_deferred'])

    def test_local_seeding_preserves_source_and_occupied_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'original'
            source.mkdir()
            def git(repo, *args):
                return subprocess.check_output(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
            git(source, 'init')
            (source / 'code').write_text('old')
            git(source, 'add', 'code')
            git(source, 'commit', '-m', 'historical')
            old = git(source, 'rev-parse', 'HEAD')
            (source / 'code').write_text('user data')
            index = (source / '.git/index').read_bytes()
            workspace = root / 'work'
            workspace.mkdir()
            item = {'path': 'src/dep', 'candidates': [str(source)], 'revision': old,
                    'remote': 'https://example.invalid/dep.git', 'status': 'candidate'}
            with contextlib.redirect_stdout(io.StringIO()):
                result = seed.apply_one(item, workspace)
            self.assertEqual(result['status'], 'local_clone_prepared')
            self.assertEqual((workspace / 'src/dep/code').read_text(), 'old')
            self.assertEqual((source / 'code').read_text(), 'user data')
            self.assertEqual((source / '.git/index').read_bytes(), index)
            self.assertEqual(seed.apply_one(item, workspace)['status'], 'existing_exact_checkout_untouched')
            occupied = workspace / 'src/occupied'
            occupied.mkdir()
            (occupied / 'sentinel').write_text('keep')
            result = seed.apply_one(dict(item, path='src/occupied'), workspace)
            self.assertEqual(result['status'], 'occupied_destination_untouched')
            self.assertEqual((occupied / 'sentinel').read_text(), 'keep')

    def test_traversal_and_symlink_destinations_are_not_populated(self):
        rows = [{'group': 'deps', 'path': 'src/../../outside', 'definition': 'https://example.invalid/a@' + 'a' * 40}]
        self.assertEqual(seed.plan_rows({'chromium_revision': seed.CHROMIUM, 'dependencies': rows})[0]['status'], 'unsupported_path')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            work = root / 'work'
            work.mkdir()
            (work / 'src').symlink_to(root)
            result = seed.apply_one({'path': 'src/dep'}, work)
            self.assertEqual(result['status'], 'destination_symlink_deferred')


if __name__ == '__main__':
    unittest.main()
