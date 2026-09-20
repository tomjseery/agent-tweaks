#!/usr/bin/env bash
set -euo pipefail

marker_start='# >>> agent-tweaks: codex-hold-to-dictate >>>'
marker_end='# <<< agent-tweaks: codex-hold-to-dictate <<<'
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
bin_home="$HOME/.local/bin"
shell_config="$config_home/agent-tweaks/codex-hold-to-dictate.sh"

case "${SHELL##*/}" in
    zsh) shell_rc="$HOME/.zshrc" ;;
    bash|*) shell_rc="$HOME/.bashrc" ;;
esac

if [[ -f "$shell_rc" ]]; then
    python3 - "$shell_rc" "$marker_start" "$marker_end" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
start, end = sys.argv[2:]
lines = path.read_text().splitlines(keepends=True)
result = []
inside = False
for line in lines:
    if line.rstrip("\r\n") == start:
        inside = True
        if result and not result[-1].strip():
            result.pop()
        continue
    if inside and line.rstrip("\r\n") == end:
        inside = False
        continue
    if not inside:
        result.append(line)
path.write_text("".join(result))
PY
fi

rm -f -- "$bin_home/codex-hold-to-dictate" "$bin_home/codex-ptt" "$shell_config"
rm -rf -- "$data_home/agent-tweaks/codex-hold-to-dictate"

printf 'Uninstalled Codex hold-to-dictate. The shared speech model was preserved.\n'
printf 'Open a new terminal to remove the aliases from the current shell.\n'
