@echo off
cd /d "%~dp0"
call python model\train_model.py
call python app.py
pause
