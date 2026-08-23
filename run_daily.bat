@echo off
rem Daily page generation: load .env, run main.py, append log
cd /d %~dp0
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
if not exist logs mkdir logs
echo ===== %date% %time% ===== >> logs\daily.log
.venv\Scripts\python.exe main.py >> logs\daily.log 2>&1
