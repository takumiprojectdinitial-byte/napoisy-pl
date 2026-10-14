@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Nie znaleziono polecenia py. Zainstaluj Python 3.10+.
  pause
  exit /b 1
)
py -3 -m pip install --upgrade pip
if errorlevel 1 goto fail
py -3 -m pip install -r requirements.txt
if errorlevel 1 goto fail
py -3 -m PyInstaller --noconfirm --clean --windowed --onedir --name NapisyPL ^
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all tokenizers ^
  --collect-all av --collect-all huggingface_hub --collect-all deep_translator ^
  napisy_pl.py
if errorlevel 1 goto fail
echo.
echo Gotowe. Uruchom dist\NapisyPL\NapisyPL.exe
echo Przenos caly folder dist\NapisyPL, nie sam plik EXE.
pause
exit /b 0
:fail
echo Budowanie nie powiodlo sie. Sprawdz komunikat powyzej.
pause
exit /b 1
