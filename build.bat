@echo off
echo ========================================
echo  Building Media Extractor for Windows
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Download from https://python.org
    pause
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Build EXE
echo.
echo Building standalone EXE...
pyinstaller --noconfirm --onefile --windowed ^
    --name "MediaExtractor" ^
    --icon "icon.ico" ^
    --add-data "icon.ico;." ^
    media_extractor.py

echo.
echo ========================================
echo  Build complete!
echo  EXE location: dist\MediaExtractor.exe
echo ========================================
pause
