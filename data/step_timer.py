"""
Распознавание длительности в тексте шага рецепта — для автоматических
таймеров в режиме готовки (Cook Mode). Отдельных полей "duration" в
рецептах нет, поэтому вытаскиваем время прямо из текста шага регуляркой:
"жарьте 10 мин", "варите 2 часа", "выпекайте 30-35 мин" и т.п.

Если в шаге явной длительности нет ("Нарежьте лук кубиками") —
таймер просто не показывается, это нормально.
"""

import re

_DURATION_RE = re.compile(
    r"(\d+)\s*(?:[-–]\s*(\d+))?\s*(секунд\w*|сек\.?|минут\w*|мин\.?|час(?:а|ов)?)",
    re.IGNORECASE,
)


def parse_duration_seconds(text):
    """
    Возвращает длительность шага в секундах, либо None, если в тексте
    шага не нашлось ничего похожего на время. Если указан диапазон
    ("30-35 мин", "3-4 мин с каждой стороны"), берётся верхняя граница —
    лучше дать таймеру звякнуть чуть позже, чем подгонять раньше времени.
    """
    if not text:
        return None
    match = _DURATION_RE.search(text)
    if not match:
        return None
    low, high, unit = match.groups()
    value = int(high) if high else int(low)
    unit = unit.lower()
    if unit.startswith("сек"):
        return value
    if unit.startswith("мин"):
        return value * 60
    if unit.startswith("час"):
        return value * 3600
    return None


def format_mmss(seconds):
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
