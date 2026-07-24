#!/bin/bash

# Get absolute path of this script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# --- Prerequisite Checks ---
echo "Checking prerequisites..."

# 1. Check Git
if ! command -v git &> /dev/null; then
  echo "Warning: Prerequisite Git is not installed or not in PATH. Git is required for managing build worktrees."
else
  echo "  -> Git is installed."
fi

# 2. Check Python
python_cmd=""
if command -v python3 &> /dev/null; then
  python_cmd="python3"
elif command -v python &> /dev/null; then
  python_cmd="python"
fi

if [ -z "$python_cmd" ]; then
  echo "Warning: Prerequisite Python is not installed or not in PATH. Python 3.8+ is required for SQLite database operations."
else
  version_str=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
  if [ -z "$version_str" ]; then
    echo "Warning: Could not verify Python version. Python 3.8+ is required."
  else
    is_valid=$($python_cmd -c "import sys; print('true' if sys.version_info >= (3, 8) else 'false')")
    if [ "$is_valid" = "false" ]; then
      echo "Warning: Prerequisite Python version is $version_str. Python 3.8+ is required."
    else
      echo "  -> Python $version_str is installed."
    fi
  fi
fi
echo ""

install_plugin() {
  local name=$1
  local plugin_dir="$DIR/$name/$name"

  if [ ! -d "$plugin_dir" ]; then
    echo "Warning: Plugin directory $plugin_dir does not exist."
    return
  fi

  echo "Installing $name..."

  # 1. Claude Code — install when CLI exists OR ~/.claude already present
  if command -v claude &> /dev/null || [ -d "$HOME/.claude" ]; then
    echo "  -> Setting up for Claude Code..."
    mkdir -p ~/.claude/skills ~/.claude/agents
    if [ -d "$plugin_dir/skills" ]; then
      cp -R "$plugin_dir"/skills/* ~/.claude/skills/
    fi
    if [ -d "$plugin_dir/agents" ]; then
      cp -R "$plugin_dir"/agents/* ~/.claude/agents/
    fi
  else
    echo "Warning: Claude Code not detected (no 'claude' CLI and no ~/.claude). Skipping Claude install for $name."
  fi

  # 2. Cursor — mirror skills/agents into ~/.cursor
  if [ -d "$HOME/.cursor" ]; then
    echo "  -> Setting up for Cursor..."
    mkdir -p ~/.cursor/skills ~/.cursor/agents
    if [ -d "$plugin_dir/skills" ]; then
      cp -R "$plugin_dir"/skills/* ~/.cursor/skills/
    fi
    if [ -d "$plugin_dir/agents" ]; then
      cp -R "$plugin_dir"/agents/* ~/.cursor/agents/
    fi
  fi

  # 3. Gemini/Antigravity Installation
  if command -v gemini &> /dev/null; then
    echo "  -> Setting up for Gemini CLI..."
    gemini extensions link "$plugin_dir"
  fi
}

install_plugin "delivery-team-plugin"
install_plugin "librarian-plugin"
install_plugin "research-team-plugin"

echo "Installation process complete!"

