param(
    [Parameter(Mandatory=$true)][string]$Run,
    [Parameter(Mandatory=$true)][string]$Output,
    [Parameter(Mandatory=$true)][string]$Data,
    [Parameter(Mandatory=$true)][string]$Planets,
    [Parameter(Mandatory=$true)][string]$Mesa,
    [string]$SourceRoot=(Get-Location).Path
)
$ErrorActionPreference = 'Stop'
& python -B "$PSScriptRoot/smoke.py" --run $Run --output $Output --data $Data --planets $Planets --mesa $Mesa --source-root $SourceRoot
if ($LASTEXITCODE -ne 0) { throw "Windows renderer smoke exited $LASTEXITCODE" }

