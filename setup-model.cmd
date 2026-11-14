@echo off
setlocal
pushd "%~dp0backend"
".venv\Scripts\python.exe" -m pip install --no-compile "torch==2.15.0" "torchvision==0.29.2" --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --no-compile -e ".[ml]"
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m app.setup_model
if errorlevel 1 goto fail
popd
exit /b 0
:fail
popd
exit /b 1
