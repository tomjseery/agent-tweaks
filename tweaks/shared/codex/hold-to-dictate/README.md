# Shared hold-to-dictate code

Platform-neutral Python behavior shared by the Linux implementation and the
planned Windows implementation:

- tap-versus-hold state management;
- transcript parsing and normalization;
- shared speech-model metadata.

Console input, microphone capture, process management, and installers belong
under their respective operating-system directories.
