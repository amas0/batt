import time
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path("/sys/class/backlight/")


@dataclass
class BacklightBrightness:
    timestamp: int
    brightness_percentage: int


def get_backlight_directories(base_dir: Path = BASE_DIR) -> list[Path]:
    """Get a list of backlight directories, default /sys/class/backlight/"""
    return list(base_dir.iterdir())


def get_backlight_reading_from_dir(backlight_dir: Path) -> BacklightBrightness:
    """Given a backlight reading from a backlight dir, e.g.
    /sys/class/backlight/intel_backlight/, return a timestamped
    reading of the backlight percentage
    """
    with open(backlight_dir / "actual_brightness") as f:
        actual = int(f.read().strip())
    with open(backlight_dir / "max_brightness") as f:
        max_brightness = int(f.read().strip())

    return BacklightBrightness(
        timestamp=int(time.time()),
        brightness_percentage=round(100 * actual / max_brightness),
    )


def get_backlight_reading(base_dir: Path = BASE_DIR) -> BacklightBrightness:
    """Get a backlight reading from the first backlight directory found"""
    first, *_ = get_backlight_directories(base_dir)
    return get_backlight_reading_from_dir(first)
