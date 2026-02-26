"""Lightweight data structure for a single visual text line from a PDF page."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextLine:
    """A single visual line extracted from a PDF page."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float
    font_name: str
    is_bold: bool
    page_num: int

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def width(self) -> float:
        return self.x1 - self.x0
