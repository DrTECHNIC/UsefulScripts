# PSWorkbench:Title=Свойства файла
# PSWorkbench:Target=File
<#
.SYNOPSIS
    Выводит свойства указанного файла в структурированном и удобочитаемом виде.
.DESCRIPTION
    Показывает краткую сводку, базовые свойства .NET (включая сведения о версии исполняемых файлов
    и данные о ссылках), расширенные метаданные Windows Shell и при необходимости SHA-256 хэш.
.PARAMETER Path
    Путь к файлу.
.PARAMETER Mode
    Глубина вывода: Summary (кратко), Basic (базовые свойства), Extended (расширенные метаданные), All (все свойства).
.PARAMETER IncludeHash
    Вычислить контрольную сумму SHA-256.
.PARAMETER ShowHelp
    Вывести справку по использованию скрипта.
.EXAMPLE
    .\FileInfo.ps1 -Path "C:\Temp\photo.png" -Mode Summary
.EXAMPLE
    .\FileInfo.ps1 -Path "C:\Temp\photo.png" -Mode All -IncludeHash
#>
[CmdletBinding(DefaultParameterSetName = 'Inspect')]
param(
    [Parameter(ParameterSetName = 'Inspect', Mandatory = $true, Position = 0)]
    [Alias('FilePath')]
    [string]$Path,

    [Parameter(ParameterSetName = 'Inspect', Position = 1)]
    [ValidateSet('Summary', 'Basic', 'Extended', 'All')]
    [string]$Mode = 'Summary',

    [Parameter(ParameterSetName = 'Inspect')]
    [switch]$IncludeHash,

    [Parameter(ParameterSetName = 'Help', Mandatory = $true)]
    [Alias('h')]
    [switch]$ShowHelp
)

if ($ShowHelp) {
    $scriptName = $MyInvocation.MyCommand.Name
    Write-Output @"
Использование: .\$scriptName -Path <путь_к_файлу> [-Mode <режим>] [-IncludeHash]

Параметры:
  -Path (-FilePath)  Путь к файлу.
  -Mode              Глубина вывода:
                       Summary   краткая сводка
                       Basic     базовые свойства файловой системы и сведения о версии
                       Extended  расширенные метаданные Windows Shell
                       All       базовые свойства и расширенные метаданные
  -IncludeHash       Добавить контрольную сумму SHA-256.
  -ShowHelp (-h)     Показать эту справку.

Примеры:
  .\$scriptName -Path "C:\Temp\photo.png" -Mode Summary
  .\$scriptName -Path "C:\Temp\photo.png" -Mode All -IncludeHash
"@
    exit 0
}

function Format-FileSize {
    param([long]$Bytes)

    if ($Bytes -lt 1024) {
        return "$Bytes Б"
    }

    $units = @('КБ', 'МБ', 'ГБ', 'ТБ', 'ПБ')
    $size = [double]$Bytes
    $index = -1

    do {
        $size /= 1024
        $index++
    } while ($size -ge 1024 -and $index -lt ($units.Count - 1))

    return ('{0:N2} {1}' -f $size, $units[$index])
}

function Clear-ShellText {
    param([string]$Text)

    if ([string]::IsNullOrEmpty($Text)) { return '' }
    # Удаляем невидимые управляющие символы направления текста (LTR/RTL), которые добавляет Windows Shell
    return ($Text -replace '[\u200E\u200F\u202A-\u202E\u2066-\u2069]', '').Trim()
}

function Write-PropertySection {
    param(
        [string]$Title,
        [System.Collections.IDictionary]$Rows
    )

    if (-not $Rows -or $Rows.Count -eq 0) { return }

    $maxKeyLen = 18
    foreach ($key in $Rows.Keys) {
        $len = ([string]$key).Length
        if ($len -gt $maxKeyLen) { $maxKeyLen = $len }
    }
    if ($maxKeyLen -gt 34) { $maxKeyLen = 34 }

    Write-Output "=== $Title ==="
    foreach ($key in $Rows.Keys) {
        $val = [string]$Rows[$key]
        Write-Output ("{0,-$maxKeyLen} : {1}" -f $key, $val)
    }
}

