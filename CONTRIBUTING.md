# Contributing

Keep each tweak focused, optional, reversible, and independently documented.

## Development

Run the complete test suite from the repository root:

```sh
python3 -m unittest discover -s tweaks/linux/codex/hold-to-dictate/tests -v
```

For platform-specific changes:

1. Preserve the behaviour described in the tweak's README.
2. Add tests for tap, hold, release, paste, and ordinary keyboard input.
3. Test installation, normal use, bypass, and uninstallation on the target OS.
4. Update the compatibility table only after the implementation works on that
   platform.

Stable tweaks intended for the default setup must also be registered in the
root installer and uninstaller dispatchers for their supported platforms.

Do not commit authentication data, agent histories, personal paths, complete
user configuration files, downloaded speech models, or generated caches.
