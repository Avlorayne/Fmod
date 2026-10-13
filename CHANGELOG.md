# Changelog

## 1.0.0 — 2026-10-13

- Package FMOD 2.03.14 integration source as `com.dotline.fmod`.
- Retain original integration assemblies, platform source, add-ons and asset GUIDs.
- Resolve the installation directory through Unity Package Manager metadata.
- Keep generated static-plugin registration code and settings in the project Assets folder.
- Add a version-checked local native-library installer and Unity menu command.
- Exclude user-supplied FMOD native libraries from Git and npm publication.
- Remove the unused Input System dependency to avoid changing project input requirements.
