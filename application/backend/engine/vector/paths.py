"""SVG path data ("M 10 20 L 30 40 Z") to skia paths. The full grammar: M L H V C S Q T A Z, absolute and relative."""

import math
import re
from functools import lru_cache

import skia

CACHE_SIZE = 32768
SNIPPET_LENGTH = 12

# How many numbers each command takes per repeat.
ARGUMENT_COUNTS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
COMMAND_LETTERS = set("MLHVCSQTAZmlhvcsqtaz")
SEPARATORS = set(" \t\r\n\f,")
NUMBER_PATTERN = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
ARC_FLAG_INDEXES = (3, 4)  # large-arc and sweep flags: single "0" or "1" characters, may be written without spaces


def parse_path(d: str) -> skia.Path:
    """A new skia.Path for the path data (parsed once per string, then copied). Raises ValueError("Bad path data at ...")."""
    return skia.Path(cached_path(d))


@lru_cache(maxsize=CACHE_SIZE)
def cached_path(d: str) -> skia.Path:
    """The shared parsed path for this string. Read only: callers must never change it (use parse_path for a copy)."""
    if not isinstance(d, str):
        raise ValueError(f"Bad path data: expected a string, got {type(d).__name__}")
    return PathParser(d).parse()


def bad_path(d: str, position: int, reason: str) -> ValueError:
    snippet = d[position:position + SNIPPET_LENGTH]
    near = f' near "{snippet}"' if snippet else " at the end"
    return ValueError(f"Bad path data at character {position + 1}: {reason}{near}")


class PathParser:
    """Reads one path string left to right. Tracks the current point so relative and smooth commands work."""

    def __init__(self, d: str):
        self.d = d
        self.position = 0
        self.path = skia.Path()
        self.current = (0.0, 0.0)
        self.start = (0.0, 0.0)
        self.last_cubic_control: tuple[float, float] | None = None
        self.last_quad_control: tuple[float, float] | None = None

    def parse(self) -> skia.Path:
        d = self.d
        command = None
        self.skip_separators()
        while self.position < len(d):
            character = d[self.position]
            if character in COMMAND_LETTERS:
                if command is None and character not in "Mm":
                    raise bad_path(d, self.position, "path data must start with M or m")
                command = character
                self.position += 1
            elif command is None:
                raise bad_path(d, self.position, "path data must start with M or m")
            elif command in "Zz":
                raise bad_path(d, self.position, "expected a command after Z")
            elif command == "M":
                command = "L"  # numbers after a move are implicit line-tos
            elif command == "m":
                command = "l"
            self.run_command(command)
            self.skip_separators()
        return self.path

    def run_command(self, command: str) -> None:
        upper = command.upper()
        relative = command.islower()
        count = ARGUMENT_COUNTS[upper]
        if count == 0:
            self.path.close()
            self.current = self.start
            self.last_cubic_control = None
            self.last_quad_control = None
            return
        values = [self.read_flag() if upper == "A" and index in ARC_FLAG_INDEXES else self.read_number() for index in range(count)]
        x0, y0 = self.current
        if upper == "M":
            x, y = values
            if relative:
                x, y = x + x0, y + y0
            self.path.moveTo(x, y)
            self.current = self.start = (x, y)
            self.clear_controls()
        elif upper == "L":
            x, y = values
            if relative:
                x, y = x + x0, y + y0
            self.line_to(x, y)
        elif upper == "H":
            x = values[0] + x0 if relative else values[0]
            self.line_to(x, y0)
        elif upper == "V":
            y = values[0] + y0 if relative else values[0]
            self.line_to(x0, y)
        elif upper == "C":
            x1, y1, x2, y2, x, y = self.absolute(values, relative)
            self.path.cubicTo(x1, y1, x2, y2, x, y)
            self.current = (x, y)
            self.last_cubic_control = (x2, y2)
            self.last_quad_control = None
        elif upper == "S":
            x2, y2, x, y = self.absolute(values, relative)
            x1, y1 = self.reflect(self.last_cubic_control)
            self.path.cubicTo(x1, y1, x2, y2, x, y)
            self.current = (x, y)
            self.last_cubic_control = (x2, y2)
            self.last_quad_control = None
        elif upper == "Q":
            x1, y1, x, y = self.absolute(values, relative)
            self.path.quadTo(x1, y1, x, y)
            self.current = (x, y)
            self.last_quad_control = (x1, y1)
            self.last_cubic_control = None
        elif upper == "T":
            x, y = self.absolute(values, relative)
            x1, y1 = self.reflect(self.last_quad_control)
            self.path.quadTo(x1, y1, x, y)
            self.current = (x, y)
            self.last_quad_control = (x1, y1)
            self.last_cubic_control = None
        elif upper == "A":
            rx, ry, rotation, large_arc, sweep, x, y = values
            if relative:
                x, y = x + x0, y + y0
            self.arc_to(abs(rx), abs(ry), rotation, large_arc, sweep, x, y)

    def absolute(self, values: list[float], relative: bool) -> list[float]:
        """Relative coordinate pairs to absolute ones."""
        if not relative:
            return values
        x0, y0 = self.current
        return [value + (x0 if index % 2 == 0 else y0) for index, value in enumerate(values)]

    def reflect(self, control: tuple[float, float] | None) -> tuple[float, float]:
        """The smooth-curve first control point: the previous control mirrored through the current point."""
        x0, y0 = self.current
        if control is None:
            return x0, y0
        return 2 * x0 - control[0], 2 * y0 - control[1]

    def clear_controls(self) -> None:
        self.last_cubic_control = None
        self.last_quad_control = None

    def line_to(self, x: float, y: float) -> None:
        self.path.lineTo(x, y)
        self.current = (x, y)
        self.clear_controls()

    def arc_to(self, rx: float, ry: float, rotation: float, large_arc: int, sweep: int, x: float, y: float) -> None:
        if rx == 0 or ry == 0:
            self.path.lineTo(x, y)
        elif (x, y) != self.current:
            size = skia.Path.ArcSize.kLarge_ArcSize if large_arc else skia.Path.ArcSize.kSmall_ArcSize
            # SVG sweep flag 1 means clockwise on screen, which is skia's kCW.
            direction = skia.PathDirection.kCW if sweep else skia.PathDirection.kCCW
            self.path.arcTo(rx, ry, rotation, size, direction, x, y)
        self.current = (x, y)
        self.clear_controls()

    def skip_separators(self) -> None:
        d = self.d
        while self.position < len(d) and d[self.position] in SEPARATORS:
            self.position += 1

    def read_number(self) -> float:
        self.skip_separators()
        match = NUMBER_PATTERN.match(self.d, self.position)
        if not match:
            raise bad_path(self.d, self.position, "expected a number")
        value = float(match.group())
        if not math.isfinite(value):
            raise bad_path(self.d, self.position, "number out of range")
        self.position = match.end()
        return value

    def read_flag(self) -> int:
        self.skip_separators()
        if self.position < len(self.d) and self.d[self.position] in "01":
            self.position += 1
            return int(self.d[self.position - 1])
        raise bad_path(self.d, self.position, "expected an arc flag (0 or 1)")
