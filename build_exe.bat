@echo off
REM Optional: build Cartoon.exe on your own Windows PC (needs Python 3.12 installed).
REM Most people should use the GitHub workflow instead (see README.md).
python -m pip install -r requirements.txt || goto :err
python tools\make_icon.py
pyinstaller --noconfirm --clean cartoon.spec || goto :err
echo.
echo Done: dist\Cartoon.exe
pause
exit /b 0
:err
echo Build failed.
pause
exit /b 1
