# PSWorkbench:Title=Сбор и сортировка списка папок
# PSWorkbench:Target=Directory
<#
.SYNOPSIS
    Собирает имена директорий (с телефона по MTP или с компьютера) либо сортирует список папок по полным путям.

.DESCRIPTION
    Работает в двух взаимоисключающих режимах:
    1) Сбор (базовый режим): получает имена подпапок из указанной директории на ПК или на подключённом по USB телефоне (MTP) и сохраняет их в текстовый файл (UTF-8 BOM).
    2) Обработка (-Process): читает файл со списком имён папок, рекурсивно ищет их в указанном каталоге на ПК и перезаписывает файл с сортировкой по полным путям:
       спецсимволы -> цифры (0-9) -> английский алфавит -> русский алфавит (Ё после Е) -> другие алфавиты.

.PARAMETER Path
    В режиме сбора — локальный путь на ПК или путь из Проводника на телефоне (например: "Этот компьютер\realme 13 Pro 5G\Внутренняя память\Ringtones").
    В режиме обработки (-Process) — локальная директория для рекурсивного поиска папок из списка.

.PARAMETER FilePath
    Путь к текстовому файлу списка (в режиме сбора создаётся или перезаписывается; в режиме обработки читается и обновляется).

.PARAMETER Mobile
    Источник данных при сборе: True — телефон (MTP через Shell.Application), False — локальный компьютер.

.PARAMETER Recurse
    Рекурсивный обход всех вложенных папок в режиме сбора.

.PARAMETER Process
    Переключает скрипт в режим обработки и сортировки списка папок.

.PARAMETER ShowHelp
    Выводит краткую справку по параметрам и примерам запуска.

.EXAMPLE
    .\GetFolderNames.ps1 -Path "Этот компьютер\Path" -FilePath ".\folders.txt" -Mobile True

.EXAMPLE
    .\GetFolderNames.ps1 -Path "D:\Archive" -FilePath ".\folders.txt" -Mobile False -Recurse

.EXAMPLE
    .\GetFolderNames.ps1 -Process -Path "D:\Target" -FilePath ".\folders.txt"
#>

[CmdletBinding(DefaultParameterSetName = 'Collect')]
param(
    [Parameter(ParameterSetName = 'Collect', Mandatory = $true, Position = 0)]
    [Parameter(ParameterSetName = 'Process', Mandatory = $true, Position = 0)]
    [Alias('SearchPath')]
    [string]$Path,

    [Parameter(ParameterSetName = 'Collect', Mandatory = $true, Position = 1)]
    [Parameter(ParameterSetName = 'Process', Mandatory = $true, Position = 1)]
    [Alias('OutputFile', 'InputFile', 'ListFile')]
    [string]$FilePath,

    [Parameter(ParameterSetName = 'Collect')]
    [ValidateSet('True', 'False')]
    [string]$Mobile = 'False',

    [Parameter(ParameterSetName = 'Collect')]
    [switch]$Recurse,

    [Parameter(ParameterSetName = 'Process', Mandatory = $true)]
    [Alias('Sort')]
    [switch]$Process,

    [Parameter(ParameterSetName = 'Help', Mandatory = $true)]
    [Alias('h')]
    [switch]$ShowHelp
)

$ErrorActionPreference = 'Stop'

if ($PSCmdlet.ParameterSetName -eq 'Help') {
    Write-Output @"
=== Сбор и сортировка списка папок ===

Режимы работы:
  1) Сбор (базовый режим) — сохраняет имена папок в текстовый файл.
  2) Обработка (-Process) — ищет папки из файла в каталоге и сортирует список по полным путям.

Параметры:
  -Path        Путь к директории (на ПК, на телефоне MTP или каталог поиска для -Process).
  -FilePath    Путь к txt-файлу списка (алиасы: -OutputFile, -InputFile, -ListFile).
  -Mobile      True (телефон по MTP) или False (компьютер). Только в режиме сбора.
  -Recurse     Обход вложенных папок. Только в режиме сбора.
  -Process     Запуск режима обработки и сортировки (алиас: -Sort).
  -ShowHelp    Показать эту справку (алиас: -h).

