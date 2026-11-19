# PSWorkbench:Title=Привет, Мир!
<#
.SYNOPSIS
    Выводит на экран "Hello, World!" с настройкой регистра, количества повторений и цвета текста.
.PARAMETER UpperCase
    Вывод только в верхнем регистре.
.PARAMETER LowerCase
    Вывод только в нижнем регистре.
.PARAMETER Count
    Количество выводимых сообщений.
.PARAMETER Color
    Цвет выводимого текста в HEX-формате.
#>
[CmdletBinding(DefaultParameterSetName = 'Normal')]
param(
    [Parameter(ParameterSetName = 'Upper')]
    [switch]$UpperCase,

    [Parameter(ParameterSetName = 'Lower')]
    [switch]$LowerCase,

    [int]$Count = 1,

    [string]$Color = '#FFFFFF'
)

if ($UpperCase -and $LowerCase) {
    Write-Error "Флаги -UpperCase и -LowerCase не могут одновременно иметь значение true."
    exit 1
}

$trimmedColor = if ($null -eq $Color) { '' } else { $Color.Trim() }
if ($trimmedColor -notmatch '^#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$') {
    Write-Error "Некорректный цвет '$Color'. Укажите существующий цвет в шестнадцатеричном формате."
    exit 1
}

$hex = $Matches[1]
if ($hex.Length -eq 3) {
    $hex = "{0}{0}{1}{1}{2}{2}" -f $hex[0], $hex[1], $hex[2]
}

$r = [Convert]::ToInt32($hex.Substring(0, 2), 16)
$g = [Convert]::ToInt32($hex.Substring(2, 2), 16)
$b = [Convert]::ToInt32($hex.Substring(4, 2), 16)

$message = "Hello, World!"

if ($UpperCase) {
    $message = $message.ToUpper()
} elseif ($LowerCase) {
    $message = $message.ToLower()
}

$esc = [char]27
for ($i = 0; $i -lt $Count; $i++) {
    Write-Output ("{0}[38;2;{1};{2};{3}m{4}{0}[0m" -f $esc, $r, $g, $b, $message)
}
