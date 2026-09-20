# Repository instructions

- Keep tweaks independently installable and reversible.
- Keep operating-system code under `tweaks/linux/` or `tweaks/windows/`, grouped
  by agent. Keep reusable implementation code under `tweaks/shared/`.
- Never commit credentials, histories, personal absolute paths, or downloaded
  model files.
- Run the relevant unit tests after changing implementation code.
- Do not mark a platform supported until the feature has been tested there.
- Register stable tweaks in the root-level installer and uninstaller
  dispatchers for each supported platform.
