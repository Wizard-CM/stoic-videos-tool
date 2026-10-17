"""Path-building helpers used by every painter."""

import math

import skia


def mirrored_outline(top: tuple[float, float], right_side: list[tuple]) -> skia.Path:
    """Closed path symmetric around x = 0.

    right_side is a list of cubic segments (control1, control2, end) going clockwise from
    `top` down the right half and ending on x = 0. The left half is mirrored automatically.
    """
    path = skia.Path()
    path.moveTo(*top)
    for control_1, control_2, end in right_side:
        path.cubicTo(*control_1, *control_2, *end)

    starts = [top] + [segment[2] for segment in right_side[:-1]]
    for (control_1, control_2, _end), start in zip(reversed(right_side), reversed(starts)):
        path.cubicTo(-control_2[0], control_2[1], -control_1[0], control_1[1], -start[0], start[1])
    path.close()
    return path


def polygon(points: list[tuple[float, float]], closed: bool = True) -> skia.Path:
    path = skia.Path()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    if closed:
        path.close()
    return path


def smooth_closed(points: list[tuple[float, float]], tension: float = 0.5) -> skia.Path:
    """Closed Catmull-Rom style curve through all points."""
    path = skia.Path()
    count = len(points)
    path.moveTo(*points[0])
    for index in range(count):
        p0 = points[(index - 1) % count]
        p1 = points[index]
        p2 = points[(index + 1) % count]
        p3 = points[(index + 2) % count]
        control_1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        control_2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        path.cubicTo(*control_1, *control_2, *p2)
    path.close()
    return path


def smooth_open(points: list[tuple[float, float]], tension: float = 0.5) -> skia.Path:
    path = skia.Path()
    path.moveTo(*points[0])
    count = len(points)
    for index in range(count - 1):
        p0 = points[max(index - 1, 0)]
        p1 = points[index]
        p2 = points[index + 1]
        p3 = points[min(index + 2, count - 1)]
        control_1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        control_2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        path.cubicTo(*control_1, *control_2, *p2)
    return path


def cubic_point(start, control_1, control_2, end, t: float) -> tuple[float, float]:
    u = 1 - t
    x = u**3 * start[0] + 3 * u * u * t * control_1[0] + 3 * u * t * t * control_2[0] + t**3 * end[0]
    y = u**3 * start[1] + 3 * u * u * t * control_1[1] + 3 * u * t * t * control_2[1] + t**3 * end[1]
    return x, y


def tapered_stroke(centerline: list[tuple[float, float]], widths: list[float]) -> skia.Path:
    """A filled shape along a centerline whose width varies per point (used for brows)."""
    left_side, right_side = [], []
    count = len(centerline)
    for index, (x, y) in enumerate(centerline):
        previous_point = centerline[max(index - 1, 0)]
        next_point = centerline[min(index + 1, count - 1)]
        dx, dy = next_point[0] - previous_point[0], next_point[1] - previous_point[1]
        length = math.hypot(dx, dy) or 1.0
        normal_x, normal_y = -dy / length, dx / length
        half = widths[index] / 2
        left_side.append((x + normal_x * half, y + normal_y * half))
        right_side.append((x - normal_x * half, y - normal_y * half))
    return smooth_closed(left_side + list(reversed(right_side)), tension=0.35)


def lerp(a: float, b: float, amount: float) -> float:
    return a + (b - a) * amount


def lerp_point(a, b, amount: float) -> tuple[float, float]:
    return a[0] + (b[0] - a[0]) * amount, a[1] + (b[1] - a[1]) * amount


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
