// Copyright (c) 2026 Avlorayne / Dotline. Licensed under the MIT License.
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace FMODUnity
{
    /// <summary>Installs user-supplied native libraries without redistributing them.</summary>
    public static class DotlineNativeLibraries
    {
        public static bool EditorLibraryExists
        {
            get
            {
                string root = RuntimeUtils.PluginBasePath;
#if UNITY_EDITOR_WIN
                return File.Exists($"{root}/platforms/win/lib/{RuntimeUtils.GetPluginArchitectureFolder()}/fmodstudioL.dll");
#elif UNITY_EDITOR_OSX
                return Directory.Exists($"{root}/platforms/mac/lib/fmodstudioL.bundle");
#elif UNITY_EDITOR_LINUX
                return File.Exists($"{root}/platforms/linux/lib/x86_64/libfmodstudioL.so");
#else
                return false;
#endif
            }
        }

        [MenuItem("FMOD/Native Library Installation", priority = 2)]
        public static void Install()
        {
            string archive = EditorUtility.OpenFilePanel("Select fmodstudio20314.unitypackage", "", "unitypackage");
            if (string.IsNullOrEmpty(archive))
                return;

            var package = UnityEditor.PackageManager.PackageInfo.FindForAssembly(typeof(RuntimeUtils).Assembly);
            if (package == null || package.name != "com.dotline.fmod")
                throw new InvalidOperationException("The com.dotline.fmod UPM package could not be located.");

            string tool = Path.Combine(package.resolvedPath, "Tools~/install_native_libraries.py");
            string project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
#if UNITY_EDITOR_WIN
            const string python = "python";
#else
            const string python = "python3";
#endif
            var output = new StringBuilder();
            try
            {
                EditorUtility.DisplayProgressBar("FMOD native libraries", "Installing local libraries from your Unity package...", 0.5f);
                using (var process = new Process())
                {
                    process.StartInfo = new ProcessStartInfo
                    {
                        FileName = python,
                        Arguments = Quote(tool) + " --project " + Quote(project)
                            + " --unitypackage " + Quote(archive) + " --package-source " + Quote(package.resolvedPath),
                        WorkingDirectory = project,
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                    };
                    process.OutputDataReceived += (_, e) => { if (e.Data != null) lock (output) output.AppendLine(e.Data); };
                    process.ErrorDataReceived += (_, e) => { if (e.Data != null) lock (output) output.AppendLine(e.Data); };
                    process.Start();
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    process.WaitForExit();
                    if (process.ExitCode != 0)
                        throw new InvalidOperationException(output.ToString());
                }
                Debug.Log(output.ToString());
                AssetDatabase.Refresh();
                // A cached registry/Git package may have been replaced with a local embedded copy.
                Client.Resolve();
                EditorUtility.RequestScriptReload();
            }
            catch (Exception error)
            {
                Debug.LogError("FMOD native-library installation failed. Python 3.9+ must be on PATH. " + error.Message);
                EditorUtility.DisplayDialog("FMOD native libraries", "Installation failed. Check the Console and the package README. Python 3.9+ is required.", "OK");
            }
            finally
            {
                EditorUtility.ClearProgressBar();
            }
        }

        private static string Quote(string path)
        {
            return "\"" + path.Replace('\\', '/').Replace("\"", "\\\"") + "\"";
        }
    }
}
