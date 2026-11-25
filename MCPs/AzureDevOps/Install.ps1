#Requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$nodeVersion = '24.22.3'
$architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
if ($env:OS -ne 'Windows_NT' -or $architecture -notin @('x64', 'arm64')) {
    throw 'This installer supports Windows x64 and ARM64.'
}

$runtime = Join-Path $PSScriptRoot '.runtime'
$archiveName = "node-v$nodeVersion-win-$architecture.zip"
$nodeDirectory = Join-Path $runtime "node-v$nodeVersion-win-$architecture"
$node = Join-Path $nodeDirectory 'node.exe'
$npmCli = Join-Path $nodeDirectory 'node_modules/npm/bin/npm-cli.js'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null

if (-not (Test-Path -LiteralPath $npmCli)) {
    $archive = Join-Path $runtime $archiveName
    $baseUrl = "https://nodejs.org/dist/v$nodeVersion"
    Write-Host "Downloading portable Node.js $nodeVersion ($architecture)..."
    Invoke-WebRequest "$baseUrl/$archiveName" -OutFile $archive
    $checksums = (Invoke-WebRequest "$baseUrl/SHASUMS256.txt").Content
    $checksumLine = @($checksums -split "`n" | Where-Object { $_.Trim().EndsWith("  $archiveName") })
    if ($checksumLine.Count -ne 1) { throw 'Could not find the official Node.js checksum.' }
    $expected = ($checksumLine[0].Trim() -split '\s+')[0]
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    if ($actual -ne $expected) { throw 'Node.js archive checksum does not match. Installation stopped.' }
    Expand-Archive -LiteralPath $archive -DestinationPath $runtime -Force
    Remove-Item -LiteralPath $archive
}

$previousPath = $env:PATH
Push-Location $PSScriptRoot
try {
    $env:PATH = "$nodeDirectory;$previousPath"
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'package-lock.json')) {
        & $node $npmCli ci --ignore-scripts --no-audit --no-fund --cache (Join-Path $runtime 'npm-cache')
    } else {
        & $node $npmCli install --ignore-scripts --no-audit --no-fund --cache (Join-Path $runtime 'npm-cache')
    }
    if ($LASTEXITCODE -ne 0) { throw "npm installation failed with exit code $LASTEXITCODE." }
} finally {
    $env:PATH = $previousPath
    Pop-Location
}
Write-Host 'Installed. Run Set-Pat.ps1 locally, then register Start.ps1 in your MCP client.'
