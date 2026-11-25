"""Composición de subtítulos compartida por la vista previa y la exportación."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)

from pitranscriptor.subtitles import Cue


def paint_caption(painter: QPainter, bounds: QRectF, cue: Cue, position_ms: int) -> None:
    style = cue.style
    scale = min(bounds.height() / 720, bounds.width() / 720)
    font = QFont(style.font) if style.font else QGuiApplication.font()
    font.setPixelSize(max(1, round(style.size * scale)))
    font.setBold(style.bold)
    metrics = QFontMetricsF(font)
    gap = metrics.horizontalAdvance(" ")
    margin = max(2, 10 * scale)
    width_limit = bounds.width() * 0.9 - 2 * margin
    lines: list[list[tuple[int, str, float]]] = [[]]
    widths = [0.0]
    for index, token in enumerate(cue.text.split()):
        width = metrics.horizontalAdvance(token)
        extra = width + (gap if lines[-1] else 0)
        if widths[-1] + extra > width_limit and lines[-1]:
            lines.append([])
            widths.append(0.0)
            extra = width
        lines[-1].append((index, token, width))
        widths[-1] += extra
    full_width = max(widths) + 2 * margin
    full_height = metrics.lineSpacing() * len(lines) + 2 * margin
    x = bounds.left() + style.x * bounds.width() - full_width / 2
    y = bounds.top() + style.y * bounds.height() - full_height / 2
    x = max(bounds.left(), min(x, bounds.right() - full_width))
    y = max(bounds.top(), min(y, bounds.bottom() - full_height))
    painter.save()
    painter.setClipRect(bounds)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if style.effect == "fade":
        fade = min(200, max(1, (cue.end_ms - cue.start_ms) / 2))
        opacity = min(1, (position_ms - cue.start_ms) / fade, (cue.end_ms - position_ms) / fade)
        painter.setOpacity(max(0, opacity))
    background = QColor(style.background)
    background.setAlphaF(style.opacity)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(x, y, full_width, full_height), margin / 2, margin / 2)
    baseline = y + margin + metrics.ascent()
    for line, line_width in zip(lines, widths, strict=True):
        slack = max(widths) - line_width
        offset = {"left": 0, "center": slack / 2, "right": slack}[style.align]
        left = x + margin + offset
        for index, text, width in line:
            timing = cue.words[index] if cue.words else None
            if timing and style.effect == "appear" and position_ms < timing.start_ms:
                left += width + gap
                continue
            active = timing and timing.start_ms <= position_ms < timing.end_ms
            path = QPainterPath()
            path.addText(QPointF(left, baseline), font, text)
            if style.shadow:
                painter.fillPath(path.translated(2 * scale, 3 * scale), QColor(0, 0, 0, 180))
            painter.strokePath(path, QPen(QColor(style.outline), max(0.7, 2.5 * scale)))
            foreground = style.highlight if style.effect == "highlight" and active else style.color
            painter.fillPath(path, QColor(foreground))
            left += width + gap
        baseline += metrics.lineSpacing()
    painter.restore()
