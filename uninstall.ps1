[CmdletBinding()]
param(
    [switch]$List,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Target
)

$ErrorActionPreference = 'Stop'
$supportedTargets = @()

if ($List) {
    if ($supportedTargets.Count -eq 0) {
        Write-Host 'No stable Windows tweaks are available yet.'
        exit 0
    }
    $supportedTargets
    exit 0
}

if ($Target.Count -gt 0) {
    throw "Unknown or unsupported Windows target: $($Target -join ', ')"
}

Write-Host 'No stable Windows tweaks are currently installed by this repository.'
