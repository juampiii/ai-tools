# Azure DevOps MCP

[Back to MCP integrations](../README.md) · [AI tools](../../README.md)

Local Windows installation of the [official Microsoft Azure DevOps MCP server](https://github.com/microsoft/azure-devops-mcp), using the existing organization **juampidev**. It runs over stdio; no Azure compute resource, public endpoint, or paid service is provisioned.

## Install on this computer

From a PowerShell 7 terminal in the repository root:

```powershell
./MCPs/AzureDevOps/Install.ps1
./MCPs/AzureDevOps/Set-Pat.ps1
```

The installer downloads portable Node.js 24.22.3 from nodejs.org, verifies its SHA-256 checksum and installs `@azure-devops/mcp` 2.11.0 locally. It does not change the system PATH or install Node globally. Dependencies are locked in `package-lock.json`; subsequent installations use `npm ci`. Package lifecycle scripts are disabled. The PAT authentication flow does not need the optional native credential-store integration used by interactive authentication.

Enter the PAT only into the hidden local prompt. It is encrypted with Windows DPAPI in `.secrets/pat.dpapi`, bound to your Windows user and computer. This is local protection at rest, not protection against another process already running as your user. Run `Set-Pat.ps1` again to replace an expired token. The launcher also accepts a raw `ADO_PAT` environment variable from a secret manager instead of the encrypted file.

Never commit the token, its base64 encoding, or the encrypted file. `.runtime`, `.secrets`, and `node_modules` are ignored by Git. Base64 is encoding, not encryption.

## Register with Claude Code

The launcher requires PowerShell 7. If `pwsh.exe` is not installed, install it with `winget install --id Microsoft.PowerShell -e`. The winget package installs as an MSIX app under a versioned `WindowsApps` folder, so register its version-independent app execution alias instead of that folder.

After installing and storing the PAT, run:

```powershell
$powerShell = "$env:LOCALAPPDATA\Microsoft\WindowsApps\pwsh.exe"
claude mcp add azure-devops --scope user -- $powerShell -NoLogo -NoProfile -NonInteractive -File C:/Repos/ai-tools/MCPs/AzureDevOps/Start.ps1
claude mcp get azure-devops
```

`--scope user` writes the entry to `~/.claude.json`, making the server available in all your projects; the command contains no secret. `claude mcp get` should report `Connected`, which confirms that the server starts and answers the MCP handshake, not that the PAT is valid. Start a new Claude Code session to load the tools, then ask it to list projects in `juampidev`.

Claude Code and Codex can be registered at the same time. Both use the same installation and the same encrypted PAT, so `Set-Pat.ps1` updates the token for both. To remove the Claude Code registration, run `claude mcp remove azure-devops -s user`.

## Register with Codex

After installing and storing the PAT, run:

```powershell
$powerShell = (Get-Process -Id $PID).Path
codex mcp add azure-devops -- $powerShell -NoLogo -NoProfile -NonInteractive -File C:/Repos/ai-tools/MCPs/AzureDevOps/Start.ps1
codex mcp list
```

Use the absolute path of PowerShell 7 if `pwsh.exe` is not on your PATH. Windows PowerShell 5.1 may have a different execution policy; do not bypass or change it to run this launcher.

This registration updates your user-level Codex configuration, making the server available across repositories on this computer. The command contains no secret. Restart the Codex application to load the server, then ask it to list projects in `juampidev`. Registering the server does not create the HappyMeal project.

If you clone this repository elsewhere, substitute the absolute path to `Start.ps1`. Organization defaults to `juampidev`; pass `-Organization other-name` after the script path to use another organization.

## Other MCP clients

Use this server entry for clients accepting `mcpServers` (adjust the path for your checkout):

```json
{
  "mcpServers": {
    "azure-devops": {
      "command": "pwsh.exe",
      "args": [
        "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
        "C:/Repos/ai-tools/MCPs/AzureDevOps/Start.ps1"
      ]
    }
  }
}
```

VS Code uses a top-level `servers` key instead of `mcpServers`, with `"type": "stdio"` in the entry.

## Access and scope

The launcher enables only the official `core`, `work-items`, and `wiki` tool domains. Start with an organization-scoped PAT with:

- Project and Team: Read.
- Work Items: Read & write.
- Wiki: Read & write.

These permissions cover project discovery and routine work item and wiki editing, not project creation or full organization administration. They apply to accessible projects within the organization, including SimpleList; they are not restricted to HappyMeal. A tool may require additional permissions for a particular operation. Review those individually instead of granting full access.

The remaining HappyMeal setup can be done through the browser or supported API operations after reviewing the permissions needed. Keep GitHub repositories and GitHub Actions as agreed. Do not create or enable paid services without explicit confirmation.

## Verification

On November 25, 2026, the local installation passed the MCP `initialize` handshake and `tools/list` through `Start.ps1` using PowerShell 7: 14 tools were available, including `core_list_projects`, `wit_work_item_write`, and `wiki_upsert_page`. A subsequent authenticated `core_list_projects` call using the locally encrypted PAT succeeded against `juampidev` and returned `SimpleList`. No work item or wiki modifications were performed.

After installation, `Start.ps1` must keep stdout reserved for MCP messages. To check the installed CLI without a PAT:

```powershell
$arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
& "./MCPs/AzureDevOps/.runtime/node-v24.22.3-win-$arch/node.exe" ./MCPs/AzureDevOps/node_modules/@azure-devops/mcp/dist/index.js --help
```

The server was also registered in this computer's user-level Codex configuration. Direct tool availability in a resumed Codex chat remains to be checked after reloading the application. A local MCP installation does not change Azure billing or prevent charges from other Azure resources.

Authentication reference: [Microsoft getting started guide](https://github.com/microsoft/azure-devops-mcp/blob/main/docs/GETTINGSTARTED.md#personal-access-token).
