@echo off
rem Start LAN server hidden (pythonw, no console window) for Kindle access
cd /d %~dp0
.venv\Scripts\pythonw.exe serve.py --port 8000
