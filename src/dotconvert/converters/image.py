from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from ..errors import DotConvertError
from ..registry import normalize_extension

PIL_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tiff": "TIFF",
    ".gif": "GIF",
    ".ico": "ICO",
    ".tga": "TGA",
    ".dds": "DDS",
    ".pcx": "PCX",
    ".ppm": "PPM",
    ".pgm": "PPM",
    ".pbm": "PPM",
}


def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        background.alpha_composite(rgba)
        return background.convert("RGB")
    return image.convert("RGB")


def _prepare_frame(image: Image.Image, target: str) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if target == ".jpg":
        return _flatten_for_jpeg(image)
    if target == ".gif":
        return image.convert("RGBA").convert("P", palette=Image.Palette.ADAPTIVE)
    if target in {".ico", ".dds", ".tga"}:
        return image.convert("RGBA")
    if target == ".bmp" and image.mode not in {"1", "L", "P", "RGB", "RGBA"}:
        return image.convert("RGBA")
    if target == ".ppm":
        return image.convert("RGB")
    if target == ".pgm":
        return image.convert("L")
    if target == ".pbm":
        return image.convert("1")
    if target == ".pcx" and image.mode not in {"1", "L", "P", "RGB"}:
        return image.convert("RGB")
    return image.copy()


def convert_image(source: Path, destination: Path, target_extension: str, quality: int) -> None:
    target = normalize_extension(target_extension)
    output_format = PIL_FORMATS.get(target)
    if output_format is None:
        raise DotConvertError(f"Unsupported image target: {target}")
    frames: list[Image.Image] = []
    try:
        with Image.open(source) as image:
            frame_count = getattr(image, "n_frames", 1)
            supports_multiframe = target in {".gif", ".webp", ".tiff"}
            if frame_count > 1 and supports_multiframe:
                for index in range(frame_count):
                    image.seek(index)
                    frames.append(_prepare_frame(image, target))
            else:
                image.seek(0)
                frames.append(_prepare_frame(image, target))

            save_options: dict[str, object] = {}
            if target in {".jpg", ".webp"}:
                save_options["quality"] = quality
                save_options["optimize"] = True
            if target == ".png":
                save_options["optimize"] = True
            if target == ".ico":
                save_options["sizes"] = [
                    (16, 16),
                    (24, 24),
                    (32, 32),
                    (48, 48),
                    (64, 64),
                    (128, 128),
                    (256, 256),
                ]
            if len(frames) > 1:
                durations: list[int] = []
                for index in range(frame_count):
                    image.seek(index)
                    durations.append(int(image.info.get("duration", 100)))
                save_options.update(
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=int(image.info.get("loop", 0)),
                )
            exif = image.info.get("exif")
            if exif and target in {".jpg", ".webp", ".tiff"}:
                save_options["exif"] = exif
            frames[0].save(destination, format=output_format, **save_options)
    except (UnidentifiedImageError, OSError, ValueError, KeyError) as exc:
        raise DotConvertError(f"Image conversion failed: {exc}") from exc
    finally:
        for frame in frames:
            frame.close()
