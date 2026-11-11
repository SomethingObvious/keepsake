# Keepsake for Android

[Keepsake](../README.md) on the phone: the same window and the same Python as on Windows, so the queue, previews and Clip, the library with its player, clips, GIFs and Save Frame, picture galleries, search, subscriptions, history, sign-ins and Remove Text all work here too. Downloads go to Movies, Music, Pictures and Documents, each in a Keepsake folder, and run on the phone itself while the app is in the background.

The window is the desktop's `ui/` in a WebView, with a small bridge standing in for pywebview. Chaquopy runs the desktop's `keepsake` package, with its Windows parts swapped for Android ones in `android_shell.py`. yt-dlp and gallery-dl run inside the app, since Android has no Python program to start. FFmpeg is the static musl build from [wader/static-ffmpeg](https://github.com/wader/static-ffmpeg), because Android's sandbox stops glibc builds, and YouTube's player code runs on [QuickJS](https://github.com/quickjs-ng/quickjs). The daily tool update downloads yt-dlp's own zip build and gallery-dl's wheel, which take over straight away when nothing is downloading, or on the next start. Remove Text's two models run in ONNX Runtime for Android, through `Model.kt`, and since jpeglib has no Android build, its JPEG copies are encoded again whole with the original's own tables rather than spliced.

It needs Android 11 or newer on a 64-bit ARM phone, and access to all files, which it asks for on first start. The global hotkey, the tray and Afterimage stay on Windows.

## Building

It builds from the desktop app one folder up, or from another working copy if you set `keepsake.dir` in `local.properties`. It needs JDK 21, the Android SDK (platform 36, build tools 36) and Python 3.13, and fetches FFmpeg on the first build:

```console
cd android
./gradlew assembleRelease
adb install -r app/build/outputs/apk/release/app-release.apk
```

It is MIT licensed like the rest of Keepsake, see [LICENSE](../LICENSE). The parts it carries keep their own licences, listed in [NOTICES.md](NOTICES.md).
