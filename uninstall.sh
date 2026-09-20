#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
Usage: ./uninstall.sh [--all | --list | TARGET...]

Uninstall Agent Tweaks from this platform.

Targets:
  codex/hold-to-dictate  Hold Space to dictate into the Codex CLI
  session-restore        Restore Codex and Claude sessions after a restart

With no arguments, all installed tweaks managed by this repository are removed.
EOF
}

list_targets() {
    printf '%s\n' 'session-restore' 'codex/hold-to-dictate'
}

uninstall_target() {
    case "$1" in
        codex/hold-to-dictate)
            "$repo_root/tweaks/linux/codex/hold-to-dictate/uninstall.sh"
            ;;
        session-restore)
            "$repo_root/tweaks/linux/session-restore/uninstall.sh"
            ;;
        *)
            printf 'error: unknown or unsupported target: %s\n' "$1" >&2
            usage >&2
            return 2
            ;;
    esac
}

case "$(uname -s)" in
    Linux) ;;
    *)
        printf 'error: this uninstaller currently supports Linux only.\n' >&2
        exit 1
        ;;
esac

if (($# == 0)); then
    set -- --all
fi

case "$1" in
    -h|--help)
        usage
        exit 0
        ;;
    --list)
        list_targets
        exit 0
        ;;
    --all)
        (($# == 1)) || {
            printf 'error: --all cannot be combined with other targets.\n' >&2
            exit 2
        }
        mapfile -t targets < <(list_targets)
        ;;
    *)
        targets=("$@")
        ;;
esac

for target in "${targets[@]}"; do
    printf '\n==> Uninstalling %s\n' "$target"
    uninstall_target "$target"
done

printf '\nAll requested Agent Tweaks were uninstalled.\n'
