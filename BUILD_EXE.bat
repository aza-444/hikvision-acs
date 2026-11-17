@echo off
chcp 65001 >nul
title Hikvision Turniket - Standalone EXE Yaratish

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
cls
echo ================================================================================
echo    HIKVISION TURNIKET - STANDALONE (.EXE) DASTUR YASASH
echo    (Hech qanday Python talab qilmaydigan mustaqil Windows ilovasi)
echo ================================================================================
echo.

python -m pip install --upgrade pyinstaller -r requirements.txt

echo [i] EXE fayl yig'ilmoqda (PyInstaller Admin UAC bilan)...
pyinstaller --noconfirm ^
    --onedir ^
    --windowed ^
    --uac-admin ^
    --add-data "resources;resources" ^
    --name "HikvisionACS" ^
    main.py

if %errorlevel% equ 0 (
    echo.
    echo ================================================================================
    echo [+] MUVAFFAQINATLI YARATILDI!
    echo     Tayyor EXE dastur: dist\HikvisionACS\HikvisionACS.exe
    echo     Ushbu papkani istalgan Windows kompyuteriga ko'chirib ishlatish mumkin!
    echo ================================================================================
) else (
    echo [X] Xatolik yuz berdi!
)

pause
