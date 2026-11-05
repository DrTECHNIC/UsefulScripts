<#
.SYNOPSIS
    Переименовывает файлы по дате, присваивая им последовательные номера.
.DESCRIPTION
    Файлы сортируются по выбранной дате и получают имена "номер.расширение". При конфликте имён файл пропускается.
    С помощью -LogPath можно сохранить журнал переименований, а -Rollback выполнит откат.
.PARAMETER Path
    Путь к папке (по умолчанию текущая).
.PARAMETER DateType
    Тип даты: LastWriteTime, CreationTime, LastAccessTime (по умолч. LastWriteTime).
.PARAMETER Digits
    Минимальное количество цифр в номере (0 = автовыбор, минимум 3). По умолчанию 0.
.PARAMETER LogPath
    Путь к файлу журнала для записи или отката.
.PARAMETER Rollback
    Запускает откат переименований по файлу журнала.
.PARAMETER WhatIf
    Показать планируемые изменения без выполнения.
.EXAMPLE
    .\RenameByDate.ps1 -Path "C:\Фото" -DateType CreationTime -Digits 4 -LogPath "лог.txt"
    Переименовывает файлы и записывает изменения в лог.
.EXAMPLE
    .\RenameByDate.ps1 -Rollback -LogPath "лог.txt"
    Откатывает все переименования, сохранённые в лог.txt.
#>
[CmdletBinding(SupportsShouldProcess=$true, DefaultParameterSetName='Rename')]
param(
    [Parameter(ParameterSetName='Rename', Position=0)]
    [string]$Path = ".",
    [Parameter(ParameterSetName='Rename')]
    [ValidateSet('LastWriteTime','CreationTime','LastAccessTime')]
    [string]$DateType = 'LastWriteTime',
    [Parameter(ParameterSetName='Rename')]
    [ValidateRange(0, 99)]
    [int]$Digits = 0,
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
Переименование файлов по дате с последовательной нумерацией.
Поддерживает ведение журнала и откат.

Параметры:
  -Path       Папка с файлами (по умолч. текущая).
  -DateType   Дата сортировки: LastWriteTime, CreationTime, LastAccessTime (по умолч. LastWriteTime).
  -Digits     Мин. цифр в номере (0 = автовыбор, минимум 3).
  -LogPath    Путь к файлу журнала.
  -Rollback   Откат по журналу (требует -LogPath).
  -WhatIf     Предпросмотр без изменений.

Примеры:
  .\RenameByDate.ps1 -Path "C:\Фото" -DateType CreationTime -Digits 4 -LogPath "лог.txt"
  .\RenameByDate.ps1 -Rollback -LogPath "лог.txt"
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

$files = @(Get-ChildItem -Path $Path -File | Sort-Object $DateType)
if ($files.Count -eq 0) {
    Write-Host "В папке '$Path' нет файлов." -ForegroundColor Yellow
    exit
}

if ($Digits -eq 0) {
    $Digits = [Math]::Max(3, [string]$files.Count.Length)
}

Write-Host "Найдено файлов: $($files.Count)" -ForegroundColor Cyan
Write-Host "Сортировка по: $DateType"
Write-Host "Формат имени: номер ($Digits цифр) + исходное расширение"

$counter = 1
$renamed = 0; $skipped = 0; $conflicts = 0; $errors = 0
$plannedRename = 0; $plannedSkip = 0; $plannedConflict = 0
$progressActivity = "Переименование по дате"

$logWriter = $null
if ($LogPath) {
    $logDir = Split-Path $LogPath -Parent
    if ($logDir -and -not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    $logWriter = [System.IO.StreamWriter]::new($LogPath, $false, [System.Text.UTF8Encoding]::new($true))
}

foreach ($file in $files) {
    if ($files.Count -gt 20) {
        $percent = [math]::Round(($counter / $files.Count) * 100, 2)
        Write-Progress -Activity $progressActivity -Status "Обработка: $($file.Name)" -PercentComplete $percent
    }

    $ext = $file.Extension
    $newName = "{0:D$Digits}{1}" -f $counter, $ext
    $newPath = Join-Path $Path $newName

    if ($file.Name -eq $newName) {
        Write-Verbose "Пропущен '$($file.Name)' - уже правильное имя"
        $skipped++
        $plannedSkip++
        $counter++
        continue
    }

    if (Test-Path $newPath) {
        Write-Warning "Конфликт: '$newName' уже существует. Пропускаем '$($file.Name)'."
        $conflicts++
        $plannedConflict++
        $counter++
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

    $counter++
}

if ($logWriter) { $logWriter.Close() }
if ($files.Count -gt 20) { Write-Progress -Activity $progressActivity -Completed }

Write-Host "`nОбработка завершена:" -ForegroundColor Cyan
if ($WhatIfPreference) {
    Write-Host "  Всего файлов: $($files.Count)" -ForegroundColor White
    Write-Host "  Будет переименовано: $plannedRename" -ForegroundColor Green
    Write-Host "  Будет пропущено: $plannedSkip" -ForegroundColor Yellow
    if ($plannedConflict -gt 0) { Write-Host "  Конфликтов: $plannedConflict" -ForegroundColor Red }
    Write-Host "  (Режим WhatIf – изменения не выполнялись)" -ForegroundColor Yellow
} else {
    Write-Host "  Всего файлов: $($files.Count)" -ForegroundColor White
    Write-Host "  Успешно переименовано: $renamed" -ForegroundColor Green
    Write-Host "  Пропущено: $skipped" -ForegroundColor Yellow
    if ($conflicts -gt 0) { Write-Host "  Конфликтов: $conflicts" -ForegroundColor Red }
    if ($errors -gt 0) { Write-Host "  Ошибок: $errors" -ForegroundColor Red }
    if ($LogPath) { Write-Host "  Журнал записан: $LogPath" -ForegroundColor Cyan }
}
