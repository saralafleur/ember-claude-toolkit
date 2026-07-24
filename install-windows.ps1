# Get the directory of the script
$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- Prerequisite Checks ---
Write-Host "Checking prerequisites..."

# 1. Check Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Warning "Prerequisite Git is not installed or not in PATH. Git is required for managing build worktrees."
} else {
    Write-Host "  -> Git is installed."
}

# 2. Check Python
$pythonCmd = (Get-Command python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $pythonCmd) {
    Write-Warning "Prerequisite Python is not installed or not in PATH. Python 3.8+ is required for SQLite database operations."
} else {
    try {
        $versionMajorStr = & $pythonCmd.Name -c "import sys; print(sys.version_info.major)"
        $versionMinorStr = & $pythonCmd.Name -c "import sys; print(sys.version_info.minor)"
        $major = [int]$versionMajorStr
        $minor = [int]$versionMinorStr
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
            Write-Warning "Prerequisite Python version is $major.$minor. Python 3.8+ is required."
        } else {
            Write-Host "  -> Python $major.$minor is installed."
        }
    } catch {
        Write-Warning "Could not verify Python version. Python 3.8+ is required."
    }
}
Write-Host ""

function Install-Plugin {
    param (
        [string]$name
    )
    $pluginDir = Join-Path $DIR "$name\$name"
    if (-not (Test-Path $pluginDir)) {
        Write-Warning "Plugin directory $pluginDir does not exist."
        return
    }

    Write-Host "Installing $name..."

    # 1. Claude Code — install when CLI exists OR ~/.claude already present
    $claudeDir = Join-Path $env:USERPROFILE ".claude"
    $claudeCli = Get-Command claude -ErrorAction SilentlyContinue
    if ($claudeCli -or (Test-Path $claudeDir)) {
        Write-Host "  -> Setting up for Claude Code..."
        $skillsDir = Join-Path $claudeDir "skills"
        $agentsDir = Join-Path $claudeDir "agents"
        New-Item -ItemType Directory -Force -Path $skillsDir, $agentsDir | Out-Null

        if (Test-Path (Join-Path $pluginDir "skills")) {
            Copy-Item -Recurse -Force (Join-Path $pluginDir "skills\*") $skillsDir
        }
        if (Test-Path (Join-Path $pluginDir "agents")) {
            Copy-Item -Recurse -Force (Join-Path $pluginDir "agents\*") $agentsDir
        }
    } else {
        Write-Warning "Claude Code not detected (no 'claude' CLI and no ~/.claude). Skipping Claude install for $name."
    }

    # 2. Cursor — mirror skills/agents into ~/.cursor
    $cursorDir = Join-Path $env:USERPROFILE ".cursor"
    if (Test-Path $cursorDir) {
        Write-Host "  -> Setting up for Cursor..."
        $cSkills = Join-Path $cursorDir "skills"
        $cAgents = Join-Path $cursorDir "agents"
        New-Item -ItemType Directory -Force -Path $cSkills, $cAgents | Out-Null

        if (Test-Path (Join-Path $pluginDir "skills")) {
            Copy-Item -Recurse -Force (Join-Path $pluginDir "skills\*") $cSkills
        }
        if (Test-Path (Join-Path $pluginDir "agents")) {
            Copy-Item -Recurse -Force (Join-Path $pluginDir "agents\*") $cAgents
        }
    }

    # 3. Gemini/Antigravity Installation
    if (Get-Command gemini -ErrorAction SilentlyContinue) {
        Write-Host "  -> Setting up for Gemini CLI..."
        gemini extensions link $pluginDir
    }
}

Install-Plugin "delivery-team-plugin"
Install-Plugin "librarian-plugin"
Install-Plugin "research-team-plugin"

Write-Host "Installation process complete!"

