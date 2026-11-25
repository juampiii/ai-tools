#Requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'PAT storage uses Windows DPAPI.' }
$secretDirectory = Join-Path $PSScriptRoot '.secrets'
New-Item -ItemType Directory -Path $secretDirectory -Force | Out-Null
$token = Read-Host 'Azure DevOps PAT (hidden; never paste it into chat)' -AsSecureString
if ($token.Length -eq 0) { throw 'The PAT must not be empty.' }
try {
    # Without a key, Windows encrypts this value for the current user with DPAPI.
    $token | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $secretDirectory 'pat.dpapi') -NoNewline
} finally {
    $token.Dispose()
}
Write-Host 'PAT stored encrypted for this Windows user on this computer.'
