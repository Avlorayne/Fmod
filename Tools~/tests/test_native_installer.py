import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('installer', Path(__file__).parents[1] / 'install_native_libraries.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class NativeInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        (self.project / 'Assets').mkdir(parents=True)
        (self.project / 'Packages').mkdir()
        (self.project / 'Packages/manifest.json').write_text(json.dumps({'dependencies': {'com.example.keep': '1.2.3'}}))
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'package.json').write_text(json.dumps({'name': installer.PACKAGE, 'version': '1.0.0'}))

    def archive(self, version=installer.VERSION, extra=None):
        path = self.root / 'test.unitypackage'
        files = [
            ('src/fmod.cs', ('public const int number = ' + version + ';').encode()),
            ('platforms/win/lib/x86_64', b''),
            ('staging/win/lib/x86_64', b''),
            ('staging/win/lib/x86_64/fmodstudioL.dll', b'local-native-library'),
        ]
        if extra:
            files.append(extra)
        with tarfile.open(path, 'w:gz') as archive:
            for index, (name, data) in enumerate(files):
                guid = f'{index + 1:032x}'
                for kind, content in [('pathname', (installer.PREFIX + name).encode()), ('asset', data), ('asset.meta', ('fileFormatVersion: 2\nguid: ' + guid + '\n').encode())]:
                    member = tarfile.TarInfo(guid + '/' + kind)
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))
        return path

    def test_embeds_and_normalizes_staged_library_and_preserves_other_dependencies(self):
        count = installer.install(self.project, self.archive(), self.source)
        package = self.project / 'Packages' / installer.PACKAGE
        dll = package / 'platforms/win/lib/x86_64/fmodstudioL.dll'
        self.assertEqual(count, 1)
        self.assertEqual(dll.read_bytes(), b'local-native-library')
        self.assertIn('CPU: x86_64', Path(str(dll) + '.meta').read_text())
        self.assertIn('Editor: Editor', Path(str(dll) + '.meta').read_text())
        self.assertFalse((package / 'staging').exists())
        manifest = json.loads((self.project / 'Packages/manifest.json').read_text())
        self.assertEqual(manifest['dependencies']['com.example.keep'], '1.2.3')
        self.assertEqual(manifest['dependencies'][installer.PACKAGE], 'file:' + installer.PACKAGE)
        stamp = dll.stat().st_mtime_ns
        installer.install(self.project, self.archive(), package)
        self.assertEqual(dll.stat().st_mtime_ns, stamp)

    def test_version_mismatch_changes_neither_package_nor_manifest(self):
        manifest = (self.project / 'Packages/manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'requires FMOD 2.03.14'):
            installer.install(self.project, self.archive(version='0x00020313'), self.source)
        self.assertFalse((self.project / 'Packages' / installer.PACKAGE).exists())
        self.assertEqual((self.project / 'Packages/manifest.json').read_bytes(), manifest)

    def test_traversal_rejected_before_writing_package(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe asset path'):
            installer.install(self.project, self.archive(extra=('platforms/win/lib/../../../../escape.dll', b'bad')), self.source)
        self.assertFalse((self.project / 'Packages' / installer.PACKAGE).exists())

    def test_conflicting_loaded_library_is_not_overwritten(self):
        installer.install(self.project, self.archive(), self.source)
        package = self.project / 'Packages' / installer.PACKAGE
        dll = package / 'platforms/win/lib/x86_64/fmodstudioL.dll'
        dll.write_bytes(b'another-version')
        with self.assertRaisesRegex(ValueError, 'different native library'):
            installer.install(self.project, self.archive(), package)
        self.assertEqual(dll.read_bytes(), b'another-version')

    def test_link_members_are_rejected(self):
        archive_path = self.root / 'link.unitypackage'
        with tarfile.open(archive_path, 'w:gz') as archive:
            member = tarfile.TarInfo('a' * 32 + '/asset')
            member.type = tarfile.SYMTYPE
            member.linkname = '../outside'
            archive.addfile(member)
        with self.assertRaisesRegex(ValueError, 'Unexpected unitypackage entry'):
            installer.install(self.project, archive_path, self.source)


if __name__ == '__main__':
    unittest.main()
