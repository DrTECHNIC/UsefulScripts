# PSWorkbench:Title=Перенумерация по номерам
# PSWorkbench:Target=Directory
<#
.SYNOPSIS
    Перенумеровывает файлы в директории, имена которых начинаются с числа.
.DESCRIPTION
    Находит файлы с числовым префиксом, сортирует их по числовому значению и присваивает новые номера.
    При конфликте имён файл пропускается. С помощью -LogPath можно сохранить журнал, а -Rollback выполнит откат.
.PARAMETER Path
    Путь к директории с файлами.
.PARAMETER StartNumber
    Начальный номер счётчика.
.PARAMETER MinDigits
    Минимальное количество цифр в номере (ширина автоматически расширяется под максимальный номер).
.PARAMETER LogPath
    Путь к файлу журнала для записи или отката.
.PARAMETER Rollback
    Запускает откат переименований по указанному файлу журнала.
.PARAMETER WhatIf
    Предпросмотр планируемых изменений без фактического переименования.
.PARAMETER ShowHelp
    Выводит справку по использованию скрипта.
.EXAMPLE
    .\RenameByName.ps1 -Path ".\Documents" -StartNumber 100 -MinDigits 4 -LogPath "лог.txt"
.EXAMPLE
    .\RenameByName.ps1 -Rollback -LogPath "лог.txt"
#>
[CmdletBinding(SupportsShouldProcess = $true, DefaultParameterSetName = 'Rename')]
param(
    [Parameter(ParameterSetName = 'Rename', Position = 0)]
    [string]$Path = '.',

    [Parameter(ParameterSetName = 'Rename')]
    [ValidateRange(1, [int]::MaxValue)]
    [int]$StartNumber = 1,

    [Parameter(ParameterSetName = 'Rename')]
    [Alias('Digits')]
    [ValidateRange(1, 99)]
    [int]$MinDigits = 1,

    [Parameter(ParameterSetName = 'Rename')]
    [Parameter(ParameterSetName = 'Rollback', Mandatory = $true)]
    [string]$LogPath,

    [Parameter(ParameterSetName = 'Rollback', Mandatory = $true)]
    [switch]$Rollback,

    [Parameter(ParameterSetName = 'Help', Mandatory = $true)]
    [Alias('h')]
    [switch]$ShowHelp
)

