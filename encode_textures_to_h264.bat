@echo off
setlocal enableextensions

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "INPUT_DIR=%~1"
set "OUTPUT_DIR=%~2"
set "CRF=%~3"
set "FPS=%~4"

if "%CRF%"=="" set "CRF=18"
if "%FPS%"=="" set "FPS=30"

if not exist "%INPUT_DIR%" (
	echo Error: input dir not found: %INPUT_DIR%
	exit /b 2
)

if not exist "%OUTPUT_DIR%" (
	mkdir "%OUTPUT_DIR%" >nul 2>&1
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
	echo Error: ffmpeg not found in PATH.
	exit /b 2
)

set "PS_SCRIPT=%~dp0encode_textures_to_h264.ps1"
if not exist "%PS_SCRIPT%" (
	echo Error: script not found: %PS_SCRIPT%
	exit /b 2
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -InputDir "%INPUT_DIR%" -OutputDir "%OUTPUT_DIR%" -Crf %CRF% -Fps %FPS%
if errorlevel 1 exit /b %ERRORLEVEL%
exit /b 0

:usage
echo Usage: %~nx0 ^<input_dir^> ^<output_dir^> [crf] [fps]
echo Example: %~nx0 outputs output_videos 18 30
exit /b 1
