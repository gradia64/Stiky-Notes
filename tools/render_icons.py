#!/usr/bin/env python3
"""Genera le icone PNG di debian/icons dalle sorgenti SVG.

Le dimensioni piccole (fino a 24 px) usano la variante semplificata,
più leggibile nel vassoio di sistema e negli elenchi.

    python3 tools/render_icons.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PyQt6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "src" / "kde_plasma_stiky_notes" / "icons"
OUT = ROOT / "debian" / "icons"
SIZES = (16, 22, 24, 32, 48, 64, 128, 256)


def render(svg: Path, size: int, dest: Path):
    renderer = QSvgRenderer(str(svg))
    if not renderer.isValid():
        sys.exit(f"SVG non valido: {svg}")
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    image.save(str(dest))


def main():
    QGuiApplication([])
    OUT.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        svg = ICONS / ("stiky-notes-small.svg" if size <= 24 else "stiky-notes.svg")
        dest = OUT / f"stiky-notes-{size}.png"
        render(svg, size, dest)
        print(f"{dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
