#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
shared_file="$script_dir/../../shared/session-restore/session_restore_core.py"
source_file="$script_dir/session_restore.py"
service_template="$script_dir/session-restore.service.in"
desktop_template="$script_dir/session-restore.desktop.in"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
bin_home="$HOME/.local/bin"
install_dir="$data_home/agent-tweaks/session-restore"
executable="$install_dir/session-restore"
service_dir="$config_home/systemd/user"
application_dir="$data_home/applications"
desktop_dir="${XDG_DESKTOP_DIR:-$HOME/Desktop}"

fail() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

[[ -f "$source_file" ]] || fail "implementation not found: $source_file"
[[ -f "$shared_file" ]] || fail "shared core not found: $shared_file"
[[ -f "$service_template" ]] || fail "service template not found: $service_template"
[[ -f "$desktop_template" ]] || fail "desktop template not found: $desktop_template"
command -v python3 >/dev/null 2>&1 || fail 'Python 3.10 or newer is required.'
python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' \
    || fail 'Python 3.10 or newer is required.'
command -v systemctl >/dev/null 2>&1 || fail 'A systemd user session is required.'

if ! command -v codex >/dev/null 2>&1 && ! command -v claude >/dev/null 2>&1; then
    fail 'Install Codex CLI, Claude Code, or both before Session Restore.'
fi

install -Dm755 -- "$source_file" "$executable"
install -Dm644 -- "$shared_file" "$install_dir/session_restore_core.py"
mkdir -p -- "$bin_home"
ln -sfn -- "$executable" "$bin_home/session-restore"

mkdir -p -- "$service_dir" "$application_dir" "$desktop_dir"
sed "s|@EXECUTABLE@|$executable|g" "$service_template" \
    > "$service_dir/session-restore.service"
sed "s|@EXECUTABLE@|$bin_home/session-restore|g" "$desktop_template" \
    > "$application_dir/session-restore.desktop"
install -m755 -- "$application_dir/session-restore.desktop" \
    "$desktop_dir/Restore Sessions.desktop"

systemctl --user daemon-reload
systemctl --user enable session-restore.service
systemctl --user restart session-restore.service

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$application_dir" >/dev/null 2>&1 || true
fi

printf '\nInstalled Session Restore.\n'
printf 'Tracking runs silently in the background without agent hooks.\n'
printf 'Use the Restore Sessions desktop icon or run: session-restore restore\n'
