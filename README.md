# FMOD for Unity — Dotline UPM

`com.dotline.fmod` **1.0.0** packages the FMOD **2.03.14** Unity integration source for Unity **2022.3 or later**. Package versions and FMOD versions are separate: use FMOD Studio 2.03 with this integration.

This is an unofficial UPM conversion of [FMOD's Unity integration](https://github.com/fmod/fmod-for-unity/tree/2.03). The published package contains integration source, editor tooling, platform source and images. It does **not** contain FMOD native libraries, banks or the FMOD Studio application.

## Install the source package

In Unity's Package Manager, select **Add package from git URL** and enter:

```text
https://github.com/Avlorayne/Fmod.git#1.0.0
```

After the package is registered on OpenUPM, it can also be installed with:

```sh
openupm add com.dotline.fmod
```

## Install your native libraries

1. Obtain **fmodstudio20314.unitypackage** from the [official FMOD download page](https://www.fmod.com/download). Follow FMOD's licence terms for your project.
2. Install **Python 3.9+** and make `python` available on Windows, or `python3` on macOS/Linux.
3. In Unity, select **FMOD > Native Library Installation**, then select your downloaded `.unitypackage`.
4. The tool creates a local embedded copy at `Packages/com.dotline.fmod`, installs the supplied native libraries, and refreshes Unity. Continue with **FMOD > Setup Wizard** to connect your FMOD Studio project or bank folder.

You can also run the tool from a terminal. Use the actual path of the installed source package:

```sh
python "<installed-package>/Tools~/install_native_libraries.py" --project "<Unity-project>" --unitypackage "<download-folder>/fmodstudio20314.unitypackage"
```

The installer validates the FMOD version, preserves native asset GUIDs, and activates the editor libraries that FMOD ships in its staging folder. It imports libraries for the public platforms included in the selected archive. It does not download libraries or import the original integration scripts into `Assets`, so duplicate assemblies are avoided.

Existing libraries with different bytes are rejected. To change the FMOD native version, close Unity and upgrade the integration and native libraries together. Repeating installation of the same native package preserves loaded DLLs.

The local embedded package overrides the registry/Git dependency. To upgrade the source package later, close Unity, back up any customizations, remove the embedded `Packages/com.dotline.fmod` folder, install the desired source version, and reinstall its matching native libraries.

## Package behavior

- Original integration assembly names and asset GUIDs are retained.
- FMOD discovers its installation using Unity's package metadata.
- Project settings, bank caches and generated IL2CPP static-plugin registration code are stored under `Assets/Plugins/FMOD`, outside the package cache.
- A source-only installation displays an installation notice and defers FMOD editor startup until the native libraries exist.
- Timeline, Addressables and Visual Scripting dependencies are declared for the integration's assembly references. The unused Input System assembly reference is removed; this package does not require Input System or change Active Input Handling.
- URP is not installed as a dependency. The optional URP VR debug overlay requires local customization of the original URP assembly reference and its version define (`com.unity.render-pipelines.universal`). Standard audio functionality works without URP.

Native libraries, generated settings and caches are excluded by both `.gitignore` and `.npmignore`. Keep these exclusions when maintaining a fork. The published source package is not a self-contained FMOD runtime distribution.

## Licence

The integration source and Dotline's UPM adaptations are distributed under the [MIT licence](LICENSE), as provided by [FMOD's source repository](https://github.com/fmod/fmod-for-unity/blob/2.03/LICENSE). FMOD native libraries are separately governed by FMOD's EULA and your agreement with Firelight Technologies; the original archive's EULA is preserved at `Documentation~/FMOD-EULA.txt`. Installing this source package does not grant a licence to redistribute FMOD native libraries.

FMOD and Firelight Technologies are trademarks of their respective owners. Refer to the [FMOD Unity documentation](https://www.fmod.com/docs/2.03/unity) for configuration, platform requirements and usage.

## Validation

Run the installer tests with:

```sh
python -m unittest discover -s "Tools~/tests" -v
```

Release 1.0.0 is validated in Unity 2022.3 on Windows. Other platform binaries are preserved from the supplied archive; platform builds require their respective Unity build modules and have not been validated by this conversion.