Порядок сортировки (-Process):
  1. Спецсимволы
  2. Цифры (0-9)
  3. Английский алфавит (A-Z, без учёта регистра)
  4. Русский алфавит (А-Я, Ё после Е, без учёта регистра)
  5. Другие алфавиты (без учёта регистра)

Примеры:
  .\GetFolderNames.ps1 -Path "Этот компьютер\Path" -FilePath ".\list.txt" -Mobile True
  .\GetFolderNames.ps1 -Path "D:\Music" -FilePath ".\list.txt" -Mobile False -Recurse
  .\GetFolderNames.ps1 -Process -Path "D:\Target" -FilePath ".\list.txt"
"@
    exit 0
}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Output ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Message)
}

function Get-MtpFolderNames {
    param(
        [Parameter(Mandatory = $true)] $Folder,
        [bool]$DoRecurse,
        [Parameter(Mandatory = $true)] [System.Collections.Generic.List[string]]$List
    )
    foreach ($item in $Folder.Items()) {
        if ($item.IsFolder) {
            $List.Add($item.Name)
            if ($DoRecurse) {
                $subFolder = $item.GetFolder
                if ($null -ne $subFolder) {
                    Get-MtpFolderNames -Folder $subFolder -DoRecurse $true -List $List
                }
            }
        }
    }
}

function Get-SortKey {
    param([string]$Text)

    $sb = New-Object System.Text.StringBuilder ([Math]::Max(16, $Text.Length * 6))
    foreach ($ch in $Text.ToCharArray()) {
        $c = [int]$ch

        if ($c -ge 0x0030 -and $c -le 0x0039) {
            # Группа 1: цифры 0-9
            [void]$sb.AppendFormat('1{0:D5}', $c - 0x0030)
        }
        elseif ($c -ge 0x0041 -and $c -le 0x005A) {
            # Группа 2: английский алфавит A-Z
            [void]$sb.AppendFormat('2{0:D5}', $c - 0x0041)
        }
        elseif ($c -ge 0x0061 -and $c -le 0x007A) {
            # Группа 2: английский алфавит a-z
            [void]$sb.AppendFormat('2{0:D5}', $c - 0x0061)
        }
        elseif ($c -ge 0x0410 -and $c -le 0x0415) {
            # Группа 3: русский алфавит А-Е (0..5)
            [void]$sb.AppendFormat('3{0:D5}', $c - 0x0410)
        }
        elseif ($c -ge 0x0430 -and $c -le 0x0435) {
            # Группа 3: русский алфавит а-е (0..5)
            [void]$sb.AppendFormat('3{0:D5}', $c - 0x0430)
        }
        elseif ($c -eq 0x0401 -or $c -eq 0x0451) {
            # Группа 3: Ё / ё (6 — строго после Е и перед Ж)
            [void]$sb.AppendFormat('3{0:D5}', 6)
        }
        elseif ($c -ge 0x0416 -and $c -le 0x042F) {
            # Группа 3: русский алфавит Ж-Я (7..32)
            [void]$sb.AppendFormat('3{0:D5}', ($c - 0x0410) + 1)
        }
        elseif ($c -ge 0x0436 -and $c -le 0x044F) {
            # Группа 3: русский алфавит ж-я (7..32)
            [void]$sb.AppendFormat('3{0:D5}', ($c - 0x0430) + 1)
        }
        elseif ([char]::IsLetter($ch)) {
            # Группа 4: любые другие алфавиты (без учёта регистра)
            $lower = [int][char]::ToLowerInvariant($ch)
            [void]$sb.AppendFormat('4{0:D5}', $lower)
        }
        else {
            # Группа 0: спецсимволы и прочие небуквенные символы
            [void]$sb.AppendFormat('0{0:D5}', $c)
        }
    }
    return $sb.ToString()
}