function Get-SummaryRows {
    param([System.IO.FileInfo]$File)

    $rows = [ordered]@{
        'Имя'       = $File.Name
        'Путь'      = $File.FullName
        'Размер'    = '{0} ({1:N0} байт)' -f (Format-FileSize -Bytes $File.Length), $File.Length
        'Атрибуты'  = [string]$File.Attributes
        'Создан'    = $File.CreationTime.ToString('yyyy-MM-dd HH:mm:ss')
        'Изменён'   = $File.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
        'Открыт'    = $File.LastAccessTime.ToString('yyyy-MM-dd HH:mm:ss')
    }
    return $rows
}

function Get-BasicRows {
    param([System.IO.FileInfo]$File)

    $rows = [ordered]@{
        'Имя файла'      = $File.Name
        'Базовое имя'    = $File.BaseName
        'Расширение'     = if ($File.Extension) { $File.Extension } else { '(нет)' }
        'Папка'          = $File.DirectoryName
        'Полный путь'    = $File.FullName
        'Размер'         = '{0} ({1:N0} байт)' -f (Format-FileSize -Bytes $File.Length), $File.Length
        'Атрибуты'       = [string]$File.Attributes
        'Только чтение'  = if ($File.IsReadOnly) { 'Да' } else { 'Нет' }
        'Создан'         = $File.CreationTime.ToString('yyyy-MM-dd HH:mm:ss')
        'Создан (UTC)'   = $File.CreationTimeUtc.ToString('yyyy-MM-dd HH:mm:ss')
        'Изменён'        = $File.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
        'Изменён (UTC)'  = $File.LastWriteTimeUtc.ToString('yyyy-MM-dd HH:mm:ss')
        'Открыт'         = $File.LastAccessTime.ToString('yyyy-MM-dd HH:mm:ss')
        'Открыт (UTC)'   = $File.LastAccessTimeUtc.ToString('yyyy-MM-dd HH:mm:ss')
    }

    if ($File.PSObject.Properties['LinkType'] -and $File.LinkType) {
        $rows['Тип ссылки'] = [string]$File.LinkType
    }
    if ($File.PSObject.Properties['Target'] -and $File.Target) {
        $rows['Цель ссылки'] = ($File.Target -join ', ')
    }

    return $rows
}

function Get-VersionRows {
    param([System.IO.FileInfo]$File)

    $rows = [ordered]@{}
    try {
        $vi = $File.VersionInfo
        if (-not $vi) { return $rows }

        $fields = [ordered]@{
            'Описание'         = $vi.FileDescription
            'Продукт'          = $vi.ProductName
            'Версия файла'     = $vi.FileVersion
            'Версия продукта'  = $vi.ProductVersion
            'Компания'         = $vi.CompanyName
            'Исходное имя'     = $vi.OriginalFilename
            'Авторские права'  = $vi.LegalCopyright
        }

        foreach ($k in $fields.Keys) {
            $v = if ($null -ne $fields[$k]) { ([string]$fields[$k]).Trim() } else { '' }
            if (-not [string]::IsNullOrWhiteSpace($v)) {
                $rows[$k] = $v
            }
        }
    }
    catch {
        # У обычных (не PE) файлов сведений о версии нет
    }
    return $rows
}

