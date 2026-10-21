import importlib.util
import hashlib
import io
import json
import tarfile
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_tools', ROOT / 'scripts/prepare-historical-depot-tools.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class PrepareToolsTests(unittest.TestCase):
    def test_snapshot_and_launchers_preserve_source(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            repo = parent / 'repo'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
            git('init')
            (repo / 'gclient').write_text('historical\n')
            git('add', 'gclient')
            git('commit', '-m', 'old')
            old = git('rev-parse', 'HEAD')
            (repo / 'gclient').write_text('modern\n')
            git('commit', '-am', 'new')
            modern = git('rev-parse', 'HEAD')
            (repo / 'gclient').write_text('local changes\n')
            index = (repo / '.git/index').read_bytes()
            export = tools.export_snapshot(repo, old, parent)
            self.assertEqual((export / 'depot_tools/gclient').read_text(), 'historical\n')
            self.assertFalse((export / 'depot_tools/.git').exists())
            tools.write_launchers(export, repo, Path('/usr/bin/python3'), Path('/usr/bin/true'))
            result = subprocess.run([str(export / 'with-env.sh'), 'python', '-c', 'import os; print(os.environ["DEPOT_TOOLS_UPDATE"])'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), '0')
            self.assertEqual(git('rev-parse', 'HEAD'), modern)
            self.assertEqual((repo / 'gclient').read_text(), 'local changes\n')
            self.assertEqual((repo / '.git/index').read_bytes(), index)


class ArchiveLinkTests(unittest.TestCase):
    def make_archive(self, path, links, extra=None, revision=tools.REVISION):
        with tarfile.open(path, 'w', format=tarfile.PAX_FORMAT, pax_headers={'comment': revision}) as archive:
            target = tarfile.TarInfo('support/chromite_wrapper')
            target.mode = 0o755
            payload = b'#!/bin/sh\nexit 0\n'
            target.size = len(payload)
            archive.addfile(target, io.BytesIO(payload))
            for name, linkname in links:
                member = tarfile.TarInfo(name)
                member.type = tarfile.SYMTYPE
                member.linkname = linkname
                archive.addfile(member)
            if extra is not None:
                archive.addfile(extra)

    def test_four_internal_links_and_existing_archive_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            archive = parent / 'existing.tar'
            names = ['cbuildbot', 'chrome_set_ver', 'cros', 'cros_sdk']
            self.make_archive(archive, [(name, 'support/chromite_wrapper') for name in names])
            original = archive.read_bytes()
            source = parent / 'source'
            source.mkdir()
            (source / 'sentinel').write_text('unchanged')
            root = tools.reuse_archive(archive, source, parent)
            for name in names:
                path = root / 'depot_tools' / name
                self.assertTrue(path.is_symlink())
                self.assertEqual(os.readlink(path), 'support/chromite_wrapper')
                self.assertEqual(path.read_bytes(), b'#!/bin/sh\nexit 0\n')
            self.assertTrue(os.access(root / 'depot_tools/support/chromite_wrapper', os.X_OK))
            self.assertEqual(archive.read_bytes(), original)
            self.assertEqual((source / 'sentinel').read_text(), 'unchanged')
            provenance = json.loads((root / 'provenance.json').read_text())
            self.assertEqual(len(provenance['preserved_symlinks']), 4)
            self.assertEqual(provenance['archive_sha256'], hashlib.sha256(original).hexdigest())

    def test_invalid_targets_rejected_before_extraction(self):
        cases = [
            [('link', '../outside')], [('link', '/tmp/outside')],
            [('link', 'missing')], [('link', 'link')],
            [('a', 'b'), ('b', 'support/chromite_wrapper')],
        ]
        for links in cases:
            with self.subTest(links=links), tempfile.TemporaryDirectory() as folder:
                parent = Path(folder)
                archive = parent / 'archive.tar'
                self.make_archive(archive, links)
                destination = parent / 'export'
                with self.assertRaises(ValueError):
                    tools.extract_archive(archive, destination, tools.REVISION)
                self.assertFalse(destination.exists())

    def test_symlink_ancestor_and_duplicate_rejected(self):
        for extra in [tarfile.TarInfo('alias/child'), tarfile.TarInfo('support/chromite_wrapper')]:
            with self.subTest(name=extra.name), tempfile.TemporaryDirectory() as folder:
                parent = Path(folder)
                archive = parent / 'archive.tar'
                self.make_archive(archive, [('alias', 'support/chromite_wrapper')], extra)
                with self.assertRaises(ValueError):
                    tools.extract_archive(archive, parent / 'export', tools.REVISION)
                self.assertFalse((parent / 'export').exists())

    def test_wrong_commit_and_hardlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            archive = parent / 'archive.tar'
            self.make_archive(archive, [], revision='wrong')
            with self.assertRaises(ValueError):
                tools.extract_archive(archive, parent / 'wrong', tools.REVISION)
            hardlink = tarfile.TarInfo('hardlink')
            hardlink.type = tarfile.LNKTYPE
            hardlink.linkname = 'support/chromite_wrapper'
            self.make_archive(archive, [], extra=hardlink)
            with self.assertRaises(ValueError):
                tools.extract_archive(archive, parent / 'hard', tools.REVISION)
            self.assertFalse((parent / 'wrong').exists())
            self.assertFalse((parent / 'hard').exists())


if __name__ == '__main__':
    unittest.main()