function Invoke-RenameRollback {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResolvedLogPath,
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.PSCmdlet]$Cmdlet,
        [bool]$IsWhatIf
    )

    if (-not (Test-Path -LiteralPath $ResolvedLogPath -PathType Leaf)) {
        Write-Error "Журнал '$ResolvedLogPath' не найден."
        exit 1
    }

    $logLines = @(
        Get-Content -LiteralPath $ResolvedLogPath -Encoding UTF8 |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($logLines.Count -eq 0) {
        Write-Output "Журнал пуст. Откат не требуется."
        exit 0
    }

    Write-Output "=== Откат переименований ==="
    Write-Output "Журнал          : $ResolvedLogPath"
    Write-Output "Записей         : $($logLines.Count)"
    Write-Output ""

    $total = $logLines.Count
    $rolledBack = 0
    $skipped = 0
    $errorsRoll = 0
    $activity = "Откат переименований"

    try {
        for ($i = $total - 1; $i -ge 0; $i--) {
            if ($total -gt 20) {
                $done = $total - $i
                $percent = [math]::Round(($done / $total) * 100, 2)
                Write-Progress -Activity $activity -Status "Обработка записи $done из $total" -PercentComplete $percent
            }

            $line = $logLines[$i]
            $parts = $line -split "`t"
            if ($parts.Count -ne 2) {
                Write-Warning "Неверный формат строки: $line"
                $errorsRoll++
                continue
            }

            $oldPath = $parts[0]
            $newPath = $parts[1]

            if (-not (Test-Path -LiteralPath $newPath -PathType Leaf)) {
                Write-Warning "Файл '$newPath' не найден — пропуск."
                $skipped++
                continue
            }

            $oldName = Split-Path -Path $oldPath -Leaf
            $oldDir = Split-Path -Path $oldPath -Parent
            $targetPath = Join-Path -Path $oldDir -ChildPath $oldName

            if (Test-Path -LiteralPath $targetPath) {
                Write-Warning "Конфликт: '$oldName' уже существует. Откат для '$newPath' пропущен."
                $skipped++
                continue
            }

            $currentLeaf = Split-Path -Path $newPath -Leaf
            if ($IsWhatIf) {
                Write-Output "WhatIf: $currentLeaf -> $oldName"
                $rolledBack++
            }
            elseif ($Cmdlet.ShouldProcess($newPath, "Откат: вернуть '$oldName'")) {
                try {
                    Rename-Item -LiteralPath $newPath -NewName $oldName -ErrorAction Stop
                    Write-Output "Откат: $currentLeaf -> $oldName"
                    $rolledBack++
                }
                catch {
                    Write-Error "Ошибка отката '$newPath': $($_.Exception.Message)"
                    $errorsRoll++
                }
            }
        }
    }
    finally {
        if ($total -gt 20) { Write-Progress -Activity $activity -Completed }
    }

    Write-Output ""
    Write-Output "=== Итоги отката ==="
    Write-Output "Всего записей   : $total"
    if ($IsWhatIf) {
        Write-Output "Будет откачено  : $rolledBack"
        Write-Output "Пропущено       : $skipped"
        if ($errorsRoll -gt 0) { Write-Output "Ошибок формата  : $errorsRoll" }
        Write-Output "Режим           : WhatIf (изменения не выполнялись)"
    }
    else {
        Write-Output "Откачено        : $rolledBack"
        Write-Output "Пропущено       : $skipped"
        if ($errorsRoll -gt 0) { Write-Output "Ошибок          : $errorsRoll" }
    }
}

if ($ShowHelp) {
    $scriptName = $MyInvocation.MyCommand.Name
    Write-Output @"
Перенумерация файлов с числами в начале имени.
Поддерживает ведение журнала и откат.

Параметры:
  -Path            Директория с файлами.
  -StartNumber     Начальный номер счётчика.
  -MinDigits       Минимальное количество цифр в номере (1..99).
  -LogPath         Путь к файлу журнала.
  -Rollback        Откат по журналу (требует -LogPath).
  -WhatIf          Предпросмотр без изменений.
  -ShowHelp (-h)   Показать эту справку.

Примеры:
  .\$scriptName -Path ".\Documents" -StartNumber 100 -MinDigits 4 -LogPath "лог.txt"
  .\$scriptName -Rollback -LogPath "лог.txt"
"@
    exit 0
}

$resolvedLogPath = ''
if (-not [string]::IsNullOrWhiteSpace($LogPath)) {
    if ([System.IO.Path]::IsPathRooted($LogPath)) {
        $resolvedLogPath = [System.IO.Path]::GetFullPath($LogPath)
    }
    else {
        $resolvedLogPath = [System.IO.Path]::GetFullPath((Join-Path -Path (Get-Location).ProviderPath -ChildPath $LogPath))
    }
}

if ($PSCmdlet.ParameterSetName -eq 'Rollback') {
    Invoke-RenameRollback -ResolvedLogPath $resolvedLogPath -Cmdlet $PSCmdlet -IsWhatIf ([bool]$WhatIfPreference)
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Path)) {
    $Path = '.'
}

if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
    Write-Error "Директория '$Path' не существует или не является папкой."
    exit 1
}

$resolvedDir = (Resolve-Path -LiteralPath $Path).ProviderPath
$numberedFiles = @(
    Get-ChildItem -LiteralPath $resolvedDir -File |
    Where-Object {
        $_.BaseName -match '^(\d+)' -and
        (-not $resolvedLogPath -or -not $_.FullName.Equals($resolvedLogPath, [System.StringComparison]::OrdinalIgnoreCase))
    } |
    ForEach-Object {
        $num = [System.Numerics.BigInteger]::Parse($Matches[1])
        [PSCustomObject]@{
            File   = $_
            Number = $num
            Name   = $_.Name
        }
    } |
    Sort-Object -Property Number, Name
)

