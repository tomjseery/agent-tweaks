#!/usr/bin/env bash
set -euo pipefail

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
bin_home="$HOME/.local/bin"
desktop_dir="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
state_home="${XDG_STATE_HOME:-$HOME/.local/state}"
executable="$data_home/agent-tweaks/session-restore/session-restore"

remove_managed_link() {
    local link_path="$1"
    if [[ -L "$link_path" ]] && [[ "$(readlink -- "$link_path")" == "$executable" ]]; then
        rm -f -- "$link_path"
    fi
}

systemctl --user disable --now session-restore.service >/dev/null 2>&1 || true
rm -f -- "$config_home/systemd/user/session-restore.service"
systemctl --user daemon-reload >/dev/null 2>&1 || true

remove_managed_link "$bin_home/session-restore"
remove_managed_link "$bin_home/sr"
rm -f -- \
    "$data_home/applications/session-restore.desktop" \
    "$desktop_dir/Restore Sessions.desktop"
rm -rf -- \
    "$data_home/agent-tweaks/session-restore" \
    "$state_home/agent-tweaks/session-restore"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$data_home/applications" >/dev/null 2>&1 || true
fi

printf 'Uninstalled Session Restore and removed its saved workspace.\n'
