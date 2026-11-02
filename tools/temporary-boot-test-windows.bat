@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "IMG=%~dp0A16-RMX2170-BOOT-STRUCTURE-TEST-CLANG21-NOT-FOR-FLASHING.img"

echo Ahmed Super Kernal A16 - TEMPORARY BOOT TEST ONLY
echo No flash, erase, format, unlock, or vbmeta command is used.
echo Use only with an already-unlocked bootloader.
echo.
if not exist "%IMG%" (
  echo Place the test IMG beside this BAT file.
  pause
  exit /b 2
)
where fastboot >nul 2>nul
if errorlevel 1 (
  echo fastboot.exe not found in PATH.
  pause
  exit /b 3
)
for /f "tokens=1" %%D in ('fastboot devices 2^>nul') do set "DEVICE=%%D"
if not defined DEVICE (
  echo No device detected in bootloader FASTBOOT mode.
  pause
  exit /b 4
)
echo Detected device: %DEVICE%
set /p "CONFIRM=Type BOOT to attempt temporary RAM boot, or anything else to cancel: "
if /I not "%CONFIRM%"=="BOOT" exit /b 0
fastboot boot "%IMG%"
if errorlevel 1 (
  echo FASTBOOT BOOT failed or is unsupported. No partition write was attempted.
  pause
  exit /b 5
)
echo Temporary boot command returned. Wait for Android, then inspect manually.
pause
exit /b 0
