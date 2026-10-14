@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   Napisy PL - instalacja i uruchomienie
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Nie znaleziono Pythona. Zainstaluj Python 3.10+ z https://www.python.org/downloads/
    echo Podczas instalacji zaznacz "Add Python to PATH".
    pause
    exit /b 1
  )
  set PYTHON=python
) else (
  set PYTHON=py -3
)
%PYTHON% -m pip install --upgrade pip
if errorlevel 1 goto fail
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto fail
%PYTHON% napisy_pl.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo.
echo Instalacja lub uruchomienie nie powiodlo sie. Przeczytaj komunikat powyzej.
pause
exit /b 1
