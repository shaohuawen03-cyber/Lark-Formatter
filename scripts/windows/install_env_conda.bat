@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
set "REPO_ROOT=%~dp0..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

rem --- 1) 探测可用的包管理器：优先 mamba，其次 micromamba，再退回 conda ---
set "MGR_CMD="
where mamba >nul 2>&1
if !errorlevel! == 0 (
    set "MGR_CMD=mamba"
    set "MGR_LABEL=mamba"
    goto :found_mgr
)
where micromamba >nul 2>&1
if !errorlevel! == 0 (
    set "MGR_CMD=micromamba"
    set "MGR_LABEL=micromamba"
    goto :found_mgr
)
where conda >nul 2>&1
if !errorlevel! == 0 (
    set "MGR_CMD=conda"
    set "MGR_LABEL=conda"
    goto :found_mgr
)

:found_mgr
if not defined MGR_CMD (
    echo [ERROR] No mamba / micromamba / conda found in PATH.
    pause
    exit /b 1
)

echo [1/3] Package Manager: %MGR_LABEL%

echo [2/3] Installing Python dependencies via pip...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [3/3] Environment is ready.
echo Launch command:
echo   python main.py
exit /b 0
