@echo off
chcp 65001 > nul
title 提示词管理工具
cd /d "%~dp0"
python3 main.py
pause
