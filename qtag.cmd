@echo off
set "QTAG_PY=%APPDATA%\uv\tools\qtag\Scripts\python.exe"
if not exist "%QTAG_PY%" (
  echo qtag is not installed. From the project directory run:
  echo   uv tool install --python 3.14 -e .
  exit /b 1
)
"%QTAG_PY%" -m qtag %*
exit /b %ERRORLEVEL%
