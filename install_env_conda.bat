@echo off
setlocal
call "%~dp0scripts\windows\install_env_conda.bat" %*
exit /b %errorlevel%
