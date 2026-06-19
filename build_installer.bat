@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "PS_ARGS="
if /I "%~1"=="--no-pause" set "PS_ARGS=-NoPause"
if /I "%~2"=="--no-pause" set "PS_ARGS=-NoPause"
if /I "%~1"=="--help" set "PS_ARGS=-Help"
if /I "%~2"=="--help" set "PS_ARGS=-Help"
if /I "%~1"=="/?" set "PS_ARGS=-Help"
if /I "%~2"=="/?" set "PS_ARGS=-Help"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\build_installer.ps1" %PS_ARGS%
exit /b %ERRORLEVEL%
