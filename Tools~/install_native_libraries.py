#!/usr/bin/env python3
"""Install user-supplied FMOD 2.03.14 libraries into an embedded UPM package.

Uses only Python 3's standard library. No native libraries are downloaded.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile

PACKAGE = 'com.dotline.fmod'
PREFIX = 'Assets/Plugins/FMOD/'
VERSION = '0x00020314'


def native_relative(path):
    """Accept only FMOD's public native-library folders; reject traversal."""
    if '\\' in path or '\x00' in path or not path.startswith(PREFIX):
        return None
    rel = PurePosixPath(path[len(PREFIX):])
    if rel.is_absolute() or any(p in ('..', '.') or ':' in p for p in rel.parts):
        raise ValueError('Unsafe asset path: ' + path)
    parts = rel.parts
    if len(parts) < 3 or parts[0] not in ('platforms', 'staging'):
        return None
    if parts[1] not in ('android', 'win', 'mac', 'linux', 'ios', 'tvos', 'visionos', 'uwp', 'html5'):
        raise ValueError('Unrecognised FMOD native platform: ' + path)
    if parts[2] not in ('lib', 'lib.meta'):
        return None
    # FMOD ships editor libraries under staging to support locked-library updates.
    # For a fresh embedded install, place them directly into the final platform folder.
    return PurePosixPath('platforms', *parts[1:])


def plugin_meta(guid, platform, cpu):
    os_name, target = {
        'win': ('Windows', 'Win' if cpu == 'x86' else 'Win64'),
        'linux': ('Linux', 'Linux64'),
        'mac': ('OSX', 'OSXUniversal'),
    }[platform]
    # ARM64 Windows is a player-only library on the minimum supported Unity 2022.3.
    editor_enabled = 0 if platform == 'win' and cpu == 'ARM64' else 1
    return f'''fileFormatVersion: 2
guid: {guid}
PluginImporter:
  externalObjects: {{}}
  serializedVersion: 2
  iconMap: {{}}
  executionOrder: {{}}
  isPreloaded: 0
  isOverridable: 0
  platformData:
  - first:
      Any:
    second:
      enabled: 0
      settings: {{}}
  - first:
      Editor: Editor
    second:
      enabled: {editor_enabled}
      settings:
        CPU: {cpu}
        OS: {os_name}
  - first:
      Standalone: {target}
    second:
      enabled: 1
      settings:
        CPU: {cpu}
  userData:
  assetBundleName:
  assetBundleVariant:
'''


