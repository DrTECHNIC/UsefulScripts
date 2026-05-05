<#
.SYNOPSIS
    Перенумеровывает файлы, имена которых начинаются с числа.
.DESCRIPTION
    Находит файлы с числовым префиксом, сортирует по числу и присваивает новые номера. При конфликте имён файл пропускается.
    С помощью -LogPath можно сохранить журнал переименований, а -Rollback выполнит откат.
.PARAMETER Path
    Путь к папке (по умолчанию текущая).
.PARAMETER StartNumber
    Начальный номер (по умолчанию 1).
.PARAMETER MinDigits
    Минимальное количество цифр в номере (по умолчанию 1). Ширина подбирается автоматически.
.PARAMETER LogPath
    Путь к файлу журнала для записи или отката. Относительные пути разрешаются относительно текущего расположения.
.PARAMETER Rollback
    Запускает откат переименований по файлу журнала.
.PARAMETER WhatIf
    Показать планируемые изменения без выполнения.
.EXAMPLE
    .\RenameByName.ps1 -Path ".\Documents" -StartNumber 100 -MinDigits 4 -LogPath "лог.txt"
    Переименовывает файлы и записывает изменения в лог.txt в текущей папке.
.EXAMPLE
    .\RenameByName.ps1 -Rollback -LogPath "лог.txt"
    Откатывает все переименования, сохранённые в лог.txt.
#>
[CmdletBinding(SupportsShouldProcess=$true, DefaultParameterSetName='Rename')]
param(
    [Parameter(ParameterSetName='Rename', Position=0)]
    [string]$Path = ".",
    [Parameter(ParameterSetName='Rename')]
    [ValidateRange(1, [int]::MaxValue)]
    [int]$StartNumber = 1,
    [Parameter(ParameterSetName='Rename')]
    [ValidateRange(1, 99)]
    [int]$MinDigits = 1,
    [Parameter(ParameterSetName='Rename')]
    [Parameter(ParameterSetName='Rollback', Mandatory=$true)]
    [string]$LogPath,
    [Parameter(ParameterSetName='Rollback', Mandatory=$true)]
    [switch]$Rollback,
    [Alias('h')]
    [switch]$ShowHelp
)

if ($LogPath -and -not [System.IO.Path]::IsPathRooted($LogPath)) {
    $LogPath = Join-Path (Get-Location) $LogPath
}

if ($ShowHelp) {
@"
Перенумерация файлов с числами в начале имени.
Поддерживает ведение журнала и откат.

Параметры:
  -Path          Папка с файлами (по умолч. текущая).
  -StartNumber   Начальный номер (по умолч. 1).
  -MinDigits     Мин. цифр в номере (по умолч. 1).
  -LogPath       Путь к файлу журнала (относительно текущего расположения).
  -Rollback      Откат по журналу (требует -LogPath).
  -WhatIf        Предпросмотр без изменений.

Примеры:
  .\RenameByName.ps1 -Path ".\Documents" -StartNumber 100 -MinDigits 4 -LogPath "лог.txt"
  .\RenameByName.ps1 -Rollback -LogPath "лог.txt"
"@
    exit
}

