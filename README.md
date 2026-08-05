<p align="center">
  <img src="assets/logo.svg" width="720" alt=".convert logo">
</p>

# .convert

`.convert` converts files without treating an extension change as a conversion. It writes to a temporary file first, checks that the result is non-empty, and only then replaces or creates the selected output.

The desktop application runs on Windows and Linux. A native Android application is included under [`android/`](android/).

## What changed in 1.1

- The desktop window can switch between English, Traditional Chinese, and Japanese. English is the default.
- Debug mode writes a rotating log file and can show the same log inside the window.
- The command line supports `--debug`, `--log-file`, and `--list-formats`.
- More image, text, structured-data, archive, audio, and video extensions are registered.
- The Android application is written in Kotlin and uses Android's system document picker. It does not request storage or network permissions.
- CI now builds and tests the Android module and launches the APK in an emulator for a startup, UI-tree, screenshot, and logcat check.

## Desktop safety rules

- Only formats from the same conversion group are offered.
- Save-as mode keeps the source file.
- Replace-source mode moves the source to the system recycle bin only after conversion succeeds.
- Existing outputs are not overwritten unless overwrite is enabled.
- Output is produced in the destination directory as a temporary file and committed with `os.replace`.
- Known transparency, animation, formatting, table-shape, metadata, stream, quality, overwrite, and source-replacement risks are shown before conversion.
- FFmpeg is called without a shell and with explicit arguments.
- Archive repacking blocks path traversal, symbolic links, device files, encrypted ZIP input, suspicious compression ratios, more than 100,000 entries, and expansion above 2 GiB.

## Desktop formats

Aliases such as `.jpeg`, `.tif`, `.tgz`, `.tbz2`, `.txz`, `.yml`, `.aif`, and `.mpg` are normalized to one canonical target.

| Group | Input and output extensions | Backend |
|---|---|---|
| Images | PNG, JPEG, WebP, BMP/DIB, TIFF, GIF, ICO, TGA, DDS, PCX, PPM, PGM, PBM | Pillow |
| Text | TXT, Markdown, HTML, reStructuredText, LOG, NFO | Built-in text and HTML handling |
| Structured data | JSON, JSON Lines, YAML, TOML, CSV, TSV, XML | Python standard library and PyYAML |
| Archives | ZIP, TAR, TAR.GZ/TGZ, TAR.BZ2/TBZ2, TAR.XZ/TXZ | Python archive libraries with protected extraction |
| Audio | MP3, WAV, FLAC, OGG, Opus, AAC, M4A, WMA, AIFF | FFmpeg |
| Video | MP4, MKV, WebM, MOV, AVI, M4V, FLV, MPEG/MPG, 3GP, OGV, MPEG-TS | FFmpeg |

Some encoders depend on the codecs included in the installed FFmpeg build. A failed media conversion leaves the source and any existing destination unchanged.

## Android support

The Kotlin application uses the Storage Access Framework, so the user chooses both source and destination documents through Android's system UI.

Supported Android conversions are deliberately narrower than the desktop set:

| Group | Android input | Android output |
|---|---|---|
| Images | PNG, JPEG, WebP, BMP, GIF first frame | PNG, JPEG, WebP |
| Text | TXT, Markdown, HTML, LOG, reStructuredText, NFO | TXT, Markdown, HTML, LOG, reStructuredText, NFO |
| Data | JSON, JSON Lines, CSV, TSV | JSON, JSON Lines, CSV, TSV |

Android conversion is written to the app cache first. The selected document is opened only after the temporary conversion succeeds. The app has an 80-megapixel image limit and a 32 MiB text/data input limit to avoid uncontrolled memory use.

The Android application does not pretend to support arbitrary archive or media transcoding with platform APIs. Those formats remain available in the desktop build through the protected archive pipeline and FFmpeg.

## Desktop installation

Python 3.10 or newer is required.

### Windows

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install .
.venv\Scripts\python -m dotconvert
```

`run.bat` performs the virtual-environment setup. Tagged releases also contain a PyInstaller executable.

### Linux

Install Tk and FFmpeg through the distribution package manager. On Debian or Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk ffmpeg
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
.venv/bin/python -m dotconvert
```

`run.sh` performs the Python setup.

### FFmpeg selection

Media conversion searches `PATH` for `ffmpeg`. A specific binary can be selected with:

```bash
export DOTCONVERT_FFMPEG=/full/path/to/ffmpeg
```

On PowerShell:

```powershell
$env:DOTCONVERT_FFMPEG = "C:\path\to\ffmpeg.exe"
```

## Android build

Open the `android/` directory in Android Studio, or use Gradle 8.10.2 with JDK 17:

```bash
gradle -p android :app:testDebugUnitTest :app:assembleDebug
```

The installable APK is written to:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

Tagged GitHub Releases include the Android debug-signed APK for sideload testing. It is not a Play Store signing configuration.

## Debug mode

The desktop window contains a **Debug mode** checkbox and a log viewer. Normal mode records operational information. Debug mode also records selected targets, temporary paths, converter dispatch, and FFmpeg command details.

Default desktop log locations:

- Windows: `%LOCALAPPDATA%\dotconvert\logs\dotconvert.log`
- Linux: `$XDG_STATE_HOME/dotconvert/dotconvert.log`, or `~/.local/state/dotconvert/dotconvert.log`

Logs rotate at 2 MiB and keep three backups. The Android application keeps up to 500 log lines in memory, displays them in the app, writes them to logcat, and can export them through the system document picker.

Command-line examples:

```bash
python -m dotconvert input.png output.webp --quality 90 --yes
python -m dotconvert input.json output.toml --yes
python -m dotconvert input.zip output.tar.xz --yes
python -m dotconvert input.wav output.opus --yes --debug
python -m dotconvert --list-formats
```

Use `--log-file PATH` to select another log file. Use `--overwrite` to replace an existing output. Use `--replace-source` to move the original to the recycle bin after success. Without `--yes`, the CLI prints warnings and stops.

## Development and verification

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest --cov=dotconvert --cov-report=term-missing
pyinstaller --clean --noconfirm dotconvert.spec

gradle -p android :app:testDebugUnitTest :app:assembleDebug
```

GitHub Actions performs Python linting, Windows and Linux tests, a real FFmpeg conversion, Windows and Linux executable builds, Android unit tests, an APK build, and an emulator startup check. The emulator job captures the UI hierarchy, screenshot, and logcat output as workflow artifacts.

## Limits

No converter can preserve every property while moving between formats with different capabilities. `.convert` rejects incompatible groups, warns before known losses, and avoids changing the source until output production succeeds. Important files should still have an independent backup, and converted output should be inspected before that backup is removed.

## License

MIT. See [LICENSE](LICENSE).
