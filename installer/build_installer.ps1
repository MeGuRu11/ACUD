[CmdletBinding()]
param(
    [switch]$NoPause,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$AppVersion = "1.0.0"
$AssetScript = Join-Path $PSScriptRoot "generate_installer_assets.py"
$InstallerScript = Join-Path $PSScriptRoot "ASUD.iss"
$BuildExeScript = Join-Path $ProjectDir "build_exe.bat"
$DistExe = Join-Path $ProjectDir "dist\ASUD.exe"
$SetupExe = Join-Path $ProjectDir "release\ASUD-Setup-$AppVersion.exe"
$BuildDir = Join-Path $ProjectDir "build"
$BuildLog = Join-Path $BuildDir "inno_setup_build.log"

function Write-Line {
    Write-Host ("-" * 68) -ForegroundColor DarkGray
}

function Write-Step([string]$Number, [string]$Text) {
    Write-Host ""
    Write-Host "[$Number] " -ForegroundColor Cyan -NoNewline
    Write-Host $Text -ForegroundColor White
}

function Write-Ok([string]$Text) {
    Write-Host "  [OK]    " -ForegroundColor Green -NoNewline
    Write-Host $Text
}

function Write-Info([string]$Text) {
    Write-Host "  [ИНФО]  " -ForegroundColor Cyan -NoNewline
    Write-Host $Text
}

function Write-Failure([string]$Text) {
    Write-Host "  [ОШИБКА] " -ForegroundColor Red -NoNewline
    Write-Host $Text
}

function Find-Python {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        return @{ Command = $py.Source; Prefix = @("-3") }
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        return @{ Command = $python.Source; Prefix = @() }
    }
    throw "Python не найден. Установите Python 3.12 и повторите запуск."
}

function Find-InnoCompiler {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    throw "Inno Setup 6 не найден. Установите его командой: winget install JRSoftware.InnoSetup"
}

function Invoke-Python([hashtable]$Python, [string[]]$Arguments) {
    & $Python.Command @($Python.Prefix) @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Команда Python завершилась с кодом $LASTEXITCODE."
    }
}

if ($Help) {
    Write-Host ""
    Write-Host "Сборщик установщика АСУД" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Использование:"
    Write-Host "  build_installer.bat"
    Write-Host "  build_installer.bat -NoPause"
    Write-Host ""
    Write-Host "Результат:"
    Write-Host "  release\ASUD-Setup-$AppVersion.exe"
    exit 0
}

try {
    Clear-Host
    Write-Host ""
    Write-Line
    Write-Host "    АСУД — сборка фирменного установщика" -ForegroundColor Cyan
    Write-Host "    ВМедА им. С.М. Кирова | Inno Setup 6" -ForegroundColor DarkGray
    Write-Line

    Write-Step "1/6" "Проверка Python"
    $python = Find-Python
    $version = & $python.Command @($python.Prefix) --version 2>&1
    Write-Ok "Найден: $version"

    Write-Step "2/6" "Проверка Inno Setup 6"
    $iscc = Find-InnoCompiler
    Write-Ok "Компилятор найден: $iscc"

    Write-Step "3/6" "Подготовка фирменных ресурсов"
    Invoke-Python $python @($AssetScript)
    Write-Ok "Фирменные изображения готовы."

    Write-Step "4/6" "Сборка приложения"
    & $BuildExeScript --no-pause
    if ($LASTEXITCODE -ne 0) {
        throw "Сборка ASUD.exe завершилась с кодом $LASTEXITCODE."
    }
    if (-not (Test-Path -LiteralPath $DistExe)) {
        throw "Не найден файл приложения: $DistExe"
    }
    Write-Ok "Файл приложения готов: dist\ASUD.exe"

    Write-Step "5/6" "Компиляция русскоязычного установщика"
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SetupExe) | Out-Null
    & $iscc $InstallerScript *> $BuildLog
    if ($LASTEXITCODE -ne 0) {
        Get-Content -LiteralPath $BuildLog
        throw "Inno Setup завершился с кодом $LASTEXITCODE."
    }

    Write-Step "6/6" "Проверка результата"
    if (-not (Test-Path -LiteralPath $SetupExe)) {
        throw "Установщик не найден: $SetupExe"
    }
    $setup = Get-Item -LiteralPath $SetupExe
    Write-Ok "Установщик готов: release\$($setup.Name)"
    Write-Info ("Размер: {0:N1} МБ" -f ($setup.Length / 1MB))
    Write-Info "Журнал сборки: build\inno_setup_build.log"

    Write-Host ""
    Write-Line
    Write-Host "  Сборка завершена успешно." -ForegroundColor Green
    Write-Host "  Готовый установщик: $SetupExe"
    Write-Line
    Write-Host ""
    if (-not $NoPause) {
        Read-Host "Нажмите Enter для выхода"
    }
    exit 0
}
catch {
    Write-Host ""
    Write-Failure $_.Exception.Message
    Write-Line
    Write-Host "  Сборка установщика остановлена." -ForegroundColor Red
    Write-Host "  Исправьте указанную ошибку и повторите запуск."
    Write-Line
    Write-Host ""
    if (-not $NoPause) {
        Read-Host "Нажмите Enter для выхода"
    }
    exit 1
}