if ($PSCmdlet.ParameterSetName -eq 'Rollback') {
    if (-not (Test-Path $LogPath)) {
        Write-Error "Журнал '$LogPath' не найден."
        exit 1
    }
    $logLines = @(Get-Content $LogPath)
    if ($logLines.Count -eq 0) {
        Write-Host "Журнал пуст. Откат не требуется." -ForegroundColor Yellow
        exit
    }
    Write-Host "Режим отката. Строк в журнале: $($logLines.Count)" -ForegroundColor Cyan

    $total = $logLines.Count
    $rolledBack = 0; $skipped = 0; $errorsRoll = 0
    $progressActivity = "Откат переименований"

    for ($i = $total - 1; $i -ge 0; $i--) {
        if ($total -gt 20) {
            $percent = [math]::Round(($total - $i) / $total * 100, 2)
            Write-Progress -Activity $progressActivity -Status "Обработка строки $($total - $i) из $total" -PercentComplete $percent
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

        if (-not (Test-Path $newPath)) {
            Write-Warning "Файл '$newPath' не найден – пропуск."
            $skipped++
            continue
        }

        $oldName = Split-Path $oldPath -Leaf
        $oldDir = Split-Path $oldPath -Parent
        $targetPath = Join-Path $oldDir $oldName

        if (Test-Path $targetPath) {
            Write-Warning "Конфликт: '$oldName' уже существует. Пропускаем откат для '$newPath'."
            $skipped++
            continue
        }

        if ($WhatIfPreference) {
            Write-Host "WhatIf: откат $(Split-Path $newPath -Leaf) -> $oldName" -ForegroundColor Yellow
        }
        elseif ($PSCmdlet.ShouldProcess($newPath, "Откат: вернуть '$oldName'")) {
            try {
                Rename-Item -Path $newPath -NewName $oldName -ErrorAction Stop
                Write-Host "Откат: $(Split-Path $newPath -Leaf) -> $oldName" -ForegroundColor Green
                $rolledBack++
            } catch {
                Write-Error "Ошибка отката '$newPath': $_"
                $errorsRoll++
            }
        }
    }

    if ($total -gt 20) { Write-Progress -Activity $progressActivity -Completed }

    Write-Host "`nОткат завершён:" -ForegroundColor Cyan
    if ($WhatIfPreference) {
        Write-Host "  Всего записей: $total" -ForegroundColor White
        Write-Host "  Будет откачено: $($total - $skipped - $errorsRoll)" -ForegroundColor Green
        Write-Host "  Пропущено: $skipped" -ForegroundColor Yellow
    } else {
        Write-Host "  Всего записей: $total" -ForegroundColor White
        Write-Host "  Успешно откачено: $rolledBack" -ForegroundColor Green
        Write-Host "  Пропущено: $skipped" -ForegroundColor Yellow
        if ($errorsRoll -gt 0) { Write-Host "  Ошибок: $errorsRoll" -ForegroundColor Red }
    }
    if ($WhatIfPreference) { Write-Host "  (Режим WhatIf – изменения не выполнялись)" -ForegroundColor Yellow }
    exit
}

if (-not (Test-Path $Path -PathType Container)) {
    Write-Error "Ошибка: папка '$Path' не существует или не является папкой."
    exit 1
}

$numberedFiles = @(Get-ChildItem -Path $Path -File | Where-Object { $_.BaseName -match '^\d+' } | ForEach-Object {
    $num = 0
    if ($_.BaseName -match '^(\d+)') {
        $num = [int]$matches[1]
    }
    [PSCustomObject]@{
        File   = $_
        Number = $num
        Name   = $_.Name
    }
} | Sort-Object Number)

if ($numberedFiles.Count -eq 0) {
    Write-Host "Не найдено файлов с номерами в начале имени." -ForegroundColor Yellow
    exit
}

$maxNewNumber = $StartNumber + $numberedFiles.Count - 1
$requiredDigits = [Math]::Max($MinDigits, $maxNewNumber.ToString().Length)

Write-Host "Найдено файлов с номерами: $($numberedFiles.Count)" -ForegroundColor Cyan
Write-Host "Начальный номер: $StartNumber, максимальный новый номер: $maxNewNumber, цифр: $requiredDigits"

$current = $StartNumber
$renamed = 0; $skipped = 0; $conflicts = 0; $errors = 0
$plannedRename = 0; $plannedSkip = 0; $plannedConflict = 0
$progressActivity = "Перенумерация"

$logWriter = $null
if ($LogPath) {
    $logDir = Split-Path $LogPath -Parent
    if ($logDir -and -not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    $logWriter = [System.IO.StreamWriter]::new($LogPath, $false, [System.Text.UTF8Encoding]::new($true))
}

foreach ($item in $numberedFiles) {
    $file = $item.File
    if ($numberedFiles.Count -gt 20) {
        $percent = [math]::Round((($current - $StartNumber) / $numberedFiles.Count) * 100, 2)
        Write-Progress -Activity $progressActivity -Status "Обработка: $($file.Name)" -PercentComplete $percent
    }

    $ext = $file.Extension
    $newName = "{0:D$requiredDigits}{1}" -f $current, $ext
    $newPath = Join-Path $Path $newName

    if ($file.Name -eq $newName) {
        Write-Verbose "Пропущен '$($file.Name)' - уже правильное имя"
        $skipped++
        $plannedSkip++
        $current++
        continue
    }

    if (Test-Path $newPath) {
        Write-Warning "Конфликт: '$newName' уже существует. Пропускаем '$($file.Name)'."
        $conflicts++
        $plannedConflict++
        $current++
        continue
    }

    $plannedRename++

    if ($WhatIfPreference) {
        Write-Host "WhatIf: $($file.Name) -> $newName" -ForegroundColor Yellow
    }
    elseif ($PSCmdlet.ShouldProcess($file.FullName, "Переименовать в '$newName'")) {
        try {
            Rename-Item -Path $file.FullName -NewName $newName -ErrorAction Stop
            Write-Host "Переименован: $($file.Name) -> $newName" -ForegroundColor Green
            $renamed++
            if ($logWriter) { $logWriter.WriteLine("$($file.FullName)`t$newPath") }
        } catch {
            Write-Error "Ошибка при переименовании '$($file.Name)': $_"
            $errors++
        }
    }

    $current++
}

if ($logWriter) { $logWriter.Close() }
if ($numberedFiles.Count -gt 20) { Write-Progress -Activity $progressActivity -Completed }

Write-Host "`nОбработка завершена:" -ForegroundColor Cyan
if ($WhatIfPreference) {
    Write-Host "  Всего файлов с номерами: $($numberedFiles.Count)" -ForegroundColor White
    Write-Host "  Будет переименовано: $plannedRename" -ForegroundColor Green
    Write-Host "  Будет пропущено: $plannedSkip" -ForegroundColor Yellow
    if ($plannedConflict -gt 0) { Write-Host "  Конфликтов: $plannedConflict" -ForegroundColor Red }
    Write-Host "  (Режим WhatIf – изменения не выполнялись)" -ForegroundColor Yellow
} else {
    Write-Host "  Всего файлов с номерами: $($numberedFiles.Count)" -ForegroundColor White
    Write-Host "  Успешно переименовано: $renamed" -ForegroundColor Green
    Write-Host "  Пропущено: $skipped" -ForegroundColor Yellow
    if ($conflicts -gt 0) { Write-Host "  Конфликтов: $conflicts" -ForegroundColor Red }
    if ($errors -gt 0) { Write-Host "  Ошибок: $errors" -ForegroundColor Red }
    if ($LogPath) { Write-Host "  Журнал записан: $LogPath" -ForegroundColor Cyan }
}