$utf8Bom = New-Object System.Text.UTF8Encoding($true)
$resolvedFile = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($FilePath)

# СБОР ИМЁН ДИРЕКТОРИЙ (ПК или телефон по MTP)
if ($PSCmdlet.ParameterSetName -eq 'Collect') {
    $isMobile = ($Mobile -ieq 'True')
    $names = New-Object 'System.Collections.Generic.List[string]'

    Write-Step ("=== Режим сбора ({0}) ===" -f $(if ($isMobile) { 'Телефон / MTP' } else { 'Компьютер' }))
    Write-Step ("Источник:   {0}" -f $Path)
    Write-Step ("Файл итога: {0}" -f $resolvedFile)
    Write-Step ("Рекурсия:   {0}" -f $(if ($Recurse) { 'Да' } else { 'Нет' }))

    if ($isMobile) {
        # --- Сбор с телефона по MTP ---
        $parts = @($Path -split '[\\/]' | Where-Object { $_ -ne '' })
        if ($parts.Count -gt 0 -and ($parts[0] -ieq 'Этот компьютер' -or $parts[0] -ieq 'This PC')) {
            if ($parts.Count -gt 1) {
                $parts = @($parts[1..($parts.Count - 1)])
            } else {
                $parts = @()
            }
        }

        if ($parts.Count -lt 1) {
            Write-Error "Некорректный MTP-путь: $Path"
            exit 1
        }

        $deviceName = $parts[0]
        $subPath = if ($parts.Count -gt 1) { @($parts[1..($parts.Count - 1)]) } else { @() }

        $shell = $null
        try {
            $shell = New-Object -ComObject Shell.Application
            $device = $shell.NameSpace(17).Items() |
                      Where-Object { $_.Name -eq $deviceName -and $_.IsFolder } |
                      Select-Object -First 1

            if (-not $device) {
                Write-Error "Устройство не найдено: '$deviceName'. Проверьте, что телефон подключён по USB и разблокирован."
                exit 1
            }

            $current = $device.GetFolder
            foreach ($seg in $subPath) {
                $next = $current.Items() |
                        Where-Object { $_.Name -eq $seg -and $_.IsFolder } |
                        Select-Object -First 1
                if (-not $next) {
                    Write-Error "Папка не найдена на устройстве: '$seg' (в пути: $Path)"
                    exit 1
                }
                $current = $next.GetFolder
            }

            Write-Step "Сканирование директорий на устройстве..."
            Get-MtpFolderNames -Folder $current -DoRecurse:$Recurse.IsPresent -List $names
        }
        finally {
            if ($null -ne $shell) {
                [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell)
                [GC]::Collect()
                [GC]::WaitForPendingFinalizers()
            }
        }
    }
    else {
        # --- Сбор с локального компьютера ---
        $resolvedSource = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
        if (-not (Test-Path -LiteralPath $resolvedSource -PathType Container)) {
            Write-Error "Директория не найдена: $resolvedSource"
            exit 1
        }

        Write-Step "Сканирование локальных директорий..."
        $gciParams = @{
            LiteralPath = $resolvedSource
            Directory = $true
            ErrorAction = 'SilentlyContinue'
        }
        if ($Recurse) {
            $gciParams['Recurse'] = $true
        }

        foreach ($dir in (Get-ChildItem @gciParams)) {
            $names.Add($dir.Name)
        }
    }

    $outDir = Split-Path -Parent $resolvedFile
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    [System.IO.File]::WriteAllLines($resolvedFile, [string[]]$names, $utf8Bom)

    Write-Output ""
    Write-Output "=== Итог сбора ==="
    Write-Output ("Найдено директорий: {0}" -f $names.Count)
    Write-Output ("Список сохранён:    {0}" -f $resolvedFile)
    exit 0
}

