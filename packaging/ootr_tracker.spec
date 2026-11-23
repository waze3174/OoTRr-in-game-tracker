# PyInstaller spec: the tool as a folder with two programs sharing one set of files.
#   OoTRr-in-game-tracker(.exe)  the window (no console window on Windows)
#   ootr-tracker(.exe)           the command line, with a console: what the emulator and scripts call
# Build with packaging/build_windows.cmd or packaging/build_linux.sh.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
PACKAGE = ROOT / 'ootr_tracker'

datas = [
    # The prebuilt module (GPL-3, with its licence and source note) and the community check names.
    (str(PACKAGE / 'resources'), 'ootr_tracker/resources'),
]
hiddenimports = collect_submodules('ootr_tracker') + collect_submodules('websockets') + ['tkinter']

a = Analysis(
    [str(ROOT / 'packaging' / 'launcher.py')],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['pytest', 'numpy', 'matplotlib', 'PIL'],
    noarchive=False,
)
pyz = PYZ(a.pure)
window = EXE(pyz, a.scripts, [], exclude_binaries=True, name='OoTRr-in-game-tracker', console=False, upx=False)
command = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ootr-tracker', console=True, upx=False)
COLLECT(window, command, a.binaries, a.datas, name='OoTRr-in-game-tracker', upx=False)
