# .convert for Android

This module is a native Kotlin application. It uses `ACTION_OPEN_DOCUMENT` and `ACTION_CREATE_DOCUMENT`; no broad storage permission is declared.

## Supported conversions

- PNG, JPEG, WebP, BMP, and the first frame of GIF to PNG, JPEG, or WebP
- TXT, Markdown, HTML, LOG, reStructuredText, and NFO between the supported text outputs
- JSON, JSON Lines, CSV, and TSV between the supported structured-data outputs

The conversion is completed in the app cache before the destination document is opened. Images above 80 megapixels and text/data files above 32 MiB are rejected.

## Build

Requirements:

- JDK 17
- Android SDK 35
- Gradle 8.10.2

```bash
gradle -p android :app:testDebugUnitTest :app:assembleDebug
```

Install the resulting APK:

```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

## Debugging

Enable **Debug mode** in the application to show detailed conversion events. Logs are also written under the `dotconvert` logcat tag. The in-app log can be exported as a text document.
