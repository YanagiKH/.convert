<p align="center">
  <img src="assets/logo.svg" width="720" alt=".convert logo">
</p>

# .convert

`.convert` is a desktop file-format converter designed around two rules: perform a real conversion instead of merely renaming an extension, and leave the original file untouched until a valid output has been produced.

The interface is runs on Windows and Linux. A command-line mode is included for automation and testing.

## Features

- Dedicated desktop window built with the Python standard library's Tk interface.
- Only compatible target formats are offered for the selected source file.
- Save-as mode preserves the source file.
- Replace-source mode moves the original file to the system recycle bin only after conversion succeeds.
- Existing destinations are never overwritten unless the user explicitly enables it.
- Conversion is written to a temporary file in the destination directory and committed with an atomic replacement.
- Known quality, transparency, animation, formatting, metadata, stream, and destructive-operation risks are shown before execution.
- Media commands are executed without a shell and with explicit arguments.
- Archive extraction blocks path traversal, links, device files, excessive entry counts, suspicious compression ratios, and decompressed data above 2 GiB.
- Automated tests cover successful conversions and failure cases that must preserve the original and existing destination.

## Supported formats

| Group | Input and output formats | Notes |
|---|---|---|
| Images | PNG, JPEG, WebP, BMP, TIFF, GIF, ICO | Uses Pillow. Transparency and animation loss are warned before conversion. |
| Text | TXT, Markdown, HTML | UTF-8 output. Common UTF encodings, Big5/CP950, Shift-JIS, and Latin-1 are read conservatively. |
| Structured data | JSON, YAML, CSV, XML | CSV output requires flat rows; nested data is rejected rather than silently flattened. |
| Archives | ZIP, TAR, TAR.GZ/TGZ | Repacked through a protected temporary directory. |
| Audio | MP3, WAV, FLAC, OGG, AAC, M4A | Requires FFmpeg. |
| Video | MP4, MKV, WebM, MOV, AVI | Requires FFmpeg. |

Formats are intentionally grouped. For example, an image can be converted to another image format, but it cannot be mislabeled as an audio file.

## Windows installation

### Release executable

Download the Windows artifact from GitHub Releases, extract it, and run `dotconvert.exe`.

FFmpeg is optional and only required for audio/video conversion. Install FFmpeg and add it to `PATH`, or set `DOTCONVERT_FFMPEG` to the full path of `ffmpeg.exe`.

### Python installation

Python 3.10 or newer is required.

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install .
.venv\Scripts\python -m dotconvert
```

The repository also includes `run.bat`, which creates the local virtual environment and starts the application.

## Linux installation

Install Tk and FFmpeg through the distribution package manager. On Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk ffmpeg
```

Then run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
.venv/bin/python -m dotconvert
```

The included `run.sh` performs the virtual-environment setup automatically.

## Desktop workflow

1. Select one source file.
2. Select a compatible target extension.
3. Choose **Save as** or **Replace source**.
4. Enable destination overwrite only when an existing output should be replaced.
5. Review every warning shown in the conversion preview and confirmation dialog.
6. Choose the output path and start the conversion.

A failed conversion deletes its temporary output and does not modify the original or the existing destination.

## Command-line use

```bash
python -m dotconvert input.png output.webp --quality 90 --yes
python -m dotconvert input.json output.yaml --yes
python -m dotconvert input.zip output.tar.gz --yes
```

Use `--overwrite` to replace an existing destination. Use `--replace-source` to move the original to the recycle bin after success. Without `--yes`, command-line conversion stops and prints any detected warnings.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
pyinstaller --clean --noconfirm dotconvert.spec
```

GitHub Actions runs linting, tests on Windows and Linux, an FFmpeg integration test, package building, and executable smoke checks. Tags matching `v*` build Windows and Linux release archives and publish them to GitHub Releases.

## Safety boundary

No general converter can guarantee perfect preservation across fundamentally different formats. `.convert` therefore avoids unsupported format pairs, warns about known losses, refuses unsafe archive content, and aborts when a conversion cannot be represented safely. Keep backups for valuable files and inspect converted output before deleting independent backups.

## License

MIT. See [LICENSE](LICENSE).
