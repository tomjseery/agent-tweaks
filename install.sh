#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
Usage: ./install.sh [--all | --list | TARGET...]

Install supported Agent Tweaks for this platform.

Targets:
  codex/hold-to-dictate  Hold Space to dictate into the Codex CLI

With no arguments, all supported stable tweaks are installed.
EOF
}

list_targets() {
    printf '%s\n' 'codex/hold-to-dictate'
}

install_target() {
    case "$1" in
        codex/hold-to-dictate)
            "$repo_root/tweaks/linux/codex/hold-to-dictate/install.sh"
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
        printf 'error: this installer currently supports Linux only.\n' >&2
        printf 'Native Windows support is planned but not yet implemented.\n' >&2
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
    printf '\n==> Installing %s\n' "$target"
    install_target "$target"
done

printf '\nAll requested Agent Tweaks were installed.\n'
