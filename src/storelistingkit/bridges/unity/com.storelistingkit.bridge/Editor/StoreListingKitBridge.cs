// Store Listing Kit bridge for the Unity Editor.
// Tools > Store Listing Kit > Open for Selected Package / Capture Game View Screenshot / Open Screenshots Folder
using System;
using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace StoreListingKit.Bridge
{
    public static class StoreListingKitBridge
    {
        const string ExePrefKey = "StoreListingKit.ExePath";
        const string BridgePackage = "com.storelistingkit.bridge";

        [Serializable]
        class Location { public string exe; public string[] args; }

        static string ProjectRoot => Path.GetDirectoryName(Application.dataPath);

        public static string ScreenshotsDir
        {
            get
            {
                var dir = Path.Combine(ProjectRoot, "StoreListingKit", "Screenshots");
                Directory.CreateDirectory(dir);
                return dir;
            }
        }

        static string[] FindTool()
        {
            var pref = EditorPrefs.GetString(ExePrefKey, "");
            if (File.Exists(pref)) return new[] { pref };
            var env = Environment.GetEnvironmentVariable("SLK_EXE");
            if (!string.IsNullOrEmpty(env) && File.Exists(env)) return new[] { env };
            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var loc = Path.Combine(local, "StoreListingKit", "location.json");
            if (File.Exists(loc))
            {
                try
                {
                    var data = JsonUtility.FromJson<Location>(File.ReadAllText(loc));
                    if (data != null && File.Exists(data.exe))
                    {
                        var result = new string[1 + (data.args?.Length ?? 0)];
                        result[0] = data.exe;
                        data.args?.CopyTo(result, 1);
                        return result;
                    }
                }
                catch (Exception) { /* fall through */ }
            }
            var def = Path.Combine(local, "Programs", "StoreListingKit", "StoreListingKit.exe");
            if (File.Exists(def)) return new[] { def };
            var picked = EditorUtility.OpenFilePanel("Locate StoreListingKit.exe", local, "exe");
            if (!string.IsNullOrEmpty(picked) && File.Exists(picked))
            {
                EditorPrefs.SetString(ExePrefKey, picked);
                return new[] { picked };
            }
            return null;
        }

        /// The package folder to describe: the selected folder that holds a package.json,
        /// or the project root (the tool then picks the shallowest UPM package).
        static string SourceFolder()
        {
            foreach (var guid in Selection.assetGUIDs)
            {
                var assetPath = AssetDatabase.GUIDToAssetPath(guid);
                var full = Path.GetFullPath(assetPath);
                var dir = Directory.Exists(full) ? full : Path.GetDirectoryName(full);
                while (!string.IsNullOrEmpty(dir) && dir.StartsWith(ProjectRoot, StringComparison.OrdinalIgnoreCase))
                {
                    if (File.Exists(Path.Combine(dir, "package.json")) && !dir.EndsWith(BridgePackage))
                        return dir;
                    dir = Path.GetDirectoryName(dir);
                }
            }
            return ProjectRoot;
        }

        static string Quote(string s) => "\"" + s.Replace("\"", "\\\"") + "\"";

        [MenuItem("Tools/Store Listing Kit/Open for Selected Package or Project", priority = 1)]
        public static void OpenTool()
        {
            var tool = FindTool();
            if (tool == null)
            {
                EditorUtility.DisplayDialog("Store Listing Kit",
                    "Store Listing Kit is not installed. Install it, run it once, then try again.", "OK");
                return;
            }
            var source = SourceFolder();
            var args = "";
            for (int i = 1; i < tool.Length; i++) args += Quote(tool[i]) + " ";
            args += "--source " + Quote(source) + " --screenshots " + Quote(ScreenshotsDir);
            Process.Start(new ProcessStartInfo(tool[0], args) { UseShellExecute = true });
            UnityEngine.Debug.Log("Store Listing Kit launched for " + source);
        }

        [MenuItem("Tools/Store Listing Kit/Capture Game View Screenshot", priority = 20)]
        public static void Capture()
        {
            var file = Path.Combine(ScreenshotsDir, "listing_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".png");
            ScreenCapture.CaptureScreenshot(file, 1);
            UnityEngine.Debug.Log("Store Listing Kit: capturing Game view to " + file +
                                  " (the Game view must be visible; the file appears after the next frame).");
        }

        [MenuItem("Tools/Store Listing Kit/Open Screenshots Folder", priority = 21)]
        public static void OpenFolder() => EditorUtility.RevealInFinder(ScreenshotsDir);

        [MenuItem("Tools/Store Listing Kit/Forget Tool Location", priority = 40)]
        public static void Forget() => EditorPrefs.DeleteKey(ExePrefKey);
    }
}
