"""Small color helpers shared by the character and scene painters."""

import colorsys

import skia


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def rgb_to_hex(red: float, green: float, blue: float) -> str:
    def clamp(channel: float) -> int:
        return max(0, min(255, round(channel)))

    return f"#{clamp(red):02X}{clamp(green):02X}{clamp(blue):02X}"


def shade(hex_color: str, amount: float) -> str:
    """amount > 0 lightens toward white, amount < 0 darkens toward black (in HLS lightness)."""
    red, green, blue = (channel / 255 for channel in hex_to_rgb(hex_color))
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    if amount >= 0:
        lightness = lightness + (1 - lightness) * amount
    else:
        lightness = lightness * (1 + amount)
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return rgb_to_hex(red * 255, green * 255, blue * 255)


def mix(hex_a: str, hex_b: str, amount: float) -> str:
    red_a, green_a, blue_a = hex_to_rgb(hex_a)
    red_b, green_b, blue_b = hex_to_rgb(hex_b)
    return rgb_to_hex(
        red_a + (red_b - red_a) * amount,
        green_a + (green_b - green_a) * amount,
        blue_a + (blue_b - blue_a) * amount,
    )


def skia_color(hex_color: str, alpha: float = 1.0) -> int:
    red, green, blue = hex_to_rgb(hex_color)
    return skia.Color(red, green, blue, max(0, min(255, round(alpha * 255))))


def fill_paint(hex_color: str, alpha: float = 1.0) -> skia.Paint:
    return skia.Paint(Color=skia_color(hex_color, alpha), AntiAlias=True, Style=skia.Paint.kFill_Style)


def stroke_paint(hex_color: str, width: float, alpha: float = 1.0, round_cap: bool = True) -> skia.Paint:
    paint = skia.Paint(Color=skia_color(hex_color, alpha), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width)
    if round_cap:
        paint.setStrokeCap(skia.Paint.kRound_Cap)
        paint.setStrokeJoin(skia.Paint.kRound_Join)
    return paint
