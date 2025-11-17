# Quality presets for video rendering
# Manim quality flags: l=low (854x480 15FPS), m=medium (1280x720 30FPS),
# h=high (1920x1080 60FPS), p=2k (2560x1440 60FPS), k=4k (3840x2160 60FPS)
QUALITY_PRESETS = {
    "low": {"quality_flag": "l", "resolution": "854x480", "frame_rate": 15},
    "medium": {"quality_flag": "m", "resolution": "1280x720", "frame_rate": 30},
    "high": {"quality_flag": "h", "resolution": "1920x1080", "frame_rate": 60},
    "4k": {"quality_flag": "k", "resolution": "3840x2160", "frame_rate": 60},
}
