<#
.SYNOPSIS
    Выводит свойства указанного файла в удобочитаемом виде.

      -s   краткая сводка
      -b   только базовые свойства
      -e   только расширенные метаданные
      -a   все свойства

    Если ключ не указан — выводится справка.
.PARAMETER FilePath
    Путь к файлу.
.EXAMPLE
    .\FileInfo.ps1 C:\Temp\photo.png -s
.EXAMPLE
    .\FileInfo.ps1 C:\Temp\photo.png -b
.EXAMPLE
    .\FileInfo.ps1 C:\Temp\photo.png -e
.EXAMPLE
    .\FileInfo.ps1 C:\Temp\photo.png -a
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$FilePath,

    [switch]$s,
    [switch]$b,
    [switch]$e,
    [switch]$a
)

function Format-Size([long]$bytes) {
    if ($bytes -lt 1024) { return "$bytes Б" }
    $units = 'КБ', 'МБ', 'ГБ', 'ТБ', 'ПБ'
    $size = [double]$bytes
    $i = -1
    do {
        $size /= 1024
        $i++
    } while ($size -ge 1024 -and $i -lt $units.Count - 1)
    '{0:N2} {1}' -f $size, $units[$i]
}

function Show-SmallInfo($file) {
    Write-Host ("Путь      : {0}" -f $file.FullName)
    Write-Host ("Размер    : {0} ({1:N0} байт)" -f (Format-Size $file.Length), $file.Length)
    Write-Host ("Атрибуты  : {0}" -f $file.Attributes)
    Write-Host ("Создан    : {0:yyyy-MM-dd HH:mm:ss}" -f $file.CreationTime)
    Write-Host ("Изменён   : {0:yyyy-MM-dd HH:mm:ss}" -f $file.LastWriteTime)
    Write-Host ("Открыт    : {0:yyyy-MM-dd HH:mm:ss}" -f $file.LastAccessTime)
}

function Show-BasicInfo($file) {
    Write-Host "Путь: $($file.FullName)`n" -ForegroundColor Gray
    $file | Format-List * -Force
}

function Show-ExtendedInfo($file) {
    try {
        $shell = New-Object -ComObject Shell.Application
        $folder = $shell.Namespace($file.DirectoryName)
        $shellItem = $folder.ParseName($file.Name)
        $found = $false
        foreach ($index in 0..266) {
            $name = $folder.GetDetailsOf($null, $index)
            if ([string]::IsNullOrWhiteSpace($name)) { continue }
            $value = $folder.GetDetailsOf($shellItem, $index)
            if ([string]::IsNullOrWhiteSpace($value)) { continue }
            $found = $true
            '{0,-30} : {1}' -f $name, $value
        }
        if (-not $found) {
            Write-Host "Расширенные метаданные для этого файла не обнаружены." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Warning "Не удалось получить расширенные метаданные: $($_.Exception.Message)"
    }
}

if (-not $s -and -not $b -and -not $e -and -not $a) {
    @"
Использование: $($MyInvocation.MyCommand.Name) <путь_к_файлу> <ключ>

Ключи (регистр не важен):
  -s   краткая сводка
  -b   только базовые свойства
  -e   только расширенные метаданные
  -a   все свойства

Пример:
  .\$($MyInvocation.MyCommand.Name) C:\Temp\photo.png -A
"@ | Write-Host
    return
}

if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) {
    Write-Error "Файл не найден: $FilePath"
    exit 1
}

$file = Get-Item -LiteralPath $FilePath -Force -ErrorAction Stop

if ($s) {
    if ($b -or $e -or $a) {
        Write-Warning "Ключ -s отменяет действие остальных ключей."
    }
    Show-SmallInfo $file
    return
}

if ($b -or $a) { Show-BasicInfo $file }
if ($e -or $a) { Show-ExtendedInfo $file }
