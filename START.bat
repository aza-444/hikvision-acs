@echo off
chcp 65001 >nul
title Hikvision Turniket Nazorati - Yuklash va Ishga Tushirish

:: ============================================================================
:: 1. ADMINISTRATOR HUQUQINI TEKSHIRISH VA AVTOMATIK SO'RASH (UAC Elevation)
:: ============================================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ====================================================================
    echo   ADMINISTRATOR HUQUQI BILAN QAYTA ISHGA TUSHIRILMOQDA...
    echo ====================================================================
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
cls
echo ================================================================================
echo          HIKVISION TURNIKET NAZORAT TIZIMI (iVMS PRO)
echo ================================================================================
echo.

:: ============================================================================
:: 2. PYTHON O'RNATILGANLIGINI TEKSHIRISH YOKI AVTOMATIK YUKLAB O'RNATISH
:: ============================================================================
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Tizimda Python topilmadi!
    echo [i] Python Windows uchun avtomatik yuklab olinmoqda va o'rnatilmoqda...
    echo     Iltimos, bir oz kuting (internet tezligiga qarab 1-2 daqiqa)...
    echo.
    
    set PYTHON_INSTALLER=%TEMP%\python_installer.exe
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe', '%PYTHON_INSTALLER%')"
    
    if exist "%PYTHON_INSTALLER%" (
        echo [i] Python o'rnatilmoqda (silent install)...
        start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
        del "%PYTHON_INSTALLER%"
        echo [+] Python muvaffaqiyatli o'rnatildi!
        set "PATH=C:\Program Files\Python311;C:\Program Files\Python311\Scripts;%PATH%"
    ) else (
        echo [X] Pythonni yuklab bo'lmadi! Internet aloqasini tekshiring.
        pause
        exit /b
    )
)

echo [+] Python tayyor:
python --version
echo.

:: ============================================================================
:: 3. KERAKLI KUTUBXONALARNI AVTOMATIK TEKSHIRISH VA O'RNATISH
:: ============================================================================
echo [i] Dastur uchun kerakli texnologiyalar tekshirilmoqda...
python -c "import PyQt6, requests, xmltodict, openpyxl" >nul 2>&1
if %errorlevel% neq 0 (
    echo [i] Kutubxonalar o'rnatilmoqda (PyQt6, requests, openpyxl, xmltodict)...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [X] Kutubxonalarni o'rnatishda xatolik yuz berdi!
        pause
        exit /b
    )
    echo [+] Barcha kerakli modullar o'rnatildi!
) else (
    echo [+] Barcha kerakli modullar allaqachon tayyor!
)

:: ============================================================================
:: 4. ISH STOLIGA (DESKTOP) YORLIQ (SHORTCUT) YARATISH
:: ============================================================================
set SHORTCUT_PATH=%USERPROFILE%\Desktop\Hikvision Turniket Nazorati.lnk
if not exist "%SHORTCUT_PATH%" (
    echo [i] Ish stoliga (Desktop) qulay yorliq yaratilmoqda...
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%~dp0START.bat'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = 'shell32.dll,48'; $s.Save()"
    echo [+] Ish stolida 'Hikvision Turniket Nazorati' yorlig'i yaratildi!
)

echo.
echo ================================================================================
echo   DASTUR ISHGA TUSHIRILMOQDA... MARHAMAT!
echo ================================================================================
echo.

start "" pythonw main.py
exit
