# SPDX-License-Identifier: GPL-3.0-only
#
# Simplified build script for packaging the mod as <base>-<mod_version>.wotmod.
import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET


def read_json(path):
    handle = open(path, 'r')
    try:
        return json.load(handle)
    finally:
        handle.close()


def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path)


def remove_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.isfile(path):
        os.remove(path)


def copytree(source, destination):
    ensure_dir(destination)
    for root, dirs, files in os.walk(source):
        relative_root = os.path.relpath(root, source)
        target_root = destination if relative_root == '.' else os.path.join(destination, relative_root)
        ensure_dir(target_root)

        for directory in dirs:
            ensure_dir(os.path.join(target_root, directory))

        for name in files:
            shutil.copy2(os.path.join(root, name), os.path.join(target_root, name))


def zip_folder(source, destination):
    archive = zipfile.ZipFile(destination, 'w', zipfile.ZIP_STORED)
    try:
        for root, dirs, files in os.walk(source):
            relative_root = os.path.relpath(root, source)
            if relative_root == '.':
                relative_root = ''

            for directory in dirs:
                folder_entry = os.path.join(relative_root, directory).replace('\\', '/') + '/'
                info = zipfile.ZipInfo(folder_entry)
                archive.writestr(info, '')

            for name in files:
                full_path = os.path.join(root, name)
                archive_name = os.path.join(relative_root, name).replace('\\', '/')
                info = zipfile.ZipInfo(archive_name)
                info.external_attr = 33206 << 16
                source_handle = open(full_path, 'rb')
                try:
                    archive.writestr(info, source_handle.read())
                finally:
                    source_handle.close()
    finally:
        archive.close()


def compile_python_sources(python_executable, root_dir):
    if not python_executable:
        raise ValueError('Python 2.7 executable is not configured in build.json or WOT_PYTHON27.')

    for root, _dirs, files in os.walk(root_dir):
        for name in files:
            if not name.endswith('.py'):
                continue
            source_path = os.path.join(root, name)
            subprocess.check_call([python_executable, '-m', 'py_compile', source_path])


def collect_compiled_file(py_path):
    pyc_path = py_path + 'c'
    if os.path.isfile(pyc_path):
        return pyc_path

    pycache_dir = os.path.join(os.path.dirname(py_path), '__pycache__')
    if os.path.isdir(pycache_dir):
        prefix = os.path.splitext(os.path.basename(py_path))[0] + '.'
        for name in os.listdir(pycache_dir):
            if name.startswith(prefix) and name.endswith('.pyc'):
                return os.path.join(pycache_dir, name)
    raise IOError('Compiled file not found for %s' % py_path)


def copy_python_bytecode(source_dir, destination_dir):
    for root, _dirs, files in os.walk(source_dir):
        for name in files:
            if not name.endswith('.py'):
                continue

            source_path = os.path.join(root, name)
            compiled_path = collect_compiled_file(source_path)
            relative_path = os.path.relpath(source_path, source_dir)
            relative_pyc = os.path.splitext(relative_path)[0] + '.pyc'
            target_path = os.path.join(destination_dir, relative_pyc)
            ensure_dir(os.path.dirname(target_path))
            shutil.copy2(compiled_path, target_path)


def build_meta_xml(info):
    root = ET.Element('root')
    ET.SubElement(root, 'id').text = info['id']
    ET.SubElement(root, 'version').text = info['version']
    ET.SubElement(root, 'name').text = info['name']
    ET.SubElement(root, 'description').text = info['description']
    return ET.tostring(root, encoding='utf-8')


def write_file(path, data, mode):
    ensure_dir(os.path.dirname(path))
    handle = open(path, mode)
    try:
        handle.write(data)
    finally:
        handle.close()


def versioned_artifact_names(info):
    """Return (wotmod_filename, zip_filename) using info.version before .wotmod / .zip."""
    mod_version = info.get('version', '0.0.0')
    package_name = info.get('package_name', 'Mod.wotmod')
    if not package_name.lower().endswith('.wotmod'):
        package_name = package_name + '.wotmod'
    stem = package_name[: -len('.wotmod')]
    wotmod_file = '%s-%s.wotmod' % (stem, mod_version)

    archive_name = info.get('archive_name', stem + '.zip')
    if archive_name.lower().endswith('.zip'):
        arch_stem = archive_name[: -len('.zip')]
    else:
        arch_stem = archive_name
    zip_file = '%s-%s.zip' % (arch_stem, mod_version)
    return wotmod_file, zip_file


def cleanup_python_artifacts(source_dir):
    for root, dirs, files in os.walk(source_dir):
        for name in files:
            if name.endswith('.pyc'):
                remove_path(os.path.join(root, name))
        for directory in dirs:
            if directory == '__pycache__':
                remove_path(os.path.join(root, directory))


def main():
    parser = argparse.ArgumentParser(description='Build the Caphhh.currentAccAndAimTime WoT mod.')
    parser.add_argument('--ingame', action='store_true', help='Copy build output into the configured WoT folder.')
    parser.add_argument('--distribute', action='store_true', help='Create a distributable zip alongside the .wotmod file.')
    args = parser.parse_args()

    config = read_json('build.json')
    python_executable = config['software'].get('python') or os.environ.get('WOT_PYTHON27')
    game_folder = config['game'].get('folder') or os.environ.get('WOT_FOLDER')
    game_version = config['game'].get('version') or os.environ.get('WOT_VERSION')
    bundle_guiflash = config.get('packaging', {}).get('bundle_guiflash', False)
    info = config['info']

    temp_dir = 'temp'
    release_dir = 'release'
    python_dir = 'python'
    wotmod_name, zip_name = versioned_artifact_names(info)
    output_package = os.path.join(release_dir, wotmod_name)
    output_archive = os.path.join(release_dir, zip_name)

    remove_path(temp_dir)
    ensure_dir(temp_dir)
    ensure_dir(release_dir)

    compile_python_sources(python_executable, python_dir)

    if bundle_guiflash and os.path.isdir(os.path.join('resources', 'in')):
        copytree(os.path.join('resources', 'in'), os.path.join(temp_dir, 'res'))

    copy_python_bytecode(python_dir, os.path.join(temp_dir, 'res', 'scripts', 'client'))
    write_file(os.path.join(temp_dir, 'meta.xml'), build_meta_xml(info), 'wb')

    zip_folder(temp_dir, output_package)
    print('Built %s' % output_package)

    if args.distribute:
        dist_root = os.path.join(temp_dir, 'distribute')
        dist_mods = os.path.join(dist_root, 'mods', game_version)
        ensure_dir(dist_mods)
        shutil.copy2(output_package, os.path.join(dist_mods, wotmod_name))

        if os.path.isdir(os.path.join('resources', 'out')):
            copytree(os.path.join('resources', 'out'), dist_root)

        zip_folder(dist_root, output_archive)
        print('Built %s' % output_archive)

    if args.ingame:
        if not game_folder or not game_version:
            raise ValueError('Set game folder/version in build.json or WOT_FOLDER/WOT_VERSION before using --ingame.')

        target_mods_dir = os.path.join(game_folder, 'mods', game_version)
        ensure_dir(target_mods_dir)
        shutil.copy2(output_package, os.path.join(target_mods_dir, wotmod_name))

        if os.path.isdir(os.path.join('resources', 'out')):
            copytree(os.path.join('resources', 'out'), game_folder)

        print('Copied build output to %s' % target_mods_dir)

    cleanup_python_artifacts(python_dir)
    remove_path(temp_dir)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sys.stderr.write('%s\n' % error)
        sys.exit(1)
