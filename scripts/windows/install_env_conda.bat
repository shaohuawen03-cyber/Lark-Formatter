@echo off
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
    echo [ERROR] 未找到 mamba / micromamba / conda。
    echo 请先安装 Miniforge：https://github.com/conda-forge/miniforge
    echo   然后重新运行本脚本。
    pause
    exit /b 1
)

echo [1/3] 包管理器：%MGR_LABEL%

rem --- 2) 若环境已存在则复用，否则根据 environment.yml 创建 ---
%MGR_CMD% env list | findstr /R /C:"^lark-formatter" >nul 2>&1
if errorlevel 1 (
    echo [2/3] 创建 conda 环境 lark-formatter（来自 environment.yml）...
    %MGR_CMD% env create -f environment.yml
    if errorlevel 1 (
        echo [ERROR] 创建环境失败。
        pause
        exit /b 1
    )
) else (
    echo [2/3] 环境 lark-formatter 已存在，更新依赖...
    %MGR_CMD% env update -n lark-formatter -f environment.yml
    if errorlevel 1 (
        echo [ERROR] 更新环境失败。
        pause
        exit /b 1
    )
)

echo [3/3] 安装 pip 依赖（requirements.txt）...
%MGR_CMD% run -n lark-formatter python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip 依赖安装失败。
    pause
    exit /b 1
)

echo [OK] conda 环境就绪。
echo 启动方式：
echo   %MGR_CMD% run -n lark-formatter python main.py
exit /b 0
