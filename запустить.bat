@echo off
chcp 65001 >nul
title Калькулятор патч-кордов

REM Переходим в директорию, где находится этот батник
cd /d "%~dp0"

echo.
echo ============================================
echo   Запуск калькулятора патч-кордов
echo ============================================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python с https://www.python.org/
    pause
    exit /b 1
)

REM Проверяем наличие зависимостей
echo Проверка зависимостей...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ИНФО] Зависимости не установлены. Устанавливаю...
    echo Это может занять несколько минут при первом запуске.
    echo.
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ОШИБКА] Не удалось установить зависимости!
        echo Проверьте подключение к интернету и попробуйте вручную:
        echo   pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo [УСПЕХ] Зависимости установлены!
    echo.
) else (
    echo [OK] Зависимости установлены
    echo.
)

REM Запускаем приложение
python run_app.py

REM Если скрипт завершился, ждём нажатия клавиши
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Приложение завершилось с ошибкой
    pause
)
