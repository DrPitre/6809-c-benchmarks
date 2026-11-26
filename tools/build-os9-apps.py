"""Build the pinned OS/runtime environment (after the compiler installers)."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    pins = json.loads((ROOT / 'tools/os9-app-sources.json').read_text())
    paths = {'apps': 'nitros9-apps', 'nitros9': 'nitros9', 'toolshed': 'toolshed', 'video': 'pico-thing-video'}
    env = os.environ.copy()
    toolbin = ROOT / 'build/toolchain/bin'
    env['PATH'] = str(toolbin) + os.pathsep + env['PATH']
    def run(command, cwd=ROOT):
        subprocess.run([str(v) for v in command], cwd=cwd, env=env, check=True)
    sources = ROOT / 'build/sources'
    sources.mkdir(parents=True, exist_ok=True)
    for key, name in paths.items():
        destination = sources / name
        pin = pins[key]
        if not destination.exists():
            run(['git', 'init', destination])
            run(['git', '-C', destination, 'remote', 'add', 'origin', pin['url']])
            run(['git', '-C', destination, 'fetch', '--depth', '1', 'origin', pin['revision']])
            run(['git', '-C', destination, 'checkout', '--detach', 'FETCH_HEAD'])
        revision = subprocess.check_output(['git', '-C', str(destination), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != pin['revision']:
            raise SystemExit('Source revision mismatch: ' + name)
        dirty = subprocess.check_output(['git', '-C', str(destination), 'status', '--porcelain', '--untracked-files=no'], text=True)
        if dirty:
            raise SystemExit('Source has local modifications: ' + name)
    toolshed = sources / 'toolshed/build/unix'
    # Build only the disk utility and its libraries; GUI tools and upstream
    # unit-test executables are not dependencies of the benchmark image.
    for component in ('libtoolshed', 'libnative', 'libcecb', 'librbf', 'libcoco',
                      'libdecb', 'libdiskimage', 'libdragondos', 'libmisc', 'libsys', 'os9'):
        run(['make', '-C', toolshed / component])
    toolbin.mkdir(parents=True, exist_ok=True)
    shutil.copy2(toolshed / 'os9/os9', toolbin / 'os9')
    video = sources / 'pico-thing-video'
    run(['make', '-C', sources / 'markrvmurray-usim', '-j2', 'usim09pt', 'PICOVIDEO=' + str(video)])
    kernel = sources / 'nitros9'
    env.update(NITROS9DIR=str(kernel), SOURCE_DATE_EPOCH='1795695367')
    run(['make', '-C', kernel / 'recipes/picothing/l2', '-j2', 'DSKIMAGE=bench.dsk',
         'OS9FORMAT_CMD=os9 format -e -l65536',
         'SHELLMODS=shell_21 echo iniz link load save unlink'])


if __name__ == '__main__':
    main()
