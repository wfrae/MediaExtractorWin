@echo off
echo ========================================
echo  Building Media Extractor Installer
echo ========================================
echo.

:: Check for Inno Setup
where iscc >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Inno Setup is not installed
    echo Download from https://jrsoftware.org/isinfo.php
    echo Or install via: winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)

:: Build EXE first if not already built
if not exist "dist\MediaExtractor.exe" (
    echo Building EXE first...
    call build.bat
)

:: Build installer
echo.
echo Building installer with Inno Setup...
iscc installer.iss

echo.
echo ========================================
echo  Installer created!
echo  Location: Output\MediaExtractor-Setup-v2.0.exe
echo ========================================
pause