function Get-ExtendedRows {
    param([System.IO.FileInfo]$File)

    $rows = [ordered]@{}
    $shell = $null
    $folder = $null
    $shellItem = $null

    try {
        $shell = New-Object -ComObject Shell.Application
        $folder = $shell.Namespace($File.DirectoryName)
        if ($null -eq $folder) {
            Write-Warning "Не удалось открыть каталог в Windows Shell: $($File.DirectoryName)"
            return $rows
        }

        $shellItem = $folder.ParseName($File.Name)
        if ($null -eq $shellItem) {
            Write-Warning "Не удалось получить объект Windows Shell для файла: $($File.Name)"
            return $rows
        }

        for ($index = 0; $index -le 400; $index++) {
            $propName = Clear-ShellText ($folder.GetDetailsOf($null, $index))
            if ([string]::IsNullOrWhiteSpace($propName)) { continue }

            $propValue = Clear-ShellText ($folder.GetDetailsOf($shellItem, $index))
            if ([string]::IsNullOrWhiteSpace($propValue)) { continue }

            if (-not $rows.Contains($propName)) {
                $rows[$propName] = $propValue
            }
        }
    }
    catch {
        Write-Warning "Не удалось получить расширенные метаданные: $($_.Exception.Message)"
    }
    finally {
        foreach ($comObj in @($shellItem, $folder, $shell)) {
            if ($null -ne $comObj) {
                try {
                    [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($comObj)
                }
                catch {
                    # ignore release errors
                }
            }
        }
    }

    return $rows
}

function Get-HashRows {
    param([System.IO.FileInfo]$File)

    $rows = [ordered]@{}
    try {
        $hash = Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256 -ErrorAction Stop
        $rows['SHA-256'] = $hash.Hash
    }
    catch {
        Write-Warning "Не удалось вычислить SHA-256: $($_.Exception.Message)"
    }
    return $rows
}

# Проверка пути
if ([string]::IsNullOrWhiteSpace($Path)) {
    Write-Error "Не указан путь к файлу."
    exit 1
}

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "Файл не найден: $Path"
    exit 1
}

if (Test-Path -LiteralPath $Path -PathType Container) {
    Write-Error "Указанный путь является директорией, а не файлом: $Path"
    exit 1
}

try {
    $file = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
}
catch {
    Write-Error "Не удалось получить доступ к файлу '$Path': $($_.Exception.Message)"
    exit 1
}

$printedAny = $false

switch ($Mode) {
    'Summary' {
        Write-PropertySection -Title 'Краткая сводка' -Rows (Get-SummaryRows -File $file)
        $printedAny = $true
    }
    'Basic' {
        Write-PropertySection -Title 'Базовые свойства' -Rows (Get-BasicRows -File $file)
        $printedAny = $true

        $verRows = Get-VersionRows -File $file
        if ($verRows.Count -gt 0) {
            Write-Output ''
            Write-PropertySection -Title 'Сведения о версии' -Rows $verRows
        }
    }
    'Extended' {
        $extRows = Get-ExtendedRows -File $file
        if ($extRows.Count -gt 0) {
            Write-PropertySection -Title 'Расширенные метаданные' -Rows $extRows
            $printedAny = $true
        } else {
            Write-Output 'Расширенные метаданные для этого файла не обнаружены.'
            $printedAny = $true
        }
    }
    'All' {
        Write-PropertySection -Title 'Базовые свойства' -Rows (Get-BasicRows -File $file)
        $printedAny = $true

        $verRows = Get-VersionRows -File $file
        if ($verRows.Count -gt 0) {
            Write-Output ''
            Write-PropertySection -Title 'Сведения о версии' -Rows $verRows
        }

        $extRows = Get-ExtendedRows -File $file
        Write-Output ''
        if ($extRows.Count -gt 0) {
            Write-PropertySection -Title 'Расширенные метаданные' -Rows $extRows
        } else {
            Write-Output 'Расширенные метаданные для этого файла не обнаружены.'
        }
    }
}

if ($IncludeHash) {
    $hashRows = Get-HashRows -File $file
    if ($hashRows.Count -gt 0) {
        if ($printedAny) { Write-Output '' }
        Write-PropertySection -Title 'Контрольная сумма' -Rows $hashRows
    }
}
