from pathlib import Path

from PIL import Image

from dotconvert.engine import ConversionEngine
from dotconvert.models import ConversionPlan


def test_png_to_jpeg_flattens_transparency(tmp_path: Path) -> None:
    source = tmp_path / "transparent.png"
    destination = tmp_path / "converted.jpg"
    Image.new("RGBA", (24, 24), (255, 0, 0, 0)).save(source)

    result = ConversionEngine().convert(
        ConversionPlan(source=source, target_extension=".jpg", destination=destination)
    )

    assert result.destination == destination
    assert source.exists()
    with Image.open(destination) as converted:
        assert converted.format == "JPEG"
        assert converted.mode == "RGB"
        assert converted.size == (24, 24)


def test_animated_gif_to_png_uses_first_frame_and_warns(tmp_path: Path) -> None:
    source = tmp_path / "animated.gif"
    destination = tmp_path / "first.png"
    frames = [Image.new("RGB", (8, 8), color) for color in ("red", "blue")]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=50, loop=0)

    engine = ConversionEngine()
    plan = ConversionPlan(source=source, target_extension=".png", destination=destination)
    warnings = engine.warnings_for(plan)
    engine.convert(plan)

    assert destination.exists()
    assert any(item.code == "animation-loss" for item in warnings)