def install(project, unitypackage, package_source):
    project = Path(project).resolve()
    package_source = Path(package_source).resolve()
    if not (project / 'Assets').is_dir() or not (project / 'Packages/manifest.json').is_file():
        raise ValueError('Expected a Unity project with Assets and Packages/manifest.json')
    metadata = json.loads((package_source / 'package.json').read_text(encoding='utf-8'))
    if metadata['name'] != PACKAGE:
        raise ValueError('The source folder is not ' + PACKAGE)
    destination = project / 'Packages' / PACKAGE
    if destination.exists() and destination.resolve() != package_source:
        raise ValueError('An embedded FMOD package already exists. Run its installer instead.')
    library = project / 'Library'
    library.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='FMODNativeImport-', dir=library) as scratch:
        scratch = Path(scratch)
        entries = {}
        expanded = 0
        # Streaming mode avoids repeatedly decompressing this ~100 MB archive.
        with tarfile.open(unitypackage, 'r|gz') as archive:
            for member in archive:
                name = member.name.removeprefix('./')
                if member.isdir():
                    continue
                match = re.fullmatch(r'([0-9a-fA-F]{32})/(pathname|asset|asset.meta|preview.png)', name)
                if not member.isfile() or not match:
                    raise ValueError('Unexpected unitypackage entry: ' + name)
                if member.size > 256 * 1024 * 1024:
                    raise ValueError('Archive member exceeds 256 MB')
                expanded += member.size
                if expanded > 1024 * 1024 * 1024:
                    raise ValueError('Expanded archive exceeds 1 GB')
                guid, kind = match.groups()
                if kind == 'preview.png':
                    continue
                entry = entries.setdefault(guid, {})
                if kind in entry:
                    raise ValueError('Duplicate archive entry: ' + name)
                target = scratch / guid / kind
                target.parent.mkdir(exist_ok=True)
                with archive.extractfile(member) as incoming, target.open('wb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
                entry[kind] = target

        assets = {}
        version_found = False
        for guid, entry in entries.items():
            if 'pathname' not in entry:
                raise ValueError('Missing pathname for ' + guid)
            path = entry['pathname'].read_text(encoding='utf-8').strip()
            if path == PREFIX + 'src/fmod.cs':
                wrapper = entry['asset'].read_text(encoding='utf-8')
                version_found = bool(re.search(r'public const int number\s*=\s*' + VERSION + r'\s*;', wrapper))
            relative = native_relative(path)
            if relative is not None:
                if relative in assets:
                    previous = assets[relative][1]
                    if any('asset' in e and e['asset'].stat().st_size for e in (entry, previous)):
                        raise ValueError('Duplicate native asset: ' + path)
                    # platforms and staging share parent folders. Retain the platform GUID.
                    if path.startswith(PREFIX + 'platforms/'):
                        assets[relative] = (path, entry)
                    continue
                assets[relative] = (path, entry)
        if not version_found:
            raise ValueError('This installer requires FMOD 2.03.14 (fmodstudio20314.unitypackage)')
        required = PurePosixPath('platforms/win/lib/x86_64/fmodstudioL.dll')
        if required not in assets or 'asset' not in assets[required][1]:
            raise ValueError('Archive does not include the expected FMOD editor native library')

        # Validate the whole archive before modifying the package.
        for relative, (original, entry) in assets.items():
            if 'asset.meta' not in entry:
                raise ValueError('Missing native asset metadata: ' + original)
            meta = entry['asset.meta'].read_text(encoding='utf-8')
            if not re.search(r'^guid: [0-9a-fA-F]{32}\s*$', meta, re.MULTILINE):
                raise ValueError('Invalid native asset metadata: ' + original)
            if 'asset' in entry and entry['asset'].stat().st_size:
                target = destination.joinpath(*relative.parts)
                if target.exists() and (not target.is_file() or hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(entry['asset'].read_bytes()).digest()):
                    raise ValueError('A different native library already exists. Close Unity and remove the old local libraries before updating: ' + str(target))

        if not destination.exists():
            shutil.copytree(package_source, destination, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.tgz'))
        count = 0
        for relative, (original, entry) in sorted(assets.items(), key=lambda pair: len(pair[0].parts)):
            target = destination.joinpath(*relative.parts)
            if 'asset' in entry and entry['asset'].stat().st_size:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Idempotent installs must not rewrite DLLs already loaded by Unity.
                if not target.exists():
                    shutil.copy2(entry['asset'], target)
                count += 1
            else:
                target.mkdir(parents=True, exist_ok=True)
            meta = entry['asset.meta'].read_text(encoding='utf-8')
            if original.startswith(PREFIX + 'staging/') and target.name in ('fmodstudioL.dll', 'libfmodstudioL.so', 'fmodstudioL.bundle'):
                guid = re.search(r'^guid: ([0-9a-fA-F]{32})', meta, re.MULTILINE).group(1)
                cpu = relative.parts[3] if relative.parts[1] != 'mac' else 'AnyCPU'
                cpu = 'ARM64' if cpu == 'arm64' else cpu
                meta = plugin_meta(guid, relative.parts[1], cpu)
            Path(str(target) + '.meta').write_text(meta, encoding='utf-8')

        # Local embedding takes precedence over a registry or Git dependency.
        # Retain all unrelated dependencies and settings.
        manifest_path = project / 'Packages/manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['dependencies'][PACKAGE] = 'file:' + PACKAGE
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        print(f'Installed {count} FMOD 2.03.14 native files into {destination}')
        print('Refresh Unity. Local native libraries are excluded from Git and npm publication.')
        return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Unity project root')
    parser.add_argument('--unitypackage', required=True, help='User-supplied FMOD 2.03.14 unitypackage')
    parser.add_argument('--package-source', default=str(Path(__file__).resolve().parents[1]), help='Installed com.dotline.fmod source folder')
    args = parser.parse_args()
    try:
        install(args.project, args.unitypackage, args.package_source)
    except (ValueError, OSError, tarfile.TarError, KeyError) as error:
        parser.exit(1, 'FMOD installation failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