# РЕЖИМ 2: ПОИСК ПОЛНЫХ ПУТЕЙ И СОРТИРОВКА ФАЙЛА
if ($PSCmdlet.ParameterSetName -eq 'Process') {
    $resolvedSearch = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)

    Write-Step "=== Режим обработки и сортировки ==="
    Write-Step ("Файл списка:    {0}" -f $resolvedFile)
    Write-Step ("Каталог поиска: {0}" -f $resolvedSearch)

    if (-not (Test-Path -LiteralPath $resolvedFile -PathType Leaf)) {
        Write-Error "Файл списка не найден: $resolvedFile"
        exit 1
    }
    if (-not (Test-Path -LiteralPath $resolvedSearch -PathType Container)) {
        Write-Error "Директория для поиска не найдена: $resolvedSearch"
        exit 1
    }

    Write-Step "Чтение входного файла..."
    $lines = [System.IO.File]::ReadAllLines($resolvedFile, [System.Text.Encoding]::UTF8)
    $names = @($lines | Where-Object { $_.Trim() -ne '' })

    if ($names.Count -eq 0) {
        Write-Warning "Файл пуст: $resolvedFile"
        exit 0
    }
    Write-Step ("Прочитано имён: {0}" -f $names.Count)

    $nameSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($n in $names) { [void]$nameSet.Add($n) }

    Write-Step "Поиск полных путей (рекурсивный обход)..."
    $map = @{}
    $scanned = 0
    $found = 0
    $need = $nameSet.Count

    $allDirs = Get-ChildItem -LiteralPath $resolvedSearch -Directory -Recurse -Force -ErrorAction SilentlyContinue

    foreach ($dir in $allDirs) {
        $scanned++

        if ($scanned % 50 -eq 0) {
            Write-Progress -Activity "Поиск папок" `
                -Status ("Просканировано: {0} | Найдено: {1} / {2}" -f $scanned, $found, $need) `
                -CurrentOperation $dir.FullName
        }

        if ($nameSet.Contains($dir.Name) -and -not $map.ContainsKey($dir.Name)) {
            $map[$dir.Name] = $dir.FullName
            $found++
            Write-Output ("    [OK {0}/{1}] {2}" -f $found, $need, $dir.FullName)

            if ($found -eq $need) {
                Write-Step "Все уникальные имена найдены — обход завершён досрочно."
                break
            }
        }
    }

    Write-Progress -Activity "Поиск папок" -Completed
    Write-Step ("Итог поиска: просканировано {0}, найдено {1} из {2}" -f $scanned, $found, $need)

    $missing = @($names | Where-Object { -not $map.ContainsKey($_) })
    if ($missing.Count -gt 0) {
        Write-Step ("Не найдено папок: {0}" -f $missing.Count)
        foreach ($m in $missing) {
            Write-Output ("    [НЕ НАЙДЕНО] {0}" -f $m)
        }
    } else {
        Write-Step "Все имена успешно сопоставлены с путями."
    }

    Write-Step "Сортировка по абсолютным путям..."
    $idx = 0
    $items = foreach ($n in $names) {
        $fullPath = if ($map.ContainsKey($n)) { $map[$n] } else { $n }
        [PSCustomObject]@{
            Name = $n
            Key = Get-SortKey $fullPath
            Index = $idx
        }
        $idx++
    }

    $sorted = @($items |
        Sort-Object -Property Key, Index |
        Select-Object -ExpandProperty Name)

    Write-Step "Сохранение отсортированного файла..."
    [System.IO.File]::WriteAllLines($resolvedFile, [string[]]$sorted, $utf8Bom)

    Write-Output ""
    Write-Output "=== Итог обработки ==="
    Write-Output ("Просканировано папок: {0}" -f $scanned)
    Write-Output ("Сопоставлено имён:    {0} из {1}" -f $found, $need)
    Write-Output ("Отсортировано строк:  {0}" -f $sorted.Count)
    Write-Output ("Файл обновлён:        {0}" -f $resolvedFile)
    exit 0
}
