param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& python -m watchwise @Arguments
exit $LASTEXITCODE
