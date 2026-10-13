# Release validation: 1.0.0

Environment: Unity 2022.3.62f3c1, Windows x64. Upstream FMOD version: 2.03.14.

- Unity Package Manager identifies `com.dotline.fmod` version `1.0.0` as an embedded package.
- Unity generated `FMODUnity.dll` and `FMODUnityEditor.dll` successfully.
- The local installer imported 81 native files from the user-supplied official Unity package.
- A direct Windows native API check created the Studio system, obtained its core system, reported version `00020314`, initialized with no-sound output and released the system. Every operation returned FMOD result `0` (`OK`).
- Five Python installer tests pass: embedded installation and staging normalization, repeated installation, preservation of other manifest dependencies, rejection of mismatched versions/path traversal/symlinks, and protection of existing differing libraries.
- `npm pack --dry-run` contains no native library files, staging folders, generated settings or caches.

Native platform builds and audio-bank playback have not been tested. Connect an FMOD Studio project or bank directory through the FMOD Setup Wizard before playing project audio.
