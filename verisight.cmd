@echo off
setlocal
pushd "%~dp0backend"
".venv\Scripts\python.exe" -m app
set "VERISIGHT_EXIT=%ERRORLEVEL%"
popd
exit /b %VERISIGHT_EXIT%