if ($numberedFiles.Count -eq 0) {
    Write-Output "В директории '$resolvedDir' не найдено файлов с числом в начале имени."
    exit 0
}

$maxNewNumber = [long]$StartNumber + $numberedFiles.Count - 1
$requiredDigits = [Math]::Max($MinDigits, $maxNewNumber.ToString().Length)

Write-Output "=== Перенумерация по номерам ==="
Write-Output "Директория      : $resolvedDir"
Write-Output "Найдено файлов  : $($numberedFiles.Count)"
Write-Output "Диапазон номеров: $StartNumber .. $maxNewNumber"
Write-Output "Разрядность     : $requiredDigits"
Write-Output ""

$current = [long]$StartNumber
$renamed = 0
$skipped = 0
$conflicts = 0
$errors = 0
$activity = "Перенумерация"

$logWriter = $null
if ($resolvedLogPath -and -not $WhatIfPreference) {
    $logDir = Split-Path -Path $resolvedLogPath -Parent
    if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $logWriter = [System.IO.StreamWriter]::new($resolvedLogPath, $false, [System.Text.UTF8Encoding]::new($true))
}

try {
    foreach ($item in $numberedFiles) {
        $file = $item.File
        if ($numberedFiles.Count -gt 20) {
            $processed = $current - $StartNumber
            $percent = [math]::Round(($processed / $numberedFiles.Count) * 100, 2)
            Write-Progress -Activity $activity -Status "Обработка: $($file.Name)" -PercentComplete $percent
        }

        $newName = "{0:D$requiredDigits}{1}" -f $current, $file.Extension
        $newPath = Join-Path -Path $resolvedDir -ChildPath $newName

        if ($file.Name.Equals($newName, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Verbose "Пропущен '$($file.Name)' — уже правильное имя."
            $skipped++
            $current++
            continue
        }

        if (Test-Path -LiteralPath $newPath) {
            Write-Warning "Конфликт: '$newName' уже существует. Пропускаем '$($file.Name)'."
            $conflicts++
            $current++
            continue
        }

        if ($WhatIfPreference) {
            Write-Output "WhatIf: $($file.Name) -> $newName"
            $renamed++
        }
        elseif ($PSCmdlet.ShouldProcess($file.FullName, "Переименовать в '$newName'")) {
            try {
                Rename-Item -LiteralPath $file.FullName -NewName $newName -ErrorAction Stop
                Write-Output "Переименован: $($file.Name) -> $newName"
                $renamed++
                if ($logWriter) {
                    $logWriter.WriteLine("$($file.FullName)`t$newPath")
                }
            }
            catch {
                Write-Error "Ошибка при переименовании '$($file.Name)': $($_.Exception.Message)"
                $errors++
            }
        }

        $current++
    }
}
finally {
    if ($logWriter) { $logWriter.Dispose() }
    if ($numberedFiles.Count -gt 20) { Write-Progress -Activity $activity -Completed }
}

Write-Output ""
Write-Output "=== Итоги обработки ==="
Write-Output "Всего файлов    : $($numberedFiles.Count)"
if ($WhatIfPreference) {
    Write-Output "Будет изменено  : $renamed"
    Write-Output "Пропущено       : $skipped"
    if ($conflicts -gt 0) { Write-Output "Конфликтов      : $conflicts" }
    Write-Output "Режим           : WhatIf (изменения не выполнялись)"
}
else {
    Write-Output "Переименовано   : $renamed"
    Write-Output "Пропущено       : $skipped"
    if ($conflicts -gt 0) { Write-Output "Конфликтов      : $conflicts" }
    if ($errors -gt 0) { Write-Output "Ошибок          : $errors" }
    if ($resolvedLogPath) { Write-Output "Журнал записан  : $resolvedLogPath" }
}
