# Repository instructions

- Keep tweaks independently installable and reversible.
- Keep reusable implementation code at each tweak's root; isolate OS-specific
  code in `linux/`, `windows/`, or another explicit platform directory.
- Never commit credentials, histories, personal absolute paths, or downloaded
  model files.
- Run the relevant unit tests after changing implementation code.
- Do not mark a platform supported until the feature has been tested there.
