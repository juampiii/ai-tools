#Requires -Version 7.0
[CmdletBinding()]
param(
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9-]*$')]
    [string]$Organization = 'juampidev'
)

$ErrorActionPreference = 'Stop'
$architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
$node = Join-Path $PSScriptRoot ".runtime/node-v24.22.3-win-$architecture/node.exe"
$server = Join-Path $PSScriptRoot 'node_modules/@azure-devops/mcp/dist/index.js'
if (-not (Test-Path -LiteralPath $node) -or -not (Test-Path -LiteralPath $server)) {
    throw 'Run MCPs/AzureDevOps/Install.ps1 before starting the MCP server.'
}

$previousToken = $env:PERSONAL_ACCESS_TOKEN
$previousRawToken = $env:ADO_PAT
$pointer = [IntPtr]::Zero
$secureToken = $null
try {
    if ($env:ADO_PAT) {
        $rawToken = $env:ADO_PAT
    } else {
        $secretFile = Join-Path $PSScriptRoot '.secrets/pat.dpapi'
        if (-not (Test-Path -LiteralPath $secretFile)) {
            throw 'Run Set-Pat.ps1 in a local terminal to store your PAT, or supply ADO_PAT in the process environment.'
        }
        $secureToken = Get-Content -LiteralPath $secretFile -Raw | ConvertTo-SecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
        $rawToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    # The official server expects base64(username:PAT), not a raw PAT.
    $env:PERSONAL_ACCESS_TOKEN = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("mcp:$rawToken"))
    $env:ADO_PAT = $null
    $rawToken = $null
    & $node $server $Organization --authentication pat --domains core work-items wiki
    $serverExitCode = $LASTEXITCODE
} finally {
    $rawToken = $null
    if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    if ($null -ne $secureToken) { $secureToken.Dispose() }
    $env:PERSONAL_ACCESS_TOKEN = $previousToken
    $env:ADO_PAT = $previousRawToken
}
exit $serverExitCode
