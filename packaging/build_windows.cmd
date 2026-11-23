@echo off
rem Builds the Windows folder: dist\OoTRr-in-game-tracker\ (OoTRr-in-game-tracker.exe = the window, ootr-tracker.exe = the command line).
rem Uses an isolated environment in build\venv-windows (the system Python is not modified).
setlocal
cd /d "%~dp0.."
if not exist build\venv-windows\Scripts\python.exe (
    python -m venv build\venv-windows || exit /b 1
)
set PY=build\venv-windows\Scripts\python.exe
%PY% -m pip install --disable-pip-version-check -q -c packaging\constraints.txt -r requirements.txt pyinstaller || exit /b 1
%PY% -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller-windows packaging\ootr_tracker.spec || exit /b 1
copy /y README.md dist\OoTRr-in-game-tracker\README.md >nul
copy /y LICENSE dist\OoTRr-in-game-tracker\LICENSE >nul
copy /y THIRD_PARTY_NOTICES.md dist\OoTRr-in-game-tracker\THIRD_PARTY_NOTICES.md >nul
echo.
echo Built: dist\OoTRr-in-game-tracker\OoTRr-in-game-tracker.exe
