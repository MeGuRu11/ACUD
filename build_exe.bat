@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

for /F "delims=" %%A in ('echo prompt $E ^| cmd') do set "ESC=%%A"

set "APP_NAME=ASUD"
set "ENTRY_FILE=ASUD.py"
set "ASSETS_DIR=assets"
set "ICON_PNG=assets\asud_icon.png"
set "ICON_ICO=assets\asud_icon.ico"
set "DIST_EXE=dist\ASUD.exe"
set "PYINSTALLER_ASSETS=assets;assets"
set "PYTHON_CMD="

title ASUD EXE Builder

if /I "%~1"=="--help" goto help
if /I "%~1"=="/?" goto help

call :banner

call :step "1/6" "Проверка Python"
call :detect_python
if errorlevel 1 goto failed
call :ok "Найден: !PYTHON_VERSION!"

call :step "2/6" "Проверка PyInstaller"
%PYTHON_CMD% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    call :info "PyInstaller не найден. Устанавливаю через pip..."
    %PYTHON_CMD% -m pip install --upgrade pyinstaller
    if errorlevel 1 (
        call :error "Не удалось установить PyInstaller."
        goto failed
    )
) else (
    for /F "tokens=*" %%V in ('%PYTHON_CMD% -m PyInstaller --version 2^>^&1') do set "PYINSTALLER_VERSION=%%V"
    call :ok "PyInstaller !PYINSTALLER_VERSION! уже установлен."
)

call :step "3/6" "Проверка файлов проекта"
if not exist "%ENTRY_FILE%" (
    call :error "Не найден файл запуска: %ENTRY_FILE%"
    goto failed
)
if not exist "%ASSETS_DIR%\" (
    call :error "Не найдена папка ресурсов: %ASSETS_DIR%"
    goto failed
)
call :ok "Файлы проекта на месте."

call :step "4/6" "Подготовка иконки приложения"
set "ICON_OPTION="
if not exist "%ICON_PNG%" goto icon_missing
%PYTHON_CMD% -c "from pathlib import Path; from PIL import Image; src=Path(r'%ICON_PNG%'); dst=Path(r'%ICON_ICO%'); img=Image.open(src).convert('RGBA'); img.save(dst, sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if errorlevel 1 (
    call :error "Не удалось подготовить ICO из PNG. Проверьте Pillow."
    goto failed
)
set "ICON_OPTION=--icon=%ICON_ICO%"
call :ok "Иконка готова: %ICON_ICO%"
goto icon_done

:icon_missing
call :info "PNG-иконка не найдена, сборка продолжится без иконки."

:icon_done

call :step "5/6" "Сборка ASUD.exe"
call :line
%PYTHON_CMD% -m PyInstaller --noconfirm --clean --onefile --windowed --name ASUD --workpath "build\pyinstaller" --specpath "build" --distpath "dist" %ICON_OPTION% --add-data "%PYINSTALLER_ASSETS%" --hidden-import matplotlib.backends.backend_tkagg "%ENTRY_FILE%"
set "BUILD_EXIT=%ERRORLEVEL%"
call :line
if not "%BUILD_EXIT%"=="0" (
    call :error "PyInstaller завершился с ошибкой. Код: %BUILD_EXIT%"
    goto failed
)

call :step "6/6" "Проверка результата"
if not exist "%DIST_EXE%" (
    call :error "EXE не найден: %DIST_EXE%"
    goto failed
)
for %%I in ("%DIST_EXE%") do set "EXE_SIZE=%%~zI"
call :ok "Готово: %DIST_EXE%"
call :info "Размер файла: !EXE_SIZE! байт"

echo.
call :line
echo %ESC%[92m  Сборка завершена успешно.%ESC%[0m
echo %ESC%[97m  Запустить программу можно из файла:%ESC%[0m %ESC%[96m%DIST_EXE%%ESC%[0m
call :line
echo.
pause
exit /b 0

:failed
echo.
call :line
echo %ESC%[91m  Сборка остановлена.%ESC%[0m
echo %ESC%[97m  Проверьте сообщение об ошибке выше и повторите запуск.%ESC%[0m
call :line
echo.
pause
exit /b 1

:detect_python
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    call :error "Python не найден. Установите Python 3.12 или добавьте его в PATH."
    exit /b 1
)
for /F "tokens=*" %%V in ('%PYTHON_CMD% --version 2^>^&1') do set "PYTHON_VERSION=%%V"
exit /b 0

:banner
cls
echo.
call :line
echo %ESC%[96m    АСУД — упаковка приложения в EXE%ESC%[0m
echo %ESC%[90m    ВМедА им. С.М. Кирова ^| Desktop build pipeline%ESC%[0m
call :line
echo.
exit /b 0

:step
echo.
echo %ESC%[96m[%~1]%ESC%[0m %ESC%[97m%~2%ESC%[0m
exit /b 0

:ok
echo   %ESC%[92mOK%ESC%[0m    %~1
exit /b 0

:info
echo   %ESC%[94mINFO%ESC%[0m  %~1
exit /b 0

:error
echo   %ESC%[91mERROR%ESC%[0m %~1
exit /b 0

:line
echo %ESC%[90m----------------------------------------------------------------%ESC%[0m
exit /b 0

:help
echo.
echo ASUD EXE Builder
echo.
echo Usage:
echo   build_exe.bat
echo.
echo Result:
echo   dist\ASUD.exe
echo.
exit /b 0
