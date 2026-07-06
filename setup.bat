@echo off
title YTMusic Desktop Player - Kurulum
color 0A
echo.
echo ====================================================
echo   YTMusic Desktop Player - Kurulum Scripti
echo ====================================================
echo.

:: Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi!
    echo Python'u https://python.org adresinden indirin.
    pause
    exit /b 1
)
echo [OK] Python bulundu.

:: pip guncelleme
echo.
echo [*] pip guncelleniyor...
python -m pip install --upgrade pip --quiet

:: Bagimliliklar
echo [*] Bagimliliklar yukleniyor...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [HATA] Bagimliliklar yuklenemedi!
    pause
    exit /b 1
)
echo [OK] Bagimliliklar yuklendi.

:: FFmpeg kontrolu
echo.
echo [*] FFmpeg kontrol ediliyor...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [UYARI] FFmpeg bulunamadi!
    echo.
    echo FFmpeg, MP3 donusumu icin gereklidir.
    echo Asagidaki yontemlerden biriyle yukleyin:
    echo.
    echo   1. winget install Gyan.FFmpeg
    echo   2. https://ffmpeg.org/download.html adresinden indirin
    echo.
    set /p INSTALL_FFMPEG="winget ile otomatik yuklemek ister misiniz? (E/H): "
    if /i "%INSTALL_FFMPEG%"=="E" (
        echo FFmpeg yukleniyor...
        winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
        echo [OK] FFmpeg yuklendi. Terminali yeniden baslatin.
    )
) else (
    echo [OK] FFmpeg bulundu.
)

:: Klasor yapisi olustur
echo.
echo [*] Klasor yapisi olusturuluyor...
if not exist "data\downloads\playlists" mkdir "data\downloads\playlists"
if not exist "data\downloads\singles" mkdir "data\downloads\singles"
if not exist "data\downloads\covers" mkdir "data\downloads\covers"
if not exist "data\cache\thumbnails" mkdir "data\cache\thumbnails"
echo [OK] Klasorler olusturuldu.

echo.
echo ====================================================
echo   Kurulum tamamlandi!
echo   Calistirmak icin: python main.py
echo ====================================================
echo.
pause
