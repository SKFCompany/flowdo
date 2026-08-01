"""
Локальное кэширование фото рецептов.

Проблема: image_url ведёт на Unsplash. Без интернета (в дороге, в метро,
на даче) карточки рецептов оставались бы пустыми/битыми.

Решение: при первом успешном показе картинка тихо сохраняется на диск
(в user_data_dir приложения). При следующих открытиях экрана она грузится
мгновенно с диска, даже без сети. Если картинки нет и сети тоже нет —
экран покажет emoji рецепта (см. screens/widgets.py).
"""

import os
import hashlib
import threading
import urllib.request

from kivy.app import App
from kivy.clock import Clock


def _cache_dir():
    try:
        app = App.get_running_app()
        base = app.user_data_dir if app else "."
    except Exception:
        base = "."
    path = os.path.join(base, "image_cache")
    os.makedirs(path, exist_ok=True)
    return path


def _cache_path(url):
    name = hashlib.sha1(url.encode("utf-8")).hexdigest() + ".jpg"
    return os.path.join(_cache_dir(), name)


def get_cached_path(url):
    """Путь к уже скачанному файлу или None, если ещё не кэшировано."""
    if not url:
        return None
    path = _cache_path(url)
    return path if os.path.exists(path) else None


def cache_in_background(url, on_done=None):
    """
    Скачивает картинку в отдельном потоке (чтобы не блокировать UI)
    и сохраняет её в кэш. on_done(local_path) вызывается в главном
    потоке Kivy при успехе — можно не передавать, если результат не нужен
    прямо сейчас (при следующем показе экрана она возьмётся из кэша сама).
    """
    if not url or get_cached_path(url):
        return

    def worker():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            path = _cache_path(url)
            tmp_path = path + ".tmp"
            with open(tmp_path, "wb") as f:
                f.write(data)
            os.replace(tmp_path, path)  # атомарно, чтобы не словить полу-файл
            if on_done:
                Clock.schedule_once(lambda dt: on_done(path))
        except Exception:
            pass  # нет сети / битая ссылка — просто остаёмся без кэша

    threading.Thread(target=worker, daemon=True).start()


def clear_cache():
    """Для экрана настроек — очистить кэш картинок вручную."""
    path = _cache_dir()
    for fname in os.listdir(path):
        try:
            os.remove(os.path.join(path, fname))
        except OSError:
            pass
