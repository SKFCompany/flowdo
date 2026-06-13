# ═══════════════════════════════════════════════════════════════════════════
#  FLOW·DO  ·  KivyMD  ·  v4.0
#  Новое в v5.0:
#    ★ Pomodoro таймер (25/5/15 мин, выбор задачи, авто-переключение)
#    ★ Свайп-жест на задачах (влево = удалить, вправо = выполнено)
#    ★ Теги (#тег) — добавление, фильтрация, отображение на карточках
#    ★ Поиск по задачам в реальном времени
#    ★ Тепловая карта активности (5 недель) на экране статистики
#    ★ Пустые экраны с подсказками
#    ★ Анимация выполнения задачи
#    ★ Pomodoro доступен из контекстного меню каждой задачи
#    ★ Streak счётчик с анимацией
#    ★ Цель на неделю (настраиваемый %)
#    ★ Трекер настроения с историей
#    ★ Почасовой вид в календаре
#    ★ Уведомления через plyer
#    ★ Повторяющиеся задачи (авто-создание)
#    ★ Улучшенные подзадачи с прогресс-баром
# ═══════════════════════════════════════════════════════════════════════════

from kivy.config import Config
Config.set('graphics', 'orientation', 'portrait')
Config.set('kivy', 'keyboard_mode', 'managed')

# ── Определяем платформу ПЕРВЫМ ДЕЛОМ — используется везде ──────────────────
import sys as _sys, subprocess as _subprocess, os as _os_early

def _detect_platform():
    try:
        import android  # noqa
        return "android"
    except ImportError:
        pass
    if _sys.platform.startswith("win"):   return "windows"
    if _sys.platform.startswith("darwin"): return "macos"
    return "linux"

PLATFORM = _detect_platform()

# ── Проверка plyer (уведомления) ─────────────────────────────────────────
try:
    from plyer import notification as _plyer_notif
    PLYER_OK = True
except Exception:
    PLYER_OK = False
    _plyer_notif = None


# ═══════════════════════════════════════════════════════════════════════════
#  EMOJI ШРИФТ — встроен в код, работает на Android/Windows/Linux/macOS
#  FlowDoEmoji.ttf содержит codepoints всех emoji используемых в приложении.
#  Дополнительно при старте скачивается NotoEmoji для красивого отображения.
# ═══════════════════════════════════════════════════════════════════════════
import base64 as _b64, os as _os, tempfile as _tmp, threading as _efont_th

# Встроенный fallback-шрифт (квадраты, но позиционирование верное)

def _pip_install(*packages):
    """Тихая установка пакетов через pip. Возвращает True если успешно."""
    try:
        _subprocess.check_call(
            [_sys.executable, "-m", "pip", "install", "--quiet",
             "--disable-pip-version-check", *packages],
            stdout=_subprocess.DEVNULL,
            stderr=_subprocess.DEVNULL,
            timeout=60
        )
        return True
    except Exception:
        return False

def _try_import(module_name):
    """Проверяет доступность модуля без импорта."""
    import importlib.util
    return importlib.util.find_spec(module_name) is not None

# ── Автоустановка STT (vosk + pyaudio) — только НЕ на Android ───────────────
def _auto_install_stt():
    """Устанавливает vosk и pyaudio если их нет. Android пропускается."""
    if PLATFORM == "android":
        return  # на Android используем встроенный SpeechRecognizer
    if not _try_import("vosk"):
        _pip_install("vosk")
    if not _try_import("pyaudio"):
        if PLATFORM == "windows":
            # На Windows стандартный pyaudio часто не ставится —
            # используем готовый wheel PyAudio
            _pip_install("PyAudio")
        else:
            _pip_install("pyaudio")

# ── Импорты KivyMD и Kivy ────────────────────────────────────────────────────
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.selectioncontrol import MDCheckbox, MDSwitch
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.slider import MDSlider
from kivymd.uix.chip import MDChip
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.modalview import ModalView
from kivy.uix.image import Image as KivyImage
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.utils import get_color_from_hex
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
import threading, os, json, math, random, calendar as cal_module
import time, tempfile, urllib.request, urllib.error, weakref, io, zlib
import datetime
from datetime import datetime, date, timedelta
import re

# ───────────────────────────────────────────────────────────────────────────
#  Масштаб
# ───────────────────────────────────────────────────────────────────────────
def S(b):
    sc = max(0.75, min(min(Window.width, Window.height) / 360.0, 1.6))
    return dp(b) * sc

def FS(b):
    sc = max(0.75, min(min(Window.width, Window.height) / 360.0, 1.5))
    return sp(b) * sc

# ───────────────────────────────────────────────────────────────────────────
#  Темы
# ───────────────────────────────────────────────────────────────────────────
THEMES = {
    "Роза": {
        "bg":(0.98,0.94,0.94,1),"surf":(1.00,1.00,1.00,1),
        "surf2":(0.97,0.93,0.94,1),"accent":(0.91,0.33,0.48,1),
        "acc_s":(0.97,0.88,0.91,1),"green":(0.24,0.73,0.47,1),
        "red":(0.85,0.20,0.20,1),"orange":(0.96,0.50,0.18,1),
        "text":(0.15,0.10,0.12,1),"text2":(0.58,0.44,0.50,1),
        "div":(0.91,0.82,0.85,1),"nav":(1.00,1.00,1.00,1),
        "dark":False,"gender":"female",
    },
    "Лаванда": {
        "bg":(0.93,0.88,0.98,1),"surf":(1.00,1.00,1.00,1),
        "surf2":(0.93,0.90,0.97,1),"accent":(0.58,0.32,0.82,1),
        "acc_s":(0.90,0.84,0.97,1),"green":(0.24,0.70,0.45,1),
        "red":(0.82,0.16,0.30,1),"orange":(0.96,0.44,0.18,1),
        "text":(0.14,0.10,0.20,1),"text2":(0.50,0.42,0.60,1),
        "div":(0.84,0.78,0.92,1),"nav":(1.00,1.00,1.00,1),
        "dark":False,"gender":"female",
    },
    "Мята": {
        "bg":(0.90,0.97,0.94,1),"surf":(1.00,1.00,1.00,1),
        "surf2":(0.90,0.96,0.93,1),"accent":(0.12,0.66,0.50,1),
        "acc_s":(0.82,0.94,0.90,1),"green":(0.14,0.62,0.40,1),
        "red":(0.84,0.16,0.20,1),"orange":(0.96,0.44,0.18,1),
        "text":(0.07,0.16,0.12,1),"text2":(0.38,0.56,0.48,1),
        "div":(0.78,0.90,0.86,1),"nav":(1.00,1.00,1.00,1),
        "dark":False,"gender":"female",
    },
    "Ночь": {
        "bg":(0.09,0.11,0.16,1),"surf":(0.13,0.16,0.23,1),
        "surf2":(0.18,0.22,0.30,1),"accent":(0.17,0.42,0.82,1),
        "acc_s":(0.14,0.26,0.46,1),"green":(0.24,0.73,0.47,1),
        "red":(0.88,0.34,0.34,1),"orange":(1.00,0.60,0.10,1),
        "text":(0.91,0.92,0.94,1),"text2":(0.48,0.54,0.68,1),
        "div":(0.20,0.26,0.36,1),"nav":(0.10,0.13,0.19,1),
        "dark":True,"gender":"male",
    },
    "Бронза": {
        "bg":(0.07,0.07,0.07,1),"surf":(0.12,0.12,0.12,1),
        "surf2":(0.19,0.19,0.19,1),"accent":(1.00,0.42,0.00,1),
        "acc_s":(0.28,0.16,0.04,1),"green":(0.24,0.73,0.47,1),
        "red":(0.88,0.34,0.34,1),"orange":(1.00,0.42,0.00,1),
        "text":(0.91,0.92,0.94,1),"text2":(0.48,0.51,0.60,1),
        "div":(0.26,0.22,0.16,1),"nav":(0.10,0.10,0.10,1),
        "dark":True,"gender":"male",
    },
    "Океан": {
        "bg":(0.04,0.08,0.14,1),"surf":(0.07,0.14,0.24,1),
        "surf2":(0.11,0.22,0.34,1),"accent":(0.10,0.75,0.95,1),
        "acc_s":(0.08,0.22,0.36,1),"green":(0.20,0.90,0.65,1),
        "red":(1.00,0.36,0.36,1),"orange":(1.00,0.60,0.10,1),
        "text":(0.88,0.95,1.00,1),"text2":(0.48,0.65,0.82,1),
        "div":(0.14,0.28,0.42,1),"nav":(0.06,0.11,0.19,1),
        "dark":True,"gender":"male",
    },
    "Бежевая": {
        "bg":(0.97,0.94,0.89,1),"surf":(1.00,0.98,0.95,1),
        "surf2":(0.94,0.90,0.84,1),"accent":(0.72,0.48,0.24,1),
        "acc_s":(0.94,0.88,0.78,1),"green":(0.22,0.62,0.38,1),
        "red":(0.80,0.20,0.20,1),"orange":(0.90,0.52,0.14,1),
        "text":(0.20,0.14,0.08,1),"text2":(0.56,0.46,0.34,1),
        "div":(0.88,0.82,0.72,1),"nav":(1.00,0.98,0.95,1),
        "dark":False,"gender":"female",
    },
}

C = dict(THEMES["Роза"])

CAT_ICONS = {
    "Работа":"briefcase-outline","Дом":"home-outline",
    "Личное":"heart-outline","Покупки":"cart-outline",
    "Тренировки":"dumbbell","Семья":"account-group-outline",
    "Учёба":"book-open-variant","Финансы":"currency-usd",
    "Прочее":"dots-horizontal-circle-outline",
}
CAT_EMOJI = {
    "Работа":"\U0001f4bc",    # 💼 ✓
    "Дом":"\U0001f3e0",       # 🏠 ✓
    "Личное":"\u2764\ufe0f",  # ❤️ ✓
    "Покупки":"\U0001f6cd\ufe0f", # 🛍️ ✓
    "Тренировки":"\U0001f4aa",# 💪 ✓
    "Семья":"\U0001f46a",     # 👨‍👩‍👧 ✓
    "Учёба":"\U0001f4da",     # 📚 ✓
    "Финансы":"\U0001f4b0",   # 💰 ✓
    "Прочее":"\U0001f4cc",    # 📌 ✓
}

MOTIVATIONS_F = [
    "\U0001f338 Ты сегодня молодец!",
    "\u2728 Всё получится, верь в себя!",
    "\U0001f338 Ты справляешься лучше, чем думаешь!",
    "\U0001f31f Продолжай в том же духе!",
    "\U0001f495 Ты лучшая — и это факт!",
    "\U0001f4aa Каждая выполненная задача — шаг вперёд!",
    "\U0001f338 Маленький прогресс — тоже прогресс!",
    "\u2b50 Сегодня ты сделала всё возможное!",
    "\U0001f381 Ты заслуживаешь лучшего — и ты к этому идёшь!",
    "\U0001f4ab Твои усилия не проходят бесследно!",
]
MOTIVATIONS_F_LOW = [  # когда задач мало / настроение плохое
    "\U0001f338 Ничего страшного — завтра будет лучше!",
    "\u2728 Даже маленький шаг — это движение вперёд!",
    "\U0001f495 Позаботься о себе сегодня — ты это заслужила!",
    "\U0001f31f Не всё сразу — главное не останавливаться!",
    "\U0001f4ab Иногда отдых — тоже продуктивность!",
]
MOTIVATIONS_M = [
    "Дисциплина сегодня — результат завтра.",
    "Держи темп, не сбавляй!",
    "Фокус — единственный путь к результату.",
    "Контролируй день — контролируй жизнь.",
    "Каждая выполненная задача приближает к цели.",
    "Сильные не ждут настроения — они действуют.",
    "Один шаг сегодня лучше тысячи планов на завтра.",
    "Работа сделана — значит день прожит не зря.",
]
MOTIVATIONS_M_LOW = [  # когда мало сделано / плохое настроение
    "Даже в тяжёлый день — сделай хоть одно дело.",
    "Перезагрузка — тоже часть стратегии.",
    "Не каждый день будет продуктивным. Это нормально.",
    "Завтра начни с малого — и наберёшь темп.",
    "Отдохни сегодня, чтобы завтра взять своё.",
]


def _pick_motivation(is_fem, done_today, total_today, mood_val):
    """Выбирает мотивационное сообщение на основе прогресса и настроения."""
    import datetime as _dt
    day_seed = _dt.date.today().toordinal()  # меняется каждый день
    # Определяем «настроение дня»: плохое если мало сделано или mood низкое
    pct = (done_today / total_today) if total_today > 0 else 0
    is_low = (pct < 0.3 and total_today > 0) or (mood_val in (1, 2))
    if is_fem:
        pool = MOTIVATIONS_F_LOW if is_low else MOTIVATIONS_F
    else:
        pool = MOTIVATIONS_M_LOW if is_low else MOTIVATIONS_M
    # Индекс: день + кол-во выполненных (меняется при выполнении задач)
    idx = (day_seed + done_today) % len(pool)
    return pool[idx]

REPEAT_OPTIONS  = ["Не повторять","Каждый день","Каждую неделю","Каждый месяц"]
REMIND_OPTIONS  = ["Не выбрано","За 10 минут","За 30 минут","За 1 час","За 1 день"]
MOOD_FACES      = ["\U0001f61e","\U0001f610","\U0001f642","\U0001f60a","\U0001f604"]
MOOD_LABELS     = ["Плохо","Нейтрально","Нормально","Хорошо","Отлично"]


# ═══════════════════════════════════════════════════════════════════════════
#  EMOJI PNG ДАННЫЕ — встроены в код, работают на Android/Windows/Linux
#  91 emoji, 32x32px PNG, сжаты zlib+base64
# ═══════════════════════════════════════════════════════════════════════════
import base64 as _b64, zlib as _zlib, json as _ejson
import io as _eio, os as _eos, weakref as _weakref

_EMOJI_PNG_DATA = (
    "eNqcm7eO9OyWnW9lcFIKoHcCFNC7ovfMWPSu6K0iARMNIMXKlCjR3ekSxO+MBjPJSf5OuqpRdO/ee61n"
    "sVn/9W//93/9z3/523/+p781AWs6J6RJ1ci8P4br14Jfva+4P2+ZimPi9xf7FL8Fel8oJdQLduBgyBxG"
    "KXblgRPJJXIcZYbTzwd6frFg2tBW9sbHZcZRYBlX5obGjiW1TldW+CqnezFVJ3FK/wt7bNIlu+JqSeiV"
    "L5+4063vAo9NWx8onuLPojGGYRpngFSUzvDtH/L5ob8PSmUmrqfucKyqmWekUqYgGBU3WuvnKY5OydMC"
    "xmLWx7D6VbI19oNYLqB/2CSMiWhE9/JLVI1EriQaFgBMv4dLJMu8zdJj7OWGOvYZ8wp0zedzV/AOreqT"
    "D7hvxgHVpLL9iWYMWTqAaJfyzqUOLvdjRsHNhmwZAlv/NGyBtZ3TA65xsIjAKX/fG7eyJ0P6HE5Oz5a9"
    "OTa9XnBHjfQdWJ9H6md2qYzRKEjiAN9acEVaM6cJvoB7DXr7roKyfSj+bNAAB1lOQ9GisCfjtct2YUmf"
    "xqqqusvxBTYQXSYY0ExpPBXR+ekkBHaDkwEl0a3xa8hQuEzS5d9IVKGQohSCk1menSsKxEqvN3YTjw8b"
    "M75+yxKa50p3FKpnaSMQqHfimj24kQnyNDBZzo7WrFxXJaPVRBDvVB55qfAD0u41msMQbqSvQNImhhmn"
    "O4omjIzQrcipuyUooesgSua6M60Tbli3UtS8bC2KmFch2Dcd+fH30XeVl0hrJPVyQI0QuhH41L1GZe2P"
    "KQhrw4ang/o77wmjVOTYqZhDMyfMOFScdchw1ZQxnX1H5Tx2RC5JXDyQ6sbamyx+XxBu8C168Msv22pH"
    "2tassxiVoyxOxNVWscprPSs5WE8wNv8CVE+3fp7i6engbvu364Y1WosQ+sEOmt4gMjMzYRztW9Prm5G8"
    "1KvILCD6Gn8sGWamQm85QHHePWODxIutjXxMTjqYgcEwrxVCyok/ocxb3/PMyLMUw40eJygBDBC0jAnG"
    "8AQhr2euK5iv2yv0icue6jvkP2ytK9vg2hsn7maWMlkGvUuox1+BPLPCVLhZiy9lPcwEuRKTjK/+h36B"
    "5zNuB+SNsrEJ+APTazhdmiJiusPdo91XJ5lDPkVnec2OuXv86r0qwAIR5lhHmsbVze7r4xjx7VrQjHo9"
    "vtmUBB3PzHu1mFp5EZJYjGA72Apv6I6ootsBPttpLhi+tHZhPpVGFzueicUbPUhiu3Gq4kmazlhAL0Lu"
    "WC340/8CO+s6LbZ7BrW+TluDbSi7MjR0LvzV6BtdR33pp1StN1M604UNsy6qoJVJyZlczxaGcQD5Xbeg"
    "t4daCvpZjVPTHPza3NaKsMOVSZJJ4IkxElFCmc/j0C2e1MFXZyueClptbyldyCKt97dPJONJkwvXA4Ah"
    "D0j0dbopEs9KodgnCXyRvJVz2uYWxkXtb2V8vUpw6sC1J4UzwxVPQvOzBJCX5fsGiT3pX8aVMCUNjNBE"
    "FhgzhAH3VDmLp471K1OZsaKitFtEKi2sopDvoGRzG/js0sgNxdX1l3/bw5WoKD86CdrLI/2AYzMD0FeO"
    "tjFc5lock8XJHA78haxA7DYvNE0mBBKFewF6N21UMV2rV5i0AtxlFafPqcjAKVeVZGz0aRHx0S4DY7eF"
    "Jiip0Yy4jqp39i5qGydnMLKK9bVWHOyfkHPfNOuEq3PrGJdGPFBCZJVOHRD2WeZml2cjm6oNu7JfUZGF"
    "83ui+7F5s0rAc8Z+RW/YT8f7Ij+5bgxuHj22lALmV51ci5cOsbIG578OoOjm4u/NSHHQ2Nk/u70Uwtdt"
    "XpQ8bXQd/CPR5VLrMRYXrcIANPXht7y1gJOhkw/+u3KfT1s7kF8ZKljvKncdu3SDvEVDDIt6dq53trwx"
    "+RBzujBa6pyGE0SIdIm+WP6QfYFa10fLrSFZnFOtz6r589YO3BLHFKAsANCRgS7BZnB7Z76sq02bQsSI"
    "Ns2kOrvI1me75MsfOC0J9NSf/bE6gaz6mhCezQWeUd7ZDja8Eot7mukvBIVU+cwxNvWxvxQ5Iwvi996A"
    "0qRuOoVK/PmFW2QNsF4d5i2KqzEwX2dn6jlqiXz7xtQwiypOFWNvQ6UVFt3DqVdmq/Fgvt77uxTJkEF9"
    "rQyGXemKk2tC/3nPmKFsWIStDngsC8ccBGk2sBI7V6NXGy710cxlxD8qUGKgiytuAZuZxxBSq/0OIo6+"
    "ryS/etH3eIhtRCB/7eB69U6jq84JpHVO9jrHCreidOqXhnNMfup68cCANMvh+26inWknVj++KatTiaWQ"
    "VFc0mGrQs3hQyr99ITm9PDejxG0+hyXihCQJPaDh0g5zq0pKSnSh3ZiWQ0Tiuz2qkxE/4yWs6wbSrr0F"
    "tNv5+8LYUgKH/AO6Jty+l/Prjw/MaKennx2nYPYWxs9OYjQ+3XRTcLZYB5oXF+TaMdGTbU2jeIOL7aum"
    "BTxafHxg0Kp7NdGcynN0AvKCQg6CeLt6VsdV2AhqAR9aLXI9ujZLu7/FzAuGIGkPKHHZywlCVn2GmXnl"
    "EtdmFYMCBu5Z/8ixRc3nyfJgJISP68kzgOOXAt2vGy+8cq5eS2yMkJxTXEfJ5pdt1pzTXv4KYiuljVZ5"
    "KtzTsVrNXzgcIhVUpY6iIa1RAulprmbckfyw2oXEtoailQ/oRxM0Q0DUFqO4zdStmWGul4SDR/2Kdx0f"
    "pO9w2h7btDM1SkQYM2MlU878M1qK0CyaxEG0tuKSXpxi7dIMAKxWpk/fEDgwu7TP89xHgdIf59CuKWl1"
    "QfkK6KyK/iRKkosnTOCI6sGgrsR2ZYy2R6dgJhzNqIx8euOiexrrUtEaoCiXQHLnObr+IQXY31gxZVpE"
    "Ey6ymmeX8lgdNaKGhhI7rH69L2RKGNNNGfxH3u8T/KQEUyIOTMfDEaIxOhHh0GWJY95WSQ1CsH3cy+zF"
    "3/ZJrrXS9ZYXl1HG6eoC9GOVrDyaB3acljwioRc7uxSWCJ0eNIvMTBOHQrNLcCR+CHX5XYPCsZCCH0zE"
    "EJTVmG1WYmzO6ufKohty8FMIWiBDFjHeE2cydtbfqVvoRa9zd3vguL/9p3/6w+r//FdYHe3+jdWRP6we"
    "wP/G6gVBv9XJrzMYKkW+hU4q9ERrAHW+JFEvv6EBTa340mifjrQ0rN/4kpjcjTFkCAck3bQUgcO6/RCo"
    "5MAjiDD3WAvu5xPPvMbYUheKDP4LfvhCmki6ls8Es4JITx75scxyz478C/zQKARmAH79J+OmjxWTIfmE"
    "PTrAlvhiLxwHNon9cnxRPif4TH5XELtxFDBeKnlwhJ8qayKNEjUVFjdpv6hcx1DiOjLTex28slnqMabh"
    "tEfxh+CBldLSPpNXIp/t9zgQCwyduckcPX/LwlQap3EloElSBkVLOpBasj0BUtz58LNxjrEhVVfqboJV"
    "SV1V43zPkKXxJYoaEiDp/QecxBgLie1Npvd4EqbP1UjzFIBnebpeSirBg714TS1qQtqGoirgbN2wvh8o"
    "w6M1DjPXX/I+Y73sC4wmM4z3oIdq69nuTjMOZe+aXbcA9F92wccPhtGFuK/evqvGaS7ptTq2y0Clqkq4"
    "+c1UcQTqlfyuRgGR/sAgHE9og1hdpWVrCxx0pDRjeqOql4ZntNq3htainrtraTA3m+S4UGcYdYtvxld+"
    "Lbt9GStgJsEJgs8laUGEUuXRPhQAJAEg46NoHgqXYg9Wt7hojk1x/CwjJiiNcLGJC5LrUjtGYZmuOtYv"
    "Snl1TY6uuhWKIN18c7FhbQ6bgxZ+abUfsqdV1WExPubfcr7TJ7ztkVkpKt73CMA+nKRr17KmLHGF0lx+"
    "sZ+LJEUMF7QcQvfr8HlR3Rr6Tk+EV07Umx6Cz/gGNxT+FiP6W3V7g76Ws32/zeSVMYsAvM8iH0EZFJHp"
    "mbZgjPgMtlnCzLiQ2DZFq09a+fDIfSpsiSQlJ1RWNN1HJcJirl74hvO0Kduc/70Lsv2WCQI/KBxNGTFy"
    "757E+xA5ZdBPL449QTul+JXCA8c+sCIGCHC5sWFwfFwDwrQ1sTYOBveK5JTiN7TmMt1+y7IYDCRFThuB"
    "aM0nZNfwVoOxmLgNeo519PRMYEBMntjMfnaVWD9X5AEsqWZ1EkTecb0C5VIxgLEY26Ld913BvYF5AhHq"
    "Y4QvXqGRhiwBSw6+pwLuUSvagCgMmaztyX3nh51XTqkc5l4qf0wBG472yMquo9yXUZ+W5YUAGC7732/7"
    "MfWLRR9NEkGKuHSqNAXbvwKQurbEIRf6p9YFlNzdu/oOJE13kPDTZQysHsCl7mtggXrK5qoNHjt3VlV1"
    "caa28ZAQ9ChEIczZ5m7q5cSExK7H88GQc3//7DmDbsuRTtGex+COdm/LG6vQX3JVBd0+cA+J1Kw0eSaQ"
    "gnK7Xt4TQHWlqLxVzKyVIjtpxqyHSPWRqu6rNmE8fhDSysphfW6K/OgDbZ4ygIjIkJAbc6pttNSWZT5f"
    "lgrjiSTxnt3SuevGPN7fcjTYHcNQxGgIaxypG2tlZ37NXBoXENzeFEDBGfr9+Rvn+nbnc7bDXvtnWKtG"
    "7PaPvGXIaiszNlop1kcn5zTJofTtWSt2w70xjseaMbcpJxCV1cDIS0S+BUSWz0eUVm9psp8oqfbtJ47w"
    "ZTQqns7fh5vGr6MPkspju91K4ebEsGIevfTp4E6IVch2KFX8HcqEyv7WehPhrroO+A19dakQCw6UOjFF"
    "NAemqD1UpcLUEKSh6GMncJkXY1ibOayQiofcJtmHk0yxasKG+nWMu6ud6aaJQ7vzLPTh3Nsmz/NHOCI3"
    "8wpISjx0n+VIJRBpaLmuDhn5U+tac8HDTdQPlrBH8OLwROYvUpu9DNqsbfFY1DHJdDaJqXo9rOZdnxI8"
    "LFtLWToISqFjGiCOIyOiM3YTrnDTcypDNY+tQol8uQc6oOvvZ8ogXDV9uN5t0OzRVrq46faIMmuZd7zG"
    "4clOacit1JJ/8wQQ0Jz98PHtI9bPDFEPzGuIDmFywLz1ljSAKZhu2do/jRXx3PmI1vIeOHsry3s7CP2C"
    "BZc6KFwSHdmc9ni9OcBJ3BuQw1Iy3kfhV0/Qxho+fWss4KCl0+JVkcBmbFO1L71PyBsw0Q2iaZNM7px3"
    "lMuT4jxyeR19cFh4q1rFSeT6a6yCYmynlQ4VmM450GIZDv3kZ3x3c6FNzx1NgIH78jHQnb7i2uTPMuis"
    "CVAi37KN57inliB+Yi4w4SxO/Z8/6RVsFC/WAMdhIJrbR8rjv7lFJ1lK50/C/lG3JD1pO+zAmSE0uIJg"
    "yF1biM/x0I+BZNfAbEawKIeG+NDJNhKuW/+cnKsgTmWFU6FLQctQb0jEpRrdFmu43JsMdcJqTuJwAZWT"
    "vF3X4zvbkMzJL7V6p4p+wRqzcP0CmyyDW5V+McKDBvAiqPdy6f2R+2/3BCqmKr4JOBkF6p3exdtOjVnk"
    "YnfTG2aIp3v8XXqCfCcw+uxSu8fb9PsQbv9ZLbI+6afQXr7CrPapaXMETdJL3Pd6vEUADNHMr2e0+IL5"
    "os3gZUlcmKoYSFuxwUAEorAGZxBIym7PYK0fmtkguR6e6bTjJXBx40YZb8PLWGEztr6CMXB9zET1KeV8"
    "EcVt+3MfQH+SM/ZZyBAWvhTXfSmOMs35e4qWiLAT0MC/UvaDwnw+d2xHGf/LyWXWg2QC1f7Gg3VmOWE7"
    "pjORGwlz10rIayFriB9lHAS7gza7KicH2gzN5b5Ci/aaEwPX57UQ3SkRcih/6Dpbz1KX8mZS3vSdqC6k"
    "zw8YDc4afiQc2CQZ6K35Zs1FdIhp/mq8xPIkovB9KNR6Ms5LpQC7IfhUv86Dw3gDsaPAudFgue9jRO33"
    "zwDB5pgZCVujxZTQQEp/pDRnaDRJCWzXbDVOaaBUQ4re0+8NCMoA8LOi6WLdxgbBiVWgARNOwz14p5ab"
    "L77pLnkXHGDSBp8URZDeRchXjMoc4a7+5LqKWFmHZg3fk+/zzD+BMotW4TsHBLa1g1HrLeMiUP3oNS/D"
    "foG3UAy/VOHoLv8q4MR/i1NV89a1nWeo9zgdOcC2Y26M8rG3SpDiFdoDE23O099gRUuc6dKL+OEoJ7XB"
    "046Tbeqqb9fzhBbsknoP/GikQaBqeNaTtw8nn9lvilxt78uQjzKdQ0AxYmW5fAZlSYkpgyJAyKq7uv4d"
    "+l0/MB0N52JF+S//Pyv8t7+SFfD/cF+/DK88d36yRYFHThH4RmbHBqDEuqT8Foe0nnMnmzj9eOo1Ju6N"
    "XefGpQ3OG1e4lKnGzyueuqGPWmW35c0mtcZtp8fp19ic3GSIitucqycheYBGeYES6EagGUUeVAx6efXI"
    "Mwl2+HaRJVDiVg6WFHqXBiDwHyasJcig65M71zzry1N/VeS3ymwiFVNgmPwA0yC1BYWXLBV5MNQG5/AU"
    "4AZadGUGsNz+bRg5rA4wLsO8/Ilot2T6I4IV8C38ZDi1+PluTSi/qrkPy17KI+CAGWrRDY97Rbl+SXb+"
    "17xQkM0zHoSmvUsVwVFbkgMF9UefPOiJUvJbN9W8CncYf7CHAWK7w9Rofbzp9VUniE/l3vYOV2H9W90z"
    "dxx7CGoG3kTTJwmM+TXd0eGmeOx604cFcbBtX3z78BVaG2t8orDEM5VZaEM/B22B1Ock8ZHLpIynXJzO"
    "nIM/lxCyjO+Lj8uuT279Mu5HiF++GHhD0QCW+aWKOUF47h6ibg3fM5Nx8n4KK9JoreacSvF+Q/6x0JiP"
    "NXoSvyFOj1GfInvCIL4jOinlP0fdXmwp1IU9uocZtdyldAUVR/GDXs1YhVCTzFEvAUXBRsuX8s6cz9PI"
    "No/pVjMZsn4WWkF91BuAu71Gix6/hlGxSlw4TmLtQwcg1sksPWTUu/EzRW0zSfw010PUNPEtUjZDMKJ4"
    "telzHGGnikYBWFG5LB1xfMO1B4TUWV1JpzHu3Sm63dsnrn4Nl8XP7ZWLxx9iK97c1mayYyrxoAW7sfy6"
    "FdgTo3AlUJc3ZyPvKsytlFgYAtjvjR7m54Irp26F8H4DKFqpH0lYqc4zkUxl6ErArLvg5qojV8VrlTfM"
    "geLikzbE8uDOCtuvf0MTdB7Enu7pZwYW+qFTwbDjNahc3I9ftkoreFcDybrmhpQp72rmqqd7Kh3Xcovd"
    "d/ljM88SXUhWO/MCAw9ywEC/JJM6i0uq38PPmQX14fMbIc28jC5t8kz6RTl31Nln1kBxpJ+mHS/5nXz8"
    "eWM4zCoiq0B+54e4d/ZAMezuUeKrhPFGFHzFyz7DnvDauu0t3wfKaJrDS4n0zTNBCP+pBG9UlW7up1Mz"
    "F3V7DzR+W/uWyx0x7aPRe1+LUCAYTB6KsiLPG0ZS5HKM6jsHrIwCEIFynHgS8x0pcJogxcjAHTcSKG+t"
    "vjHIrRNvsebKxcuMdfaD0mAcE9bDft5MVzQm43ufX904iHd8xt9DLb2WEvQ0JmtfCJZ5xzglj+zwxHEV"
    "8dJaok72HgyPl49GNuuIfdQ7aUtQjjPx3hocqqZG0BW/x5f8zgy0TiqNYN5iccAcV7iYso3tWn11WF4p"
    "qa3qlbmvlzPvhNCnDHAgp3GpHilDmJVYfkZE5FkHTn/763iXb9eT+OH2EJn2rLY7zm5khQvcVln7HTdJ"
    "LS6wFsyhg79cOu8jkEkZyo9Cv7p/O/v2BOPdaTtSvPqAVReIQJ8hitR1zU5U3Qawp3JdvKlpTwcFH7dz"
    "pUehY+QswfJyr1xbBDlDkP0TMvpwrj5ndFwez2d7N2WSNLJvuGL9U9cXda+4eRbbr0RBCA9H5wZF2dnG"
    "uQmLehbLxbRp2y7TnHNT1EytaX33N92VydbtTXHLHyK0OgkR2tOyXs9TLaue1Qqr21rgGqlvwl9zJyy2"
    "1WqUzW408Wwveo0RvMwrqaGUTL8TUbRbLOPs58HXc2i37gOjRgxV5tvYVxuAoslNOQvflCdggKvyAIw1"
    "Ifxjbt7h+Dnb72icG9Xxmvaji/s8pd8uXtBuG1L/CxVdPf1yeljUN+cJalDD1+yx4SNbugCJgZDIauO8"
    "1Fpjp1sjow5MayB++bMQmiXbIx/+ek7dl1gCWqSptimceqsjpPjvnZCb9l6ZHLYUyjGkiH/udBEGw8jF"
    "ejADe29rU5/oNj0v3DyjpHRE3TWPKYIBTXYvmDHPSn4sRwLyHya5Kto4c/v03b3ZQUGigFhBhQn1r1Gk"
    "BMDkQha1s+GlGZvxoYcYk1jwkcEl5a2QravKiIwOTjWqQFItXJeNnq40vsk6bJ+PaYKU9SSYMUPzMzNe"
    "lngBu1TRB33F4nUNn403D9Ok6hHJIJ3+oBrYZqbPNW8OQjkLan4Q4XKV/ruySH3D4F2YQnoFnBvdsD73"
    "ThVbAvnyfLynPSymP/szlZidhx0ch4/0CpBY3eXEdhBzi0nmVzBJHx6oH1EXxigrgsreTrdfALJTE/V3"
    "m1yCI2lFFCLqKLME2Y6vHwfNmrUCzroFjpvb0qTenfAW/lSAqfME7ewu0PJ3ii00QolB1Y3Zo1y4Qln4"
    "O/olrqDePIiWdwLzrcksle8/dsgfO3axkEV8/7lOFpSuH8GmyvxavQ//oHxJ73EMNKI1g+2Twfrbytk2"
    "puFLg3Na+NzGupDNW4QKASIuaDDzRxTuZGhBynC/J33vzcLIUVHJxZG+PZu0CInn5jH0Rkics7dgh/al"
    "TDE+1ZrLy4oYinNoG/Nu8uXyxZFpGVwXCPf+pM3KaPqZVaCQw2y0q9eEc5uoyUaiHnOzLxRVSEqFRGD8"
    "5DNctB4Kvo3O/ci0IDON/HKHg/7WeyMQapTEbyQaasrb9/XKKferAc98AgWJPnoY/bLfhb25LRn2d66A"
    "+M1DHaqbgp2FtX33Qr32+hP9nk7TqPKzIRQ+5veBfhd7WnfyiT+HfP9AOkLwb4QGZBQE9VcMSN99sxub"
    "Cq5mv8ARJuf8GTGWv0NDaCsHI5143YfJ93o8lhuKxDwS7qIvbkmo9gPRPWTMSyGNRbxJ9Qdb2yITw6GF"
    "2sF6veFW1+oqs6pBkKtxZh2qMbDLTuggwyIBegIVGuodVibkP/SFOiRLfdOjvS4C9/FPvFlW/OcE+D75"
    "TjrSIW5yp7Cl+ht+W0PMuvjnWEo4vZjQLNbx/OHZBQTwg2mJdrOcAsOHKEDiT7AxDnu++M8XwC8I4dx9"
    "tNF9JGJLEoXxBOxKCRWI4xzMS8Q5yEuYKk1LbwnMh96r+Qeo8kGCJHTVNvypPz8tpb/eQn9+rX0ivwQf"
    "k+IZL7rIagmTomHSH7giGhOTnCOsfw+4lk9JfRy8SgH8VbUZ+ke54X/8ldxQCP/+P4YifDLYkWULtAqS"
    "LMjod2yIgGXCs13Miouc1I1a4rmvg46i6Di+AFltz/i9P/mLO9mBIWgqFAbu5n8IRpyFrz3XTzz37tjZ"
    "mt99xsk3UqFjmYDjB8XNfkcU5hsJbsQXPMSvfAqebSLer0+XCf/hz3ENeLvyMqCPLp9+YB9ZGBqBzJ4X"
    "Z+4Dp7BHYku2Bp2MlRccOB+Dpgfrk5T7SkyvWCvZcmazsVtLSSlI+QR7kNoUEF/GUDjVfTzi5p9c382A"
    "r6G4rdBwIitbceylmZPJVpsjZLZYyjABKzgyNdLg+JMj8cr6w1gKySDCb0WEal+xHJPAUgghk+h+JG6T"
    "9y54oMtMIxcDM2DP2wv2L6Vpjy5RLG7prplbVmANqS1H86YMkxVXc1b4JKNTw8rqYQmrXKM2at7waEpb"
    "97jQ9pQh8Xi0RmgUjb5rVZaoyHqLMFQIInXsd3J/RBRU/zxKf5MzN0mc4uih8sKAG/Zcl159QPgaMF7E"
    "Fv1gm/NRJSuWA7rIHuU1PLgc6aNhLB7RFRo377BqBvqgwLA+BT1NNuT7gbAkEVO/tidytuBmLUmC9VdT"
    "61fUum7m2NTdhrFAReLJJBlHcnGVPPKRm8CTHESGW4LTya9teW4FGoAV0g6wv4L3+N6wMQKniIwg7KOY"
    "uwyyduOs9Lk/da6cevuiNvNIfwuxuckiDOcpQrcDx79wV3BRblDVJsvFjO+kUNEOatgK0nHby75czAm2"
    "/hFWxsA98GkoU/eV0U99Kxj5uPJlQkCoWsbTtoXIjQt0AFQOrymY83v2Nz4Dk3ZlK9qYZZpKLvrylTQH"
    "tx5LZ6MoAmNzey/Z0P7EfrLYsvkoyaD7uTPfa6PET3tIPNlrrJ35LrSPTwU1R4n1QmDi6SbnNQ1/zub2"
    "gvRQ6ypWPhOU5eazxCiCHPc4wepjaBkvjGJffGzC8EVHBmkisD120Dt0QYUhbHYo8VUt8AGcmJpRZEW/"
    "9xgoYWchW/2S80YCGx6Ikk44myjzk0H0SlvIuYabP+O4MVCgXTiQPf580RaxBbIdiRGuWLHiv3+o5cB3"
    "9CMa+CZghsVNwNta/AJgswUl/7stqUO+q82uv6gkdJP+FUI9nfZnx2cokIMV8fpXddMrfwjgGY2n+Zka"
    "/Ubp4wG+EUhQDREPNimPqQRpREIGt0LQJ3Dib6KDq5/pURvZ2uFJaOWOkixBI6CHxie3Hcu3W+Qub776"
    "YqS+W3g9NHbOPvGjg80/WeKa0OK2N5D/GmRIwvKTqjNBKj43vULW6IFTUcGqWidUNS4fcmT/3bKFfgmw"
    "A8FDJfLwK/OG2XEaQPVhaY2B6HLe2ueiGVwikWdofL8A6kPoZnYNc/IKHUp5dTlaNKx+OpD519RueBo2"
    "Kk+Wb7Jzq1QUTZfCTyw6ijRuWNt566MHKy/CSHw1teIFw3Uocih2q28XHlzRvdXp1ecmx57QW9ti5Qq1"
    "Sw08nkL9oLmSGqJ3a775+c0wXmE7gYjCnWUBDCRYrH2gpXFVYpxWIPvt5rAshffwcx9VreRRjWKHmpgF"
    "+Xj34x5NbzNWegv9nE12PZvo7efMCXjqrm4LxvIW0lDzZ1Ta4PbmGYr0JvSOZDrngCN8/LSlvgpvAPOL"
    "SjFCHldoAuHdrZvYsj7dfydqShVdvJ5iRsmjb1MiXHyC4hd+/EkH9KGBDYmkyT2+NIVnw/CKJu+5CYyt"
    "N7uRGnaHlhC/oVxYo+TTzCv9Cy1NNVSb8vPA6jkn/VB+eAMCLSY4OGbcYkJLV99GxmpDt0rsXu3r/gCN"
    "dtnwTRsg2ZIElJROJoU5I5QeJgPJkRa0ERGKcW29FBOGMkeNzRifjfkOnhAdSGC2k+uxT9Lxdsx9v2us"
    "htZnoDCK/wbh1+CmGs3Hj+vGxaG5ks0x4WyK1IhQxpcG4YdsZ9Ss2IpCxg9Dy/HwwaAb6PornmeHIb6G"
    "5rrVZMa1imP6mvHHhTaH5E/Itq5kCLGeD0mCW4UxYOJjXOdfPMVJ2TBAM61325Y87sX1XnmP6W7TuLWi"
    "8M1QSBqZqz0ZPbeANP/JKZgLqD204sh7PzkY5Do7S6sn4AN/wNhF0CI0IzzrpEEau0kMv0x1Owj6UE4k"
    "sgBrVn7UEalx6J2Bzx/e/Go/3vXajN5rlEJBly4bmkF6m1O+bsuztRgr0omIelaUv3V5Wghpf+ytNerN"
    "Xf2vRKUbK0S/3WjQdX456mpodbpbyhAwHkiIf0+Qgm4XgZtDbwHqMqyBybymF5f7DSgiPOREoNEzaqAx"
    "qs5ruMZvo7xo5bPSHwNMeatvhRDcPpGFpYr3uF1OntqnUFU059Iam7u3k2SfoH/1UQbVmhUaDKbGl6XR"
    "+/OQjJ0nFrU5k5/XV4R8DaAorWJ50u73NYnGVsKLohyh6li/Vy02Y0zpw6spalEp66DfOv1CY0CXR7nN"
    "4DZHZD9OgPuE6WXQWDzR+ZTAOngW/reRv0UP4+90aCaAwt96WpybrYyLmWLbfkZTh630K3BrIROxphQi"
    "u4oKYrCG3NgwmIfHYs3lr1fWlyVfZE/yUdxozEU/wePSA/9US6I7vhrMEG5XCCtM4/mYs+9bMYtdcrU5"
    "Twx3k+kVGNnz1/PkBEk03gnDZZPQmEI0H2CLs07UaB38tQKZQUYbnGvX9V4wMqnsSQHelLtKPbEThCJU"
    "Wzf7Y5MbL+49Bp9qGMvYoBFOeT1Poxfi65EBEhqH+9hwpKKKwd0xlMyMw3AsWwCVOMuithq8ms2vKZHa"
    "IIMA6txWBI4LYn+JKj/eXIkPYInEdLGxDn+O8y29pwt/kCG9YaajV3ybHFpoT8Dx+lWqmQEsgPsm2Srt"
    "eWWaPx+6ZkAcDGGe1JMxlwGjl/b7973n9ApHEF8tqNzPIOzk0XlSfrcvLPGJFcNNGcpQpgngEYW+lCHA"
    "N3IYJUzGuLT09g1h/4DR//f/+SuMTvr/gdH/9Zl96c9zQBmF088bTVPv8FQi8KYC9lNuhwV2rizD9l1F"
    "Z7+d6dvKwLATOyvV5AwKVtedfc6GqHRB1ghh3DR2zDepg3Cs6wTDrX7Dbip97pcbc/IcOvC0MPkBAWyD"
    "qGIsFjwDABruSTKkAfTpFy6NTs1uCwkefO7kQvpYYr0SWDY0qEM2pyDYPz1g4CB4D0o+aNCOsBZCpmQs"
    "ho73rO0EdA9qDZ/BX1NqlUTH/K665ISf4fAYU+8j4ieVFW2iF1a4PUGSBE5/wYThNS7/+SmxH9fE5nzS"
    "BMPDHgj86KABlktNt0OUzPicVtPxmF++XXjVPiqV4XItz2tHFhCkPS//Bw8gRfOpdFEFCZeiYjZTUFPf"
    "ilu4oSOcpSFAmlQfGYGXhybC4xBOh5P76/V09VbGRm3b3VaDIGNb6NY4Or7WvKZMi0XppEylP3F62BSv"
    "wjnrcG7MHpui1BYaypNoGEC30MTwocE6KYZq4CuoVkYBFs9ePd23Q0hfs8difHDMYlfhth/iOPhjIr7l"
    "URhh4Jycg+mnjIi4R4mZslU/eCUJDHemPdk0gIQfs1kctApCuq9a02XCRK9eYkm4PxDPC5Xp8VYsrqJ5"
    "mc2HSDkIDlsXEtMc3lKMGC35QWtzkvjxUzeb9WBYXSoNtFtFgXyGL/E1PZgOSmPzNT+tJQD7DbwW4FZu"
    "uJ+EE8RN4tFW9wSQB+0xcUVMzzRKupnbYqukqUCcX6OuNTY97ltSCebseOD7IWg5KhtsAeDv8o03Hh6I"
    "We52Nh8+4QLTA7J/keg50NbiE0DRK6pcOfcMWGLqH0XEMENUa1iMcFDQ6xemxgB1j/GrDI6eiWvkU/q5"
    "SN2xZLI+yvT8Lkvy4pIhn20m0xH5G49ViraYCSoT586UXIlIPqKv12HNwJJpqGS4gAqNKoepysRKCGDe"
    "Kyb3uhL6bB/+5zpR/8ZdOYmVquQaNijhIC/MMYPrquOXR5WUGbNR+L0k0ELJ9pJsw9Ysm/HF61LYLdOx"
    "GJzvuVHmUrtSq4uylnpdrltOBg2kwmEcRMIY1Vp1rcXuzENOm3XSgoqu8THB+PUQ2/coUpfVdRt534W7"
    "bckwk1aPuzlpvKD3lOC2xuMIiNuTs5Y/HKakMF/a80cFd6/XCEZwqmKBlbttfqWgfY6+d0FQJpGdGXci"
    "Cpk2Vwct7tgrrz8C4Rjpoz2wNKXCqwfo56i2q+qKP3cipcrpFkpyZSfDuE8VqIPr5sZV4AuV50TcqqE+"
    "TRl//Rwk7jwbBuhteMMovl5COiTu8lvPUdKr5J6GX6eIklJ2anxIF6rxic69M8aQdrrDsSzDJ4OMlb6O"
    "x1hjH8hJTNIkbXE/XwLktAlDJHyUWKyZTAxnr9Ml30oQCibYIEOyYI5W+bVBocpR9uJLea4unZ2eOPpb"
    "++dx3zghfyTipzCI5ka9fyo7o7+2OTgf6KshbBC/e3PXShPV9qBi+yMAyjFF/qhhWrLgzfMT7Xzx4QCi"
    "Ozb7LMLuDLqoB7TnN46VE1iXcaiQfM27UFjiDmJ5NsGPyOEK6hNH7eBVI+Swf+n3XAmONigMZ8heJY4E"
    "81t1hB1sGLPjl4HeqBovOLd/Zt1SAfZnfF214HIY1QKVa/UFlRDV+/DEFn7i3nFaVlbbQkOcV0EYyZE5"
    "dfNYBcI9fjTUTtMtv+OkJh+F2Qy49feySP/CZhGqpD2dddBTfE8JTsBGnyC1vFbLdCbtOTKGnJw2NZDn"
    "gVRwHd8aYwl4bFN/fojern50muLLNxniGwRduzbAWJjiC4nQIr1/xwoUw8avC6fE1U1q8lhac+i9iIOK"
    "uqdUbF1bEyvKGjFZuyPkRcpRa7Q7J1oQO9LcmYZu3jAlX69uN3czhN+2l5U9QgW+wb/Zk9sfdYsDvOM/"
    "mAjnnyRNP8NOVrfRb8ObptAQPJJyk2Cywgq664JpP157DK/uOCLr+V3NnIU8rVc77UZytqTmLEJVF84w"
    "lqzXpk5UjuFh9NsLuMexH0o/Siv2P8jDf0xufXGaudf4DZ/SqFIKWSvYn+eECq/87sgalVH+Lhbfimmt"
    "+zn/deEfNMAky1z3UcXxbe1JwhMoytLLWcYWwJW/yMaOpshktZ+v3LKFXsKKRrHAE0/D6tPs+mwuwRFv"
    "x1AWDKDCR6Vs9ld1O8i56sUdPBcv+VfTJQI76tDjflzvCG9MLzhAgX6lYiBVqHB71Lvk6lmHzPcYAPgG"
    "B6+Dc+ieDbxwrakPNDnaPSZGTDhePZxDG8e1MAb6N+zrfFgXH5+/3RuA1ZhdjW7dB+plJhaHUfnXsh8c"
    "SRLyXhldjaQFWw0EpaAWBTy6XaKkbanhnIgy5MsIwPSKbm14KApCj7gJIZpN/MIJmJ2ap/avv0qEDa6C"
    "Jif6z58atFHCDUIaHaoYPfBnav9R0YOQtIgV0r04ZmO1xfKeNpX7FJ4KwlXOY8jb5fEzTtyAAXIe4DJt"
    "snc+28QNdgqi0uCGY9hKuu1dPVX7SKykuk+S5Dv0BhGgwLSfniz5ohV6VMOcyRi+2qqD5wH8tnZGnhSh"
    "//GJMkX2oDlcOAjk8tj6o2hTCiQhqSAA8sXJWwVemgY+uVl1O+l+YqCz0Pr4WF/5sD1pHAx1HtOEXfWJ"
    "Q9VVE2+V2Vs+4X07vpqUPVuTGPSEhdNcdbSY0b4sZ7Vv6VGZ3pCLOCww/VH+cgR3t2QqWoq56xXAIiZG"
    "tJnEDT6ko6fapc0iQPtwXtut3QWLrEEpzIg/k5vZHRQkRKf7zB2cs+wonQQUdDWBdg8trgZNS749HPq0"
    "1ffC8T3ewDcuMobxptMIH76dEt8KnGqcScfbbUiS7YfZRkif7is67JHpxF5Xe3QsdoRDeArGee79EpzQ"
    "vdbBKIg005fz35wFv6ynGMT3O+Bj6yq+zcmNaAriR4xjyZ0c2V3WGQNJEYx1qiyEdq0lvyUPSsfggbY7"
    "VSil6qMYEEyW082XzpgpydeHdX3lWeUVVpJd0xg86A/JwTkB+Hbwol2Uw1gJoMrX90YajTFU/lzkJXqd"
    "apkQUJggVp53p0G9xWw6Ln8qAfHSAw+NW16qzPz6/sdKaNqwKAt5FfZ6dHLA4n90j/+//5X88Aj//mxQ"
    "iFz55YTS8bzI+WDA9eCILFKux2FIx9ou041NVVUzFuFeYHvcJs3LVDva9I19rX69y41W9+OI9vySiqAf"
    "fhLK3C7b7sHa3afqx5qxNy0UVJX5No6ZmcLr4mCKk1OflF718+qFW8JrsoAn0ZGDpihgLYE4stY/3/q6"
    "KkKseka8AS13U8bhR9GLC7GLEe2bObjugh8wHZV2sdMHRHdFLGZsovwaxGmOjXcbLkHsKQu0LZopRVIu"
    "dELnI0ObGevXwNhN70PDEkvktWsxgZf0BT0A+0UIlhjqpuRjjhuVSokD9CAVbFmopzBSyyiXF4097Pgu"
    "gl2eD+t1g1XYs0cu77yV9vEg1A6ChGldVOpnoTKq5+22hJkNhh1E7YFFPZqvsAoc5qMjmcuFoRVvUeSM"
    "s+IpwIQFsfgh49r+8Rquy/Nb2fo+oA95wVmOnjjRsSYPsNh0rWGn3eQXJI+dnJ8Zsky/EuS/f99XYBo7"
    "O6f4gWxbfIWmYUeXY+4p41j+vRQcxUEUzP3MrjKcoqnaio1BX8UdeFVmoeFPeGVRiJ3LrDVGszmWaOgo"
    "F3ek/fUUllFVy0eF7n5icRS7q3CNVhi6tGnGPdSzSA8NDS3Al8a7W4nZ32zATXZM9HYWKEWSoIy71wT6"
    "vOtKw9ZA51UjMt8hGXeNODFkmLu/sXONqjYoJka6QioAhd32mt7LnmuDz66p2rEfVHZgQKkw7qw0waMA"
    "PQr4rXsR8eqNPO+qDOAQyWA47mebZulgDEUzs77K3g8AuY/TTnWnmh9bw7CWfCpiwcYz9IWULQETq/FJ"
    "XbFDDYw13p/EtzHLbOddQB2N++zG4M3rcej6XngDXpLB8mrJjvqMeSJViTBf6RZTNBcA6MPBcZ6y06ny"
    "A+0IS8InP10+DMHdOn1LkXZ8RyDxO+entcLa2NWyt3iiA7DWqDk8pvGkEx5TkofcwawC9pCPqp52hZED"
    "8URyLT1wU8cwWTdaQFqODMfycBFAJwUZoCU9vVr+tfri+02tgLki5FAbd4jr8REHir2oauvU0+c589nX"
    "9qxFq+BEKzviBrSY+h4AsP0KzkWN050Swu9jYaHU7836KJ8KAcTPSPAdAMCf34B/Edj7NrA6Iw+NBHub"
    "5b+0/GqiKxabwpvt1BRPfe/zZpJOMfbwxSXhpHPXzE7NHE/kzthEfc66RsEuqOsuyWmaXFlkATvY66R5"
    "2l5wbQSrnHoOKV2xG1zVxYpqd+l+2mHhT1flstOt4z6mKj0M/bwUjjeqn425M0C39Zo4uxLz/jjofdvt"
    "wtc/mXHg/fQGCsc91Qawxpv5/oj38pDiA5pLfJsClJoN7igcK4Yc0ZXdCmkV7mrT7L9Bo1d6j7WrWtXh"
    "JJiuQBclnZdr56VtHZ10muKMNzIAxVhMBm6ZqYohQByIbgNQ3m86resjZ9J0M0HuE1YKfT7GGL6sAaV+"
    "sVIsAwQOPMeSEs+iz7PnFDzNA2MMXDhz8vWSdX6krz9A0DOwe9aMUaB4F6MJBcl5++KEQzORQ4jZ4/es"
    "YTo1HPdDOPDBFa3xSirz65uMLyj385D1V/08oq1689MAybRwaTiyhCJaR84d6cL0He/EISS3gmSdPRFn"
    "i56+M+vX4peFO2aHNPULfsdaYHRl1PzaEtp2F55mvUoOR6IwOtlAMcOGbMYcFgySegS5WtOqrXVdW4a0"
    "9l9u/dH5OZIyvzQxe85tQg4mxWmCZXd5dY1MoR0FpdiAmm1pYv5Q1WiC52eGQ3dGc1W8yvG9tGyXE7IL"
    "3/h290u8L9RZWl+OlOou1YC54rbabD7Q3Nyrp3Kq1k7xlEqkuynbJATvmnT3kRECcnQ5WvzsX8fdkGFC"
    "DKeprp4FESwKp7Qwwb23vaOUTvMnY6j3V36wderINldMaXmlF6K5WWB2e48FXNLkx5+2/SflRQ9a331b"
    "C46R6WFl5zwNtRSaje/o1xw7pfMuQseOWhT8/zg7byULoS09PxAB3gUKcAdvDz7Dc/DehZMoUaBAiR5A"
    "uR5R9J2aqlHV3ORWR013dR9g7fV/H2zYGKvzou9ELwpq7AF95w5hBcNnUxQ5/Z8vn5EM15lQqvvhS7oX"
    "R0fjaofWKt73zMxiidY5FIYKmEMp94d+P9Is8u0GvsC4Mit27nQ9bPWS+nGSx/SnxoCr6Sv0SLZNeJG6"
    "LchEJWVhSP901seMzOJLKxFP/zYzqxzwtfraTjN+Fr+vbDmViMY2ivVn6WFMdCa7umHbr0yLjo/ZNDM/"
    "kpci/rao9zbbzgkyzkrRwAiri2mzEy5itNxRraTXe6dXCPC6zbLU1Zv+MF9LiHnlZwlrznuxWE/G4hob"
    "X1nsCfQyy2apP3hsxmGxuHgNc4fDsvRZmI6MlBA8n6+IzMxrv42pjgo15v9I3RMmSMzlCs+CrIWDFL/d"
    "mLiyCAy+ENcqLcZE47cZcewYYqvG+sDY5Z7h0rCd32Z4xTJOW2T98xEpSEx1ZYP8dU40FSzygxgkOWMF"
    "kMe39JJ+v126csSw6MQsp/Y3rctZlyz3ckPd3YcfFqpyX53U0amwHBJ4Hryoz2IkMq3+5AazYSZ2l9eY"
    "dgrcJeEGMyo8Cim83jzCrVuhcIHEshp0PsF2kQ9p05rx+dJjyasw7s2G2QhRZH/l+naGolgO+UfQuu7+"
    "PGx5vsab6oDtGaFE48MaiTY5VIJt+wShKvbuImRQkizuk90Bq9LmsUNK9Ped41VY7gZZWhZR0m2RFNtw"
    "faIuWKQuaGa9RYKoqnzWNiJWZxmkrTHtFCLort6W3Wfd1yTZs0CeNSuHxqlATbizFkSc0rPd++kHM9QC"
    "FMOj62VBfBoMXc88xddSHGHh6NpcyP4YduNvXn+Mk+66KpLD9uCsK49gKX5FiLWWG8S2HjDfG0HdxUqY"
    "940ipBwjoGyIoZX0nSHLbbXWDDUx2ObXLRjMMhXkVz5Ui9W09w3uqoRzqN2gvjQgiwEc4wmWUCVXoufn"
    "rwTe5fD0V+P5QYTQPmdS/GkK2cYLmI+UhBTTP6CcAI94yA9tlTyyBIKGxDbwMETFI2wAYU93WZs58v7R"
    "GQd7AJLpIlsMXLwxqrhk1YN/oyL1+0Dyw918geaU0W9ASLFjxw6O1/5k/585wf/5v/+CEyj7f35eIHqd"
    "AB7EEgB1syiKFS2PZSvIhABDAj+i3FdwMrx9T5AVhBcg9zv5b08hP6rXTt/O0HjfruyK9dPI+XJV5fhM"
    "ovrMoraijIyc4AuCm2ielsQ7tAbmQDdjaVpHjaYvaBevAxg4STbo8GgPleXFhRER9PmadInfDr6e5PM8"
    "h05RC/gKwQuF+hgWA6OxC6IV/bspks/H4OpC7FIYs98zTza2zpO6dsg8uCMTnOOrkrbLNT0UbBwJdaiF"
    "8XFaYjWsIg85DLOo69kuHLlolKWEkKLOq0yGFwVHChR1F9KNCIm2FLSvEiCOmX1WsjppJRIxVd66zG1P"
    "ZVRSIt5SCAM0GM6njCpQicRJDDwQ0PqwWws2+/09U5T81hhwS2oPDUwjYIe+qptvPGqpgOeMyJxF2hO4"
    "ESXQDS1FI4smod1zcGkgDnXBSpqO+GMnnqZ6Hf0s7sdMfP0Pke6Zw3nxDU4J3RwJCZgXW6dzOFU19dld"
    "ceSa5f7QgcTOi1N5U5l8TRaSuNFDPe+lnUMiJDiGvRd7TPIhbtwOyRq/291lUx8f6+mLmcAjdWqVfZYE"
    "ErLA2akXbhgJbcvJe2kcHCZw31QebIS2fqEgOgVRE/pTZjMGUwiBOQB5/hprDy4pm4GIfXmRDw/Le+69"
    "wINjSPANlxKAS9K1VSiABTVAWgWNkKiEeP+pSRVxX5dBFLViAvaVTfEH29XnrCP7tBO+mxJjJ6vfmU6F"
    "IFtPOJMJi7E9uX9zjn1ePCczRCl2ENVA+Pg1s1fvTG2qla/FNse1vAd+I0/05a4UbnOZum/1Zq4jkm0F"
    "dD+lNCEygCJfwA/ZDz2SuW6lN1a44GfiLCPAP7wyu7+ZSG79i+VLuCmKljCy/zNWY8EgBMhGUJNYwJhf"
    "4LCk06Zhb8PtUawJZhRt3MLRizZAkwKSuFFw4D5Nng+wYvc4RBIV1VZ/oy1+hS47Ly87gK9KvCCOcGBW"
    "gEh53Si4f3vakA/t86so+9zg57xNy20Eul1K28+rRyytTmPIb8gXY51Ty1GKotrBxL6eo1rmmWRZYaQc"
    "iyRP4xEUX8r2jcy0n/UWlg1xYMkFb7FIj4AN0dt9ygzO9RTd5HPmP78j4jZRTgAPKAUeVpH0R143p9M+"
    "k3PhcRWNU4ABZQlsvaZNTWtAQoV+9wO1na8fMDhL99UlbjOG4yj0/UP/BgSqQgi6SjxpAdUUqyN9GmLR"
    "MpJ7t5NkJh7NsR7oVtIssopYRXltWLk/RbAb2cME/yuUMbhgMUnCpNoZBLc9oXY4zzRq13a2iq0/SXrf"
    "Hg1RpVQSu9RrX9/epRw1H3hjitGDiM7OUxyyEYIK4GUufiRpkK1+nHVPb1wgkHDaApDxuzJOvma+Shre"
    "JiiJpIZlWNhVZhX5EwNoL3pc5X2rSno+wvfN3vGD22T8Ftg76gSwFzAdpzHjucADfXKqIA3AEjIJxAFr"
    "KWYlmqugSr5qovS/IlJVO25MfpPTbe71ZvQqfwl3vU0L+GQDNQTVV4MiO/zoU9we4+XG0BTZQSUgtc/m"
    "pTu234JGnoMaiQzh/FoWLXjqGLX1e+q7vcQqJ6jqm8lsBsi+isG3a0LmKnQ7Wbswk1uvXp66Zj6azAQe"
    "fnLngIeCfIVUdOSJvHyicWWCdZ5sMmChXAxWzZuVXdXsFtHUDlXCD97wAGKbaGTJOyxpYLBaASpQM8o9"
    "JBk5AUX/pIv3tmLFObGzDLPkBKhkEM6VziKKIAF0vBlfZA6e3+5RxJ+o/Hju9CGrag+5Dx6PfGbu4Sfv"
    "i29GHbN7I9U8a3aVQ/jVbH4EltEWX0xvL4MrVC5nXTBYEXlhCmNUjTOnGjieNC2A8KbM7b9pActMxO0v"
    "vlJwnkrNID7zt6hkzcOZQVLyLXpVGIZ/VOw0fy+DEivlRWfgks+mOvOMTiHUf9MJq0IQhH/ycNUldoIb"
    "InzsBNeS2uhn+SaNtRy7D+PWBEYl6YZQpfURkkMYHhjGu3i4gm6aiyeEO5hb1YB74Vt8zi6NYlBl7xPi"
    "FHInmGxrK+YIiBiRnCyM7gi11wiRfxEwZW5XhFjG8iSQhRbJscUy6lkyKajyjX2otErAwpElYmT5bhBo"
    "TQ10CfKj/dHQB3Wgb7gmTZjjvK46F7lSf95FpHpWzWLygdmc4ClsXDr+h6CWeblHRCM6Emy2NEFDzxlj"
    "KRVZ9yDE3aXoQ4RwqzOWTIEXnYdN9MNm3xu75v5pn9B7QYahyw4oeZPbKDzorf3t94Ea+a7HMyLWNWNQ"
    "GydEQAoNEHumF4n40WXX17h8YGE2DdW7muEviIE2U0MgijXsSQMFqQ45+qrqRuRCW8Tj/DmvLxxzwKvO"
    "INJQcijBhxVDkXqtV+96z6DdJ3F4XJsax/fzsjP/S8Pg7ABpMqwFClLVWyl9SIEJ+fCeod20qSWVcGUY"
    "0zOxNEU1pBTfZ89eV4iB6WdZRrMdjiXMf+84yTyZ1tSaunpd+E6funT9H4HwOt0dKSJ9FvHJzKt/xgZq"
    "ktFK2irx018BULXLCVdAm+sb4stEPehKmr0+XJNnoBYnWYQowvjOzA1AA2AZTmhdmOgTFon0FPmVGrb6"
    "EB/fvmWf/o7Lmt9ZEoDa3Lc/iqCGTjK6Yq1/5mGmMsqtF2TQwgbjYinOH5yo3TcnB6tiAQQafvtiFqDv"
    "QFz9NcIzvGHORXEFWUvUIF3Qe5pS9c+Y+mKBgEKeTBhBf3oc/lu+Ix0AvsCV8HS5YGb7VT4OPG5E8jcO"
    "RvK5xwizXW4nG/kx+DfdrrdLv7kTNIjboqt4XrDkLKpbXi1oLL+NpOhsj2FOFWxIYAWZ5cVQwFlUqZnZ"
    "7CUZfC5u8EwO07Qw4fqB8R265qVygKcEOBbqKss0gUNojgXNregGRoEeeBEU8bk0YWg4f03ZnU5xrpIh"
    "XIWm+Czm9YF89ov4FjvPbxc6fWjBfnXrSTyHQtUz9MMSHcru3TCRSWta0K0LPBaDxg+GgdkyWlfhrpcc"
    "Pl9WbNT6A7uT78GnucoeQRCO8XMz3x7xAkF97GTrrA336YNiQIsoOtpvYW5eTrlM6MljUf510c6YXS2G"
    "c8GzWZZNqIq4GUM09tmLr0N6C219Yb+CtJqMsp2V2N+nmnyDyOYXj7wD9BQolkCQlLY+Jd/Ba0oM41AJ"
    "v9bW28eQZyF6J+W3EE6ACjm17oP/rJq0znuCsOJlXTrWXDyW8i+xqmj4y0uTi8O+PTcDprKZzizwWDCA"
    "LxGKjOmSoQxiwF7tEwJ5UI0TKOasb4wDDYc0BstAXvae+HXdjXdpP9fdhGQLXwAAxcfr/Z6xxv0SUw2u"
    "s1A5YFwVVeGEGe+AW2paT2DwlUieknnSmQqoJMAs2PvBgG0Gr0yhUzEv0Occ7D81YhXHw4WlVaqq+m//"
    "cZ/lv/8rTvX7T/dZ/uZpweG/z9MqC7zBNyx+HtbipVjX+ahwL6FKxB+XenJtqH1iN6freBMnd4Habhzk"
    "dR8lOHh9U1+77mE3UX/fb+2/vxKaptxxg5PbyW+1vv0s1QjDCCDzHp1nKhQS1cuyyMC4AAsrK+IK+87+"
    "Tvh3vpOhBSwETHdLiXRbZGCpeAGIOX6FXDiHBafB55YFk3jiVetvoJT3AL8p337HAiK1jlYgTjFT1U/4"
    "6KFlGldoPdnXLJpqyRVofRSIWh8cAsD9LEuUJQ4XFkRrRiOuEK/smHG5Sq5Oq8KSpjJx0x46zo1pp/3M"
    "KZLzDl8tz7WumC4z2fbdtX6N7wcwvAayKbNjy59FRg5sc2s/Ev4sxstNsGo+kfvRCe6YGaBw5d11aApr"
    "TV47uUpdtLsam4KWoTCvQ8JAySK2TBTXtjS0OijJxvamqaMAhxqirdy6kAwQXhh4QrAQfPBD560BfJE9"
    "q3djhnbu4gL7NqfrVYqtTGeYd6R6oG7amB2TSp7iSY3wU9jAsbYBWXUomdcFrPjiCyMgsRjgCvDuCW8A"
    "HulNsucinwLwOIRlk4PUNyxvx32ml6BU2LfAQDvai4pLRmHkeMG/G533GflTSOtDitwun6ZTSRogcKxD"
    "VOu1JSFx02FMzRY94BMRqIz5erXUgJf4jnYETAcTnlFFnxxTSg/rCIdYsK3ZTckzIAfzUPt8hjPF6oRl"
    "z9eyVN2hKh56u3Pa3GJ6LY6P8eWm6s5ZJfIzxHM2cJ6/afbpf49moztV0KxF5zgQUcexvxwPgbM3JltY"
    "YVCEL0tHdZIVkzrCTVOMWKhzRvRhzjhp0qiz8mno9YhzxYNQFYtJv3VUC0DyzffY+OGODm+u8rURZ8N8"
    "pkuXPpHt9fNFBL1H6nRZMtfQjAwUfYjWEiRYH/6njs+XyJflgYEdyLtTRy2rMYaVZHMAdeEds+bxIKKB"
    "MdybqdyaYV3e+tbVbkHSDQHZV402bj3Jmmk5G/jk4fAKB3geRgkaUr6RUEfQP+0dOYxlgd18AUZOkuTT"
    "lwadtZM2WAOh5gKLhobgWHVmf2mdEZpI6OVE4XyxR3WI8mJtD4y3J8LxJRzg8VtgmoSxORMgVoDn03kV"
    "fePFiST3+ygt8odnGYdcmJiJkh+rM5G3G8x83Xn8sisMQYoRdKJAoQZzB/snVJvvPO4QYSufA2KXdWp6"
    "d9Tt5+oeQGxu85UNLIFK/SctHPe7HZKzyjB8sJTUODj39S1KVToWfoNeRM/5ZUOGbWSl4eMLVli54riv"
    "2LKNZ+KaILByrZhTWqasq+Ewme7GC67EYL7wD4cHC4IPAE47sS9GCHtfXqdE9ZN9OeOK01vg9t4WHUzd"
    "WUyQAp8wOJ+37Q+rfQo1uAheQGRBuJweNQRyITI4AzMMoL3AXUfGrAqyZORwJHTK3NGg/X4djhfsdW65"
    "NkKbusBhUMTxPv/SP1x+McLaYkXpLdvhBW7uueesqGIAimmi3mHF5HsaWNZSaZcw1q/im1vdXkM4TGRw"
    "xNzsddVzCxYiPAEqM76dORXL+NnTsLCxfyywv1XhztJRn2sJ9/DsTmt0gGnGqhgvk07Awj7gobIr+iud"
    "3ZIe+Iv9vTEaXXbSltBChmIGNrkVt9Q4P62gka/KMbjh2Hj3E4Q63jsf6LY35W06gJU2HHlCe/YgKqmt"
    "aL6xBX40CAgAN0cXc/B52J9u+6dSAlSU0fF0UzjGFWjkvz96iR+5gPC7pLxRs3Yr9+mTg1aYEqHYnOyv"
    "qhws/Wbi8NijcMlMf+8sM0zboR4q7qLZlYkmq8VbX5gkHqcTKSnzS+lMTmrzdZq8KVnHTn5Nswsuc5cu"
    "je37vmmbOXB4phdVpPGxWKJk0wU4kCYymqQnuCzXZ/kVjcPJXy6WnVfT9uSjbTQ0fX340lpEXGvBDRux"
    "dDuY0eZUxxlUqNTvkUCSQ9vX5wh4DDiB7xODCea/VVR1uBwy329xzBfHVvzXDX0zaDmDWqMDwQsmgQSD"
    "qw8fOR2K+5MyLhodePqEfk+K2im2tpNrAWzw7Rj9GMFxvS7KzgRQR/cpW99ek0yj+3mUR/U3gs21dZ9P"
    "dTdq9kxe7xG/7E0HPPaIUe0NB2W41k4lI1LQ31obRrGF18IUlN+zed7D9cL9JrQviV1d6HIg1j0z/u47"
    "DRqJ3tRuiBMBq05wnvNZd255Q+9JuazH1+di1q06qG4ESUS9kiHBf1hhiAj3ukaKKuvfXntFokSd7Qly"
    "u7reTW2SBbb5Z5NlKb82JphhiqXaXxX7aaQ1HwcYGKYANso9+AtsBhCv6ykvQzX2qNFmflEZI9G3BBNX"
    "/0ClSZmiJe1ldzvTr1bYMenLj9RGU0f03jmZy3W2+ZlVEZb34C451UWn6w/vAZ77NI3cMYPKBhkHc+PB"
    "oDwFnCC8aqwcFlKbDzXlSb3SKT3fh5AmsdQyWLn2QWfZaO/EUNY7GwTxzVpiD5SN0i2UxouCCzTqcPIc"
    "Pm99OWsehG81PtLtKnZRx9vVJjK3ZkNjGlyPOJ3MWhbawbC9/Wok7EUoyUbnA9FtnOUQpJHgscl1CZuA"
    "gjdg7TmPzTa2OWvrYDxkHfIQRee7N0r05yLFMXbbS39rItt7EKAoD9kTFG5bFansSHNqSVATwbSOeC2D"
    "Iljc44aYRuC9IGlHyJ2ZKMGf+zfy2Ec5+xGpWX8G0jWhDW0CEsy5/PqjBQvLpQ5kS2vX0OvA7oA53cDO"
    "GU+NRPeZmJEvTkHHuqWnKPObEU71a7Dgx0wspK4/bsHiSu6rhEF6acpPUGrovVFw0yTBKSn56qpymvB/"
    "u4JjDy1lfGG03gP42UojaIpYLEO8qSEK1wfGqu86GcoMiF4NaaF6JqUyIbK7wc51R737+sdKeWUIah41"
    "mcYcO43FRpiXEEUTlU9dUNCwbE0A+vwlxejnPQWz3yCjkIkrwe+38jr/d441m3NGND8yaHr0o8FeQTuJ"
    "0koIFnBKGLPAb6Ut3/Kp3CWywg2+S3QrkQvZRHqt7k2xq2uixH2H6blXfwyFtM+3CkVtB5Q7wPulaWmL"
    "Asq1xEfI7xEA/B788mV4iobhDCVLBZ267aaBQC3sIwFA2dYTdr0Y6mK6JE2Zc6ee16UCo/j5VInM5kKi"
    "wxeVo47ZWRAeOYbTm974OIIiMHdPyk2Jscizk7shaz16pDtTf577PIfLMB8lxvOcYpUKyNvP8gqlIjrI"
    "Z210HoyBSnbW4kqu9fiAbJf6pLS6y60SlAWCmUzpqxQigmDadc+jfIttrrj51mgHbC/USCJ/ngofGpZK"
    "wYzQV3uEvEQ8/6kP/Y9/Zd7ZT/ivn1spMyKn0ZVoToyfUheyPUv4cNCPzWzhzGxPR5qTiWSbtX2FFYJG"
    "p72xtupxbpJvIOz1bFyOAP2cpDI23g68rp7byXcSYPoBfVHkfXgMw2Ah1Eg/MTypheej2aDc9NYtSwAc"
    "W/o6EKahumO3PRXO9eqbxn0hc137k2VHcEJC4ZUssnWD9W/+IV+SPPbgDv0UHiJJflmMvRevnTKw6mIa"
    "euNuyVmqjmVBe5TO/6RRJisgKmCeckAAdTRf54cDOEGmdIDOdcGOOXkiTDVzMifhnQ+Hz8cvPRRW3AHs"
    "MicNUpGOcI5xIUNWFaECP42Z/nzU5C83XIZrwzA19kfqZbSvPE5QoyDkkIkf28/fNkIW6SQ5Hm0USJxP"
    "d92qTOT6iiLEgvtjff9jsb/7vrjFtM3PieWm21xH3qH0ASN6fXaymkm6NowCqcs+jfqAxy+BE4bAOWle"
    "VP37M+WVLVzK+SOgjTlUpTjCiXIGoR9oDp3A1779V0BJfeaSHmOmH7prUJgRXeWjxENRwLbe+6Hh33hX"
    "udHBr4T/JDbDfW2DuWrCbgUuN8BAEA2R9S/W87TYTff+Y1w2DajPfMr17+rbn3/vo5uu5NVc0YX7Pmi8"
    "qDF1CUe91eSz083USMNN5B56j4vBzMb23jBEIIfXuoo58Leh2i8Pw6SqxSDcpBip9Gjc3m0DAy8zLARI"
    "Z3Os33PoFN4uv1ER9mBHWaJgEViOT1Ih24kU1XHmycLc6//wiOXHSl6lr5E0TG1l0B37dJQiKkQAsbkN"
    "sZlvmp+Jx1so1p5YssilHPJ+DQpO+IQLTOnLIuwZDmyc61xRo/rOoiw1Oez0AVEUJWM6kggPfw4MEXlM"
    "t6pj9beWhnGe+xOL7mJy0jD3vgBk9MoOQ03UljzLWC+zDNxtvNORVbYisIDi4VgjZcrj6572lPVcWNCO"
    "25I8/iEF1jDKPIjlvz0MP+PnY0dfinm3yhEo9y2nLfPat145Y/H1kOPggE382w19uOITXNq4v2gHpZ0v"
    "PX4GEhXCm1aw9nxZPZUY5e9Vg8u0Lr6uOKoh92EX1J0HkgRPkwqHjeIvk7nXpeHgnGhHJKHj0CNglqsu"
    "K3zPoChsGt+OS8ofpsxrW5lho/OhM2SUE0kiYRUlUdPlRPga4pFrX1JhiB7UeLdTDO47bqbFNWALMeEn"
    "SEpJ2Ac/Y4X9l7WQIAnjhLOZVC2K4+/yv69FodsagfKo24+K/YyXhnZ2UzDHMtR1j/r0s3/ecSGuiljD"
    "6fBy0vqC/nT9qn5PBWAJedBEr8i/jW+eIWYaryKQW2/v+863PFmHIEdxSxOA0LmSTp8ftap4Nz0/ducB"
    "jpeKdUyjXzP3wG6XPuQweuXSu+FTqWCQ+xYOfu2ZAPbLO7lMV0p4RE/cGjMDJMhTly0/ZZcYE33+JF9H"
    "XzCc9WDxI9inrUcBjPpf+VjQWEzEuxu7UOCqcax+Ci8My3EMQrw/mkE8Nre8BFWdWv/cXZOgUWpwQlcI"
    "tlCqaFmimSI/i0G4LrBIAC59gtS4Fx4aupTT50/kC7ZNnv4Cp4HnAWuPIZm9gEvfCIQKGViwikrM4geo"
    "e2l5Rk2vrNvnR8xjGsotduGuvMhBl6ZIxYaaSTcUyVYSD3mQ0Y1B6NfKS6Gdqdw7/fWkgqC8zqjhx9uW"
    "rN07qUyuohN1H3aYVwvVglJurFSXpFMUtlTUUtEuNWM+in1/boICkgIZp6fpIQrwrO/MAaKSWZYs2lhS"
    "fHSeZRBDwqjK2tuO5cEGioXp95MjGvJZzlBu+7LGHoP1yhWWj4CsdOYLl0fHWv1RLKH2pPvQs5yTp9gL"
    "xBrDqc3C/REdnZ9Q+uOoELowz5fqTMPtTk7x8QR1nhLs7+4rAsRGUSIsx3XP7xbIgVt+gaXH3xnRmoip"
    "XRE70dfVJ5/+ZoLhC5A75BXPODDfFUXVrl/Faz2SEkS7449VkJRCvadU0n4jo778jV39eAQT5LGRqf8x"
    "AxRYLgkFxidFdNgcW8xzHbOLegmKz2En5xJGo2BVAnHU38aujsaFgR9aJfcJoUHdhqXwPdyq2Yu+gLZP"
    "xgNV2djMp7MlmVmvd+RhtLSxcNxK+zbe30cpMAgWooL5mbKTqnzrPKhWDn3m6vGJZbIaT4B72iGHLpCb"
    "Wtur5CjYF1wdouVXd1HGIex4iHhRWlilNzf0wggzfkBAReOJnp3Zqmk9b7a1eDvd+hUa402M+sYV9Wu2"
    "cfSmdT8mUhjA3VyC1rrslucXKJ+aHHw8hzYt1UGwNUfnMMUNFuxrxmf+efiZ+I/3lglgRwSV3RqMBCqN"
    "E1InEgoyUwZHMgASN3/390sBtYaNhba8+MBEExUV/Z1bKrK/33FRKtv2HhPSTQnblejnuVwPb4yb08ck"
    "pgf90sBs1/LT1Sjr/OgEPFbyeAsDoHCxvEnrwRHLBOoB1MZ0rkW0jL1dDUkCJeDtxt2yxOt+/I2kcBGr"
    "oxYb9JJoIJ7TbyBhTqBpPiHV1+6EL84KMKTurSeSR9bLByoVnP+S9L6b/Csa92MOvtGh5cymMXXR55lA"
    "pEtNY9zknivMdeJ6nMHp0WIyOausaKN8VNWJKEd24ePiTQfRn7Oy3MNqZgwnfm/GKiRuU4OIgsMxM0K0"
    "Qdvzac8FUKTtC8Ew7JgL9iqkWonG91sR7dEhhIuyykdInSqMXFfCDIyVnEGO0SzD0y0EIy2fkM3G3/Ph"
    "lAA1RP42FILRJ4veBR8feFWb/oqCXfS/uWY/CY//CBm+qJ+Fo1l4Ae8QAP+mCivdyoRoSu51HpDWnraX"
    "xWM/mUW8q7N8qndbw80uo+aNNOlrAcoMnlfimD4Ca7UsMqH7K4kp7x2lKlH07OQdFwjvPDKiDsk5C867"
    "EfrcQ5BcSETjBglu++gEQtrbTS/s7FIgU1NRhd1k3IUWVZii2Aa0GfpoAHeLqLcuW6cN8X+97sT//rd/"
    "hdv59p+sEVcQtI5D5Jtd+TShUwRVH2SVpfnlywg57P5lVZG9ZD4VbMoROHi1K2ZXdJkQElj4ObNgQ03A"
    "VnXP2J3TsJ/KaVaBFeL7Z5kT+u02+X6e7QlfATvK6yQnaMq5X6U87Wvz9wPTr577IHhELpp9W5m5fkHK"
    "vjvUYA60ZQxn2eqOUeqF47b2s2RQK0ESVj754W+ZSafpzIfzTx6C2zqWyl464LM0tFRI38NMqZ5scL4m"
    "ueq2ojVJnbjaanuGvTHqEuZ4hLN1aQSiM66wk2ofTZMWk793ySrcrppokrXdh4zBOeyvHVGcjLT7ZBDs"
    "wzOZw1EsxfkOLYm6AtXRO05Rr8KG7/7R8zg6dtinnXa5twyzfiBhLA2HOZoPAGhpWQcLdtOx698c+m/0"
    "o66In+eluooos2fZaybbkp4XFTJyCh8acx8oNzw9MN7oSgxduo3rAbO51ODDXzkPCn4TJ/8UURMSvWJE"
    "R0DsumLiDwOJfD0/P1fvnkz9QhnYhc5MB9fXsBucwuXi5nsZ4Y6iJD42tZkkfH2fbmir+QeP49M6lcs5"
    "Kusoai/7JilDws92lUpeP0I0n64PidCgGQp99Ubwt+KWHjCcErGNkWQd5qnpAeQqgCd7kl79JMNr1kdf"
    "7qlYTWQ+meu5bBH/MGUmv6UHDvuH5R0HFkzZpk/bMEbQNxono1F2KQOatES7zXYRzPktjDeTQAYsezFV"
    "d4amESyBK+RKFD4G0Uv04FZ2T2OR7Xky4ztfGwlN5xEK6ouY3IPTxfCbAXJRrRplnt4k84ddEZldUjRM"
    "09RyTVZpNFl2M441by2NDOP2Kysb4IrhoK/MKjCjX7LHtLbKeY5ntR2SjeT65Oh6vCftqo0ZhxT6A5hI"
    "2MEElnQhT+dB5ke9/o9ZZMpPp/SqnOgfPVP8jfvDvcRvALNCcvKRqp2Ev5tgiBE/qXPh2O40bT3nX885"
    "ciKpRGqF8zkTOwlMcjA6GtR4eRp3BQz8LUmoRoZ6FbI+pWwNFDhfos/BMwz9IjYR850w1kvkJ0QLBybP"
    "fvHySC+0nn0s2NBnEYa90N4CEmXNg8SMeTMsEtOAPkgFlk4voiJeN/BKXQXP1o2kiltywWiU8pKAuHMp"
    "Fg9rLrkZMPxGig2DqtUXIy1ry9qin2wpD2urPDekUFvFg1wu2d6/YzztjMihzkafq5SgRKCMnyEluSD6"
    "fQxr+kR7oySZ31STaDwbF+SKSJmLIINtZZq1lYIIarRhz/0NgR1jjTFNJU+yBdZzmHZWeAPxPf4Iv1G5"
    "xzciivkdbvN39kQdt/octHpjxaPB0/nSIm9jmcK4ZHw3hh5BnlkexUchBvBdDjCmpoADFzWtx/qOscRp"
    "giXF8tZJUPD7/Z+8TQxABPiv63+K+kIEzhR+i4Ys7A3uw4p7tFkstRfb83XYkTDHCmqX1Pa3ll/XZbjp"
    "4PYDSBrDyQ4BX0KrfqolbVvNDfXTMAey/nbuqRTetNz1nIdmUZKI8f0oAH3cQ3UmKkkky9twU/AtXJXb"
    "cwQlylAS3dFr2Y+oq78OI+i7+3VVvayEBIpuK00ZxxiRSuyZ4TG+D8uqYKq9+VJCO7ogbR1uQrLbtbCG"
    "SfQobMq9ndYzbHZnW6j0tNEGLndv64+ccKxiHhbVOLvZsdiKYrFjanOVYh54+6dy8/3xyOmOaSO9Vm+G"
    "6o83ahDT6C7jFWJ8VfkWuZvbZSMlEh2z/+N695v05++CJGdeKKIQJ0NAiu0af6zQ/e7G7DoCJ3q9hXpt"
    "RQOZ/UEubS4s621phNt2d+2rUEoT2rcb5pSH6EbnDXqqYlNixZDIZ9VMMZ6QMkaPjOhg4BqA12uxyill"
    "RCdWgvGCuO+/KHYBSWQf67m+LgYjwAtORJZ7KNjw8yM0mthzTcdIAXefvXIyNCqZFlvfkcLNOWIKeEwK"
    "Pyo7nOhcBFSgp0TzATKu+pJAoK4v47FtFV0468tTdvkzpkhdFOJ3X4EiLihNBAZs1MGwxCsYH/AvtAXC"
    "fghCHmKnGlORshoLQGyUWUoceC2z7ka7nkeBEcVrSWROQ8I/99mGCMegn1k7a3Yl7GVvXrdH601vZmmD"
    "QYmsYLulfIX1bEoKZOGl6zM8SSouc5xp7LxGrMM6TOdTolnALhT7HU1y3defFIV7Hi9aGfWpijlyTh4m"
    "iqhlfM8de02RpGG6LedtFHf129gygkzmDESovBAEJ5dfjx8WHxXh1nvATPc6TczRJoN+P1vV/HeP6M2F"
    "RXXy663VO7iYCEIvAhr44fxyfc+rvyilRzDxGVD0JXB3LA3eX0dck7MdBqZD6UIAjhFtUTJD0IVHSJl8"
    "kymifrkvOAqEmcVHyHW1Xj/4ao3B8WvRjFYvzanAG2trnCB79LaxHNK6Zp+u9TM0QDxYfhJk656YeIyK"
    "gDyJs2+/RsKzv8/EB8Xs/13XtukmTkWluHyaiEQeesdnD4YFBpaH6T6nB8sogdauFQ70hiXUPmlxthPr"
    "xHdqMLONjzkyRYbVPv+sutKhVtfPUKQxeorSk9KtUzRgGlLANRA7vj08/POgCE/RI0kqcZZRZh9KFp9k"
    "yCZmtYAJTxKZcqT5SSxx21ebXKQLSmrEMu11jZFMZYlmkWFEs/wpF+LvhovMyWzHIPYOIMsidi8fwnGQ"
    "9lDnRl4RIhzlVdEQXzV50+AD8qb37flxWtSU3t8a1UBr5pEotBkTAVHmV34xmlyYT0rqJtC/xwSVvxx/"
    "xFWX4KJxapbm1e8ZIkyyCt7PbYJVcYEGeG6kWnwrkAZOmvmn17P/57/AxdLx/6/H9p/WTgZeKSSgyb50"
    "MUkowjZ+o1HJ80f/Nrpv2f3pdhFzvbhod4KzjqsYR6M921HVJjxj65yrutaXF76vYIvwCsvfXyCGo2dt"
    "bXBMVbxNODpYlhkcOBafpH4jPFt6PYHjtDQc25aXwCtRvLW6lm0tBMWnthTclYk39aOw3GD0IviBSrTl"
    "sRJE9VYWC/Lgahz0N0pMQcRh8PVSqZSz3wzZ+eYGwK1HHJD8WTs3e6ilBkpHfXplcEyZhBlxJDGsg4DT"
    "QiXjcXjQ++TSeTLn+RK+aw80jKTHTrhwAiLLiJWqOCnJrX8qTyYfHTZy7erU4crNRvhayKcjC8uSUJSD"
    "X5SVmF/whhPPJJGc4XW88EsNw6i2r2sakNvMnQ2ned4J7yL3FtyjkwrpJrwrPR8ZcUWc3+GTehW6ykO0"
    "AanU1DGu/eNh/oIyJBRc9Dktdehg2Dt8aBm2n/MbK7e59AFjkyiNOG4OhPg3daIz8K4YgMf8oGH+HuMF"
    "/zlvDX5eiCVRg7CCu/ybXu7QydZ1T5lLU54L4x7xl5IpAq5Wk10d5/j95Cqm0QT+VU6Bcz+/LZo0jfz9"
    "gDmsB9SFfwU/no8fydXKvhxs7QNBlZ/QDdPgu2B7+GOYL2u9HEzZF4FJohg3scVQTB/8vXgbZgUImZPZ"
    "B8n4wrBFPXgaLAP9sCbsWiX9AYDIMuk4z0Kp/c1RKlTj3q5hxfz6DdDIpsoaljjLgQp0twPboGVi49cB"
    "8qsjq5eV0DajLrkOx8/KE2l4du7FxIQvpNUJCS2595gdpB9+ozvr3lFL37Y3YIdW5xQ5vMZeh+XQJ9jM"
    "viY9uVOiUhQ3NMWpqyuB+SuOJ6aIF4hzARP3nYrDqvH0yOy+hiATr4O1ulrG4QhGI/0Tu7/ub/wqaiFz"
    "K1lj0AUR6eDPIIDdIc0ZfZ5mJ5BBN8R8KUI1xgSJFEdQw9Q3LcvGhprcdawMa3zIXuFq3e9oQBvvX9qv"
    "b6TzbmqSpiNFc0npuwuO9amZL7TP8DYUNN8zlvYUOwfx5ecbECDzkzkSfFDB72uErHu5KHcbO7Hsqy1n"
    "S5luM/jfpaqDQmDyK2ruG3cqMpzX6+XVFQgwKaEzpI0fj1l+3K+ZuQ5V3JyxqlCgLHdlgRIGSajT4jzx"
    "8K/toQ6cTOYHB95vOo64sU1fynAC++XZ+uwTSOr84+anKYrBFIcSkPcg9tXLcMUvQOsT2YwV250h7dSS"
    "9snfsT8aKGx0VzTlkAQTo5E1iR0azMbq5bJTZQxSGDT5nHDnlmmhjbTmYuTTFFWF+scWXwn5Xpqvc1SC"
    "bQnxakv1dFrbLMYz6oqyWPptI+hlNdBET6NFHkKb6JNPIHumI4nazI3JlGaVpaoSFyGQN0n8tgoX6Wez"
    "xwsUSyY84HKGuEcu+2iJCPSpm37M1rFQ2DXDjUuyNZz1hqbnyaxR97MsCPKbMsSFAyTgXgTroq8kAUv1"
    "oEA8HRYlTMWuKYahZpjSr9D0wYTVIw7/m5miH3Z6uGmri8+/qKlg11JWU9lJqO4bilLl53eopg03zFOk"
    "taR2+ddUaylcglu4oKmlVqf+dLx9npRtL0mptLGZZZbbf4Gz6N05gCVvNRRV/eTn62PbE6l93Z4zwwNM"
    "XiiAloHtI+TMdDkav9/ySjxXztb4hwC9qwfYU9AlXVBeJgWANXCfdjU39sMHFjfHn7eZRk3zpkWYiGqb"
    "3s2n2s1IYcZD/3tcqv0ltAGPCQCwGl5vQ0IGn1Tccqj6fA/jzvvuB+6fYr6oDD6kIEWHqVYDnyExcGq5"
    "H2w0a1YQM98MrAYjHMM/bO960GUqGsWrby+He0jNJBsCj6FdvbcdzoRz+xz/GLzu6ZBPXG3r0bx+y7Oe"
    "KEM3jrEFy1AhCYglAcan/2SnsWnNmRREOQzsb4rTGFPb5WezGmbfM2v0xBgvCpeiaHdVrE/KvIAY2cB5"
    "kmrDJ6x9YLXw11g4N9OyNTiF7r3YHiC5o5AGwwrdzLD+QeCvnovuW2+W1+mPTCzDtxsXO5QiyIEUbXfq"
    "kPu1ZPBT6z1sCm/4YDquJnYyR+Z7HGD6dsav1aQYct/ZLRgkHxczCwrmljcpOCagJKd5OY6lHjhkHpm+"
    "ZiSPzdqplV1x4jSwpfWxkASBMnLTbDe4RYlQ6xsJsHfdjJAYX+Zf7m9hdgnIrRkuq4WEfEvNutdeu7dW"
    "JJW9i0ICH7L14Do1FAmfrm5SonGSklkRuU/Lawf6thsu6KNBSpAcp0r0s5MkOUm4Fy4nQq334IDmqJYo"
    "FicSSdJk75LxTeUoXf72pMNfQU+Ed/8ew2GE2IkrHVMCZh5VU76jKVR/YUkTKlmvicDfcQYCA4znMy+d"
    "bYg+hydncyLiRo6uombAHlqawE5t3Z4+fwt2qokZCdgdS+T5aVjhDWGnX3mPFS3SQS5qMyK0UJyjBGKF"
    "/j3eqFcSGb25EAMwjsPlPluZ1+FlMnfFIdbX66oejDlzy9mnh5Sv2HUz9hgkRgzrhuUWdZxGQ/VLZIKp"
    "FCOXURzTWYZINVbjC8Q2kSLux9uDtZHdbgLTa2ujfPhmq1dhOq+Zyw5SL+xvLOEENNfv25UhKZSC25nA"
    "LJLTfPbIzDvggfUhKCN+kg28wicYODDRrawOMnNnYDztzC3KnsYQwJtDRhd4iZ6Qj4HimYzH/F/tSc34"
    "z97587/+lWu4jvdPWLXAm3gnt03yCJ2Dt9H+aJwzrQ7jdN+F4ezqRFzW8t6+zh3c86FY5nzkezJndWS/"
    "oRMI39+aY6xAS+fvTS6hNZlI9bxvdUB6jJo0Lx7mY6FZ9pbUCQ5oi2v1qYlDcWfXgy9kGAbIvoNwTQFn"
    "x9l2JS4P6ZFlQuZzoHhtPkJzjSrBu/0/5l/UNkm2hadKfgpfciqzf/Mv3u6A9NZ5HQs+UGSH2h4SZ5jJ"
    "tPiWauxUfTTFp0b/gNemDOBbHhYA7Q7keM0BDjqo5Cv+wzgfx2LSpYdnIFNwzS3bmO4Pw/3iOmwZfCWz"
    "gxenk/xtBOctozJ1xpKzQPQH0Obml1dFjfI/rt9anXaXN/aP67fp23e2oVlRCIePL1nWb17oUeOYiuAL"
    "0+8K/I9Qfabt4pTPF/2AEwlQB0rSWJoDYtHUc91eh20hzQ1hw1ZIJpvSU4DXOe6s6+crvF96IEMpU+n1"
    "te4seyRyscA4HQxi/zEs1D36y0PILE+hWbcVGMSH5uVVLfimER9mOygcqWgjy123ru9wsD+dyqXUTMsw"
    "7TuO9DkfdVbtX8Vmzsppluvj2VqQr4ZIXy+n0g11Hj+RGXOlJrq1hliEDE9QL4OQ7TEI6hRCUFyOCTJZ"
    "TnQBs73HyEcW430PBe7IICChcUTOMZeGhKI8XlbJ0LISnTaw2JaC7hoIe72x3dBjYQ5hs8wbJX8P29in"
    "9nf91uM4bHuhN/C9918I2Pn8XNSYhkiNTG7RP/GPU7fam/RGtx8Pv8DLGYABNIEw7FKO/k2C5ELAEJ8r"
    "vvPStKFEpV8iZ4vQMPCFMTzEFCuuEWWZWyB41fHr0rqZrEx6/5RBIB2R4BDdTxdhji9kXVx5yzDvg2gl"
    "5z5yYsSxYWJLGn+o1isTVCw1ppuHvNbbWyAVgK+++rtD28tTN61HkiyWp5ZRjNpD6WvxeLik26H1CODf"
    "aUSsQ89z1DcQcvDbNciAIyRpFsNOVwTTDQn7ZHfc+ssUNz/D2zX+q6MBDO0UpY+tC+JbZ+kARP0S44ti"
    "XEThTHjFDCo5GRWo8bEgNXo9j4/t+9NYTpHB2Z5wHxmKMcyMxaDPIZTxP3zWyf4PMe14fT8lMEPR/+Ps"
    "vJUcBtLt/EAI4F0I7wlvM3hLEN49iVKppFDRfcGLWUlVq6q7yU4wVUNySLD773O+AzS6e9HpvOpuWjA1"
    "ZaTCkSY6jlQLx+mER7aK5ImmL4J7GeyBUHRbOPsByhtsBRwuX8/PKoTaewhRzmBTPnNlsAqOFF8T30He"
    "Qh9pKMoh2ZOXWr9pprTJ7LfCl73hTeEiMejuJhqL5WeyJ0YsKIqJbxxIVdGDnRCbl2jg8/sw34Skfyz+"
    "xq4oCprnOjNX/OTBzdXcG76geJGB23kOu+hOJrllOclUuM0q0aj8vPeG53IiIQfOeGc+3qjmuj6hSVLb"
    "aQ1J32IWU0YSmtjk89Lo5JmTnGQ5Td94Ef0GRBbSlSvR2KRz20h8xVpfNqFm10y2QnWZOVMJSEaC8bgr"
    "IFe0s3uW9485XHoIVjYTwQDdXGUlI+W6SG/N7Wm4Rch6hFYlBDTJ3/FQyDhYS9uOGNYSQovALEe1VFxR"
    "gjMO5DjtfEQfEDzmgknd3e23Xt3Y4rbBQZE+arxO9IMgMOUb98Y98irmebsEKuLXr5r6Eru3PuhiSWrm"
    "N3LzIj4Y4Gc7eeE1XQXkV6fqq2SZ2yLZVt33LwTNeux18sAEPd8a5yo2TgMX2gc5l6e+dq4zeH5riiFi"
    "W5Y1yxZPxm8VZkbueRhqoxdw5TKhaeR75MBLlaszXIVDSWpOBTAG9/j46ToKNPKHsQ23dcIxRD8dF9yk"
    "JeD++yMEizz9nT/2tUy0iCawWRbFyLQ/NpUsc5lMBGcdg1pll4SdvY23gsv1vI3Zx4P3kp+4fVhmniLR"
    "+rTwG1kZqJnn9leqHdafMVJAB7m1bwzAsTDUwVdqdF9dzudSCVj7pNobUQIjp14jv+Pgcs6vZtAXBybo"
    "XC1GEKjJpvrLC1STWOepYnWishqDZIynNI3l5/N9UKYu5Ps6JP6XlY50hEyA1YHvcAfAczh/Ks3N7hwq"
    "H19e2O3Pr/4237mXpB8mcAVd1wgtFb9HtHzL99qv/Kn0mKY66q2EnWwmx/3aN99cbunzmazAWirmfoCT"
    "K3aC++EHrfSJD64THymNMKHMN6lO6zguA2cbmhrASRdEM/jJX4pIT30mKok+8iYDYC+4ixs7hiczsnwW"
    "Zr5QScysHV7s8ymTP83Tlw/Ef8y8WIu8+4Rs/1hWIOYoRa0S3oiRqLEM+8pkAHy5O2GyUmqerIz5Y25V"
    "6Fe8+UU8IjzFcOIytoM4zFRpKd/9mN3HTvuZZ1cpWFoPpAvbGSeb4CRFvJ1gAGLnU0Vq3I2Wq3hPhqbL"
    "G2UDr0LDCKTgbCBGo4qlt9hFBO+PFlsPNVcBos1mbSOuZY9GHRlVAjP94vfxtNabbkZ4e7KOT3yb9zWG"
    "m2D2ScHHIecz6iLnVBu6rhkJJztA2xbuChuhCkj0voYNCPqBLxJZiwzeC2tMwsXV2PkjZP7f2kzwAeWT"
    "L9HMT3GouMH0PEf851wbNM6lD/6cH4CihfKmyu7jUaee9jFF21CoP8iI2fkTHsYi7dWg+I0XxEYa7/aP"
    "1PBAx740n76ha8D79FPa4q/SmhDhUascGnQgzZ/SyngcHJFN4hSG3+n7X4sZTaOWON7nO7XycKrfXlLs"
    "yxyGBreY/u1W18R9FQQ9wHcIEBNEnKscGikE2V8s0+uvSPybH0H4hTEgS+jdS+OGTYLii0Ean1UG4p/P"
    "x5anm1/sjQ4hAqI3OkiDf0XBqwURynk7zgsGbHZsevpo9qo4ddMBpocmRA1jRXmAA4UrGbfhya3nhU0u"
    "6qyZXaG2naNKgtCmNsYx6XUHxXXp31yigeQ95V/x9f/4d/ia+Oe5zciZw39zm4GqRBK4WC40a0uoL3Y9"
    "VlKh4dI3nXJ1DZeiw6qupoycELZfxn0/IuDqTRjElBQa39cYvzHmN+dOs1C4X4v5BWnta4LU6uHM+HHz"
    "qy/ma9r4E6foTqPT+DfXmbie+stUH7ckoueiI8OqzCKnQPwZn5NNUo62nLrwd3mCV8ISQ0Pr1MFZ/Kcs"
    "Uj5weCCC1gAp9ACL0CZ/kOItCK/Om9GkZC3ctSkr582EZ2vGx2EMPQ/fG/97JDl8/H4Do0TsLGdTIr31"
    "MFvR8IA1jYKEEt08jwHyyYi2Iziolur4E5ZHt5BHMhHkswVwlODzSvCDwpsYh3Apd7Vx96RWl7hlxYlL"
    "GpAwCO8ozsxO7Q0KUfU9rO689obXrISjTXf7DcNmejiuxuQkI/iN6ukLVW+vqaYxixx3Sv63XxGNlXwN"
    "UDJ8oxi0muPbHif7dUbmTCozEiYCIkOd/G77TeBPkCR2K3hC+2L2a6HPKL6s7U3iG5kKcwCvR/KM0yDr"
    "z7keBEn7g92yNdg/MrSROpJ+Yr6idxN18DnEC1+WHE5q49XxakrwVCZ0+9Vz/Sel2edieT81yvd5u0gk"
    "Dk+CyHNOjz4Ox+OhmMGRNr/83ILRbSPgVB53atKCdqy/k53erwTOfOIGs3bVuGudPWg7NZ67LrMZpqJx"
    "Lqm4u7+EfbSgXSWQw4DBuRW9cWLgQygL6TU40NegOyPUV7KI1iXh7rFrlWQgbowEjJfIzVNp3/CbnN4o"
    "TrV32dytCM5TB8FQVsuo2A/SffgAfyRYFZI8EFhjySM49bqLLKunrduDk4uZBz1OegYygmIBnSiyTKSV"
    "KhIsXuO2MugbLpPuiDqL8Xn8W0ymLHXsxNhr7OY3RyXaCvMFziugGMn6h5GrsjoZMLk43WRo9amSBFI5"
    "enKM1+TheYLNN+JU8VR9rCwEln1J80/8C77E+OwmyFoMCObxVf0xRPOWMcTz1vlyhOFZ0EuY+i8cmu9m"
    "An6+XhG1nDe6mgbb/2YIVAQ7Mi8Bzwt/zhA89rf2pIr8eB+Du+ZkIDiNonIJy7mtTPqEefuKAKrX2B2h"
    "t7gI07T/yVr9IiKi0q7NGyfzKZ2ty2RYzwNAWOQiooAlFi3raFl5BWeTHXmDmF06GAuTXOfDHFuY8c5O"
    "5L/0VmXP3aZ9UF/BUHniN2gDLkHwF5u1jvOyvIzFrWoTK8L1DkHaTJADHFRbeN1HIL5w6mfIuwnpcCP/"
    "9ggwnyxMs1SkldbRxCfMbeNYZHRLMr3BKDgKIPXt7+eY+2bwUv1Xu6H2Hl9j/F2uhPTugeB7r4FfBg03"
    "ZVq4NUbzHRhD/jbY3yWmg9/pHwO+5dzOUGVih4+6r4/Ejg1Dn67Gwtxw3b7lV9lC9LT0pr81NQVFFiAk"
    "SZduzjbBFv2fA40y3hfNBTCCDNh89aFOi71Z11Xk01B7KBNAmebQFL9yuGMIuTW4waubW3GZ/kuy32ZR"
    "jQ8I0W0U+aJ4X9/PzPTPVWPMVc9dt7HG58q/MWp/hmQrsqAhCse3xFexT/ZHIgp6p9/2JIH6o6llhAWB"
    "X5+dU6iYpNogt5bMtswJVq52cs0NPcLTCyw8X56qtcGoxT8ozqEk+IyySMg5pPuUKxeKqcdBWuBJnIVo"
    "t7aeFMqq/F30zxdzk657Ay+8moQaY0V/hTlM9tSdk+vGop77otLV9vObhTelDkuZ370RoPABKUxk/cEo"
    "+PNE2XpLVxGfBm0/oh1uaYmXB5y3bBAVWk1anBoEInvh/oQrxuvR3squZkVjC645lVl6Srhj0iAIn+i+"
    "rRqH37op0bLynmvl3KILDDE98/WbDB91XNfBuf3Kd79Y6gG/erOmI/DfIG06puQx/5jfofdWpyAhA5YI"
    "lNp9jFSnZuno7Vg/DgN6yN2vLarzBQ/Ni6C2t5FJj3VaYKPUMqRJV8aw85sKhYaKktBjQRPkRit5btrX"
    "ptIvrBG59G+vYt6d6jIndP6s2Fgkh7Xdgq/hD9cFZKaWOdLP7tIOzZ+TqFoyqCnwhjhD3L7Q4jcNaop/"
    "a2CuTkubeY7GW/Tsg9Tks16rrW+Vzc9Pk6/GxrkBMAYT1aWdnz1DlVlzaUtVfYE8fhQH8EWQdy9L9L+e"
    "EtBeQ0br+TpY8RB2ouchY+vAp1Ol0bNX6UogIBHJxKRMBKaDCy9dw9WuH987mPDrUu3J270Pm7NhsZpx"
    "mSzPe4j8QEguV18qSXGkMupOTz66FUrtEvjALUsGYkPKBC+JrO/uj4BKolmeSYbFIPwFqkelhne6xk1/"
    "sQqnFsWYcDy0cc4yPPGHM8zhNRFSgrvsdnAFXsGRYmBK/N16U8KiWI0ZcFzwHk5kMkDLN+PX3Z9UXrUb"
    "txOW+O5NLihyZD1FMkUxOPLjjFiM+G4+5i9DnPJZefiLXFxZ5kJtOAwevMHK64GUJ6tDQi+0NYdQyEaP"
    "qAgO5QG4rEOE1pobiFU/y7RFH7t9TLsLSA/bp2vv048KC1ArjOhCAcreZBUe5g42G8BJHhai4jrf5tgy"
    "F94Jb4UUX2MVchR/Y5y2+0EDwPrsBGF6WRmOIrc/mobKiG/qCaJsO5GrGeqEQHlgGl9MXw/HgXN/Nuqb"
    "TK7nJN60JddLSdHI0C34FA3rV7+TyD2xJOa7cWbBERti7Z30wvoEiTeJHPXDCp9DDS4aeyXKlndUnz8w"
    "BHj2Tq2rBJZG4IANDCDkndZpk+BIhlx3r3old1/r3VeRO0ONJLcf49ym8Yq98XwGFqBxngTnX4aH8gbl"
    "BlSPd6jI42lP6Wam2dz83reqLJe6DjtQYq1tZrX3LTWEGKdN4E+QT8rqc0AFebKDaeUxvipkbmaxnr1v"
    "es88ayA48R1OAQ9BTPOKVARcjK/rBJMrH7XrK+fLRwXP9oX+8q7b7RxXVRBYK9Yoc/rrxpBAR04Czc/S"
    "4kbxlErLmAPzKJkOmD9gnM12luDcSR5eZ9AHajSE94kzohALiiqGXPuvqszTsmafLymAIcVt9t5ZRcPj"
    "wAuAuMyvc1F8DfAGMH/YFB0qvko63J+lFstUuICF3eSxtmA6lfIjq7PBNC1CP2E1jYF7iYnjv55b/d/+"
    "97+zRszW///3RP6/NWIoshufCb0euZauBidBRhs9BVY1oddCds7URjL9OXRWUdC1SHEUgdloVfhpAvz1"
    "1I/UxI4M/Vw3Zu7529nPkqhKW9ihmiU6r9Wxfd1l14nYNQMJFbUljY4mOm/gyPbZRMSQP5XQ366IqB4h"
    "0DCRVQGgmJefrNPnlznvR8+itB3Okhj0VTMGevVFXwTlKIse5rXdweXlYTDOUEkNQLAQcB3hY8lfsgMf"
    "qc/CWw49Z/Z3Vzsuajpp+f5+CDs3YZXBIQ1VAoHJd6Bn6NhRWTViirSXKhXRui288YFxwRjeJ+r+RPpC"
    "DJOLEL+gvY9AXBhDInf+N4xR4ieLHiV39ob8ZUaKuXtjM2WmhCb48gOZgFNzU/uXHbLniXNqd8m5BXf3"
    "2NWGnb0m1L9g7gve3z4kvcUPq+IYrY84FozdhTWJdFzSpXNdVWokoAI4nxj4WN8WG5BX/sQfDC39tOVn"
    "wER3/Igt63dsx3G3BpLa2PzjHD35WHD/9twnr5wNWcmBBhF6RuayUu7oHB+L+gHNp/8hRg6uoFrtdOxn"
    "xCyo86feiqZlLiOJIZW1e5FT3t93Ux0IXzaxoFyXE2dfRf2pXpasSyRmfl6F1UAL9s2H1MMNRofr29Nk"
    "oEOldHCIIX1cXPpxu4R6hZxFNK9jgNXzOPYNHRkafVv2t7P4BaslKIWfbdKbX+NfqRvoJz5LDUxNFvl8"
    "l10iRYq4yetMkGqeS/ALJEW5h8GA3dypQXsvnUFeWm5QlaGbx4iRwCgBfV3mFpja5bj4FBgm7Hixps6k"
    "Ozkrpyn4krfzOotDlpYb/Dyi2qPyx5nB1xYCgKQVkviCsyJmJVLtH4mUqx2Rg6MNlh70n3ahaUxxaADu"
    "tAQg18T6yN9f79lAHPByPzxfA7jv1ZGMOr1HkCoUAgTA9TKb10Gto1RTjP4c2a+OR/p+awhw5aDqgtFt"
    "wd/niQ+U9hwhuCSoquVxas/zLtzjOJT8IGsIQGJbrXcNEltO/K3ESj2WQ3BJv9sSl34H//exRpzWMNOi"
    "PebCswa8MHvYFvI5d+9OAEz9/JqVfr5EUcUqqUn0FZ6qeEazKKJ+po8HBSPrznVf5AQKbP/SPu6MBOrA"
    "A9ld15juRHs0eHe1T4Pv3/Mhx/b7YFivOhuRKna9HeWRAuZVtOhwxswIgtsnMXaafknKXlayN6euUM5j"
    "ECnJsDJyts0ynfRivtzqAzc8e1poB5qtrN71Rvp8OsBKVU3mSh5dWuVHDOhCuC4K32jsrzTJMalIiGxE"
    "v7GysshaPE2zqlQR+IgP7NkKIhVmgZi8hwtVE7R0oYW2YwTbmihBSwiXKCLQX8fpLw8EvPb9zqNKnoe1"
    "pKKJgDQ0EMfxW68HRC0RrirlQZdMogqNkewYA+f6xx7WEF6tT7/uBQLHB6qsHu9bip7oE7M1yFSp/InU"
    "qeugUuHGbLBQQuMwhY35tYbHMDWk6a5ZmdVIF9VqitoUfMPzUkGe+dfdnejeZHcnyOLbFwB/rTEE2FEO"
    "9reRQ0nP58gjwLpxptf8PHkB0LF+cSvpUU/+zgEnWUxJ8TG+tCKHmU2AGuvM26mXx33fGYyZ35OKnLvt"
    "jG7YQAuTmY+8rUVsa3zbizf7OhNlx72iob6gmb+b4PdcEi4dj3rMhBym389FCcTk7kIJFmj+DgKo4cYz"
    "6Bn+VvMf9ALIdEH7Lws/HkUFXB2sAcwl9a5wW8oI0Dq0t+yXxeU5rDdapk/oW+d+qWJrqRsqgN8gXl9N"
    "2dnpLa7xMnWW1Zu5y3p+WLqtXLWdRzj3imuV0gOVmD4HJpIAV1i+4R/sp3EP/2NxzJByv1lTPBjuKiVT"
    "a0byX+BHDlm5CQj6MnCXhxz7Ccrf7hghJ328wMihJS12Sr6BMK1/wI0MZceFmlKyJTYiY1rYmSggDDP6"
    "Fe6iZxncOtYsMAT683UqzocFeSIdHb6EZD76DZgorNF3xDgtb9CuPO2cn+5IBqgtsYwnuzUg+SYHPz8X"
    "q/0KhyugXNZh+NGvIkf/9nyAuZqYLPy8AuHQ3GnJ4YD/kqQQWLhcdEWCiFYwE3gUOsTkTFAdsLNV21fI"
    "OgtD/Z7+eZ71orxW4jiKPREKNz1ZPvDCTyKZ8MjiqZoU/G7z0cey1rwiFCZf4pMXPcA+H+si3wKO5fsG"
    "N/QOzWltBkE2BQp2UTWZTDYwvLSGP5emuL3rvAgqqniSu1IzF+/fnjTHXDROi6pTte1/0m96l7JKWvXE"
    "ruCPKb4mDMlrQ1IYsC5+YC28y8tliiWeNnyNITtHDq8XUz/nzr8n2EPgfS4dbSXHSD/r0rioMvwBTJr/"
    "4D58JgqNQzN45Xb68PtcI53JJS9ENYDDX9SCPuxr75Iy1ocJkPvnuTZF5IrPcHr5jbw1vXZbDVea/fRB"
    "fUgFEvSDZ/nVGxMhIx0vf05mj4WKkf+hlxmEQkAzz1uaMKcVPKLAlXm8wgJen2IthyXvvVCwArFwpFYs"
    "7AVyrvsDodvI49kNtudOCBNr/22Ytkil1XV/SwBXyCYUvvRRB4r6rr3b+XC2234DVfDW01R7m/zrjNkG"
    "WCZUzfdrVcsIcLcOnbRZYKAYlWv7xhXNyVrn12BBcvPDpDYEGOirlnI3qtMszfuiyM5tMNJHG1Gx5vK/"
    "E74xV/0tLqlRupgC3is01bKAlrlXP/UTUn0NP6/D6Oxkf+DgctBPilf0L7gihKcjnYDWhQOGcp6+l222"
    "3GSOd3o2Q9xQIv7yHKQ6aituGKfYhuMO1297MeMCLtoKqqKgSgMaUpwu13I0UyxObJZ3csiZ0JuAW7M5"
    "cTpEl4quKYcKF5q0oQItdXd1EwF5Jg+GRive+E+I+hItSN+1o5DfEyRrcktqRHvAEhnHQn7VULxgSWeE"
    "+RUBVSP8T+YfYcOYO5jqsvARNhs0eEraibBpmKCl6Tj4NjnYd3ICFfJbo3NXhuonNWE4AlJKdYpZfb57"
    "R3JYyakAVEGE0GEcgnU8ZR3UZz+eMYPMpPeTTkNHeQhFX6UMLLR3I0USGbosrpLZGcClXsoH5cSfhBnE"
    "UsYtdgvOvxsKH1CHknHeQsyKe/PD6SQsOisxyI4jIOoRMdfpgt+gv4AKASf0RdYOxWHc6ru/fSBosKat"
    "qyNHpwgLR1izJUAqMqid8WqxOW1XFxl6vkWIcnSOB4ZyACitMc4cyytGJKPTrd6PvWpA4A7eb3toL6lp"
    "j7NF2ktYv/eRsn/01LJI+kKvOzfHE2noD+lE+JLm1udzpdm3gyIMzwhHbRbJB5blryN87HOgi76jZGzM"
    "DZpqO0HLRDn/3XZwKNFLZv72WtJMnusLJcXKZGUFeskhVIYFy6V6RxTvw9rlsLhhLee/ugbzP/+dLDX5"
    "/7SHQcQWRTLKFgUeBUXQu1ccXmJAXqFFovS9XCbSW9p6aZvb9/X+KYg5z2SrhBJTFKOQfwMR2ZYycYLO"
    "537t3m7rdHyt2dBx6E3Aoj8lTqb1v2HBpBCa3U+Puipf4gtQUdUKAnmiAYpGECWSADR9kQ840CNeVRR6"
    "V/glA22/sYRh2XuPMcSHHHqSYgWzdoCeUn/k7tNRjQPAAxZE33pAFrIRCB8LVs7YQmUAqIxnxd7jkpMG"
    "eGJqGUaf6PWAczC0g/PVLEh6KP2J/D2k3dyh3/G4afMSwCovjishC5YO/BPsFPH/zHlis2zoYuCI4a8N"
    "fSjggjcbZe+FuWqLtcxPPUGp2xksVI3qrBxH9R7FUu2yvNyBHIysPAUBcbkg4f/fOU8g3vqZ2MImXi4Z"
    "NMFzk6reZotmpzG18q0QRePm9refiM8KgdqXS31XsobvkSWrGHx8u97qF1a/01VhwS+Gzy7yt1K/5MDV"
    "t5yAlzBu1XV2fv71cztYYtiNlcyA8xC5HyYPo2S6LA0TJrNOraGh08rYLz79YaoohKd1OwhZNHsdknjx"
    "KTrUXW8Rr3gBXQ0oI4vd5ZGXgpvP90rP+PNLM/bXJIbbMZNtv0KqBNAPCCfLDnbigpAKBKaz5HALdv2r"
    "ZctClJEf9qlI4OedBSdDwdg9sMlYv3u9UHSp3Qgt4Dve01RwWFVTmDdy9z9nMmVTx19/IXPTGDnK/U5l"
    "Lf7tWMZBMW9KO4CRV4jgAmHfTQ8WqKFpHK26ue2ISjnlfTRWLZgfwKStFy1Ft5o8PpSFGWqR1gJCUUoX"
    "fYRBWX227yCsmdpeJvNnwOwsRTN+4w/Uyfzk4suWDbReSo4WDdkbF42A9A6pGyH8JmmoWMQhYxF/GMcU"
    "cz9CPBQ1+RaXeNAUCi7lAoIR5O0oPx4B8zwJCAGhoFeWcdAHYctQfW2NsCuO3SWOhm4SrhlRJA8Pp6ag"
    "nlt0dOGcofh1pvZJNx5w0dtvdjXcdKMD7/b2OYnptN/Nq2VooZ7fTFx9vPHMV8v7BjloQXt2pCgpzkkF"
    "g46PsD3uXkLrcbA9xas0ssyTbJqAkU1PC7oIlE4HYRPkOv2MoJcUWqXMBo532to1s+r4Dphz+5I02QUE"
    "iI/mZlk8qy8p+vg7gHax4LbKj9UlTgg0qIFD99JyQaoPUYuCQ2nX/Z6Fvf0QJ5yIr9WJmcB18TaZSXb+"
    "Tra/WjvWfhZOF78QNREcOe1ip+9aQIOvHsR/98qqax+Et0nlGmuAgOWJwq6tvtbMlnfcsgU1f3ehTIpL"
    "HwhyvS8ZCdX3w7MWmTd+T2+u4LfyKuI+1M24WVnNc1OYXV4s/+XOWYHzem7pOTmJtIJXjbGRwY68fQJV"
    "sh+oinYdHnxTHN6k60Jeu0ixFDHIDwGsTBxWmQq26AyYeR7NPId+mPTTGdEG+IBbRvyafRav5i6s4zI1"
    "UvxTjl48+RURUtwmvdP8As7JHobF+LjFZ/TDVVEkpVHG7wAjoRovzWkK94Xh8swtUUW0SUeDsT13KpLi"
    "5egGXvw00GTotS/YMdcV1KT22TLtVuG6F8YIcj3JWsILudlFT43wGdjaAQWE9TO0yWKzo8aa7/iGNtwk"
    "3hqus3YajRKIYa5FCiWwffku8lCkX1l3RuTo5O7JHzPtoc+wzGGLGqapu7qJGmXO8ZujrLNWAZ7Sw62Y"
    "CxeXukmMZWyQw6l2Q5vwfpC8nVtuP3wjNkuTYuFHmF403mwJ5qVUmXOP4Ge1hyPctAWKiUdBf5WcH7Gf"
    "6+FPiR3KqKfzJObh5F/M1NjAG1GpPOaQOACiOvmWdSTxIlahGC7yEjYbt1E9xme2G6+q088NMI/NLjkv"
    "ztss+svWOYmcA3KPZeXEuCsa0S2lvyoiuVD6WA1BEtN0jIWvQgx08rBMMStqqAKFUfGcOY0m8R5TShRS"
    "BD8uWbl6fkTXuKDL+/jbGXmUxxv72atmK6Q28NtV+MEZq9cPSmWeIugWEN4L1cn1b8GU5lpUCQKa/EWY"
    "QxIEVTjPIzlzVeS0r8UU6UIgpsyHR8dLsCejBMs/8N126DV8CxL9+iHxVq0JVuRX71DoMsJZgcsf35LR"
    "Bcb0m5Nw4+V5ixw82PHdWIxAVK0X1HKLiAQ+qGqkzOchKBO3ZG6e5mVR9qgxG3q0XLkEcNmzzhyYSqDn"
    "jspErmiaEjgm00Edg3F9M1wJw2a7yXD7i/8Ew8YKAG92E2Z9OGxMQjvvNV0kKmvnbLsuTMlZmjFsEy2I"
    "ktNdsUSaXMtUl9E3TG/OQrqZgjSLsdnkssKZRzzKwYzgAXFiiJ3qzmMuomjA2bg8DyhxfPslx1HCE8Fv"
    "0iv2qAFn4rj5oiPxbR8yPf3RVkereLM76JOR39GXH2BbzNDPTgbp0PrY5tC2lGNJ93valr1Fm4fwU73W"
    "w7Z4PP4yKBM96wq1tWNgObNQU9RKaVraNn1WUIJRXaLX7eMLJ4D/uHj7cQ+lQVlTBJurt9XxZPF1VCUw"
    "uujPnleVOX92YwQ7NwJniX1GSKdjZFSYWZkvErzrxFPsU4RqVQQM2T+CG69Y5EgDl+KGzCQT6DzQ68J5"
    "4ZlQanZ1mKZ/YhgTgIcXdWLbwc/tNq1oBtkdqsaZ88m7q1Ca89gjtVzpiUk0uOL7Tc6y67tFSpqrFdWg"
    "KFo4+ybz8Ak+MWOdJJ/RVj6y5XiGlozfxdgWut7jeX7MF6rMgKfn2UXupv29fxhhYSLM/vqgCxM9kz2g"
    "wPrg0GQJjwc6SKhy0dspb2xLdHRDgT+lY9jRmZ2n39R2IIRsSoKYa+4ZPDz4iZHfaSdUwlfgiPhR2e+m"
    "M0EkS3RvSHFwkVUgsbfpuXBoL/3SXGKv5cZbfFi/D9StOJU4DixY1a+34sagfWKiXARETK8c+jyp4VGQ"
    "ccj87xYq4EVhACgOsAq/4S7zhwWfdG5U3+aZMxS8yyKlKkCt/s6nWYcOIOtJcuH809LVbsoeJ/W0brHl"
    "/GD37zYgFECEkS6iiUYBTD/I8zEPOTdIqKrMEnjf5cSxg2MdZNtB8nkbeUMrvKbCy3q1XpI+QeKJPqyM"
    "yveNYqABl4hu9+B3HvTj3oKB/Nar24uzzXAcjbOiZonaZHVqvuDQ7xjq8YCm4kMRwEKWVpxLZdHgL7zW"
    "i0Hp9aR4QxSznN4GgY/QoTVdAzUkNS2UdPwiplcai3nP8RvPMg2qHPyjyWrbH4Ld9aCZy3xXHNlR9uPf"
    "BpAzUrjWz6EOpSOi++qRLFWizcrzpCKpnzryqQi447dYiHuX9TcmTZuXa6+lgNR2At/fg5Fx6ZmH6PLl"
    "ud0Wu8tnTNqFRBMGjYDkDVUXyIgXRAJsB1018S+uP/33f2feWiH812v75BROP9bh/FxE1BzHCdunCex9"
    "SNPtJ3icS8yoI5mrXrfxF2uKzhCesb6l2mGghm3Moemd7roUd3BnbXTjQKE5P4DWTY8g65HdsrhIFB0t"
    "E11XC6cIqLF/vkeqT77oaFjuIAzOx4AyZYep9tlxwsrGzIPEfm1Ayn3xiPLiPJEbOv1WJg0LduR/TvQA"
    "gpVZ7uxb9aDdOtbw0MZzU+O+a2Vmpc6eaYca7U1fawxvXnA7mR2xPDpERyBPVciK6TxkbTKvl3/z1H52"
    "6UTHjeCRu4XfZ0/bRxuun3Y6PsSyjBgzbq/3SnAIehtz07BPSqkZIHaheUFh9F6poof8TCeaXHT3I2BA"
    "Na8tvbhcMHyhIgTfDq4p7ffb6bBZrtDKMvFZOGIphFSAaHKbQIMbO7M9+pTc1HlR5RvY7KBRq2bvmbhS"
    "lpSZcciXvr0b/UKbh1JcDeEV96p/K0Aio3R+zEnsfL5YqZsK8ZXDeglg3vRK0fwwRLrwDDWGQEa32ea7"
    "jhSzjpS3QLAAODMOpLkVAY5pVMBhzXTXniMxua/ktZAi/Y2LlW0wphJ4HtrLiWrx3rCgquMIkVTU0QXj"
    "Voo5sfsJew2W2+DWV+WD5sqBt5BCEknc6j4uI4PHf1FlMCiWY844p2eJG2tr9nOXJaU3sunGJXL7L7GC"
    "y8D9czJGaKJeI5xBkzj0t0jw0wdvwg8LfM4hkdWrUaF/zyx9SreVUk7i7I6RG6P5pldmk7oidRzn9oEt"
    "OLzkzt/VrQDzjfrS7kT01ZCuYJUIt1Q1bG9cgKOE1lezdH8Y+5f7+dumkAwpwMN6ppYOj20QCrNXrNlx"
    "SZUZm5Oc0Yj+Ln0OSTOCbLfdYmSuWNSExA2hChmh53Wo8Df6+/Z8iIKlsN/6mO+f+TD5OY9oyBLbt2lT"
    "pry4IS2EbtXVyC6ebPn4wIHKhEfr+qOzuqnDWitwrQiphv6E/cPi3ySh4I0Pl2FkWMFkPow4EWnZ2h8l"
    "AVuKkFAvHnLUZECeNBjg4JgnDm6GEIIuvZ1IS4wTeLbFlz6n07KYhGrJ+UnZ3K/L105GMpda9xHYVtOd"
    "n9Bsom4AQWTHmFY+UgdEF9AZJHsbRcLFQsiXcy1KqdRODXsz4Xee1Gk7bFMIYFvocGYJuTr+irxrKhHz"
    "UyQRYrqwZ0Aaq8vXDNzk8WCYO18Vn5hvJ0icbiQjRj+9bqFWR37o6x7cCXAzpnsOXQ5Mxb7FSLYUicoX"
    "0CSt7BHO75e9xcknMmDSO96GxTWPWBkl127vGT/0AB9zWFbyM3VkKOPZjYgkaZZZhid6NhuK8sNMy7Cd"
    "Vamnt3vpv6f6jqdtLUulR0AMuGQvyMsRHRau3hIeN81/bJPDGTwVfVbA8blIB8MSDzwdnPjIqgK6esx5"
    "CcHxwqgKO3O6TIDqienn6XIf+mApBrPWoGd7KZfCeDykgcXC/CHoH07vQxM8rjixJtzx30wneq2bPZed"
    "/eGbhpkcGLNoWvMqLdgQnWEl309jDbxTQg58kaVndHhsj2AnCy/LajZYlHbiooc1pd/o2FEKTGf6UBon"
    "CZJ85Cypx53GEQyMNF6u8Vw/mYv1tge/Nb1H800WlYH7rkycwmF3nC2mg8gL70hcnO4mkEPUYoj9SA0h"
    "UYQVaNloCCvdTXrKgLHNe1Adu9mT/ghwd+agat4ENCSjDd02FM9uOSMw3egvQ1TTxft7PuQlk0+yX6+l"
    "6QJRb/LBC9iSJk29zqgI+Tu51zlM9UdQ90UfE0I3d4x/mnrIibA3sLAlKPySfLhenU4ACnUwvjOoVSjx"
    "ka+O+Syrz6ZtORzudn9g9XQnnMVUOYshlQtjOqlQaolxIVrNR+fl8vhCxS9n+qmLTzZ4EGQxr77ovJ7y"
    "Jbn71njKYUn/+yWqzNlmG3wUYfOnOLvmER8XFvipsA5gTbtHxfSNzh/WHgv8Szmk9rz+50h147zasHWy"
    "wQ1qb0Zhe65j8/3Yk2dHeuLk4cpB4V0Pvo/rqjSo8C3chicGzaH8krHKZHThXsaATyRNo+akhMJ5m62G"
    "KzlDPxY9hrJE12p/DutPDm8CU0yNiutcZqUfSBdxB1iOYXRugU2Xczc1tWkDm8LUMC5f6Du7bhz+Jt8n"
    "6q+hwvVb0f5af02PnrcvjJXWzAykeOLREhsr6ld/GzuiTi6g7CBK8y8WXZO7baXlGVRuEGuvdvtnwtS8"
    "Ik15Gb9FGr7ApEhh82Nf+E6weMt/aQ5f0N+OHd0kanV/i6H5nXHicqy4WnHz8Mpx3BY40AOD+N1WiiiV"
    "J4xJIZ9FFTYbkKIjm3kSQiy3Ij68pJEyR19Udc5h6QB4fslh9KH1OOY/sjoR3nkOYCmnRgRgcYyILGDo"
    "t2wMwhBxX3z6KkXE1GtffmkDO8irJ6UpPKV3NKVCzZRH2YSrblb3UqyE0AVAb6BpudKlQs+ObOSf4drN"
    "C8d0440S0M+B2WfijSlrE1G7v1ud6ffanJFYP51wjtHGTcg66XMqKbKHOV/y6qqwAnNEMki44XNw8MJp"
    "3cnHVsjgCbZwywZ5JzBbnW+jgfDvaEjG22X12RtxT6INT8I933DYA19Y81UXh5aiEfQ6lpoIGkEPnkeA"
    "C164T7apMnrsKWNii6ybD3HP3YH7Qaln325imQnZXlFiNfUxvWxhsSgOiZiuegX/tDZhtEEWEcCXRvGr"
    "AEd7t2O/zGgPcoAjHUAHTYlMOixgWON2IGOYE4Reilcq5XR/XufJTdoc21go02NLtZ5vtxdyVPN/C83u"
    "llFAtEp0oQ3EjwfVR9Qy2bI8/H1ngMyS0ZRqv2xd1AuZCYkXuzNoO5zQkoqyomssS5RFdPNgM5MQo0UH"
    "LbBlkJ/lCEdKsZtRPvJe9Cd1a4XJ01bRwbVGTo+SwE/agjk36YsDybOFV6fACQ6IpdzGxPW/WmPof/3H"
    "v8HnGvfPawxFzt/8MLkC9zwHQA+iP2uYGCPLEftpf7CYmcSt7nuy/EUCYAfBesSwFqjfToH5HZ4bjp/q"
    "KfYj04gx1Ma12A7NgvFLWEhlyQ6kzlJMKTtrnkPOzBrScXbR8UDRxSKxfESMJfH24QXuaNmRiqLBV0Qy"
    "QMinuWOYW4NKEKs8XxBoCRg9qf9NH6t99iAXmMAXWI+25FwfEyisFV9/LaUgRIL48OwC91719V6AWCcI"
    "aGHHS9Bn2yKqmscbNDxLxDMNvDTY95ixlnHqTm/wPa4gqBYiSQo8Bxf2U5tnd0VP9o3UHeZjJAdnOgNb"
    "Fhha13lZ/n7xuBdNsykc+9PgmHSs5qiAWR6QyLakfxcKQ0Y4lAUfyeJ30ASdbtmIb91a8lpilaRIvrkv"
    "TG0G6VJhvfzL8COMTXhlQsUIdjSxDkRBOOTXaW09hbexDb4gLjwFSYaf4E2Lb8S8oelFnHM4kr8VawOC"
    "MpHtDZLulfTLiVbHs4K9r0dTSyT5DgYXRhT8KM3qBt/FByWLBz+me3E98ksSRPIOuK+3kdOh4PKbWsKg"
    "PxZzjLcR3QYpJFmEHnMB29GjWC2ugwketnAmQwHew4CC2yLv6F8Y4J8Epzdg1V8eOTQaQEjj8SFR1qFZ"
    "KrDQNH7QTvLNTRNlXppopeLu9jjId8r05zdDGxbIeINc+fy91vmQr2MqETnqqi36pCmPjMB+VORNluYX"
    "pskzgqgjQ9AKGSF0Mukpzb5PcZBU4kbjGBSWIDDzEDXdGx0byRsgwkINNKqs4Pg7XfGBQrY+QjwrVdAs"
    "kUZhK6vDJnObP5W1tVsxh7ONy0D9UeDXBj1KA4ILuCQnJ7dOBGD18JT6sU8jgjbAevOkF2NnwykOZM7p"
    "/jSQVbfFMqJd65Hh9mTDkyOT+vvNiQp2O71m1TeaGsK3BoxSQh8ZlceBmAabL6k5/B27nfXQfOMM5m6l"
    "qPEZPYX1B2tNY3vDbos5eeZhTkVyH5wniVQ0L8JLLr3mWtmpnb6Dlum4AjD3fBv4Sr6sqeVXZyfDrtWH"
    "WrkOZxn6DUMiWVgkwk8aBIth8HOcwA3iIAxa9eN58a0uxUhs3ge0tGiVONZCVnXTrOCeXkYosL9LzoXR"
    "wU/2YBA6HH64CJhtXzVrnKo+aP5c21Crs5m0sMejiLmFeKTCrxoQ3dzmpcvbo3fnHKMof/W9M4sYecfc"
    "1xt/uAl+vsFMZIjocwqMzQ9f8scXZsawdmq89Rkf5ta08b3n5X9IvvXf7mSXkjptpRO1+sah/QHTh1sz"
    "PBaqDfNydPJJ3n+PBUvCyixRFbrWF/gBq8cykkCuqxWwX+pxdj86cw7iv9HoVNisudgZ2M4Wp2BTfxuq"
    "NH1m/CIpJka1sTuUFkuTEKwHLV1IHj8Yz10pJKnSXpqAhqmExqXj7bv7tXptLkixcaDT8zWhF9bnzL7i"
    "TWt2byoV8mdrO6zr8BJKyNF9tCpEmc3e7zeGrsr42y79cn5LjE76sJOgczK0MSxZJQ3e+RuvsJZp6FrG"
    "63LhwEqijxrlgia0zAAn6TgC23glU0mNoygNL8xekT5sUcdhCyqodgbu8OvYz02wkuRcTocJq34jQwX/"
    "+LiRauGpnATIx98Zy5n0w0UsZZPoaFsQ3zx/u5zBlJYJqb4B7JJA32oeomumTa5BghNTUywvWW5Sucyy"
    "QVEIVKFfyor9l9IM2V6TLZqjen7rnUt51fiy+nNCNZdFDdV+GExzdUyI4F8QbOSVvrhZqK9trCURd1SU"
    "RbfOKE23tDs6fxVqdzT36DTuVZnvOIDqE69ZaT5XspNE0sKP3sNeVEK1lmQMu2qG5AYUnSezPFDwN4xQ"
    "eJSTUdRn4oLKXEzUKS6oFDuBcm38OctSuAZs/45+mSzdK7cCwA8cl+sE9QqFK03ovUUJuuFM53tYzVUM"
    "xF+jra+hKggTWJwtXu4Ws9Q7wEpFb+teEFpuVDXD8Qvyug8Cz73J2PPYqsiEujZUJveptLwcq7FkUG1X"
    "U5J8mXJFP6kX+gyj6X/z6cbK07X18pVtTttaP2ZM1lXGp/2dl0H1C/ET47aI7q4ojgQ8lCtMtMxfyLoD"
    "SWrzSLRqcBcFFhg9Q9uYJNzSh8ci1QPkW7Q9lIF5mrcKdEOPX5Nqr4PyuD42HIR+A2bJjWxwae2i1PGF"
    "fDBR6woZJoQK6oY9esZOZcmRuXcgwzbh8RqJqn/fnEFkipLeQG75ty3tGeJVpeNehQJXQZNCqbN257eH"
    "Ko4VI7ZR4hG+npFHyOyCEJQ0jUhH8mYTXEeQD7a8JZPZF7cqH+tNJKrPB8nsxPj6hSCKM6Jz7i8itT9X"
    "0VtTBjgBUgLPSh2IIuBrzUYGdm8S5f2dJA5+CKdZyMJSQFXJBiDRZeUh7+Cni7/blg1lTn55HA3CPNo+"
    "fin7mLleA6TAaRlyeDTuLmI67JQDi14iDgzcpo36757FBjjeo/MtQOifkZQ8fV2d6blS86d8Xlm/lCWv"
    "e8Oxg7LA8hJi2JMcvw60Yx14mDHYDXkVW+m3ykNJ+aqMi19NJYwijxEbAIFshJpZiYIvph5RtADw5KOG"
    "W+tutymHWUc5CEbyxmJIAnqf+zk6RnKt8hcPnJ3wdfDBTVjfkU/Lesv+LFzSnMSbgoPUwcskHSztbDTu"
    "283t/dHTQSXe8DBJY/23Aj2FoxVA/VQ8Mpgsnb9Rbh9VhpPeEQrTDxsHZttbMb4L0B0dUVNPp3hdFh2x"
    "nvsoinjmIsAqTPRiXRQVo65boMMsoE6HHH/3YqnE4Otn1iPQO6pbbqoUHVHzrYMwJtx96M3fuRx8I190"
    "VPTnF2X95MXkJ4LVV9NdH/Ho0Dg1rXWwc3G6E4vZYCZ3vNJxqSJ/M+r3/8nZeSNJDCyJ9UAwoJUJLRtA"
    "QzbgQWutcQmavMDSo0mLpyNmP5exy9h1fsREzBgdg5iqrMz3plBZ7IWqs6L+DDbyQvK0MFpnvax4isNF"
    "qi+4uKRvNLrjDp+nRoJH/vQh8kwztQfqbTvRYOhRIL8lj6PfOs+xwc2m1BfuLPBXyswmKWIjBF/lY7cj"
    "kQhTBkcHX9OzYG1Hu4gNqfIHnTW62zyUwnVZaG6xp6PkhgO1RXgpSLJXNFgAVLhv+kfbY+WAGR6lioW8"
    "5sodv6usabYft76/NGGIIUTCkgXTjTi567FBA1royUGF62+RdDl9stp9SvBzvo/p2qH+3VeBrw8vBOD8"
    "d/ghAHDANQZfu6cBHp+eViDT9g67ge5tbsaAo7SgunSb92zvUkW1IQHuR9IyQOH0kdT4HQMZhdLINlVR"
    "hji45UYU6ag2g27XZt7UpagqgqxacNPA0PxENDIry1nQxyrmHpn3xZzH/KRmj+D5lAn9T5GnzdlyuS3V"
    "IWVAQ3amcnYk5HP/bZdN9BhBfrwu3Ofl9pLuKJQKXQ8+nn3m8FGnZhbzrY6/jQcV73P9axA1QQvvoNKu"
    "2P5X/c74j1eZjqegtkUQvkTPe7Ws9SdnRRuxno4v4Egn27RYSbtnSVI/mAAfB95dqJvZ5iU7A4YsKwa7"
    "JvDFSZliXHQb0lT7Stznv3gf7V/++z/zPhr+/913BsP/dt8ZTqPPgRz802SAjnXuWwhjV3Srk3TD3vHG"
    "Touc860ziOiU9iidAdcZLBJ2v++3shWu+Hb7l/ZevZzuBoBS79u4MNHOIZrtS+wixhtnwHOFF4k+C4oe"
    "VlI3z4YIDbtpi9TRaWGbwbGR6EWSCLjxKKGODvNaYpMd2W8iZ9gUY1N7FN+W85mSKGHmLLr4Xj+7dWTS"
    "AXKDFwd/OGmhGAR7kc6hRzfIxuk4H/YqMQFo9Nsfy52LGJz5aPwQz3bxFi3pD7/7x0uVEwRuUvjDzOaX"
    "y99/9AQAP2Txy3jy9BDRhZOhz6i9C034G6W8Shcj4TuOu/ieE6d3tB8T8QrQ7QLGkfHEtdMUTWkCsTA2"
    "EksZtFDMv53vqUC6v3PqCKov4HftV6+/58Yb/idwMlcVF/H33T1IeBKD0FpugKm8SfeftT0EDVCfx5yp"
    "taKqUNkzsmWsorD15nnwCCx+7ET2RrwKtuRBzifgxZpVJZzUU5ZicWqqUMLnEe25O7OvugHtLzAH3yGz"
    "6jYuc+oRBATEDsRLT+T8kQ8W/EBzKWuQFBF0trdvCMFP6UoSlymM8uVGh2OVN/r4QfG/hCx7cRVdbNv4"
    "3ZlsKoQSsepfIVAA+XwXl8x+FA3P26XNq2O/REs/FhVyc4ndJl/4loPA9aNgOExwKYyK9ior+k+emrdR"
    "G7m1scPI0TWmt1Ss+f3acn0cqzoqVScYWODdRBRAAby/50/SYNdq4WdWSPpUuPl+80AkCnc9/oRe+Aja"
    "Hums/0X2WGe6Gl0YKbnZUYrwrMuzCivk/Bevz2KSBHVCnVW8EfgkA6ZpkkK3W3Kt4FrNeTCcDbzIGeOS"
    "cKV8mmLeMHkhUDX7dPCnqBeJ5YRQubGkiRANAKxSlA80NT80VZxRYkg8w4ZJpKWgWZDXZwYQPHqJLl2H"
    "c8vpNNxpq8fsroIL1mSFQhFEaxhllrKEamVOYyY36YiYLJcWHHVRGitG5dBlaR6c8fgxOJ7LVRoSWf0p"
    "79yM5SzFLVV+KIGGFW5FJBzQxYb3lhR9YA06woMs1KGi0MCVQ9u97L+WX8JQtolxhKqOo95P5r8ovW9Y"
    "s0rmekL65jPyRJJykuCRzRxsc5Zcqz8k6GEmvyR/R1N3xwJJTnbW34mKJd9E3koVLhSoOBHWIkiHHss1"
    "Q1gIuf0899lr43ES3n0FoYX432hwkNo0aYLaluIHYgbDFC8JpM/JRPh69jz28Uo5QG2bbf7O58LKmg/y"
    "XvUnDflv+Uunrjxh1FVUatyIc82EYFysJhJEzNa8XRfi4LdCUo8kcP/ZK/dOPCt3CMFJyvgjXaRUmywI"
    "vEt6qJnBIeHfV7BdDpXM3JivvyaZJIpsNcnFgkobgd7e7DlFk4q4DOfCC2dq4+gGQhZx/HLe5/0heVAD"
    "JHAdWUY0eDjyPU5Yd8lrZEK3rG+yMuLZFw4B4d7FwiaTqIltfytTz86xc+49v/yoHocJcX9vqu5Tsb1S"
    "hVcL8xpvc9jZxIXpMvABtXoIoq2rMbQ+qtDb2Fe7N0f1WON1Rvvc6nXSrlFjYjbWHjPRImUhbBX9XL9Q"
    "ZHWVR0P5ki8Cm0dPoQiwP8ZLIn8IcQKUJyXXtaSU6cgiSDwK4uUvQUu9qAtJ9fn0wCUuOVaTGgmUqYTB"
    "PiPKZx9Lr6Ky/ItrOXDgtPuBjRXtqur+ad2PjT+CPT9Du/28lshfEr4tU29f0ZryMUGp170d9HnzEfEO"
    "cTU9EF4N3/SmlDG8Rd3KFBX9YinRd/dGJDZhaaPUE4uqwNPHM4pSANMNw9dD7pMBAvJwdnbcY+oUE39X"
    "MWMV93czuWRXt1Icc8EmB42Lb16DgktA3gTEXqbu+gpUWyPZcHAeijsC/WSUSPAMKXIugDZRgwsHQmDi"
    "4W7kwhxmtj19SIuP63YIcJYbGR2NGt+o+YOuycbG67u0o86OCqLXyMkiqJgPGw81iTOFE1a9tOmlFxJ8"
    "sw8B9ECoufUPlZ8HfB4MgtPF4+uVjxIwoPaeZcEjiboVvA36+juYOXDJNM/8p/3gVjs4aTgLAtfE4VA3"
    "Z/1dhBJn1ixKz1oNR6pYNPN2u3QJ715Lez/4qXoy8zQ+SeuPVUl844UbOgDVaG+V8nl2Y1onBBKaIEUD"
    "HueqGNpXpKJIGjmojHezbeIjWog7GGL3W7PBhn8fr5P5OH36Lr2hriqnVjpjDnYChUOUSVPj77KQkKL5"
    "v/PxlmETFzuwSm0kChf0XpV24fYsfvasLFAa5f52IHMMgEmdV1kDwKkzXIPcSauAfs1QFXxHDVfKiVdX"
    "GrbPPFUfxZegIdBIlpQ67ZCjNHs4OGpwhnp2FCo6Bsy0dCGnCSaSQX46oRgNnm3t4gM41Fb8+Bilfevv"
    "YBSeQpG7Axy/MQ9Qr6Zooh9mxiZDXiMvtqoA6jx9VfJeuHpA90cdLWvYj1UKKzsE646HeBIbfJlcy2hM"
    "F7aFKIDnIbAksLYvGBjTJLGQqKiE8WZZZoBjJOF1GEdj9saNJL/2USWL2crqXe7tnCeSwHlGnMH6sv3R"
    "css0E87cPTyCH4KSjXcSQKpLlM+hL2hJIaNFpvo8oW9efjU9Sz4ATFetmdU0F3ko/la5PL/FYHnnYPj1"
    "JdLyjEBAjTncanqU4/ecPbR1k/lNGb8mtm0VvhGm/SodQdXWQGmDYHKMBCGzcT0yEXndupPFdgI5PtPV"
    "mktM9IN7YioWCY4Fj7COvHGpxArBAVfaFcu3L3Ex8ffauom7YsPmxh5QSCcrFW7rOE4V7A2iXtYUtodR"
    "zAGL8/E4TIc0CGhErQW4K1OCbIgjNP8VNqDs425Dw8rqOywRMUFZR6fcL7AYFGmt0wgmaXNNT4uWn4zy"
    "Q5AQFXQZ5ltNaP+i0INVCeYKJppZ4SjYkZ0f1S41DRlj7yK5f99QwWkDBPEvgPDHfOzuA2THr0QNv03a"
    "Lv5226TK3/GHiIE5XCf8pr9EQRtFlL/s32vi4zpEPSoyU+6v27wOb2lv1bWtRUdWFgBB75UyqTU/3sck"
    "IOvRccmi1vjMH6JYuf2h0z25QU03UXGP36hYpJBVeN0xRcRg9/vzXaynX5oghmdENWLp4+5bLahNXBkj"
    "+nyQGEH76MVy/Peu0az7qT0lwbzA9tzUi8TZXQCdeHzyvFi501uu3tlcNbiFXGFucgdHgsERJNeRBCKF"
    "UPvjgK1aHROSdfqSgwAaGyQIQk2AKT7+u2+13SKo2zvkZH7TMtTym2w8mCS3RzKtg/ttNAUeTwH2ZOAE"
    "L+PB0lumBSo/LOcxcDoDkYZicNazQZfIerhlrd20D2BP4t+5lPfFcQaPqPTxeLxULXIib6uWWOb5BYpW"
    "6l2vOfEq39IawXhQNh8vNyk8Y24sZ8tMWoMmpamH6MUw/JwnsNy37NAHhRUgH4cTymH8RZ/cf/GO2//6"
    "ZzzM+Lc9tOk/3judUgT9Kgfq9kUch3lg9XEvirNWkE7tb8IUSigjEhUfthxbaZwiOCbgjIOrVYLBBeDV"
    "xKUdfpNOCC/x0kNK2p3K25+/+0bRCfxe5HOgWUrm9wOaQ9A3YupkpHq7LYoGG0nAMFkE6MEE1aiOOvzK"
    "2zeYUT/0R2zxJljetmWeNKDZrl+E0vBE5OuZIPkxeS/mCSRT93SGIr8PmggdVhPmYEMwWOA0Iz86Su47"
    "D+nVTeR1L8IgQIUY/9B0UHQfeWPTpQOYv+ac2Awfw3Fbhaw/si2rgfSZuZ9mGWXD2tnmx3AO+rZIZbIc"
    "Wb831J4gcEn+oC4NIPhSSgtatiLqymld4l0HdT+V0XCBnh793AHmUTapZii1hg0wGcHHAmSPn/6C+uqA"
    "5MYi7bw9ZRwVRqu5z8IUzSjrNnfiAuVA6cOLv9z8PRGf/YDjAjS4QeEPPTh0LGtzTD7jsCdBn9GBDJ0H"
    "PO5zcaMtu/Nzq4NLYR7m8fNiGQW6z5Uys+SMYgUro8ZJpjmpI6LkWtQ1RL0YgdYlFoWkmpyCu5Y9KsTe"
    "1FSAIIlRZEYD0eDyA7R4SE2rY+8qiCXTA4hgNpBtjYBJbsP0LXZbIKwBJzjo7/PIat0iR7AbXPgqVChI"
    "DKtLCnpTIgBeRkzPcAtEj7kgFVgHsmBmJH5ydHe6HF1kL+EkKoDlPdo9yD4jW/x34wVkHKWGlSBMS1UJ"
    "3tYaIWrwCw/8CtLAaqYhTT+DNomq0Ig1QwpO/X97ODPaWd0fB8IV8n546oj2HUifaiGbaLbWYh8dz4tJ"
    "q421X3bIh21XpgjkkfPxRrNJqTiR2kUX6PkMi+PvlmO/6aJzR4gUxGjS2x4Y//K1B4/fRWQUpRSXtzL5"
    "zInMDXNm7Iwm1smWhB8szYHG+FsAvo3AOISJ8BnEDkK6NjzITcKhtq+9ghqCdzSQZVlB9ruevbhCPg0d"
    "/z7pYRyamjTbdt9YaJEUyfu+QgrC+2fqn7UlOvPzCPUXQpRruJPzF3+wDKO7TIZEo5uWlsreWry8FTMx"
    "8m8LM3Uel+06LIGN8t2Dhur6+8ezclS8x448kNGnV1FHYCA+4qZKcv91Pr/m8qP0a/Yz3mzgyAbz0UMt"
    "DF97Em+tc6KYO4tzjRnTYAXI80pKVSYd5j1s/eZogzzkaUDLQxNAEXT1BGkgb4GnUVjmjyxLCn/X3Fyq"
    "TQTX8uyW0aHTlbX0RchZKeJywjJIof/lL2Z2H8bJ2nkd1UPGDtnfIiDPQdqk4GhDJiKK99Mu/VWEWMxn"
    "uDTQme+FnewePsxHOARqKJWqbj4WXorjViJjtkfY82u5Tm5anjUXvpvvHNqWkI94LTW8gKXr8YzfIa7Z"
    "WviIIafFw3dsXft3zp3DHifXA2N7OYYXX/nXeAdqzdvMjWaJq7BxkMXwLmt75DRY2IOyDSHa5AVPBnc5"
    "CR6euTlcVcPhh0hPbq6/DW1+bP9VmYc1Pob+XG70yRfRcZxOl5iU5K/WlxFyHu2nLJWp6jkiSoahRh0Q"
    "ozS1XkdFUbFKeAJ9b7ZoSrKDWaKV+dFvar3lwuqN4bFd3Sgrh3E0p9BEOjQofQUb1Tg+wu1ZCkhHowOj"
    "aJkpJDu7odSSusSGgc6lAAyzaFPfP0ELUgODCjlhoRyjov2AcAY+NGpxYf2umZlr0+nUsvtZwOpdxHnB"
    "NmKQrnEfOCZ3MZgG3eiyTKAB7AD1lBDKV5z4nYN5EZv8FP3fW2d1uV8F8d5FKYrgmD7C1LCWRYTQL8to"
    "fz2m6W1NgOIdmqS+r6ti7dRbAm5j48typ3a+vsXlMaUojWIUPM16uFA2XFo01OVpmlW412LzlO6DR+O6"
    "aIjKsOIVBT+YLVMSqT9w8q+fe5ZEgeNiuIsi1GojJ9z8gHU4lzSL3WAdQqittV+HWJC2wh4ia6WNEJtQ"
    "fpVh7eK+qMFJtJpWUMT23MzLFCx5HZMmptI09To3/btDkFtqjCyRXDntE5wgvEhoASuavqJMotxc0pkk"
    "hfs7BMs0ctsPzvX9mFrmtsN3Z712dprbgY2MaJva1wbilkdexIjFH73bZ14uncdZaRQsLTpQd2eTEFa3"
    "gXNFtJS3AhU+7RToizdlbyKeF2D0Z1EbldlfKvWR32sHLKW+KtGN65soMM9L3uXfpFEg6l694BNUQZM9"
    "+UtoNV/3Gse2Dp21l77d5RpHbKwmekTR5ZrNfhcWxzGbMQTd2ZF5H7dq1Hb0ZPMI51GOLnoF1To69E0y"
    "smZe4aZLAHrG51f1iE154XcBWGeIV6Xulfs8aiGiEYN5bjQLldNlNlNWwIswPw1q6dme3oUMvJNU/0ro"
    "4BYGDEYnOiOkyT2S7z4JvlCl9DDxDSKHW2zog91CQzmaF2fqUqlsOV9YP2tc6MnkBdZIDLmbHoiGAKAG"
    "n0VIH8qk0bopBb4rQjPzynAMQ4CEsZUX5ZAq6rYVIJCto3Szfn6VsqXIfdNNQF1yLAetYTrH6otf3G/u"
    "XbfcJMzTKt8auLoJMZIN0/wK0+KstU+g0f5M9KfWN7hqaUtQEe8qesH5Nqvli16GGAikOXg1sW8yjANq"
    "kgC7eTSq+CbXzkzGcIWFZ+7qr8A6PyfRsBVbhftnkUbMNDAZXvJRdLH53fCTMAD78amrBRpHn+kA1UER"
    "23xs9ouApOk6y/HP8iy7sQR5XvsokhcXKAsjSttcumNiC5BpfJBLu4hDQTswHrehq1xzu/il8hl1FdY2"
    "zedTG0aCQNODe4BGQozWFycNdh3SAky2+QdX10rf3eFOMKym6F4eFP2NHjsvpuVXtCY8av638xd3YptQ"
    "ZaFdbyZwBDxc8YQQUCZgWqP+UpoFRnK5KYQCwEW30Jk750A4ld3Brdd0xUPqd1/THkdVCgzT5pZcxbtf"
    "eE4/zYXV0LtuSiyhzLaqXPmvt/gkGXyXYVkFdyjmoxRF2fozrQRlAuhYpeDzbL1Osr+I2Y2YUNNtNicz"
    "VMbyw3HZxQyxNki3xEV3V00++uNe1ioFK39xeafYd9WdBuiVhb1XcA8eFR50HKkUx/7oUjeHbWcEPEua"
    "K5y38afhmYQDd/HKtoc0LQh8bc73RNcFn2ztjXkDEXrkoYhcX1rtJuM0CzzLSTku0fbZQS2Qv/JEUDGk"
    "t37AOKDlBMgqCQzKQAUJ5QRAcw120A0pklk9xjJFbnT4n/vJv/wzd7Oomvcf9olS30Zli6Qf8jW8IRum"
    "kMwf1CUQnpqbKtA2S7E5CPAr1hBCN8m0hmPmSkkVpRPyNVvjsfy6hs2oCuMZdTrv0vp5bE7ZBOUyWm+Z"
    "ODy+k6RISIcgTXJ/1sdAyQUd8ItGs25/p76yXuFt3ZU80h9hkQCIliB9bUnWmM94zm21SbSPzDewUsnX"
    "ne8XKuFIZqGQRAhoTl/ZbrIPoO2b2h80gkNGdGQcm1GipIx8RwF74fgH7ps3lEDd8vp8HiMxrKtE4UyZ"
    "3rTLWNbsaTlkINuWSJgemTT1uXz3uXbUMHiT42rb7xL+2meAEHPtg0QxTK+ZI7a5kRftLlbHdgCAaRQ+"
    "0uRCdH3R6gTBzVwgrb6QNlebN0cY2IAuGwG1WkV+2GAr+g1Tx6uFfVn/a4cw6yPWrrP+CwvR8ebozTXw"
    "3NMYOJjdGSHvmaSL1LxfPHtknmx+A8eFeWF4k6+kkaNSmhAiFzjl9CtuPxraQTSZJsiGEBu71zPPB6eF"
    "ShoYLZEnw9UVwYkoEdsGXIZ48O8U/95qHy31pn5t3vemFkF59lSB1HRH1EV9XuDUm/7s6RFL26lS73RU"
    "rUHk9wzGCYLgyOSHpdNG5fAwiYGGnnP2CJ7RZh4IwH7w5tjyjCsKAFBd55FmAcDGADmGQJpEiWZ0YzKx"
    "3XrI7P0BjHVRU1WRnEECTWLyEguZXkQm7Fx35s/vcSmcwtCcvV5w7fkx4XM3cPSjycY2kJc9QF3w7H8w"
    "fAbA7E783OBD/oOt3gbpRGncDrAxevLZ47hxIrtwHLln7MQX1vmUx8i6ZznI+We4pjuTzBwVzBXPW0cY"
    "r16UqCKnf8uF3ikkJ/js4TaSfBZt11CyGY7+t+lxv8xr/F0CRygtTODbUGfsNb/XurM1LfrmQGhOcxt5"
    "Dn8EkmWpZ5kUKIteG+k6ABhBFP/xBDUs4MbOBL2fstZadngkJ5eaCSjPYQE9PDaHs6SEMde1qB1CTQ9P"
    "76srz6NixbsedGi670nBGtAWbY7NISNkjpmRPqE5Gs2DIa5BAz1XThYJH6VFoDP15bByqJV8VgEFnvAm"
    "GEiklR10l/PO7EVA/xWNPpzD8w6lcJm8WK8Ok89ME8VhRJLToq8U9QuSc7zyEeaT2jmviRW/ta+cH3tH"
    "Dz3iPxKOOfYa1YFp4/b8cpD0Mu78Oaw7vik8zJAtbaQnbEXqZdBR6qR4RrKk8ouBLb+vkL5rhr4W0x0A"
    "8bpI5wp++NksFW5EQMq89QuIp6Vqo5rNbjPu7+cRiejkx+uHIT6jp/ixGFb0RD3MCO1nk174jDYTgf2X"
    "ZErJo3a7H4c3RlWlDtPG/wihoAqCzrC/rLsu27HMd/oqrQPAgotxu928hhWa2ZCEDuFPS+gGb14ZDPWh"
    "ULDPhwZz67NZd6gIOuQLbe+KpfH1vPeX6FATlNzXtvBODgatLXKZ6EFLlXHB6a7gul1k08J7NFnfiZN9"
    "XHG4T07zFBJWQY+xF+9Myd48TvrfVxq3M0pT/cGeC1lArRNm8/chTqqy4EF/p8ill5mN6kZAoE8dsiIe"
    "xJtjs6aTM619RsFy77+0TZhDeNSxmy+H92qOxWcB0hEyMyjTJIFmCIPbzxKYE7166GGMGu+/l8JB0hSn"
    "uHjXx76v9uyh5aLwy+QOornq5IXvieLmInPPY+herPshofRLPGpg3waQK79pkYmDiXvcua6FOU07f0Iv"
    "Fw4Xe+7nzY6pRdNL9FzE97kqLgxyEewEz6pT2Nei6PkV/czd0XiTUGLaEcl6yOp5UbvyZcQ67+iIj3Mi"
    "K+jX880IQYxq6xtrOr9rj4FTisgOw7Y3vGXdHuZb2U8dCJPRzugK/TLTOi5MV5H72/mnojtw4ITeXeuM"
    "+tidRYOVHc7cpcf+ctyKtVO3sVOTVsNZuPfyk+lmmJs21TxMcxWzlnaCEB36DEeHpX8VJkJmX9yTE0Cx"
    "dZ1wZBcmvRjDEA8VFmolP8KsAiFzp2bcdecjuSPNOpjeytO8L939uuyMz2ipQChXd9Y7l30xzmFh1Rzm"
    "r3JijWdyYf87fH8dez02Lk49EQIMLaN8qCXOuiftDcoQT8AMMxatAaSEp+VpGPO3C8ZG8dvwIFT3JhsS"
    "OWu6+tTomwBNJdC+vS/CRq49aoafikvrwcw6eqMA0oNZJReXxOYoAp7qWLTqmlCDBamMxxHozhf5tN3B"
    "qkPCOaTZDV8n1EPI8DKEGggDY81RQ1MOiysh21xNEahM+mEQ4xuJ8CjgLo0kyWeKHrQyywtl0WDAXfqc"
    "Rse8WP0e2h49m7h93bnhsATsJP2ygH+AgB8adJ4wlqcHJNc/gvXC9DgSP5lTUejw9nVUCeOIhCohWHQ8"
    "Pg8Pmn3WK3T5gWCk6w35I4qYIO7PGxQfnDe/34elu3w8lo/sE1ht1NwTVi1WEYcgI2Xf0MjsJOI3xOFi"
    "mRpAflM5mqDpNM6n4vT96zMbE7OV25EXmyo3ywVj84IAJ475lzi7jB66SaCTOkLyymcv4RaFr/oVZiyO"
    "B0u23dz+rinufU+0IHlBBgh1sQ5KAcid+OiKjb9ZoNA73F8S9mqn7/wLMO4b624uW0NrdcNNu0ixSmqN"
    "YO9MUaT1pRc6a/p2/cLWp04QnavBNAuNLDk9eAChM4chIos3Y4ETNmL888vboldx9b65raaWisF9QTRM"
    "Pvn+M36fhIRV174FaeXWHBAll68/RmhfbkibO2Mcv67FVRjIKCPKqONoLs8MVaPpkCcqOxxK+nnd0iHH"
    "DD8hKCU8HW+cWAHpIWHx0xhNfkY9yOMTNaMBhwLmq/eYxpN0xZ16xSJ2hcqUHem1auB3L5CyWH4bTl7Y"
    "wYgiulEu3dM50ohk/At53HZLOy7l3ziNkerOniDcdIJlKC0aU99KV5OVce/hzSCy3WuK346bDxbxUN2U"
    "q2PYgATwkpgHU3eO61KMYCCAmNvY8icGVqJTqXF/NiQZ3BRwnO8neP23xt4c0uAED6Dx78Aztbu9wF2X"
    "IeZdBnMlqeCrr/SSATAX4RYEoC+wtp8YFYM+LeTdburdxa6W4gQ/a/Ekv0DO4jV3YmLWb08Xi9+rxutz"
    "06ld8Fzc5tVLv1vRrLbkNWT/sSZiCoVwKAwqvF6hI9doQ5UeZWb048p9AY3Rzp4+POZXZlptRaGWf+wm"
    "cnoxYP3jrbX/tI/af/tnegL82v+qJwBBZ0iyW8ZifpmU+GL7VnjChxXnczI9/szCdzTDmXOUr+YJpcMM"
    "2hfx+7ZWDY/7fFnn67cRP8uurzQsrXRuPAW9wp4Z64wiQ0R5BREqihYRQXfX355JN03Pw93ZK2INjC7g"
    "rwDJX1AQVFcokfxNqyoWoY3RngiLzIKx+VFYwkIII0QzjyvdnwxHN6+1c8I/8yL3gf0mxloG0wIIvk0g"
    "9taMQgaKziOGadLVM37r93nd24DaGw7zCeoFtzVw5CWgmyvBBCgaj/kd3MvPaBrumTFfnxVYHeyAzUh0"
    "GIj2RAIuH8/Qq1z/+uFwAs2m2uVdLz2EoASsv4ei9Si7fBrEqYH/Ektmz/bPDKTfoEz3n3PkpjXIbg4N"
    "1wBHZt4/K6OpIV3DnFDWwpVAxiSL0RNmCvPVAFO+zw9P4sXL2A85OrCL2QzOtmqflsSZ1bLdVTRkbWTe"
    "J0MQvUT6vc/ari+pURi2jSykLAu4HmYqP7xJdRnRBkHg7KnXuQjsG70RxjiCGQ6INZ5Ktu5ZBCJ4Ecj0"
    "lgfQHEUiLI6qyzVSpWjC+9WGYTVrl9PSKyGU5SAiAsd9Zq1rFHTQAwQjN7aJAF/4mA7RGKGpP58OVUTZ"
    "HEh/j11gJ36MzznfmuHOsvyWr+m6JYKb44cZ0pRjzfUnOx5Znn5GG/kHLqzjhbs0SKobK9L5ZyX4+2dB"
    "OQ3O/BAc1jCBgO34zXx+e6/cKqdsFjYRpIZj2bU9T/a7CJxYfp2ihkub63lGFz5fXuIIrPtUWbFn7pbo"
    "QHeI9INIn4owl2eGU/eRMITHG+mrviBJOMLDXTriHIesnffvcEKRD2YBS0MnCkUuUr+9+j0DP0EOOK88"
    "UXgN0HBix7xqxXm89dru51QCkTz8ps+BLUUeEl7v/EV43F8xc4+XF25zFqfVFdCX603dSzedyBO8IPyx"
    "zPZ6g++mbYLL1w8IPqTpXlR8DkfnUIeDys9bsvHl9Wb5+NIStyc++k2PI2eB7YHtjU58ptnGZLyJcr78"
    "xbWAU+B9VJbB0B6T1zRScyy6+1Hb/rz3VFoG5hMzGloFi/YMd+xP9A4tf//Yy2MyQj6gRU6oDpXelDze"
    "tiSvMPUcxfa8wZdF6BtT+nK6ClHJWmgDozrHgvyqRCPsxTA377sFjhskniCdm/WBYcY5YqaLUv9Duc0J"
    "XBThq8/R1XfFhrWr23bIqPuyXspRbRv5FiNHdwV7rfShxolx7Msy5N2qLdLdleUPzpq1CT0nMhAFocxt"
    "55RHX71U8Y7O30GhJBDXXYqRolGbuyunQpE0DbKc42f7x5cBv1w/y0Y1qbDhmZdzuROSF1Ju6tNIVq9m"
    "M1ng4HmQ5hmKUI2pC1qZkaS184UOkbX4VRZYSlcUnPoPTCcwVMLuvLwswV2B1z4w6G5OWK/a8ZOcHZK+"
    "wleQ1fsxPh7f0wtOucjwecgqMF7czkEwLEOzc4XJyeyjLiVxIfANV0UZR2VxrxPpuv6cwaJiOLU9D4W+"
    "F3OEHMzG18eA4Hz9Jnf+1fJDG9dgiuUc0w6tg4tgRQ70Y657AjifpnL2hStUKpx8PmKcT62u6CObNwIY"
    "6b4aK6441pfYMpyY7TdYp7DtH2xZZ36Bx6o+ZsN2FnG5BXnnzNXq3/SWmiJbgcetnEwJwNPH+Tg41otf"
    "AoeyNU9uvs2lcAUy0VdWNdCA0U/tH0YtNn+1F819GXQHClm7AlBmv/vlOF3usJ9QlwQl4cbdi8qW/wKm"
    "67p4UEmaGNOfOxdQHhFh1dPQ6TNV3ip36YRjW8eXXj1zY/1plvuMpyi53tkw3Gb1DaNLJiFZEM7de2bQ"
    "Z3tlo7XEAm565qkWyKxjZq5DFr+rQw0gSJC7TfUlnyL5ylpUpFZYUrn/BWfhrxNU9Vmm61v5YdVUXolZ"
    "bPXcEEofuoTaKjdX8dTz2Hl/UrLdDUrylt3cAPBkLBSntlhVLn8Im98cY1W2bt9O0a8/raNc1C61mV4V"
    "4WuI0we2dAh+6BBsEv54fjr3U8/U5uF5psiWP0mZQbsbAhGGNhUYRrxjD8CTzkUKlO5Wkr1X8a3445G2"
    "pGiekl5xOUy8J+Un4XyD8TZNkMTT0LAy5rldCZGvsXIHPd3L9iKvURfkhTnkl1K+ba4UOrh2CTKZ5O8b"
    "0ccPHsNpPZACI+dIgrc4QyJuf+uPS/PEqDVhc1g8JelbrvnalL/G1IUvQ9K1gCMlEP1d0Ta4nIDFZ5p+"
    "UnxFdI1BZUmjsc3FVvHzVEVoNOBv2L32N36DbHXEd450dEdlIxmIE4LTnznzEitp5zcanSUBtgGhMJVo"
    "FAl/7Gm471ZpDXdEZLus7F9BItHy+rE3kSfG3zPc7teiX+Spk0h2vLL7FE8Fn+aOYjQ522kxSwlmqDnW"
    "IAmx4/GhX9u7llRv8eIaqUqFsr61aWZgOTUChnNB3HmW2Xuj0y1EUFqByxyXEEvQVOlrR6+ychnsIZIs"
    "PZDJ7pM4CAvyFqfuUkzUID0nt4LcTCer1AQnhj4R8tOFeYyzQFJWp70gClFkIzf9yL6dn5AnBHp1b+pq"
    "8l93kqlU0RSN9QBAMTIOFrJpodg+KyJGtmEwkMCadIYbAB+UWOm14lgR+q6zqbhTDreC97GxLZIWhbUa"
    "nAHbzL2Ke4ciXCkWuZdBlzG1wpinP7JOd3kaiiTxkrdSxWN1xNyk/tueAMwZkKeJbWyIdW+J2T27ZA8e"
    "DWh5c5l1BlBOE2FY8gch9kegLYep5cn1W5Oga8d/gq5yPHeyYiIRtUfBXAObWSrVSAs1fvTwwPLmzCs0"
    "TXMq58NxDQjNkGk08sP62ajrFI9WyenZeI2ApKaeLS0bDv35p/Q709GjKwGpNRo7O7rw6NPAIFMoyJ8P"
    "xo15yxq//T/fD/gf//uf2Q8I/11PrvzHZv9vP2CAE+rQnE3o0L0tRa68nI+oS32pc6J4ElrdJ5Ak2i2n"
    "YatbzRA1vu4haTwzzRclGK5dS5F92YI627Adt5mee9PeB5AUTb9JQ1H5MJ+Hzp32jR71jgAqp2nwAl6G"
    "BgC4wGQ85iAlrka/ZXqjqDScYgWptP0Fqkhz+4q73kE6ZW3d106C/QJJIw2wzbczfGvIGxXm8y3QCFBN"
    "G5i2tqtXeeqs/BUGde8j/ir0HIYJm438fsRn3yR2Nwaxe35bEDYdAzQYCLEey3hC+tq7r7+qOrgXeuNZ"
    "e52e7xu5cIfczVCNIoi16o+KFGIyApo0lYM5oOPYgPxAYiKHe5JY0wMn0wH77Ax91kMWvKKu1FXv+Bdx"
    "r7MGmjx62knMQem2btYJou0zTopEtpS2Lywhm0lPZNOeMJhshVaaUMzKLMn8uflzOxf1d9QJQtKuI9sP"
    "HjuCsitC+LE1hH3hHLkxQcrGijjmhphYLSkR3aRTC2g1NEvf/MhjGk8//PFBRyJS6dpH8QWBPk7Uez+x"
    "Uzq9Zsel/A5iJfV8xXHVl6uU8VD+vv1dERSKtStI3MZymVjfa+i+j4k388jjAKolY4obBc9/JfZLVRiV"
    "3/CCpc/tX/laO19otEel/fsd1vIM0xiX1Dxu7MU1mDLyZkhnfsf7olu3tZIbVmQj/YEB885nKDjG5H5Y"
    "vzoogkO7P5qRHJClUkDxcX3a/+vDGwtqopTtW1ISI7soHMVzxK9KcuqiH3MixmsMNeu1gn5xnmTiGJYd"
    "qzxtddIN0Rt1mApx4fTUcfW58ceQ7xdzl7tboSdZFTuHNuvoo1G7jFzejL7wWUTjBKV9Y5S6z94vkHSY"
    "fSzGKEUhDiZ3BZ1r3OqiVdb2sEjTCXSYe0/ajyEc4if9UUJ8Krm2OWL9ir+OXZbac0bznQ81gF7K3sru"
    "dTVgAWqgS8zKNbJoRf2hB9DiGMmiSNNF9f0HbH6i17iSRz1ycDc7J3wYnJM2jh+cX/DDB+MGDj3TQ8lg"
    "Cfdruer4ZonNk1986Cc7J91pe2vM6r92pr2Vz9jC7kk8pGwr/jjUUcVODSgCiLcp/NPaf406t4Ex+0XZ"
    "zG/1d6ScgiqBmWpekoMPWaMiQG0bQYTfvjvaLEdt9wuxfH28pGoR8OdO+qf/fWqLmZof9uUSR53c1YuE"
    "i6u/t/9Wr7trbywCzIoEBKu37SbeizCOPtf1KwKP2JK2+r3wbSciZ9pLRX2zKkModycngjDx+ImD3yPx"
    "u0rqAnAe2NqKAh9Kvi//av/DSEsMhULxPCiCpdKdGLBcQ9ZcKkbtr8GehRDaihwB4GU2peX2s7KC63Tq"
    "GbYYu0Crkm2cu0yYKxhmtSzXsUcgXkNBdrnUuXAqXERU97MfXQM5/Pc2dZ+ME23bjL1ASi161xITMquz"
    "CIyp3ACFkUM6s89VkuWM+gCvdH/a+TE94U/4ZJ3b3/FJy7Ir8TB3bRiodGpvTkTCqz2aTLE3wkU0JC5n"
    "2xJVOmzokY8K1aGygMD3yXjo2wtb+VV+JdusvSRRcUSHd+Da1OS9AuDn9fS6auc2WvEEfR5ln5Gvalah"
    "Xioo1jngs31aRh2WzrX83GyF6CptfX5vdeEnV43t0RNywAwsJ/argqLy7PCNk4idWZuw14BfYIxs4bo/"
    "v9HAYM+CkTS1iUJ0keRYggQnn6JPixbTX38Ab3qEH5DD65vs1yQp2vVpFaHimHxMokWn8N57jbq8mJCi"
    "UvZvUPak30Zi68ncbl478pZ8HycAJ71Q+Gv9HAWxpZGafLDm4dTcuGJ6WKZYUuBDXjRog+o6HRUXAh47"
    "7hhGCnfnaQfeTU1ThEP8Uq2g9eHVFMMaR3IxsMnBe4J1cTG2+wwDPSHsfhrTD1IY+FhGdOTI7MWoPsP+"
    "mtnMLSb9OPfKGPuZkmPboFeqzPK8Lk4yA+4x/Ar7OgZ+6u7SV4j5gax4GVD5ffaMU2NImpK/GzF+8Bk2"
    "zB8IuNA8WAj7wroqJZW+qZXf02/1dUSfTkMJll5+TfHl5sD6YenSH77Eoa9FMe9HrXsfLMMmoqH7fBre"
    "ZNesrL8BFn92Lx+G6xaArchH4RR+unboH3x3ehlBIRwrE3Yy2JHhjykAnhWsbbDITxsYXn8LfvGbbItV"
    "4d7J+3VkkXPwrjY4rNrRy9iFBjdECe+/2pP8xk8IpZYrGnYvfpRHYslDTIEonxlebn9My4LqZ3g8JPOB"
    "Hq00//nJkNhYTHcKgfZc+v77ED8kd0iQ2HNWHVgyLLL6Pg6wjKq4MFrWrtpYacARLBNOUxiTJ1lytGwG"
    "u47KzWVsskQJMsoqtMeiw3p0aVmuPL+lvfItx6oqp3+dnyo4HraSFH8DNDJ4kutoggc1UxUbsjn6Enq4"
    "MO0VJIAODcH5uccFWBJsV4pn0GJUI08TqiaEmT39qnK10J7/BMrjhVf9/vBRoCnkC1tKfjVy5z7Cnl/T"
    "VDSfgfMmN+dr+37qcvWMhqdL7LHyqHChhsdxnAdBx9jvJM6aHB2xGTokGpz223AV8EO0hBh2BAeFLGRX"
    "HsUQq+gnOUIBfHOeZ/rh2K+IbHiqPgTZjCC/1G35sXLBaxQrHoOKCrg5Ih0KLGOEPtt74bzjLTevrspe"
    "SkYbtgExRJrgGrDYRwxJGBOJdfCbr9TYgfE+u3xcWpbYCipMFzO4NO2RCFwAq/PPWWEuarqU1KSRmdai"
    "ECK3q8qOGNMekPbQGNoQow3eTHb0EI1604k0ek0nWZtMF1yY1rbUuJ7w3wDyXqp1zLBSmSItn9byP0NF"
    "VBwMEAow3Z3WW2cUoyk6GjV2M6D8+ZL7VkNveGWkcbQqPfcJRk5Uj6eY4XX4pk02RtDzq1K9dKnfLljc"
    "ego+kKAYlavh3oK73FcQ7+7i3ywkxLQYwRZu7UP2Mhp4pOkB7s1GrWzCozT6axgN20RRllGnjrokBYzZ"
    "6ih4/yacKnlw/pHYeXzMKp6ZumqOxNHMkKusN6oP/Ni1xN5I4IPhGWltKWOLaE0twQHDfTUOSLs5SOFG"
    "d75AjXhlTKWwLBtTJVVXCvLac5uOeHkkdWvtD3jcqAVcMlXGkAVqzUa4/RIg4RTuS2JfnjpWW2HPzUxa"
    "H2cLpvGxPnZcRhj7LmCYV5CHAGLj795mWXzhdEnL4w1yMGQcWIyNDRFMDHdZtE2yyIWP4mkOQEdV4i3+"
    "YT2f3OeksThQxQvqSEj8MccIjw54kBOQgOxhk6kBO4jhLv/FOYz/+c/sK4zQv+tl9u/2FYqUoCmyeQgV"
    "iZ7ZzAj7Q3gsx7POWdSrII+fSOjD8dLsd/HzDCvATM5lhgR9p9nXVDY8YdtLKhEW+Dc/MZnnuveHPwnP"
    "rKEhm03SewYwqY8UTO6TbN/8ZWOO8ahOiuH5azYgutJgv24AC0jlbt+BiSb4Yh89bIkzp/kX0SCq/MEX"
    "RT/Ba55rMyJIC6B0Omv8jIpr/aYF7VpV4hWimgZ31NDVfd23lUgFwg4D2Ni8k8cPjgrqAVcUFL6KGieo"
    "I0yahnhEaNFvuRoY9ivYnnvmBDElBVnaWXvAvCcNBGruJnGeoUi2BGJ7E2H26m7y0G10F4hRuIXLAIjh"
    "r1T54an0YwVIJze/sDdq5UVltA/LNjr9fv42/+LUs5jR7g2BEV5VdKVyLucL0e3XmYK30uZyhaV6hhAE"
    "kdU5+zO8kjutUHqRyl5Vmn5SOrIQw/fIQg+6WKmES2nEmhVOxdKkI2f/7ra8fp1PO4PQy6i1eqYMwD5F"
    "UUP3r+8jMVtPfXOY/ESpkq2gEV/4ZBEGYd/iNs5aCY/jU9qly7EawzIaq0jyP+6GZDWO+37dehHNHyvb"
    "33USZopYwe2+gGd6lKq6rSCsnP6LV892J0Bu7cu0LCudaNHxZSWFVbG/8wlcz3Rw64Rq4Jss+5afRapT"
    "YHRlbK3pX/6FzKNpHvClTHnZJsy5yHxtFHp861Oy/X5JtP+yH3r3XaI2rmkKTqowBCVk39bAbUbg0pBF"
    "1IjVUuXXCnbD+JHNlb2/65KnR0DBGuALyR2o8f0qkRfQwCToRicSRuVGQZj+9etGCE6mJAVubiWOEBnI"
    "tmTuwc//w9l540jMdIt1QQzIpmmSIb33nhnZ9N679OUSoEjQBgQo0Qq0Ga1EHAFPUqA/+ZLBYDDDaVbd"
    "uvccskxfSSRNd/JnvfB70/KBUhgv9iPbV3TFnZJz2Wk1fw4/3UdgRVAEwPYdsbcYnANvm2cmOv0Ntg/H"
    "6k2wF5Sjzvrv38SVTR+JTHCk799moAFxsKBJ4URkweYYTJvyKZnXp6laxfEgOXbxQ+BQliF+9lTXuccb"
    "tdGOCGMI6aHy5QDjx9L2CBlayOkA8EetB9KhVbftBoRW+CU8sTi73IjmSiiaGxGj8wJqjU+QT2OCA/O3"
    "ZUQ99VpLuQNsucEmOmDgv5ntdEJCg1kKwolfQrm8pNUr/EudAWx40SKS6zeHDSowtvUlfC3o2fyg8zZ1"
    "qz0ohj5e7k39CbkMrpITyH15lTTtaU87f43tVAS9SOtLpEGgh7s5KuN0ri/lZuawRikKnzUUF4G7kJeB"
    "4kqfdpOXyNS4qqd0kLWwWoe1I9qXYathFPnf+yd/GwIqJNOL8vJrYKiXoRVeWJ7upNT/SovhPi8y8/fH"
    "9/RUn6NzLc7eIxBo8QCZwWZpA6gBzAmckBLzEK68nfhdqFT9TTobhRVvssEzuqMJig60SameHMocA7P8"
    "fpwZxLuy0tG48KT1IRiArCMH7zKu+ZmZg+PjSIwnT2LHyM8y3L7wCHVe56Ijf5bq6ztBMiah45qfbneJ"
    "buipUVJZ6TMT3SDT729NaRp72xqMXGD+bG//lJ6xpPcygeaqyzbJVUNda8v1RRSLEsV286n613wG2dUW"
    "qzm6CAyctyFkQhwtGbMG+S51gVgwSoJrW4J5ba7EhuucePQi90VAfrUilx+l7x7LW5ZUAW/5vv9y46Bg"
    "haAozi8zOv5zFkK6Y+Z056tMb7NVhhW/KDGcQLsKTVe5Dg6QCWRizd745EZ5znaQk5O3NTKaRPD07Y9w"
    "+TQcohNHhdqiYe6/nyml5II/ArxJKJGL+GyM45h9GaWLyKOzEhWIMLy1Ld+z2+RQOfdaTUEvlW/HD9tL"
    "0iL/UU6o2Nu8wfizhFPGzkLLb39q8PHVfLtkODklwPB0nZQX1PNOrJiEpcm9btL4vo5+uw9QxlJ78XHy"
    "qU+FtXy/HdY/5PnkQOyKV4k8kQr6HLBApEV2r1bwwQHzJSoKcNCGH3B8LrDeM6MJmG3yy1USpMioaEed"
    "AimCQPAOxFpRZE9ZjCM9ZYs5WqIAOlzkDilPOv8dTI3FzfEQ2Ls+fH+yptBFAeWR4NSEwLqJSOMQPSa6"
    "J73yeOX9940OrGXVh9Sv77hrixdXY2K03NwlwmeJEBvqjH5SsviANfaHM5fYXN9uB9f1EKdcsKvyvPqU"
    "+RmvgjQiT7AcMp6FGAFGA4qWVJmKujz9Shd5Hqrgh3On7B74WSKaxtPuFQdqxT+YyoAgfYYGmLSZQP8I"
    "WfaZ160NtMPPdtNW/r4XpiOUPM6Fkyjopy1tUyae3piIFU1co7DJec2vMr2JB7sFd84EYzoMsZ9OApg+"
    "z+Lb5s+vn9unI33IVzJF3YPm6+d6AfCKscLYrnMBurXvGHpHE30Bm4wnZ33ut6GLPSLyUr/P19iZmyLn"
    "gW1oHEVo6LcAm3bOWCDrn18XuhBaiAYf+JGTfVWJvwu9SPDmi5hZi9+g7/+Ci8OFPuWv6DJ0e8Qba0xk"
    "lLSrRtMiy7aFumyC4LdwmubXl82FdP9ML9Mac3XiKX/Gqv+Bzx7NbiN/YPxnHzM14PnAFfArVz++yP7W"
    "OQwF3Kffs/pVCm0YuoY2vnMHp8rHfFArlcN+ZVnOLVJikht6tF08xpA+0TB9nkMAJfbJu7p3sONjrUQG"
    "ZScZxTocrk9yjQ9ttd78CCP341qKb2rUGqu5/FnNVR/Vr+7jO25xg5HrhHPBY3neLMhOFwh8hg9N/+zm"
    "Q6p/x5gvxwcvvKOQ+xH9MrziaUpZ2S06pCfPy2YEv81s7fYgNOizIJxVkaQk40tTh2USJh+2HcKYdxEg"
    "Zj5Likffc9uX21fiOQw/LMO04jMq5mg7FWAr7lvjbgg02MkdwAvgpmLArwywJ4gttpfpAT0/+JXWX0Yy"
    "bjaT8AU23bpOvtGXX2L7E/MshD2eM7LSm3LWOWse0TJvi/d46zKQglm6j8wPOMIG42EPZiRn9/3wcPDy"
    "qjHj8IE/R+6HxjfVwKgGTvZ3DmcqrjUKvv5GE6cxsjCuhWoBBlT6pAD1oXzq3BDquKx/sYbhv/+TfYq3"
    "/7OGwQ+TkPZ8OwWeBT4+iDUMOdq2FERTDlf+ssqz6UT8OZtIP/6V0Xf4qx51jK3kvvvPR5jOt7z6CFNZ"
    "8beqaJ7XeDp4Rw5S1osi9ZznMk4l37qSkSaWk8hxDEdvl0ozpkYxLGHxkvkXQ56hMH4sGGnn6g5Wzo4Z"
    "H/pwlgpsILyJaBMptJDU45KIt09EybBOnaKRY5f4GEaeblCkJC5bKgvAfdEXn0s7PITAFfULZAO/M/q3"
    "EhIdiI/Lq9TB4tonRuP1dVa4oAQXNegCxhP6YH64/XT7fQoag08wvY8/awrhZ8KxKsL0r9cB5KWVmnLy"
    "G75fC4LrN4macoxCmjHABuHV6gfv1gLHnwHbJuOjMkRv3ILWkq+oDzahGWRwGqa+ZdpkLt/gWFOKOhmq"
    "MJLyXNfqbIx99dE475fbqqjDqO0t4tW/jYPiJY9N/c3irpwt2PTaN0N/oGZ51VPiNjFnuK66BNm1K4sz"
    "RRTpqE8L7QPaetX8y78rah9Fr4Nex9wr82aFtiIIHwCK0CfYj566HMUIFCdkf/vap0b7W/yALY1N3wr2"
    "onFkyGQbRfovsAKikseGEn/9u1RQqnX96q16quSVVquVM85+f96c+XTr2D0sJinFa+KUud/2Zc3vkhrE"
    "ChZKCCk/sAlB1IdgbA0+xf0Mv/gMaAvc8lsh/WZx4+/CQSk2rIjx9+C96SasnkyvEFZYonc516craaEA"
    "S3mrfENcC6jPzZ2/r13Q8gn3eMRwrlW3L5k+vcMAcPzzctz/7YrwkQIE33Z0B2iJyFIcKfeNsLQyjUr5"
    "VdZjZH56ZIilZ1nR5EfQsMNkUdMT3UKic7fdEJVoW9K6RJbKpeW2Q2rt10nX2lQUcZCBNwLIyQd/gj0B"
    "kLLrlns/mx1SGgnMdeE/d318OxTaLbpMPuTgFBdFbq+Ltmfe14ZfOqeK2oInn3xCyWWb09B7Jxd3oaQx"
    "0j4IKYgMbTMAzECxW9DvJrLjG+2QKWzcEj5jwFIEQOcE+ncSMybTuBAJxB09doQlxlOHO0Bk0pNzyVLf"
    "auXQtdlwVHXTnPYkX6+OlcKeGbHsO4EVXJ8VHHSj0+XzPVQc6ZEY1CqcWMpD3ZFSJosbP0s34axGYLFO"
    "HabjdwiDj7ose3x/M0G+EEmqg8QfU0kmWalwgkPJOftjTyleqYqJIZkjd8Bl+E0ZT80QxUsJsZb/aYPK"
    "cfwVMsbiYzi2W5elAGerhXPDyqHrnFgiLKJQSnTj+v7TDp8nXSlfDE3yAazXK0PZu8bJ+0qBrvTI+DCY"
    "wO0T86EggR1tiekEmYQErAqwVgAcgh14meIu0VO3XvF4iP4ImFQHyY19ATOwCy+DOJ7qGa5tWuPc58Ec"
    "Fv5Bvi/fYUWxmQKSYJm/4wv0WdUZsApiJIVDAWcCIezzuHT6A7MpJ6klZFnAd7MrDTB/LYKchuUTwqp1"
    "TASxDaexRuFCpGDWXUM+cUg+5Hor2vrD1EzcMVTk2JGeFKrKiyOVu0JTxUIPKv2lpafrgOV8mRiJchDu"
    "MVdxzPvx8k2Nf0bmeBQaIk0DNlhl+SPlTCdUn6tAiyy+3IR68HJFetVXOWzlmymmT7HnYUbDfPxAJs5b"
    "KU6XCmIfK6Rs8vQGexO+IGxeHHHGdSnM8ZVfN1NbeW4+RuEXxW9Yi/Ltz6K5PvB9tSRzQp0Nrbm+cTHC"
    "+Xr3oIqs0lxemTHEcZ3YcirlR5S0ZJVAhxw0p+FaaNNeVGX5UROVlkr0F+3CF/odX8irGp0iYnxDEPQH"
    "w+Pa2ST/VVBgSvHngiJGrT3S94uUyMQn+5DcPTFj7vfXxngnpI0LR3ekqHFjmVuqDYvdjnrOAjmwdTZR"
    "XWkqkjQGqZjJB0fFSGUs7u9EAcOwkClreRpGmDAl6h9nn5KxAYNtDDgcbHlqoZ9xFgnr8gkxrc5ZDUHE"
    "DrQwWfv2ZPtwzc1fAvWeL8kuhdU/UpCf9Eyz3WJ/Qv83ffkJGMd8WPnyuYh9i+Y8QiKNtiB8mlvDgKY8"
    "b4su4VuZ7PCCZgU+AuKFZzO4gadFNQNfQoRyQ5ItP/vW9T4hcStOSaH/MFp7R4Tt4yreuiTpPh7w3RcG"
    "m2y0kiE+5AbevYhb2d8PDqruQUbDaoPeiuAAC7XYkeFvPGmN9Hrbg4SiiWYpxw806lEgXDGHMMuFqOVA"
    "9ugXKgymK2tf+HkZXSIeDTSlZwaHEIPA5gKw/72ZeBQk7l78wocHQg3Jf+/ffZTF/PZTH29ksqHBuhvy"
    "54UiiMXQt9cec2A7UEbYOtjD9i0jmqfvm5Jrq94zwkvG9GIem3Nh/Iiw9+pNSXfB0NOTlN87P3l+yWZ1"
    "6jx4ZQneDjjKYLcBhAfJSXqNojVeOYiA2f7Q6impK0+qBDXaQ8dAmDJzC2A7pArXwYdKKC/iAKZ12ajm"
    "+77uk60M6n7/riIeSVQ8xtFqk1OcyJnGWgwtcZxB/Xo6Ktw6YG1NcRz+kAm1sjy65iRIZmiZ3h2edR0r"
    "eFWZQz163C1nW06sGarnJCirpM73SrVc995k91NqbvprEplsiLBhqdHoyxPpxXKzZ5QipBWVd1ukQry4"
    "kxwoDB293DDwmq+L7fTq++4Z3MyvIhiMSiU6rjbLQNVcfZpfASpsWJE3ukem6AlXCyd0F2HSq8slvXEe"
    "Vw82M01pmUs04Y0sx6ujmhbeg8HOFLwAHs7dOk+Mw0O1pMitYOQ02wui91uE68qoeoc5xyUoVoyelv7K"
    "raYFJyKNu8mdY0qSKXw28MkpDyh59ZJBI5YBj+pjz0d+P1z0hN6n7ZcF/xmL3d/jm8eRLkdL5ymhxrME"
    "aSYYhkGpHfoKHi9YqwX/3pEzqScdsc7syCPfMk00l+qtjrk9trRH0wcq8xmh+0NX2nGE81uYZEMA6AJ6"
    "qbuX3ALxFivhFMwHNiPO9oifj5u5fptmp0sy5FCCTWGcYTC2pM0UNqodmRuIbugYZp6hS7XfDNXirrtc"
    "Bn3k6hv0FB1Q86pA9F3uXSD0sUolCTzC/fJ95t0CG0tEtlGJyfYLfR1l5g8n/4HEMX83+ska1tzqwP1I"
    "bzlt+ftvaxLn02DdgxNg2gE7f3LUTKWNPLhHWJU/d/j1I3VXRNxBaFx7vRO51M+81whGsXm6cRb4qgCg"
    "27ytBvdeYvdXVoVrS0Jc34Si5dA+yrb19/tyQ2r+nVdc6HB6nnsUWS0nHxBRqhBZAiylG2DWr8InZeW5"
    "j+i1h1WnlJg7/pTBZyOOPtsNY/5tY+FpkbCFDF2y2/5BFoWq548NxoX/5muyuezkuO3LE9b1BX1nVflx"
    "0+4qjUXOdCm292z9bQE6agY/odhfYNWDAWdMhm8Rd+SXuSFFskFYWiUJ1jhpcDYr7MqfSeg2h92t713Q"
    "4jEAsZwS8+BLA7vNG1G0MCPHnrdjtB+rOYR9XCUSgmiiLTkrYkgEwZ5o1WrzrvuiMm6cIdW0skZFnuT2"
    "30IcCUgzpy/ni+CXwlBE8pGUSL16Eu9gyAHgVJDn0XrPmARdU9HvWOo3LttczWiv5rTSMzpQ4VQhF281"
    "4VzZGim4Oe8LSESnQeeMyqOaR3NMz2iUfy/LGnBv9PpHSQsNPQmSTbv+BdSrXRrs17XX3XN1FrhbxKFO"
    "90L/tqpQzBO8ek5amuMbmxYLG10Ku6/QsmRP8gRLWVUFiTH1UME5wY91ka9z+sLy1qjww5nkSS2XWazh"
    "Jtr5S4fySPyrNS3/6b/9Az8VmX9/97TAQYJevn/9vXt6qwSANeKQ56f2nMWKqi2b+PUsaUJ1pJceS3Gl"
    "Lhpkb6kCXatjzfC68Y0NJjRlft6ihchBL7hgYFdrAlOkXDOq5wg8q7zVjh29++8YF+3IruchcZUFf8Zj"
    "UpElmThWRwOA3etWxOAChiAI8GAoLwKNdah+3GA3R5e3Yuo+BTOPg8q5jsteHDIAcn07fYBmLYQQm7BD"
    "rZEprAj62vc8BJC2XMVipcgRRK4inM5jn6u0RJAsr/nhBw8fSNCVNj3oSnLvKIfXVDwn0kHFHgvNrPKh"
    "0tzI1TUxrIA8JQeGCf/Uz0af6e7GryJGK7nK+KeMcw0uoDhFpSkiXkkeeA/TOupcEzeCA+T6OBsJAo0y"
    "gboIDMeVVR9+QrclPYq2ncQR00AU3E7zIwDV0fj36Gu0i/LIW58gdWwvciec2ktM2tuZx2JIMK3Sy02Q"
    "Lj1NACUHUuPfbDIBVv9ZbMEiZ/26naSbiI62iF+Q5f1O5MZ1EkFLbdv9ZcFral9N/QoE7G1Hgh6I8ghv"
    "HBBqBNGil3tKy9dFstYT7WDFU9v8GY8uSSFtEQlvBJFGowkQjWuyNJCNC4PB9DGUPo8ZyRVYMjr1vxWY"
    "J/DKe69b0c6z7cUfccEmw34DZnUXOfs9EAsVcjNrQKHk9QhoeDzb1xrO4SsmamSvTn54pMb2C+QQGigg"
    "V4CXZzxRsNULh+pcmwJBu3wf4pXsq9sVuK99nFub7qBpECNVDDOLWPzfSp9YAOA5Ooo5nO8nx7QWdAGx"
    "YCj3zS8qUTygXbHw4+cv2LYLbP3aZLNcuDO0xCGPR9aF/plcsNHwxmBTRqRCqt7QlNjmpOweGSbg9Dr8"
    "KiUgq2GisYT0UMmlZGMXxvnbhOGBGby51aT5ZHvI8b7tg+xyMQ4iRnS/xpKIpGZcpYFOeGDjW8unhaqF"
    "lyE9YL6LxCbbuS6FX9o8bdme35m6yiPaNyDAcvpqgsupAW6zhRjspVvbNou5XF0MHh0L9sPdsCWVRQM3"
    "TwzGfYcQOjtnUbDvbaw3eyh13sKfQCYiNBCa1wBYroT60SN9VIHwLM7oBEc3Oee2F95Yajuk/YChaMu/"
    "vQZ91LkfplAt92IP/SJDsvMFfYkWdVena/friaZdOAhSDUNzsaA4VBRGIpke3fazWdWjFoL0gj/gtMaq"
    "LKiCjq/Mgi0rQInGc5SFFOlVlVm4oM1R7Iw653jvv4ZnAa4wJOarPt1wx6skQNbnJXvR+BQBez1fMJpw"
    "OTKX4bY971yiT/Sjx8TImn3+xpRpKEKDAYLshV53d7eKdISIfsUs/LDeOlQmjseTOPeml2OiOkcgr6My"
    "rUmMiM5voQDzxlueM9xgBpT67EGAbN7w3On0vymHBwqEuhB9IEeEHJpf+4jwKkd07Po2gekH7oyUB0/5"
    "zQ+B1H3ftLAp+9vTt0HiMtJovP810QjmG9FxY2A0X6wtoforHJNWjsiXu3jW2uWLGGlKeuhEGpCmQ/pL"
    "F2ciKEKdJa6dQIqPfsYGtczuvU1UbzTNJLmaonwcG6W/RruvgKXXTu0TVVHRFzUFlZhJ+Kq2KwG/jsCb"
    "36Ixh89+bQo16gnrKCD0NT3qhWzUXeBsZMW+T+beEW8zrcsFNz2JlC1EzTBCY+tBargqv9E67GEUPNdP"
    "JqL1md6mHMD37Rt1gDH7C9DOYVNvuxjeyeYQ3uKurotQewmWNg6l7/vYilCCdE+cMwTNRSqx+bL8ZnuD"
    "HNumOtNvNv8E97D3bvM23yT+TbiehRqCK7GiiJEz0EoHTu/ZeZQWfYxSFq+vyk77O34tGC2J12IflNNW"
    "56OelhWbGF1Mclnmc65hI4UkbgS2DFw1PX1rhsIKM/R9uTinn6XCXSxSDNo+2H5OyG07qO9xTFTYUJvz"
    "jeTAmZ84CSspznNPAw2Zhsj018IcKmK+qbUWORSugEHaQWRdR4oevOH7ZHwy/mBsXEA6uNnL9Hicgy1m"
    "BhU/liXfSXjCqXxDbcHhN/G0HmEX56tu6EtFfjyu3sST8AZGaf8i9eRm8gAqpOE+8XFX9gr7inEUhQjs"
    "H58If8Fkp313a3JNOWJ8ibYCmxONqteldBIBSkJfFaJCnbrzcU6a5UVpFz2jrNWZKmGx1kZMZdkRvDw+"
    "EFVaPZHXgOuvkohzgQQTUhL+DxlMgccy6w2ogPMt8Tm5i2ot9uPRKQSV2yL5FuU8KMVZ1KlEsG2yhR59"
    "kAyNUim/NURLxLameSqGuUU8qCTIL0zt4WkS7U9jt/CPX0GL57teFkzP8AqGuLnAEt42kr9BqHO3ryoE"
    "cUTn8XlwC012/+ek7iIwrRY9QqJODY98CRSemnxV9Ugf0hBhql8Xs77d/VCnaboza8SzPfHdHfy4QD5u"
    "mLFH7rqOTklJrqBOV9IzC32OyK34cwGkp5TX9bzMxfzAuUITspZ+/8UZ5f/x3/4BuwnSv7Pb6ocJfP5e"
    "dgOe7Yn75Alvf7kUJF338Ztl6UKnP152El/4QhYv5DdDR49Py2fAaTzTBA7DyBSFQgK6OBLnMBUzj69l"
    "KV3VQRbh0/MsDYfH6LKg2oKvo2QNodHLDsMLgPDRxzBWXQCs3KYNyCEDuH2SEyQibiTylOHeyn0/J08v"
    "Kkj/qHjAIojXEZPnSSU7V+wnXXn896MB7Jer+G52YR0HrzMGqgPsLF9E1GYtsv21VEan1YwNfH71cxPe"
    "VodzJXHlKTnJtq5c5ZIpp/nZS06p37L/PXaHGJC3pDfH1Khbzl4XXhjArn56She0K0sHRD0OsR5HhR6p"
    "tCXm7jzfcAM9vVgb1cnDsXkshdG6+AKFV4mSfZNx9Wmpui0oGtKZzj+jdGuq9yoQqSjjUhQ99uJB5K3b"
    "j6AdmzyngyJYCzgFCr0oCtCV4/tgvkeYyEui8i4EaSAMGfrrUvTzN5H7M4WAYlJaDadhJ1IuTSkSYWtA"
    "0xFg+175HD/3jrRRxHhJ/SMMijUNyf+xF4BvPvjYgJ2zgIa1HUx6V3OBNTY1pgH8ShDwFA5xdf/BIfXT"
    "XUB4Q5nxI+0F8EsHZqG3HoN7Am9enqOEg30W0A9BKAVWeX7s74HBXTEXVQZOqgy4kxOEnymhRsZxJBZO"
    "DI+NPeR7jB1IqGb3EsEmn9JOfmLQ9JVFXME+jHvc9+xq9JUZ5T76YyqyhwPoF9nI1Nw4BzhoPBZhyooo"
    "gEMTxc46PeJJ9Cbg1x53bFqEXxOescR1GvRigqhNmPe2fSLvqnKcxzK8Cf4j0EbcxZISJM038XFvmfAc"
    "+sBI4O6ln2wf6PdGwEnvt/NreZ1p1dIA6d5vBwbFdz91hs3usgIeTmtuyJZsFyFVqQ3T+9jqoINj6akF"
    "THMoqi1/cpxCwOQoX5rV7SU5MLE0LJSS0SFeajTM9qIJkKhACv2xN0SHfr/0kMrdpXu+frhOCgv6q82p"
    "K4qLD0ImfeJ+ihAFpUPpRaMEgeYppfFQ7ddLAw7Ti9iGXF4qUsX0R2RX4rOGyKCoPboTJBllmkF+29k9"
    "gvA2z6Lcr6I2K8L4KfEBo6QOPupeEnu8cdk7+KiVeaScfnPBlzdo6giH8AQ4OAmprf/55jm9PO0vcSdl"
    "wGPjEUCSaYYiNL3EBA+uCboD4oed9pPQwoHcCHzvIBAP3fIBhr95bSBMmEYonmOmacsRRdH9YACf1VFU"
    "dY2r8zcBFO6HDLn7JSdU6OED8ofhzbCsYp0eDRro38Edb7XVpZujWqFPYr5t24gyNUrkEqKl5FiXpVp5"
    "SW7FA19Y7c5G4BKYjMiCbAI34kaI+2GRNOq0Gy/iKTVaHfL72fHfDFT8g2PXM23+brOUZt2Ww6QAsoHF"
    "BG2q83x/T+Dm5dcSZZs23BZ75Ji2e5oDMuMItDTbAAfaRCiF8L427p0JdrrdjUrYkQE7f3lYJnLlRvoM"
    "vHX4MHJk+mZjyKIB2BJPj8xKJTnfwvWJVLiOkTYVc9lnZU4OEwCLDRzrRkGi0YIfzyejcY3Uy2IyODMs"
    "zOowQVPQ3u9qKmlsiao4pVK/83yPY72J1td0y1vbpK/GUqekeMSSjDPlswxaUK7seJ2Y8Nas4wjgJ7YG"
    "Xq7+bIDmu0nEOogJey3XwUD0c3mnkamu97E0+Gx7RdfqJdJZBqf8TeY4e+HkfmuRXdadN5JLMCQjwZee"
    "Bna/bijI85fJYLFumasRQFbkAj/Db4x4oweAwqfW3DWEWOaYzYiCdNNdgVehAx0oEAIUnwn6shQlsheq"
    "qdSLbSNuwObrFLBoPON3O5DB6vc5QcawV5KJCpGcNJ7w6HQ/CDrD9WDScMdv3hOQsH6SbvHOVGguiOV1"
    "D2r7FrMl2XB/2TeOUq6JFk9zutoPR0rXutbbI4NP7RMDXV6Q1m1YW7TjpB5OpnKhArC6hgHlLH5WB+0R"
    "7yXSWTCatYEuAFLU5Rev8P6eSEBlBhyBsL3xh4wfP/zqgfkSHmYG1HI9p/6W46pQZFfO6xjU2h5lC4My"
    "rYUOgls3iLDdS7Wcf1Eafy41WmLmpNwfUrj9uRwNPkxHym00+0QB054xZVNvgoAFvYmQL0gmTeKM1+9D"
    "fdD6CkisBo4CSp3NFGXqK4kn9y+eIf3X//xPniH5//cs5iCH79C/BvEgCAwHDwBfQKfrsDFJ+7AbEql5"
    "BU3toSFyalXetoR7e1huxke+414DhQLLsqLbq/32kqC3mVvgHGlrz+DHJT8moFsN2/xYMSXVuiranxL4"
    "+O444BENAhI9Q7Fqog15qOYmgWJGXuCFjB/EKbsmL00zu8Xuy5RHqVLN9xqTJxHmGo0mBAg4+IacBNAu"
    "SNpHMyGJH14VSec5c+gmMb6WsZbjObIxJcv4RykSITuyiM7ENb0G/poFz2dvzN4YyTB3LeKF+eg75LGn"
    "zEHvS2K+1Pgbv9mgz58MCJEKlf31mKvNwbhi1dqQYaS6tutKpZOrkIwNPgGChC1lZF3K+77tLdE6DVmr"
    "VLa3EfA9VCFq4AJQXyNhdaHJjesbmu7pp74O5zRB/+yWdb4gEgziJz9C+THzjx1gYwmGHpnUgHenYrmf"
    "s+zR/HylI9ANxn3GQhF0e/3+sKTe7KFDn3ORpguwocCl/Tz0u+g+is/QoGGU1kD0GAyJ4iQ08pr60vNP"
    "W1uv7G8w8c64cr8Ld4/9M7+ceXvunhbJiTpcyGcaCShfBqoWd0ZOVLOJZ26deTq7jiK1l4919lWFw2JH"
    "nbOEbJiaz8+D7hwOM9DztZgr72WUN/5kjbPKGLXN71HnXQdOzGigoKK0KKN5xz83atO8qkLJBtviQwXO"
    "bHDsu26Kg2m9F2AYuMN7iz4uiTBkG7rZF7iwysfi96hHKjm+QJ35jgFWcQTz6NJLM5rPHnieDBqfgD9P"
    "83OrK2XpyYGM+NJeuSthGulxJIz+/jaYl8Y8AlwgN0Ty2EJ7R+Ll96HRAz2w6eEXt6sdQcTf8TylARBj"
    "2DQTyJ74iN0D4PJ9eDv9Je1cdCgMXKR4X6/t6XS2ITTaphJvwcWrFbkYDcfRP8hVHabWFd/JH6n2b8Iq"
    "rJLoJAhq9JXw+BO7GHqefrphzW2LH6Ec2hH6fJuvDtG6uXj3HizreYigSOMtQYnhCL3gBnanJnIV7V3z"
    "31sYtrmmZUh+Y6l1Rq21gSPIO2+rfFA5SvcazWVYKtfZPiwcxxwqMNfy36lUmabfALOB52OU6p6gKUeh"
    "ZUuK4qqESquiR32j82uqx8VPjwIfe7vvT1AiPZeYFd8eNev14I65WWhVNUltO6eWKPozimL720Fv86m1"
    "otMWSPfRMBwPI4fZASihFt7/FAWoZWUCZPuyduRc2LytYz4A5PfyaXZqokKAcweTIrplZDU3xTA6YZkl"
    "y6/6qjgMuvNGdIj2DGajaLJfXlIyDDuaq/oi1FaWDafQnHDpp8dylISyjFb7ljHiz3epwvHr9H5E0/c9"
    "f86JedntgmLvyjZpecu2kxIyNE6STDVZLSVBpgSLbHm+cCyIf5fj52ML2/MTjB2aZ7OVEPuT8q5hoGNJ"
    "WZZQUlxLCRffyw31Sa9Lm8f6rHhx+WpQbuC/nAxaFaMV63W2eO/5acVYqwDgwIGe73SGbep6gcQj1aMT"
    "VydpAs3BlJw5J4XKiqEXB2vX2crb8zALYP4yYKoHKn8EOLQe+ls+yrd4LGP9tfOtazNl3XsBnoI4UIVT"
    "Pq5+Xr+JWfhuFBRF+f0hTeu+LWdZjF9TbMJolkWUKf3JGz7wH/E5niNqnyvLM6XZ4ZEZfiR+DF84c/Tz"
    "UphAqb8fNh/o7WugHn9/lmb54HBLECQRj9/1APivjrUjbsLowCMFiqOdncFq85neEb+l9RM69+eFZTPx"
    "L4ZWsVhzXoKsl0FUUTc0cWTGAvP5AnIa16hSODoO5UexwjkBuvK8imKH6mnl5aD/uGvfVCfBcBoCcdgb"
    "4mb6UXFs/WomhsqnvwY96+XzwLah26dIIMdcUmXcpyOAgTjNZsuEGTNCKMtBrs7F+KZbgKTaXHU/kjTl"
    "jBq3gMRjIhDfESHITNKSSMOGQJIUhEckH9Kz75X4O/b+Ic0ww+c5JGv5QawBHykmarUAZMmmQCW23rpA"
    "6y8OnJkZMVrD6+3oJ2JOkrN2Aj2vArAD9KWL/PoQ4DCadvEmfcLaIi8EUF8ihHtdv3XQyjk2wGtjkFBI"
    "Vbzy6589p1Zpl8jxC250FnNO/RV+NCQcd6hm/Mf5bOyBCw3hMusspRdKe6zkeZx+Fy2GtnWcKO4vilmq"
    "Iv4OuSMElHam7LxlkykNr1jzvxXqLLv+Tf0hVhAAuL/t57CG4SiLzIjOvxVoSvx7+5u+YylulJEdW6pN"
    "xbppU+JrLL93XQVvJTNfO51Qw9oFhsO87yOryZm3XUo7Gj+65XWysWvgecbNz+NfBTQUlHotlDYNfcXZ"
    "2Gtn0kf0EmpdPRmo70795jBF2Sv3IRe6IE1wLx4ZjbRyARE9dgPfVZXvV/SgxSr7rKIQirT4cGROuuAV"
    "iXr19bZ3HIXz2aJeSI1SEuOLy2VumvU4u0tcit95B8qZwraJgg/P3+4yRvlDi2h/+pcGP0GrZw5qvpft"
    "vW79rQXORQv2Ve1fZoNDCWMgMqGsCE6fzxRKgSc2e+xXFhPpQO/eJUYpO8J/RmPj13pD7KDIYS1AMZA6"
    "j6Oxv2pDecD/7znV//wv/+OfbNsx/fu2HZMfpiHtfewOeJYBwTckS+VUvxqLrnhaL6XY4Zmx4Np2dMra"
    "Kv+Wu/PsnDDd/IUonJ8zWF7jwOacMli8r60IdqMab23yAHviWszRLMaWAG6SpDccrZZynz3rcBLDH/JF"
    "BAdyOxSDsRXX8IwEBzMHn8HIfzzefFAt5K983o7pDro57bE9vXscEdOaCwmwIw6lHh3TBj6g+hAf/ad2"
    "ubLsG3IR4VsdYKv8yUwBFIb7gLjSfAEQGFCBL3R8g3HWYk8gvBUEAMKGFRncSws+u8O+maFRocs4G+j1"
    "RfPmAgblk+/eSzzy1QtWEk9erzfS5QNfJY9XoHAmKh+Kxv/kW/rVcm1orAdEABBR8Pc2DhPjKVp69Ufv"
    "/4IswAVc7bKYAAMPA86aqSAkMP2PntoSugFuPMTsxwzOB2/GvH0IKNeFJjy3cZRKiNScawXVYAvSX6rB"
    "hRu1c+gxt9J2oktKqFWejyPXQqN0zMDgN6HorgVBY+/K8DtmGzjUYTAfKI/SSd8WzJsmTUdrlCd+IfIp"
    "ZPdbo4Xmk8naeTY3+oykartC8RvT0lT9ju3v3kyK4/VVM6LGq0KyrfClxtV+FwdQ/NsD2aIpW+YNwtgk"
    "DPJ5O1CJNwyaIcGA4HKN1zaGTV8SYUjnD9OPcznx3u8NTljTmL0oB8X4bLb3WibCCDBIcoDWI9TbU2eo"
    "rlPtvVTxCZOknbTa62jx4GnLw1hWsOXaeOPkREwbihczHuQxJ5NBn0rCOyt5SwNEAcS/R/+QO3+S7Vzi"
    "Db4Z7jTZ6rw4iDWetDipghe/EpuTx9m+nsLR7u/cvy++oCdw8KvCs1LicRF6TnWr5gED8K5oChXVunUV"
    "7aFeMbb8fNLwY3uxELUNv7mxq4K/rNToZmbL5DOo3bMa7nXBzANn7A+Rrjcao8oECZKUjkuqv5VJ4MEb"
    "/A+7bFn1jadIemidgyzutf637AmNfcZqqWhaICRTJzveocabMLhTO055WrKHMs/OhuLFcDmbvj+QNfP9"
    "Sxv3OIKqYJhmIxX1LL+pQQhvNLRHqGhq55df6EsSHx7e6fsKawJyLXMQOYuTxveCy9tWhnhLWEl8I+4U"
    "LZZ6vf01NyRz/CKFT/CLrSh5IltWnyY1WC07dLLv2xkDyWRoaus9wf77P7m6nKVRYpRoKlvKod+SLV+P"
    "w7TVZLm2HgO2tyr7F67mdE3Ud+zRtUJPQmXzlEUpfS1+gX1VXfT3ObVvZty/v6NO3mIEOwh+fdDVlYvN"
    "6M3RxY5h0Nb6fmNsEfKpVApENX6JWysSms+om6UHEeRsLTHqvKOIzFIoms2EC6rTLU59LzUoOeRgFKw3"
    "YIh0d4J4fdHJUuDADzPcttZd/+OK8k3s7P4MyfeNkcqmLRrkMTBuMuTnSIx/WZDe4TRQzE+gbruYf6Um"
    "8K5fITocoH/0z2dzPmGD7lJEcTZvR7BeR+9o8yTnQ680qbpedmh1/RrYYT5OfdVOL9XBa6xXZBJ0qg9f"
    "zv9MSSTs8N8EJolN8RRXv9EzO+HMXgLPX0QqWO0o2774jqSfab69Ar35prQCILf/rldZimRHy1XE8CuT"
    "raGzI7O+rrQbsCJPfSP8NIQVInoUbAVA89FjKZpmLF2DMjGGpYYEKeD+Nu8o0xtKMOjbqN+k917DOlWm"
    "usMGaove8to3HqzG/n0pQ8BSbeDQoRasH46vN2XS3yNtEqhU+B9cJ3wnYLHfWTz1XjKCI0Pk6pDnjVR/"
    "TnaKQOKxBQRZTUphPpv1yUqLGTeQ7Q6QyHAxxm3W+P3uWilHh6PFkgAdhoP0ECJFiyr1z56eAZVDiXn+"
    "fni2ihvhyM131CLjlRPbHPxPFkRmrwmFafZREc4fi6HOSBPQnI/hovkibO8VH4GuZ130wgQVxTe95/og"
    "IYQi/RxkL0tqXyGhIiFDg214drxOfq/hvfn+mPuJcfLFJbTTTR9wOeUVDEscr6AP02i3RrIxFH35+kor"
    "lyCAGgjVDtIk6hdHDSlhF8ZyNnXJLucaB9uhceHPIvtxwNHApwTe3vrj0lSHGYlEL2SGfzsaM4Jp+SK1"
    "B52DYXiPa4v8pFhfr0uE57CR5TPjfFl6qjS4kOt8ZUmcyAiZerkckRSKkez5/dgy3xFSHZ6JFOPPL6T4"
    "lHWgSXkziSa4Rj8u6m3TxdK6liz9KKx6/bqa51lgq5ETUr2vPBs7vAVFL94VjvGllRMO7nFJYL6j7ctZ"
    "owjejnQNxcbe8BgZ0xZTrHuY8lBG9OeHdNCmHNVNLA19fWCa6HLbluy8nGxCgxAEoKE3z3MEAkrDW6VW"
    "vVuJt+9nBTho4EeivfE2OKWl+lv0Azzbp5DU+iKviiIvwhWkUcZpK9mgWft3LLe85mTus92gcVr10d3A"
    "jp6xgl4zXZ0TdUkaiDllYDdQHHmKkuIKNVi6/DQXIur3N5MGLcB/u0mcVzN5FFNuqu1RvZZOCBrZj2rG"
    "pLquN/bmcRsVfNribZTIT/DCfrcxhB2RnAs5zeNSQwdYe73mzvthoNqhxAB75TJlgbfu+TFcb1w3qeyK"
    "3+SDA/mbLdao1m/1fqsmsakWlMh1xSfnYOtg63nokOzLzLGWNgt/J8YiallRNVoLv99lA1/tpxYIJIsx"
    "lEGil9EKg02v/V73XH3DdAFSglg+9zc3hc9fvf947bTAiDXP40wcHXHPmLlNwGuWdF2gvyeZT0tarci7"
    "H9Wq/wQ5C3l0QQoJG/3LcdpJqvXq6cGdPA6p00X4Fm7AYzAy+3m+73O8OF6QISSUicuYs4U4uK+xt/iw"
    "ytW0eAcnZvu+xw+vxeF6AxARRpfnz4QA2Ph7u3Aay5D1+g3XLozJ0iApAa8HRxAZpuAm9b6McRek7GRs"
    "CQiW5Irgraq53MW9ra3H1NoTcM/89nkPDSoH52X5Yof7DuUo1gb3mx4G4kcqTq7nT+VT2DUf8Zy/yRfX"
    "Ehos9/DKxdq7CY8pLTbdkd+RvV+qn9lVXw4fvxQeqmxKWmVGUTUVSfc0zynNilFhdJ07hOb0yK26v+hr"
    "MsThktioCzpHa2gk/nUcmi3wBq7ZsN+x356urcE99OFsKHffYbeOX43940wUhxn2ojRhtmamtuy33XkF"
    "HRUFtgTX2aF0B/fBISjN3BkEPuFYa/T416jt8y0e3Ie+mcyz40u4kAU9+wdeH/awKQcxrgVnJ+cdEgTf"
    "zxPNUHsQu76kuKiSDQ54DCCIzCMQoQyx5KKHg7/l76VNa3/sgC/RczcvkH/cTdw5TtIzdcpE3w99TXoo"
    "GCD3XbyntRC08yhD3M9Ttss8/9XxPRTVsJt2E60l3v6FM57dbLoB97LEtYmBNdvKIZDDCb7+i0fq/+Gf"
    "LBuU0P/36COEfZ0pFE3wNYzjyB8noiOiTF+meutlxaC4y/v82w2o6pSKCWvuxM/7ZyxS667bjnBD66d6"
    "eCr4+8KOKF9H2p1MXJ1QbjtGlK1zVlvajMMxrBwvBg5nSIGTOEBYO+3zwnkUQP4DcAwZTBOIsYcWMlSn"
    "6rktbI8J5ZuU6nKCfpTOWvC3nyyqccHnq9PfftYgMjmWJp4t8ZsOTa3vqLPb4yikEoPU43w/h3iW5zX5"
    "wrzJd3NKqbvZ15lD6oRZqtBg68oa11hiFktzFDS6r5ITAVJ1M/VZVQglsecKD/AAefmHP2IHeyV76XkU"
    "XPEFg2g9ba7StS6BP2aSf2bT/jCU0UNvB7CLSJmx90luQ3AlE5kytSKoO7Hq1mcjvhyrSTLt/Yc3mlVy"
    "NC/dHYfxKB4Dcc+rMKzpLT/SV3NDYxnTqj1Wm1n22H08xJpqrNiHFYn0sVXSdWTzUo+eakueRelroI23"
    "fMSmbPEhIT1SDCSj/g5ZvT8Kd94Rg+4DhI3QBXyTQnxvnvvMOlAeV/bDFislM1+2sTUjI/G1PqWjvq5j"
    "v4JirYAebD/D+7QyCJIJr8q72KQFS/xwel+cKNpEBgsLHpo3pEDEBev43cgkT9HQ6aPrPWna7swnmWTo"
    "EJIXz+xK5NLtBoEQwW8v6FLM3XYwrJXOOLql4rbSKMgmAZhkfHShY5XRV6gqRIuO9u8wTaefTYfo7Lea"
    "ea6h25/RrjKjqmsq3Rrv4EjAx00PqCoML3K6CcyBZ39ELRCrLcP6j6cuSrBMK1UUgElgl96MuhzwzEn0"
    "X83roIo2GOaxmJ1Jv8BugtovB+ceCDGiBv7+0oSwJcKpCWQCCQ+86xf9yX4DpvoPLZLAM/d8QJ35EgUC"
    "FrBpM/Nb41as87Lhm+oWVBFEL+LKc6KJbThZHoZU7jqSaQ7syTLoaBY+a5ni5kVEUrQkcz1Ppdfl+49t"
    "fv3v1BW7LZZvSTbi22ynsZEQo+IEJ5akxEQB77GeG3cQ7REEP5yAV3ZZYRXIbc/XyEtinRSEWTvB/+Ls"
    "vHEkhrrsvCAG9EUyUEDvvWdGb4qu6MlIC1AkKBoIGCgQoHVpBVqC2BJmJplJ/qQb3eiuYpH3nvOdR773"
    "CFM81iuVz4qI9eaT0nE22YVCYJueiPuZ6MctjTLmhKvPzxVKVh2DLjcDbC9nRPZT66dDr8tkactTNx0Z"
    "1NdLWCsEdAVySdk28ABIZJ9oIZmCqPrU/WKMyvvMsyAQBm09NZmf6EwSaPTaVOnu3B+Faqe8NAnr8Q1f"
    "r7vZhuBkTK9Tl88FmNVwxuvdahxIsUr1ygkjJLaJmKddhfFGnPkgY0R9OhfBFJOwjZlOMxG7Kv4l/ZwV"
    "nMB1piyI+fmGkEiOO16TBGD3+2bKDUTFY3zykWFUCkutdWMfeWof+CQdahmoYBXXqX3izACbxlffcOth"
    "36yEKGV1WSjaDYmBrwa4wECrpcwmKOWIcw7RQRSUd6wfhR6syrHsikWzacrTUdJEsRAEi7H5hpPhDNSp"
    "oAgB3MMBEumvPzXo2Br4hjHU915wxULk02GtHl/Lqce/+d+6vMsc4NVDGh+YsuC5LVQcSJMLN1nxMTLz"
    "6nn6nLTTZXIs2impe4Y+2TY7rOe9+5gXRUcj9qjPx+mre8cXnFKzPjZQWZ+69ZPfcZR7TEqBtaQRUwXZ"
    "6htBnZbhg24aXMu5HtMvHAgxJDqg29Iy7K5NqubUTSU4+U2calv88vQ1JIsE/5pV3hbn+uTZeEvNwJax"
    "gBfsJVFrKAoyK7ajsNIkJ/uQPhbaK5u9A76WE4geH0YgmAsdi1k6sQDoD5e66lvoy+rqTr1AVCQ0lUd0"
    "gHTdb+N0X7z72ftJNbNgTbZON2rMTTSjbkwyQWXN1AA/GLTWClC8hDHTstSBmCq7asqcsM5zrGmchZXH"
    "NPKhogUkgBaybOmoUqwrg9qvQrv+mD/ANAgy4lFA/FkbUf42mnxDOhcPgHbiP9rBWi6XrjaNHBbFcZPw"
    "7xF6YuBNuGAWa0BrmPvbn8o2KTw9f37FPXUydpFkM+gbVTSLsBiN4B9Yi22OGPMv8oGjBGXUJuaifjhi"
    "ZtnzNMiUro8myb2VWiNHlpWGrbyB1P6p2/o5oHPZnL3ysJXLvLg6XjWunkVKM4hOqYq2oor9OtgYgtoN"
    "OfqI5ag8DU0u7dOxAExJtZQ+xUPo/bK+ricALSjxoRTwdUs4za79JNSVMkUf7e6fVO4/tdcho/9J7nQA"
    "X6Y6LYiH0k7A23VUt+sCXh7lqg6rminNLaZGufYDXCbPb2dVILEUk61AGETkjGjc0ddnBZbVEQLzDJ/V"
    "Lp6btfDwVJAshhrtoh4lo3ro48n06GUH/dm0fPUMA70+FoLDCvEIcS4X3zxFus2Cut2iylTskVV4681Q"
    "ZnuJjaZlZhE4zREz4ZQVfI+WtKtvSUbrZwXO6OwsfZ3G3CEy+gDUf17mX/oehXQWBbCfJdeAcCwhP/Eg"
    "cQfzsy5E05ozLjnoPt5DJAcJojodYQpDZTTV8cZd0AuJV/AafXTngw0fE48fehUBK+nx94L/RLZqd92Q"
    "gR+uZ9o+5hu02fIZgMHPjt39A6y4CusLuP0yxR/MnWuvHqSreK1NcOeLPo8kblX7GmVo046mES4ZgyXL"
    "F4mQNsC2nRDZY16XKxHdbecWV/5kET662JoSHVWN1R86nNahjjxCBsBroDt0PzThD0+WHl80yl+S03aT"
    "rkXZcdlR0xuDKuciKZWP+RFhmOwm4lOiO0qsvsHcH0AYivi355T6JDAKWOamkjRWoA0LrmlDKQhb749a"
    "i1sybyvM3nwtLZXv66oNxCFL1r9Y30KlNZKTYhvyrQLESPmPuXhQCdvWkCmHznqtucHUyRNlJaDWMoZp"
    "+rXsWAGd0MCL4FDqvpWOnNhy22bFpnOVRkZu51oTZmwo/kdF9TfLjC/kgJ+1uhwL1faOWncTHBPQiRcF"
    "t4/PV58rolhIOyeQwY+buTKCPIVpRPXXoht2alsLE0TQG530jFbugrZ2YhHj7rwXul0sk+0xn+vPqUna"
    "MIuXyw92g/6bSSgh1PbqVXBk5jN7WMknRImDT8tMSlHNYNQnyzPW+BV0zAbsGkHQPQsxblBGsdSDTkMV"
    "T95MMJeW4HiQEpRUJcDxVW79R4/g/Lf/+Y88Coz+S15YwqjC3sO/3rwAVCVFETqhP+vfbqbrRPv9Drsc"
    "o8Q/lQ/DJs1C/vs3TKa93Vy3hVdBYddGz7JKEBpUb2tGVBxzXjDvu2kNx6fZtpmGGiBt6TBj58ZVBS3z"
    "lfLW1sc8rGq3KuJKJn7L2K+fofK9RwBpJuBzlFWe33g+f0J4aL7VFRBbgSqB96X5Qgd+QR4Sv01AB+A3"
    "iCtWvAlwJyqwjjAsZyjO8d0D3o8dfE9AuyXLilbH89FgH3xYMDJ+U54rf3Mt0TH6W7Hp2QEiJ0uwxX/Y"
    "K7Z4nHYyB56V8ivLsq19Q0jB1VsgQeINRh49MOk0AAfNL2ehv5E34/RZn+Xmu3N0dc/HDQCYi0arITlc"
    "v3iWeuG8XX7bYFhlHKoH7RQxOhAs4GgtH88UDplzNpnLtBqXWDTipnNWLmQ9jmdH5CuRFiWFTkKfkskp"
    "c8OE2qUf3/xQfCc97rf9h7lobAkojTFJ6PHHsNMbZDfPSzzs6A2ol+gsIV56CMmsIzepOM04EbOrVFYl"
    "nNPhqssf/QGWZ1VmGSOOH3r88PAW31RRNofQ/FiB4fiho5FBcRA8MduLKsJXwGfkuph8LQmJZKjC1suw"
    "cW2CAaWb1wdnSUJCQD2cIS5l9J1f8oJsRtJKu5aj32GEVMW0/ze+qkE/JoxbkDoGwF3L6ADKmjSDNw/O"
    "GEzE/jacu7mgjiBoFZtSruLU3lvuqevoehuyMFexgLGoOZ/epE2un74Pt4lC3/eegqQkgUx3yO/2CWtw"
    "NAHNRpLYOudE7lkWqCP7lww8M9MDzugKtm4b5NHcOrTWZ3f8+MrrGDwSHBXI3x2yHH7Y3UJ1YCU1F2UG"
    "txKgvy2JUl2TvtLfXg4aoFcmvCc878gQbFmrlABmh1g4kMPNPAhYZ0JuvtNOXV3+S4jgXYDl9mmPKSHw"
    "xWT4EfhC5jaVHxa4ziFoDMy+u1qoJgIrV2ISXDG+81Nym6b9xF/t1E5xjPXDcK6t+PXgpGg1CYbTouH+"
    "7KCKMk/WXKkAunTdGTriyfA2ZOv864Zt+ALFCZTVKfiyI8uWNtoj7Ai0VX1vPBLgvF1Db0XIYk+aMUkY"
    "x+E/S039wJ9mlscRyN/LDtWT9Qpojw72S8uhwqn2CweIfp5rk8dQSk8hy/B6ynLL+8oOqCw4OJULAMAd"
    "82TvUYm1QFRbaC++80h+nh+fMBh1IH75uVG/zLy73adpkZ6MOdy34d9H2OnobdIvb/rsORtMAavwSMw8"
    "KLoV/p3QqD1BqFm0YsmYudD9nD3c4l4UME3zzOC+kl2qRubng0rztnhwNEZzEMWLaf3dm+UqPi6AnAx7"
    "QVRZF7j7AaM2CHDEUk0HwletR7v4abYEstaTRh7nFsgI4bnh/jHcRzO/7JnZ/rqK9jywXWbKoan1DZXj"
    "aezbCd2uVuMprDoYrlD6VPRM1zcAnZ7WMQ+hnbXt+B346MkL4yFN/H4Tk+hfWeLV9MkYfQ3tcsnuuO5P"
    "UfYz+sdM8AIZMLGmV0ajC7yBGA82qVMHHpPXGk1bxxbQ8UDzrKfH78UnjmkN+CXRs9CivysxMLYT4M8j"
    "bS3E2tSZ8ZNl4vlP6CytdNuTLM2EHoCc1vuRZ1Tm/lsLVtNjYyTVRZJLtObCGhWnj+nmNKeKAsCOyrUe"
    "xgyBbm3L448tSnqV4lw3Q4lfDsvON+FNPi5bDS7M6pjUyw9Lyu4WpDdOi3o1G9KAj7YZHWdPdSXbgK5j"
    "ADTk1KvkEWO+SnXc7lb05NYarYhrg+L5MBHNcBLJk7XmBqtSV+U8ldKb/WwDWHqipuNP1Uaf3BD7twe3"
    "QSlaiuFc/kfvYXW32sBdcuyl9EbRD2sgASHFELY2jAxGRICdKDfU2+cJIyahr0PGOxSkpg/QJmmUeNcb"
    "F6yAhPxaM+zySb16j8Txe44ON/g0v0pfwRw9o6vNvBLO1L/RiiOiurg84i7JdHgOelV8lW+M3KqtojZJ"
    "0a/jjyZJxbd8pvrHMw87wLrM8peTq8oKPt+rB7CLiArCwEKbZ5I6IjpVRcYIsTJYAl/4e0Olbj/dYIL5"
    "NVtJGYx3P3x1JNNsGochlJtg6JOuaeU5IlDCPQhbaxMVzKVZiQEk61vrMbHZRCjuZQ88NeyXkXumc+6z"
    "B/8TWzLRbRUYStnr0EWY43n5iUDuDyN5k/ulnLf0WdMxauOhkKqjii5GeLkxMLB7FJ4rCdwlzrOUrSy1"
    "ihLNo960+plfl9AYuezW5lOzRu0dsjLwdwR44KHXnWduM4VhWfkq0pZTczzVWRgeeDgMsuHetBPyB0pl"
    "ARjB68P/CpqMXFKgtUVunv3gkaqBU//Zx7fceewVOcysP1wTbruJSd9DWovBloMCy+rf7+Y2fDlIC9u9"
    "t9tSzNvjf5e//vc//Y9/AL8E1v+3mVhvCgkK5wLAg3q0o2RN1hOE22ZoT+J7aPJVrNyFzwrnd4jkP3z4"
    "Ue9JxucFSAVCz6ocFS5tEf0FTR3XYw4dCJKPc9fsz2OEiJ7ic0FlPIEJ7X15q8zJKuvyiv+6j3pYPWj1"
    "BPcQb5VbBPilmLPuQtoWuHOH7DOkc4rsnwwBLCTOloRra4f26vUKaJW5KnC+IyRiY7NkWlmWoEZIZf8r"
    "02KND1pW7kpngj+jA2u3/jY07zDdOKYrTf8Geq/eOmjx8v45gD4nMAIyJKLuo+XnQm3JxmDM2dAv4v59"
    "7og7ieqrNZDQikpQgSB5PQErqFs2Ub9iUHJYQxy6H+XuLu2AIhpwa2kq89hheOqQD0IUvq5557z0IJCq"
    "ZsOEGGLIh0Dqp1CkFpaN4nIsEpCkS3pAn7owXjoH7N8tB7aihT6Agr4B6YtbSnmxKa8rcWJIZRn1NpZE"
    "rzF0v6yIPF+EZeXmmTH4sJcXQBJrYtorYGvQevCYQ7hTkp91TObajLw7/kE0D2SfN6AAzkkTVup8wv1b"
    "3uMr9qHs76hKzHXP+tQAIgxe8DG5vNGB5GbfhuLUHwBHmsvxl14zqtzROKNrfQNuzlfV67Buq0Z2HYiy"
    "3tbI73TplPQVAlyW/gRuFaM+lKsa8/uBfvXNzaUFnxyvw4xTY2FLqDsxZKLa6TzHUuHxwZdOvx5A7Fgz"
    "D2L3sCE1pQ2a3j8hIaNsjzg7YfgyPLUhn9UnPjUek45hLFtr4YwI9fKN9gJdK8c2DVfAJxHlgJLl3FkA"
    "WI2MkTDvtXfqeCKNRI2tL58Kprt2l8itSer0DsDNMY9KHZszNm3wzJJ/rQsNHrYcj6ZFsbpb1qEep+sh"
    "s57o6j0ciakzq/urVpDJ/gJTWujGfk5lk1OZTmXj8bMdOWj6nm20fAUQLYjgb23W4oGP/YBqfX6zfg7Z"
    "/dw4NusMsINM2pcxP0bb+eOUolxD4R8evCnzZyu65ti9/eNpsXnbvad/WqH3lF2HK1qOGyE2azoJkfUc"
    "TCm2nbWnL4fbqyz2axmPcw2fgai4THBuNnsjtdowIswlOE3aTMuwf1uas8wu7cxFG8RSC87xfTM0XFi/"
    "pZ2IBB0pPLqOloLUwG6mE5tORX4eFPu8NbqnxSORkMiyFweI89fy6CJsX/Ag0CEvDbTvHvMW2PMFYv3v"
    "wQ+Z0W7Gp+fJNI1wTwZQ6e+qDfYChEtMScv5zQtMZWrUgs23vii2muQKqVPzj9FOM379T6kQHkvcQsuI"
    "jYfjpLRV9hrg7QBWWGGZWiIzCXvUb+bvhcd/8x3elQe7eODxi2gq+Y2pXWt9qQ9pNjKC7iJGY4+e5xXi"
    "defBf4hcrojGg9oEbCrZLMTpxIOfhNYvuzxGoRwI4roC7LqAHg6VVFSmRVUaP87GA5H03PeOsCnPeLgg"
    "/TJwTXUVIgVisdHJBzcTrsQvPT8spHBwBV3DfCtDQamZcKaLjF8/FA/3znZV3vl1Coa27Z1Y6PXF+lJ2"
    "tpLFlchDNEsDlBqqdpkNj11GzSDimStA3Cou1vR10YeBR5gVXmbzEOi1k0a+wJdLTAagqfcY9nX8Vctc"
    "CJCwq91XhLMl1S2jNVkj6Z6k4iP+zo1ReeZ4gH5vSG7RpEBj0Z+IOMY/58uHz0pi14o8Kfe3pQc3h0gs"
    "PemFxo/tmbuWPKjhkuNqhecOIBA3d5hNbsxKp+yWqFpR5e5NADAfMoQqfSiqvcenHzZ8BHm0xD+/DTAs"
    "R/v+B8MR/+Wf/5Hbl/K/7tQGRyXK/g1HgGO0/+2ZNpAo5rgqS0INXTOMzKo8rhJex8lGliL+I2y9RU0X"
    "Mr2MGV5ouq6knYwfPQh78aogRsqiwMvk4y8xeGbPsC7fTDWvKHZLW2Tb4Kve78VREcQhWo+vyP5sxA95"
    "FwCJUCQOP0Q3gOQpA/QjcvPxK7lwqP421t7NUSZXatYMVR5qQnoODpzVvrzqq2UaNB3xPDCF3MdUzM3G"
    "E61u/WklqDQdvdQdDQyyOqrrmmx9Af65NrvA4A6o8RNEJottLmmY5eOIDDYvmb8IkA8AAsHd3LWMBh8R"
    "YDUAfpq11w/DY7idLAsBJLOBzLFCwO/V2BVIAugxaRhiTxFtcIgAwg54Ds8EiPT7xrTVkN8AD360xFL7"
    "SGcFgtcf9H6N/bWbMo52s8KgOadrdVONMLbLmzdLhYcCcYCoBe/B8SQJiOzfby6tTOZgVZeYWLh95pbk"
    "RSVzczHzjGJNZ79gK87rTProjRSEslnqnlLqyDUkCgEZJKs61i5TzR1VccTXCQ0kFHohiorFR1bRWgIV"
    "8U2YcvdRyc7Pf1sl5fIpIyIA8Jr2ASfvzTgZLVBYBkRiIzrU6PyuwWfdheHZ6K14LFWh7wTN3aUyqWOu"
    "EAF67Wa5qZ37unRzHpZwn9oYePXXzIfFZjkNgS8TK1bLlB7sZ5XcR4DC0ma7qNW5FAhcf2BFuTQ8vtXl"
    "icMMWHKUlI9jCWD0LlkarMZSMavTeosag5tnK9cjZnx7My9R5y9F+dn2LerNODEnPdBNvtnWDttkgp54"
    "wR3gJ90ydTYiTUqRtNZTtRXsGNcxEfdO+tQ0J7yHLMXXKtJ+MB5xIF+ihEFNGwpq287LvEr7TEkLuaKy"
    "UW0av32jz/fwH2wFIPcqJH16YCar9s4zsAJSf8cWm8g0yyxbaznrcJp13rRcsNXjC0hLIQBtiSRe7NcM"
    "z0eEP8VbbhyHQqhcAUMz8Qo+ph/Mfysu/wBlejNVr0U8YHZCl7Qhtr3+0ndYtsFcO3pCrGabXtf4yfoy"
    "XfgsfclhNvYynf8CtiAgo2YkbrKN1wLVZvUK5cwF2/iqDODlFg0pXBATzdeDKGuXVWz5tiN2LLItoE6G"
    "K+GFwJJzdjYrvLBN6w7TNPUVMsOAD3LKKpgY0gJP87pK18PKyq1s206r6qTh9MVWqy5Dq1udr5DQJ+Qc"
    "af2+n/lKanNv9MhJY5ed5pMjKrv80+ZcP7piYhPaYbjO5A99WuRYAfqcZE/oioWX0rb59B1BSrl8Af1A"
    "sj6Xzg5xBgaqYsDfkxEYnufF/vDmlFRMiHHpi/eYM56gDVqdfs16z3Kz2DUu7bNkRRoyaTRy34lWOdJM"
    "ZkrSxoe8dJTstBpd9+p3A/LdSWe5hfowosis2BIRNCCLpojMSR5H1eUKSF8FWZjFDY2CAh8jJcrcXLdg"
    "dmbjkZUeCl1O/ORqhP88jGqVSUVWlm9l8e0qTpHTReXLRsTzLkFTYjyGmxcWYpCqIfGkEV1+iMAEQTog"
    "aWFc6aV4y/VmbgSz+CCK4c+qFYhnwgF5KfSXuPjz8WM5mc1BriS5mErcdOXCX+YHx2bDvmYCmjadUJ6P"
    "f/U57pZszODRzf6UuyjH6X6pIJ8hgI3Sq0kGwr77+ARh1UXZLqU4PNKJD9LBLK3FxvsRVIHzgaH9pmnJ"
    "Xk5g74eBkzJCaRC6ckcpoI2werKWjGwtCHYzPng9gyd3VyuBIxxx2u6Xrz4nKiYyDVNfxTYDD5be0IIF"
    "yodGaKWWfDSfYml4AFYAy4T7/vh4oq/4qV1atruvar9QTk2vy3U9bJitiIQjtW0snpxfs/thDZhr08Hx"
    "jmC2pt7ejUO3DB9jgsED+ng34uX1H1mO/RiCyMumY63WdaNp62AEwczE1lqOer9J2PILTcbJX0xLWQGT"
    "CrZ5BZgM7MS0VVjnvHTsiuORiCCwHYxDc81r+mKQ9fJwTtOYvIEj1lmk/3GKIBUn6MGZjJI0aYRiDS8K"
    "No6vonej0Z8m+Gy/upInVfgsnFJtKL2CtLLjrgpMP6Gc0+jXSD9SQRAwcVjvYLpzkaffYCJpWdIka19q"
    "7v3M+Kje3L8I/Ew9Q7hyKbkunivBg4QlAifT9Crpx0uSMSEb/JYc2j3QhOf+mJltHxOXxEd8NJMdeBfq"
    "GoHXxBSXk3bs3/7la4S+vPmWfw2pufhCH0gfOTq4nfzJzD7qnhOnxY/h8zx9cinCXVlwzleWDKz8xbzq"
    "xc29JErK27+MVpCUFnC45T3V1uifm84c04mVv8XZxWgzH3q54i8fQFkip2qR93zM8YzJXaGNtTJiVRrI"
    "OFzbvV2Tc455w8n3Y4bi3mwsgdvUEn2wWRqa5rft1KdYf1nTXmhUT6RAo6nW/y5N9YU6aBedkG9PLY/d"
    "y2uuln+qKuMtTT7+pC4nSzPx5qu7Lpxt9PUxeUPeBpmdCKmmLY9FEF907m/bimh97MMaTTTebk61gvet"
    "8fAkKbKiAHBXd2rjrOsHm2ndp47M8tGbdQFk2Gyudl2g/9ilRwkYW0steitGMjf2/ivIdOXxMrOPYoSl"
    "nNRdcYGpPSYxlNZZexTX4f2r5BqUoUMfBA93LnSDMQKfKf8x2MQWJCvL+mz+0vvmtaRDfEnaKCdMLLCc"
    "IxPC/GyhHhwXrzM0R4YknOp6/e9Vjk0D55I+6c/+q68Xf2mrw0JdCo9f1tY3KgWNo/89ZS5MY0+tp40g"
    "xyuNO34NLoDtLHB+kqPSQSuqm4EAyYEwsWYTnI5aO0XynLNSyE4B5YNEijz7e/Z+Oz4ybBjW/jyumbhE"
    "YZRgA+CNremsYPTbH/vSjOL4OL98lRf7/tP/Hz767//rH7l7B//LQj5bEGUB48NXD6CjtaN1gAgwHfqs"
    "EH6FTBgsup9myPeK3w/0mE1KWhOs/rZPhVeisD8QhC8zXlGxtyfekLWFnujfeUCA4m2vZpGqv/urQzj3"
    "8TdMUYbv2a/z0q5M16sGoJFVVkf3SiEbmAo0jyhIZOjrBGZOPc9BEmc0iDlf4xwmnW9pmIx2BSMTqyMu"
    "031r/VY09DjzkNlR6dJUWv/Gmzixnc/O8EMcweGxqNSG9rgKoej3C79XI8rWOwDgJ0fLqkqjy9fTBvJT"
    "FcuS4zmhAYRtn7ps5JzgeXQIBGK+nvQi3DDLexVjWuRri+CBAiyNBCKR9v1n/p5opGl+mRmO9bg0ULPu"
    "Rr+2FbKFcoHfJ2c+SO0SaVO4PEgq2ecMaI2BvsFofuy3hWdf4hD8dbAIqpIwFdYElBm3WhUWn2rHGugs"
    "LF/o0x+Mf1aUfR7stelr+tsK0pIrD312/sMnVU9z9OcTqH4zu/4ufdxRT2p1p52XjXDYZ5K9NGcnx1M3"
    "QTSQY+6V4LHe9m8d5+00juiYzB4g6+OW5xp9bjmbFQUlkFWlKT8B0RoXydUSjWnM53NQGFZbT+agDLv5"
    "XMXukkzcKDbjFhSAx22FxhZkMLklCk6I3xJQub0nzxrvly5GTZou5fpRK3R6tUEXsJC2/JchaZRuulrW"
    "LyKAIn3SkeoO0D3vTcDvpzck03fKQk7JYm1bF7bwjYlM31mR31sMwg555idzbhiuRE4pvuG67tYHFSgk"
    "CXqWZtMJFb9J3KbXUpaa1o58qAKKcvJ8TIs164dZU7sPDqiTCoQnzcY1ztCh0BN5pz46EOwX5z+NKnV5"
    "6L9CAy/ueIIKvazxB3uGRLjVTjHMPc+eGY1Y++259kt/OCortqYarAQ2QnmRZ0Wvh2hXqBrhJHS7dy6y"
    "+oh6+s2MfjCvypQjUAofS5PNJLc6NIPLiktbAIcD57vWE0MV4syY9YUTXpL8DYjQliaEBV++EuSP+dI2"
    "oEsl6CAgG/u78ilXxcNDpngpyG3BTIzCZAakY1YdpQOPp5NfjfVCh7UBexAipt4OYRWzZhHlvfuVGFd1"
    "blFlLpyTyKms6/ANP40uo5ZivmQHcHMFfLYPEoeJbUPm/CG2DNX59UD2bHB5md3f87ilays2A4TwBvxK"
    "pb3uekH3lfijlTVsbownrA9PDQorSukdNkjwASBtB3FNB3iSLichZiH6C6PiPVK8an7YH/pA7WjQoqrG"
    "zJg0jiLAtcsSce+vBu1dngNVndGIEPrS4jS8Sf5zO47L+3vApZ/34KyEcYtI5/Vh/QkkAhxRH00FCl3n"
    "baAlU2J3H/i6NwQDdeWs6ogNEcwctlyYJxCGMmFi0/vVeYMtAa5sy98plV81TGsy+msOtoCr1yhwvT/w"
    "blCZQd2/lKU7Bb6q1T5/fvMAZ2O4/YAVLmdVKA+zcB4CQZQ3CtuW9A0i5JZ8j4vLOuvNtX47ejGBlbB4"
    "hVZRIkAeOYc6tkYOg19uh8rxmaLal4KJlY4YL/PFlfQFkSJAJ6AOcq9Y+favFH/he4J/evQmLOibWlJl"
    "HNX4QkFrDQhzfln/4WFB9spOcwAVFrD3tW8qjHZ2V1cEtT6FBKApJC3uT0dyt7v71MOlRyipx3teG0E2"
    "n9BPd7gORsrIoDy5+tta2QpNF52z+PlZq0+0HyBfZeM64TgJ3fd+8hOdShgXiioBPD+AWYkHQC3Kitff"
    "Ts+AbdeOgKz0JQG+H9MtPX1x5Y6ZjloKNFkIWVizGcjHFOMg+gzZUjlNVIKRqwiSzPlWZfw2l7Utkt+1"
    "U68ool33XiWVgRIJAG6aldg+UZI81GqBxKTj+s2xb8p6JWF7KEDt+nW+7brx1yZJrT58rzyfniLvcZ0l"
    "cj6M5RCd1c/8nntmh45L1RwN/N64VnnHy7Bd2A86735DDIdQB7YUq5ki08TasU1FlvNNtJDpsLpagEIK"
    "lUqiUeI8tWhV5lBMYUqGmdHIyyThrtB6DC8XrWMtZ4fAmOrLg4Ej7qAs5lOFRFxsxJGFo6hnH2KE1R7K"
    "RlIJT5HGwTYcDEyoux19QQyJMqJEPRSoUp9una6QGFoat0bKolNR6rwp/UzJ32ATyHMahw1/wSH0u6rt"
    "73F7a7TwBN/eKNG3yR3k8VUuJaKAT2GAQCeGa+grNz4vjWQN4EmZQfgMaLvsFpLkG81cC1hDHrHBwrS/"
    "SbZ7fNUC99Yw8+cYGa3pFgSO4576BAYFRBXenB063vP2+v2XkC7zClUlUMIwipED5ucWwsqvw77xf/fw"
    "R0W14XuJGR4Gr7+IuPeQHW0sfkYbtHOT1Uc8o3Jfar2qMJYW7W46fbDFnJmyzDjlrupaPebwqsdaozaU"
    "j4+ymgo2/QfDlP/0n/+Rmend99+GKf9lZvrLXQeaI+5jV0pTO7Jdy9/adeq/O16nHfCSOp1wtizCYxbe"
    "NxKLryfC+w/q9v03lnMsRPYKi3MwWr/Lr2aO+fGcIq5nPPuHbAuttdX9HX7CJ8LHFaz2o6wgh6x1dqg1"
    "KwLfn8t8zyniGYe3k88jZwKD1QWgoHFai1LC491IUsuFdvPWOj6kwNF5bNh6TDwHYU9QwCNl2AK1Z+rf"
    "ZirgNC7I2eZtPqSWFN54hy5BC8jOknVus4agE21nftYj5LuEgpOY+1q6AeX63xPzchu6Felp/Q/gLQjX"
    "O7z3pcC9+pvtdpxfsb6BsE/8v9ngNJ9Lf4s9jBDyJZnGIwtemmUoFLYeCLwPArvV0Ld8yLV6zDZfLXdF"
    "R8bmczsUufjS3NT+1KnjxCV2ar3+W72Ho51vmUDmhFYWeLCfGYDB0HjQ3HXDXkhbXID8L4VUJOpfzPu3"
    "d8S0+qdvwxC/hUuh32u9aSly9EUeaU8HWFJ3nh/LQeY1M2z65kHgqYwXNr25w+3Ud1pmZTCt4PfudPGE"
    "pQ3dmAQm5l2hFUMe0gWLr3CLcKWoPzQXmccjKCJf05Fl2ZWeQdMm049O0/3nK9eM8zdrVZToj8ddOTOv"
    "g1hFkY+LiuzaLxVBNvycJXcOtNFh57Bqd7MNVYA9BYC7IRl8LUdP47rq5SbNQ/p6gtoY9cm2v/QgJ9+G"
    "d6Z+1nmZ+i0Ekde8LHeq7ApP/IlUPFEq7Xqj3K9IwrvsoXQBC3JNf+0+J8AnRg3BG4QmmmgCB5CiwNlR"
    "NDCQS7u8idmPOKl2o9B1xQiXKbZ2/bsw4mWRUkKqImJsbiNKWKh9rkZ9U+K+EEPLoCSfAq0wSiLWq6jC"
    "0C6g+vGGXhDYf9kGIaUxGCNc3h+L35jxx1sNECRvs6LwlxDW/du7ShFMJbJbN+NEtLCYE17b0ysIP1s9"
    "nzaCg5d39d39Smb5bR2FOVnpfMQw1Qhqm5EjqlH0PMHHgSkKJ9KbXKdC8Pwn8TdGakiF+QVzXLulh6Zd"
    "dtM0gMkDqjXYa39z4HXnG/1soPiajQXAKME62gwGVAYQALhZJXOaH79QEFFF75M9H3MNOk7gcvljVCjR"
    "zcP3SfY71Rc4VZP5y1PQuMNNcdR9VQrHeaY4pbKL7jy3c866hdpAFzMK+XUEEvcO7Uvg5dA9cQEnB/IY"
    "B3AssJ91xc7aUqMfwjVR3V68dgMWn8KW9dMbM1JfDfaEF+Jb3nfo3rgw85h8W5xdil/RCHl+HWIvzXSW"
    "f6O0La+h7e6OPkx6dThUV11gkKsohCzlhynOXGqelTDJr5FbYyuZeItL2TMQxXaDCDYPyTAO934jgjt9"
    "vIf53iesBcVOtEiAq8Fbx/szE3vy+/3OwQkxeh1XSVMor0F+ze6EzG3on+PNmrkzoml+hgMYkaCi4oxk"
    "T9JYEhmQxmBBzGo2UOjHSQqnpaD97/NSJRwYRWXcSwgsuDkFdX22KttjXUNcKBSH2lc8Nmz/hibiS/2l"
    "Z7Ut0zI0hlbYi7Lv2gmLk+r0+z005NO+BGDgpFgvehyKIx5LslXqgRKUEW01OF4dSKtdSzJL0lOvNWer"
    "97dhmXyneDczLA956febtGWJfNegnRJil+qpj+cm9OvfctlqkT9/T0RgtUGWPEh/Q44tXEQCsVaRHC7u"
    "l99B5TA2CAqaAOZLx1IYWnlOC6sZlAtIlGVFT8G5WUmgirTHiG+tj+sbaaIcVHHyavSJf6kmnuDxgRRA"
    "s9e+l503wnmazHuvYrdtdCV+KX2LGGqzumxxKAsNEydJvcn5D3VkULYTvw/RnUeJfZWag4RWQOAcr/xh"
    "NJBmepyzs36tyA9KLdX0V/venOz1he9LzsWbzM2swvS6vyiojiYOYc2HASI5tCPSrMVihTmWbOv0otsG"
    "0oylJuIQwQ7uEZgZdcDL82FUr+8qZBU8A4vqp8zfQhs4RRw+YlrztC5x6rquwa2oqvorKUtQYquBOPr8"
    "NqpBEIBRuiTVuTPIPV7SGAQt8zHEBT0DqGoHnZ3If8+m/04m83pehRjPW1P9twerleU1WgrgIgBD2HCg"
    "0cp9e9SIipdpSvN0cIBkK7SbYNiDWVQSuUmMT7VZlJ5FzQWSTL4vQxQ8WeuIJExUZ3uO3U/J5LR9xadc"
    "MkeBbLKgQfibW2hDz4Jr3PHPdRXsZUHrXJKSKuZCo5ZFEiWA6VzzgO91T/NvrrjR67/m9rlMDsnwAPzc"
    "Ghy4N0OB+U46ytGeIVGQlub0XPb8xMv4EVOKUOKdwIKEMrJzUnnffPmen9I1PeZvXETAg1Qv1lbdmFEH"
    "RN+0ee5XrZ+xCDwzmOvJiF1AljJei0m+QmRtPreTtL95rGPxuM5BctCTnwyB/GMdtuGQjJ4ccFrhZY4S"
    "+PH+M2hVyO8E+NPwcjR9gDAtowNnWYuGKMTQjCz5UdM6jElHnk8wjdPkadw+IIuk5EbBRp2vFroTLgZR"
    "cShFmQraYTvU9uEYt/Wyr/HjYGSNWsnyt7BoJ2Koc9JhP7+nbFbdPUGKMS7z7ldcNSnQctlFXVtgNJnf"
    "HL4sAUy7ERAQ24FN863PBZt5K/0moLsZECyQQZiyDDQhq0ztanysC+5RWrudZvqrui+dDMX3eYijGM0I"
    "zYmaypVhxaMvDuTgF6q/RO3alknOlx9IsuxqfNbjO1I5o5osSgP38HY4JLAWmqE59efjKPIvm3drgJ88"
    "mfAe+WRmB6UVSaEYaY5GilVmGku/VwtVX7t7KO/cv0Ei+RnPXmAml2b4GjzWLhXh3jG53hhFa85+TFNV"
    "PJVz44U3lt6zwKdZ4oiapkef6HxzDkpXmXFL5E9uW5kSs64sf5m64XJBxjkAM5pUjr7lTkrV0dBKgnMu"
    "T7dPgBqe/JSGqJY98VI10r7EEII7XmqbzdDUDCjJw0DgWorEa3Yh7Azx4E2+INNczdgTI5m1YNDySVeT"
    "BGnLymX6c5nsK1GmQfQbdEJBZjOsZQ6G0A4LwKSGODir5MvQpRIwLe6nlrnXgexiGuKUYyqKZTMO6Rmx"
    "HcN8Pt9HX9Eqh1efFsMl6aZ9dneCLzrtXwYr1qJbA8l7MQnvfeHKcNYrQkCMid/w2Y5M+r5aoBj4Cs/1"
    "h+T40KSlLvGB0pnIaZSq2DpKmlNYp4kSFR0frLx3FcMy8CHei67OeYWgnWzlfNOF5zjk8U0R+ErhlLXP"
    "ddBmKEKV2vDBZl9DDSsIUaTVg+CVDdakozXnvt+XT809joSl8o3VhSNhfzO6mO7x0vzyhmYNkOy63K/L"
    "5+rq2U2O3+IYV9M1y9K5YE3uJblHQGzOzfnvD0f/n3/+r//IbBIF5/91U6CoDK+8ICLJIigiAfUP9sAl"
    "v1OaxFKXsiRdAigKNKepOfAaT4hIoDYfSpZq0rZlRvLaGS7LiUW+b1n8XtvmZ1fhVEcOZlUdcttQhqc1"
    "v0gyj1xzjbqXlXy/XoCePAQ6gqFgfZB4JmlK2pfF3asKffMSapUVSRwV7bkJYFiYofy4EkM7kcjS+8O4"
    "lQdSkW0R67J2gBcETT+xH6aqkRTRDkIl9OgTb2bnx5uUbj90/N7akjKNL4usOjEVUGgl96Q2vRAyJm73"
    "gYfn/D2ocjkQkK4WypXVKoIfPO0Tx3+ylTnlcfgtEeOVL8GQkBGh1PgtimV3rDrFDqvsEHjExxyRuA4v"
    "l1/P7ZessopmvcncRojmKT/PWU+dHZVPUZLR9zDOxCigW4It4iuQk3Vt288Ey+9WpL9H/yz+DvH7FiMa"
    "9bTauCep4WwVvtml33L5JWs1jHusJoTbNktGkVNjz7TV/oiL1O90lEzZCJHS8WR+eMBo+V6TpMMzY9si"
    "tLq20OhmuTl+yZh9hn1D7l7fc1QhrtKnNjY+ElcIvZskLHfgxiUA+5Ia7yMiWqgA39Dr7oIuHSaRRpxF"
    "xGIvV9PaoCTitdGRNycxZGFN+/SCaJMmnrKBLlHvjIupbmKhZGj0BIjFXIEG2euS4qGB7jGoeHP1+pDk"
    "uBgKPxR2HZkg4MiegpUid2ujPfqwM9p4IZWGs3+/X8ogGLc1d+/RRpCFW/tHmKXRkAwypQLBgo82Buhi"
    "L7dFAT7LfjOWMh3kOHIY5sr4rqsPeCAfLx6tGdynTUbLqMg7C1ujMhZlgpe+X/d+IY5NiZ8uiPBEQyar"
    "WAKYU1p2s5dyttrpCrhwJOuRpCvF0QKKv0FhsOD4UZajdQTcjYtvoZDmFvgVA0L436JPh1A3pzlqTWSd"
    "Eb4Ruo617RDj2FQJqaFGW2KgqpdahPaBCwqsuXmrLkAJ7XZbuI9XQ7feB4JMqeVBQCeF4lpC/jJiQXDS"
    "CzfKkg36DpOyg5THwJXqi6dclewCO/2/OTWVM/MpGK3Hg9UxLwV+76Zj5k+wuou464fk5SfFzwVm/7mR"
    "rvyqLJrFYPporrqmaEg2vdEOK1ykcBWmn4VQzzf9JRORBXWL/9ZlczHzNxvgHcC/vfDR1bK2D2Tqntpu"
    "NmkMUbXm3kRwlURsDrpp4A72yutmlavfnmZSyZjifWL438S+41Lf1PvaFw8iZ0DEPu8F+HXfiu+0K1Au"
    "MfBRualF2Ch+H8lw0C7efFKELARTwGH4Ez3xlF4qVCgrQR2fLk9Jr2Ume5GCG/3IAJFxJY46CLdnIZsM"
    "TetB+njDZ37wHzZSipYkUWxgECM3y4s3xsk9zaDAZqJEbTnpqSJq90cd38InUxqovDGNIvX95xfcmNZ6"
    "TmjlfHaydRHb3JjhJFunOI8qo9m7ktAvdL3Gp9kk2CIZUtEu7TFCa7aj2XKAv8apqOFwAh3hI/7HoX1d"
    "G/MdWMMl2KpsQHUpvTRnQndnhmFn8rYgBVUWrsHejYpxEH5/G2Nwzrdk19Ltl6uLHOtZQavbu84pliEx"
    "LGkmSMwrPHJJvxXi/r6GIXmG/FKdHfiW07jswMQ0JdN7i696bCxDLH9Q7poV1e5dB41w5XHS1oAZ1oHP"
    "vV8o8MbSFJhASD1pMA2WIvPQ4jzIvSEidR8zrzlkXEfkTg87hlW7KYqDu3JHj+//bm4WPnf+JtepAoTV"
    "Drqvf3oduqxbx0q9+UoGAPxxIaJAwzeESEA5N+ZMoAd3B1bPnCDARVfZIijIOWVkSibV2/GD2Eg33H2y"
    "NjzPXqHkI9Lg9d9i5yHnbVj0PLRtEhrmhgLD2FgBW7mpLmsKKGoNC3NBa8jH9OqVi0PVpPDfz8TyOLfq"
    "N7AEXB7F6WmWffE5ZvFt/cdpaIgTRlX/KUPyQw7N/zKP+n3li/MF141X8GmmHyQ8mnmVYcxPjvzhFOez"
    "flFuTUtx06kLS8Loe5kShP+yh8EwYfsZG4dw+TnR1cbAgG8i8ZuoUUMJfM8i2yI3A7f+sS8a0E4Y2D4N"
    "KbPDXPXwlf7Gr3vZ1xiyNmKGGDro5XBAyI+bH9vD9Spywd0VTQ4QxtJ4rPKGgevFQeVdg8NDNY/nY6NJ"
    "BQ+YYs+bMYR9NueO/jkxyy7g0yHqMuLvu59MhUZ8HqfNrRWPuSHZL1bYcfsz215h7tQdSWz3mHG4ty2z"
    "qthlOKCOnl/mIlcPQISEfuhwK7oPoFW31dW7p90X5vKOjKRh3158Xgv6ha1NSrtCwwn032bDQ14jtcUp"
    "CHPydDrGbB1wLTW+zEYc0bbj045yOW0hNc70vPphuywP4Ymi4u1LkD5JtgYL2bNglyPrQCU3yTB3RuQq"
    "8Zr4wm1wMs501TKnYB82zbnceiOqPh5pEaJDuitHDVv3jYmXSBZH7+Mau4jgtVvWr14B7GByWGjEXvST"
    "mLfhesthZY9rRrwB9lyOOtXBmnJI1cJEjsMMeLjOxNUL7yPv0euF0+tzmDH6owcflwc8SnFdchVTNwm/"
    "6OKzkIfOxH5aC5eA4/7FUSgLVv4bs3qSmBwpnGjGQkDfLsTvp0oOO9S6aQ3JmfSXo6uGU9LNp0S4b5KK"
    "jRs28fJI4O/bu+H/5ew8ciRWuvS6IA7o3ZAu6T2ZNDN6712SCxAgQNB6pO7NiQWoWxr0P3mTGhQKmUXG"
    "jfudEzShUfdSxjv3hiEhQvsWl4f5ACemQeAEvTqWiw9Bx5TBl19UQa50v5Wfy1PJIiAmIqSNT6YP5oyp"
    "gXj2NYZNvUvga8hpE/UNncLL1jkHReJ9wWDq9dCOJ9BMUrofXTjmYvF4f723BEoh4STHjALgMbfyoG8z"
    "rKZJR2ntd6b3329oAodHB3SPNJDlTA+uw7oUiqAZ9vCvFB+3ODRcLg98JNmTO/htOBcJa04pN1U5sZBw"
    "Te/vAr+lQI/PZI9/XKoQc4YXj6Z+DfsuW++MRq/Q5wku1cA5tsMWoqGDJ8pP6/4GlXxJUdoveSK3dRaL"
    "yRYLw+/sh3kLezCJ+qH5YglxFnWerhlcmOASkYrUUstjrOPPVnr8fLU9v3hEGad7bmlHd6FTUELJB0Lu"
    "WEOQRcm92c+HjMf9k5s3dI+3PEuzB8cZApTYZWno6O2Cz38cNSSgQcAozJh9EVxdamo3d06VFxA1B9uo"
    "/Ib8dPGNSQN+YN/jZi9xIQXBKNUWJycFOAvhAzVLlvUFOws0P2jX2DcBrxYJ+yeKt81TvjEOkl/uB7xz"
    "fQN3kpr8REwHkpyo8zeActuiKQHv9vfcnoBYRwumBoE+tQd8uS2Q06YQM7UnQLBckGW0mgXPjp0+H+8C"
    "HOZY4HtbBTsBSWgOht8BfnJdcb/uDpxXdMGaiiRE+zmDfMYk0o5mDXTQOp9uyDhu/D3fBYmK5GhdD3Pi"
    "zdiey3chl2TZ54bCLHA+b+UhMm3RTaN3wCVdboKniVyiifZgX08g+oG6z6OPUBDoW9qDSJOkzkmYHpCF"
    "Pdt1us9JBPh/vcHX//zv/8DDVML//2+jd754HIJkAWQFhdM4CHW67XCtUHGKyjKTK5kfzUnmL1rc+LpQ"
    "a6cexxNl6US0DXV8KZuAYFX7erbvdrNG+DOjFByfMF2lMksgCLXAyU5o969J4SdpWmWRUURh4fKrKhe5"
    "IekLthGO08eZgiDCkVUAhBe3p6ELP9RjM5cNTmBHgb2wFkWanVR99M+vKwD/ORY8LqInBuJvz+gMgP4a"
    "hxGF58pYRjkB4e6ME9IPhu0YKvDNMt68WslMXO9Ocj4MuACWCI/4yzi9lQL3NV5+VulYxtuTMO3Mgm/v"
    "8Be/UX4TZoVhG+7Fk3BbwBWxdoEO91UplQNcApuKlT6wLfVM9iQ4yJck3Prwc/OxpUnt69uVc99mFT0D"
    "My1yQ+NXB4PnnA/bLFRRI9jQoIsnj8vKtiznSlW8K0PbZS1JA99MjwBIc6BNFGmhfXav9Dd5fxTQqeRn"
    "3pBfDP2s5MaB1kGTpXbjYQif6ye77H3cQ0W3Bo2xmZ1FA5bhb4CCcTPBRv33BNDf3WhjR0wnSqWCvabF"
    "c4zeBMg/pak+0fn7W34nTFxhAi2FMdeipTh2yZ00NakBcGXUftU+D8svXEYImS03DPA08fEifWUTjOqv"
    "3IYeDfPwm1wAw7KMOa3qK0SApx8Jsw+inR/HIBSMcad9EUzrXZsSYG2BHI2HjWWB8EmdQ94ZlsOOfeIY"
    "LqfEH/YL91MBrUmKt1L1vJC5meHiMTmGzVDaHmgtMgtgEfkDmq3gfSuC+rtjHOPYzwupCOLMIdccI4zD"
    "23Li9hDiIgEWhYF87sXr2oVUmxo15sSfQU+kLJRNUhYxKSS9iwplJFM6NDEe5tagrTJkE7GKHNWJNNVn"
    "av0COFOUCreRp1neNC23KsHWDbq4919c4KVuEai71e9E+RheDH/suuupeQBZZ9/2l8LCpmF70dT3/nxQ"
    "Ft9OHMR8ibGsowfABleTcUHp6tpdac+qH9UXef2jGEjqATwGLIUrxgcJh68B7PRT99RmdOwg4F5bwhFE"
    "1Gx2crrzq3m8FxpGZmB06qg9zkm12lLqhoOAfoZeI+xPReZtFQWO98UI8gwSl/92fXG9A1CkOJElMYmg"
    "C6lvgilPTgtlkhkixJF4PxSXekOm+8H3DCMM8sEXKSjdprcC7eIsRosxfs6XceHUDrGfAvqsTYyDT4Hr"
    "Z7MYs4B/kqFs7WPJ/ol0KlF6sNkncWf2UOHEytgGbbYvccTDu/P3IjjNqu1EbBXD6FXX7+X8WRwQQHI2"
    "/+kvnn3XtuY4z0wQIzwXu8+7y62C+WOOgnVOO1kdFlaWd4M48PndvzBx0j6X5CU/4VRJVkgB15x0h2ma"
    "zkvUp1n/M3+xJIwzZssndc25F8WiPHKRwg+jU1d0yuNBRgA9JjuXyg/J0G6n5uqoudFd5jcVJZmTxrvQ"
    "K8lfuLKuq4yYy8t51ijYaeRzt2Op5jKHvXrJsksYDEYOBa0rszmz93ADHTdiMiA09rE3wCrHz/FY4KKn"
    "O0VPnyiZFvUxEnuAeXTIQeD75DYIEvE5YtV5RFsdjE6xUqcJY2iBriCXRaAJ9WABnAERHxQn4W/nXeS0"
    "bLgCnash3tH+fjCq/NA5VHsWutBdqpHq2Bs+/aPzl63XpRhwMjOkcj2/Q7zlYBVblEpqzRt8njq9H0+G"
    "ml7fvMdzLkE0D9jN9rCWaOPi+4MpjJeR5GukXfrbuMYYXFP/7S97baAJ8uYNlNoKG1oHB6hCHzk1Nc2i"
    "pK0UFGE/NRJ8BbtfFyn3woemUL/COgaItUoNI+LvDX56OP9wH4exYGdXM1CeIfTvSoPTj3OKnXNn4/iq"
    "E8MaPBq4CelH+wbOMg8euQPlt1V+pu732RB+GY+xJRbTHeINRVpe9J0mA43EsfuDriR4RExzfmwTAEYn"
    "8q+lIvziSCJeYu6Iq9G8UYrOJUvQX7zT44UDSeVPw51OnKtCXesSYl4QDLpiKENflI2y1vf11FSyi5bQ"
    "vcKk8rFWuCRt7tIVmAqT6gPyLwFHw1e9mSf15S1uv29rwhyNEOmf7LS6sZK5ta37+zUdF4iBSa6SLG90"
    "xVYYa7W+iKX5EFkALHUDKbZlyoR3vd5VwcLhGxLnhIbAxVf8W2Ul0dSZaxxFnY78Af723jNE34J2U3vb"
    "WxXYTDs2x0Gc6KTfmR/a6jsWLqTvps35rxdysl/KjN2+IObHKSm59uhRak03qAuMGbKJJISDKOlBGgqI"
    "cwyELdDrE7eAwYwqbmdiqFn5fugiOODruK5R8eUIeafrNW/Z8PXmwAeOIpPatIgKatddNVOayO6K4VBl"
    "w+Ee3rL61me9ShKsci63Ziv7y4kAlJTFQS4FY9vjVi6I5CWSCN9wTNqCPiBAnrSKEhOy565wf8Os0VkB"
    "iwqjw9BvPFm4CwoPdZzV9BFdteHCPpm1N/TcV5mRmPXddO3hSoUkcWcF/LjeNtiQRgvSGIq1vH8pIfuL"
    "5m9kDNjvuEr3Pu4zLOmqFlteEZnY1jn6RBV5nkdLrxypGs9f+vG9QfRtIqegiMf1SuG7dock/KkG06Yy"
    "oxeI2bae9EcKZGXEmdbyjd6Zhv7D2T0VdCbxuJ1Ncv74TRWThIYsgMJnIy3cgZZx+GEphT7bOG93fI+x"
    "ZI72dYdvR+DuC7jn+X6DVp6bcg0/RYrmAr4pCTtNs7DIOaazbKEhgq+r5txRQj1gk/21cNDjfMERg4vj"
    "QpokrOY78FdKiZagdfGOObPZPYmJxDt0p9EPU4ZMqPT8eeoIy6iMfbP64sV3oBnEuzuafCweCLPvCVBQ"
    "S08RiTTyMxkjfzNy1euMdBqJU9N3NhP81xPCYGAq5WK9s9FoHP3q3dSqSNeijbYnLfj4TpI0wu/6CAz3"
    "t+e1yGUed3DhdZtygavMr+3WZPsaRUE9ZRpzd5FiRBFje00yXZFUX3lFGMR+Jv57fTi0emVT8x47wht1"
    "tSwoSF7oJArA8wvtrmlgNb/U7zDB5zctJ6CHx/7FRYzpIt9JIQn9LZFkf1XDuuWds1N0vaV+O10NZQpO"
    "2x9eSvW6Qk8zulxEG6xSfXj/pghAKZLjUySgCvTEejvUynnEpGt5MnyPTTKOs1xnsA1RgmAcOgiq9SU4"
    "GAq6uIxOym2fT4opuBG2KIa3EOx/LLaqqlhcqYhYIi61Y2UiD2GrxkiVhW/1OTy8aTq4Vfvb6dxQ3ljO"
    "Sp5nO/NTIu6ylP4elkGYjD1pUF6T5vo+Yx/DdmssYzW/2vEljlXzN7L/1ftbhewab6bqr5m1eaN2Q4pj"
    "1BHblVAb2+Z5Mg/eIh5f4qcuAsigx8C3yK2VSU8fH9Db+cXO90370lHvZ9VoEdQFQjfSYf+4GVlpfyzS"
    "NukbV9Nwyczu4PILNqBhxKpsiwKEgkKY/lC5NAETdVrrNdLQH69k0ICG8rJJYqceXS4KAZcJ/7sfbwgx"
    "P9GpD8hBdBPkonbsfNFwSCENSG7QEUao81KCO6JfIlgmLQKkMjr69Tx8WfViobGlDvCFqY5Ad3xppJ+r"
    "+4OLwfGEvaVVfoFnS0lMCa9LbjIkGm1tYNrBABcMRShuMhXa82iaJlL3c609wDIPd8u3d0+Hh8wJWkGI"
    "q32lsSef0llyLhN0qMWhsY+03hKwD+Ygj9loh+6W5v64yKqSb8ZLz4EmbDgCJdu0GeCB9VTTnmmP1ls+"
    "hxEfG56g+QzQImJyzJfFZvICqFmkzmRnwWwM2ojUXVo3FQtPwLefzB6eXVvYv1yyqRoLAE+acUovGTQK"
    "eoR6UroFWRfWiQf6996U9l9sYv3f/smj4n33/16d8n/fdA08J0TnpIGnOaYpXNfppXotTKVDneYHS/7R"
    "RJM31+93+H6mPIucH5WXYZ7EbYeR+2J45h68ZNJM4jCnUlQmQNdcjVxNAauyJ8/8rap2Et13IUmTJNC9"
    "DZ1T4a4ZIdCynuPJXvUl0WcszZziIOxGjLrVdTV++qqt8rnK6rN1Nxx8A2AQ0iQHEGY2WDERZVkW38DP"
    "wm9ob+31ohsB6+5GXL60yxkrqD3LbaEXmI+AOUIWoD+eLIQJsG3P4BmFQRjHZl9LYjKeIrlDmd5OB11j"
    "EjkKm5+vOgjB9Pe8eG/KabireRxBrtrCzA1eeGcL2d6z9sJrSrtN1p6hKYDh3dg4Kt09w6DdPmcwBA9c"
    "EPO7xYlpoYjYF1Apy2kuktm6aQd0ARUgTKk9fzTA8XOCkyU5lQ2DdN1XH25N/Ea2GHj2S59i7HZT/9hr"
    "FUyBPTC3gOuO9iWQ47RKSRfAwv+4BFWx86MW/jsi4MrqTFYv3NyDGR2QxDL3KQUduS1fru0mq/M1fsAc"
    "N7uE3tCD6XkuevO1BeKJYuxP59Ja+RyXZLNwxfwi4Zyq2h2jzW5ZzF9UL9pLmjXHzcPwVU7ySK9gWa70"
    "n1yW1uWQ8wxC1JDDRiRi5LpODEZL318WIuCxDUh5+br4BpP9MKpZt7/sp85Xp/y0/WI/ms8vacCj35O3"
    "re3NL+JiPs3LjHTW2bLM9D9p3bXBBkX7EBnLZboWpwYofDjVu2UcpRExTlSI0W2rj0unNQEG7c4zg1+g"
    "9/ASyee1vMEXW2fhqzdZX13IlTDyLWDvGUsclmn49yxStchwlSWzT23ayjx7up6rNtrxTPPDEJn8HBRG"
    "QuCkAAbAiMmwQqcbB/h6psLH1bpfDOaKjGrT+zf2xgA1fWzmtpQZ8PzgeRURN/pbfykjghDVjOX0VXOR"
    "TBHUi/lSjkgo4oJc9MlMXMG+GphUFZ7Ctj9TVNjBii+OQvTIxG2JeBkVOE2K2kpnkk6gD/d8+k7k7ptX"
    "vp+zTT3uPfxXi7XhTpu2rgofon/AtXg0jG+Jb0lX5Oo1/mOcH8kcal7ak+9/vuEiDWssu2BMKWTo8zbW"
    "nw7moos+eejH/3wYwJL1gU8ZUBnmaynGBowYaHMK57BNqbQRkAu9V45X82fvxQasGmunvtvPhjoWH7Fh"
    "X9gTRPRoH6qQfmgRarOKthaBAGVuofDsobXKWm+WTbkY0W2zsppK89z0zlhbT2AtiAHF595mF05xpHLy"
    "bkopEII7+MF6Zl2BpORM0Azp585LmKetH66JhXX+EuGtbUZ9D1YZ6Rp5vbz+gCbZZgc6Gvch05YNGkCZ"
    "UgO4WMNEThgqpKIBah4XM9rBiM/ydkr+6pjAE6cPyldi/ypgzEjjMiXlcAbzWar91pSPVivhTLLkc+7G"
    "FUuezUR6ZmZ8pWfZTi+J/QzjjKDttWgE2auY3D8Tgmo3EgZ5NJtQppWO//NiH+UGRncZir1ghImKJI4Y"
    "OcQZVquah1NwhGOImBdeIz3CTw9kKvF3gT/dcF9BVOUDk7v7AV9NL+4RHH1ZWfSMrRphG9bpBD7b/v32"
    "RcqXTWljVvi2OZ0+ErUxs9wpzkCL1EzJTfkTGZnH6DsFxSPTByaDYobK/Z4kXVQEyorg+bXIE4u1xpXe"
    "j7AKsAzWCaNfdBBLqNc7ZnvnZGZGZYFOLkSB/XfzPTcptiLpmmVdUx6+IcN92ytVHZd2fW0e8DtutRjW"
    "q1zo82KWRFcnVkbRwdXrZby0jt0LsJA6uRMOkJeOE78hAZnOrT/0aHmy3Ox71Zh705SBhVFpTXpzbGUF"
    "tnpRKmwlsH1Ra5F643WHkFn8p7Jqp2Lva4zCS8V+kBhfwCt3j7zSjK7m7V2KCGYGLfxGZqqAC3KDfubk"
    "UYK19ec+j9xBEq5MhBi0WGSZXDksixUMZW/zjS/25lLLkpMh6zMW6YOD3n5pNkz90Qgjr9TjM7c1CkRg"
    "jx4ONHxnMt56yow+ZqHMgFbPClHA4S086zWDqXP/1MtYj+Ejan8Xt5OyyvyViWPh7Yd3BFRBbk3YbAqg"
    "OF7wZq7YlmMxEngpZODNt5a0mJ9M47QhyRWDrQjuKtxLQG+7ABp/l1QRpmUkmAKg+qe9i2+L4XE/VCob"
    "NVudpj8i51v6lhWyJfEPaz3TgIbH6LylhiHmneDnGlG9twfF+aiMRw79qX4qRqpRm2g1vXQymJRtDzTb"
    "5kelp2SoNWjFHbBugmFShaY8g91Wex+1FpsjaBw8ZBav34VF1MQghjCJggs+KhRZ3jRmzcPvT5Cr8dYx"
    "5plsRrH2vr+93Kd4YM08/Lskr/+GYh64b9AlkOeZZeH5bKt9R4PGw/jg9YlZNH734i5q6pgCP2YvUDec"
    "zLsi/6CBYI+C49c4WBu/PkvCY5MA3o2SA7kR817kBQZH3/Z7LMoUHXAkmsqVFqnn6Bnwqu8VV7V5Pe7b"
    "dBqDwI7hC3cpXd2ZOkwFHcJGBqk57bbZJ6+asrFlKfBWIThDNCA7g1YCSoZ2yEqlvVcf3RPKDwjbBlNf"
    "PGPtO+q5dbQdOLNjh8LjdXy6RvWpuEYwmG5SBq0BPXcoQhPapQ4QMMZD8PSAY30vx5EV+eLUF2pm6pYI"
    "fkHS1DTh+yOZpaL4sQ+PkK9PhOm9oZIssVA5h2t2z/iMVppjuZWzV+2MBWbbBmQBLNUQvtIOzz5jM4Df"
    "upQKJwd41d1K7vMyd+kjGgIGE1upKsR/b3hbPi1IbefvFASS/QWvIAkso8ycF2xnCCr1pYkvv/t0Eneq"
    "VaKfbbQsTxtBMOYzEMbl/CBiOd2Je7Hr67VkmmkgUtHEucOej9qkw3FkIs9mhxh8qm//dghVfC6JYIek"
    "BqA278WPpMuO6Pr8yKey3e/AD/Wd5Wrh8eP/EEqH32yavmqzgB7EMU0wuvQ1TqrrLIncUuNtN0rN3u6p"
    "/bqitfYDx2iwCZdCAj8nJbLH1nDRyFDjv3zt0//6Jyyf/AfLry/LR7cf/0bw7bovSqPbU/3IzEV6Nlu4"
    "BlXhiPvZKuUHkx2RVnK5QqfuIM0GfFC77G/hEsFdDGN2K/jDzfw+m46s9zDU7KsDTbnKSfp+a/r21u/v"
    "lac+JwG91DF9e0+wTsS7Tm0IRT2oRIIjPZ45XpX0T/eMX0ToAsPJnE6bDJjFohidH1Yj5Dza6xgU66Qw"
    "kTt7+/BQulg/aKiXcU0qYfb8gEk53tRE7hIBmxLym930ecB92i149zoaJv2+By3KjK0YyD3gIvZVmncP"
    "sB6m/AF+a4eZUESQuLoOTJdFTr/9P9upvz3I5GKuuhVOcpQO03NJsOKsWaI9Pm9vvQBCQ0OToguzNcHy"
    "6DzvtbVGqIy4P4s6BDn15NcmrsHURK8xxe2Y/xHHa/Wz47nfLwTnnARJvO508ceDJDNQ4TrIfbBvVHQN"
    "0XW+L/bmWYYN9QUD+IczUjRW5EE+H3QlKBBbsPQ7JaDEKoKnMG4lqslsCw6uCi/2y6+Hblu5OC25JqBe"
    "YK4sMpBRgdN8ZIKxskGFAR04iNGbgYMwqkPEUWPGyLmKICxjjjVEpwyRDre/KO2A6bF4R4hB9em35y7W"
    "yTqxkpMQHg8ud3TKMRzaKHF2+7EfxQQ4s3M6ZEjOkT8lZuDz0whtSGU/EyyRRi0HG0lcdMZ6U8j39ANz"
    "A1Rzh/XN1nZIb5hQajnbhIHntO/gv5jiz6eIU0Be0IzPpUvpK83QlN2YdDZlkTQFlzRsvWndzcpez3cb"
    "S+WHJ4hXWUDqzlno4iMmzviJnQP2VSfvKiC2UAgOU1he5zmVg2PYpbRDkD4yq36CSnbNlNROFwrjGUhh"
    "DV/Rd6RiCMLOBHZRElXxKvmYU3G2nmslsSypzOCztsxp5iAosJKIBseYCcNuiMsdkc/8LZxcbj5slsuy"
    "QuxwVx9+vVzmQ/WC+Z2gkVDpQ4CGcJa0GwSwHNMILUnyJ0EdsjZ03Eqv2Epghb8t7B0BU7Ju7jTwy1BP"
    "V8n929MpUbUjgVK3sZVCnpBU7uJv7m0LMmo1zlsfcRC4puP56MwfzJ5FBkolNX0eKCd2loU3TF+VHYKm"
    "Sl8R0zse+Kxc2PmCuoIW5d1ZW+5KRHAp0pgTLAxAgww5IrN83M/n8zuGAD/BkhcIR9cMBE1ifWrE74JI"
    "Vp3IH+1XK7iqzChLjaqf1D+hEsW361/wOkU9qbM9KJ25GNiE9vH0fGNgfyvs5QsQU2a7LPcZnLw4cxRP"
    "dHAtWAjf0QP5mkzFvvqWrVu2OhOdVmeqFaXs+O4IbuzokpD2nSDDATOZvrUXwc5YFaGUxiUxIjPTTkqZ"
    "nZtl/3JyA1Ge7AdmKH85RJPCGWUy9/18RueQVSDR/POKEQf6Z+czgLafdhbEvI5wpUP7bQ8z+A1pdwXm"
    "F1b7VlLnukMPeufziWpAZyOzOjKpN1aWBMqoCssYjDmftKgNOiuIpI3qosSuxEDvjv5QeohAKSnf3BgG"
    "TEZA00KaDllMbzyd9o975xPKAZw6wrSVF0LtGuqQDOjr5xhh+CVAzYV0cc2CuECFk1AphQLOwK7/ZFZl"
    "mhkDR2LEqzaTan5a7tHXkay0xX61aKP454TWPOj6nu2uJ50OHELhLWHUO9GFT7pJar+H3tH9cn7Kuaf7"
    "aMw2XDZnVxxy/W4X/p2pLr1EdbKqy6OJQ5trMfAqoPBIbKu79uKaOUUTUNLa6lKlo7nR7FiiTZpBwxq4"
    "dAjRFL/p6WmOqu3YOjnP81Dsjrr1Hn608CgX4j7ANJRIgubU6gUkXZoloV5uLjIQPuYTVsXX1kn2Hyzh"
    "rHAmI+3UhOWBlTRJ0+9v6flwK0pgRNDmvGizxakaceMz2BQelyVMN3Fj+BRA8+cwPGv9+CJFEUaER57C"
    "31BCRvsGCT/EnngZu5gPKgfBUnEoy+XGrsGkKEUVl5LL9aBafHxrA7Qelsh0my9q77MpPbx1be6CfP3Q"
    "OGJq8Epmfmn3KSwqWK2PI+/8sDVAUruggyEU1FCOWZ/hGaqJVZaU1eHL1Bp81cR+0UZg6eGpRRvrFkmW"
    "VHZV1VeEGUHDMIr04vX3dVrHGqjJAPlSwMis/MF3lNB4fniCq9onHX6q4PrGUAW1EAplteGy7bTeADeY"
    "xVClKMRxVXBzkqi26VQr0RYy5CiIJw1/E1t7C0TsJL62fsfbaYDzlLyxJG9Ms7NrFqKdnaE+vtjPjdHA"
    "SIByj+J3YHuZtWcTBG7jSOqc0rRbKNim/v3YNjNhkSVdy+he4ieK1fiI3anJuKCaQ58kHJz5cOqkOPt2"
    "MzVDrfvzFnzSMBzlK5655wRla9DIcGz/kfW3ObsxS7r+2yL9moEQkVHMD8wd0utfjKfs+tPVoRM6lARe"
    "+s4b7AIP8YiU6wuOoVM+94gx83wdWQfxhuVndz9lA/faNGvYcqqyMusaX/Y60uEtx5kkcuKw8SFD53Ei"
    "ULLfirAkbtoMyfJrvLLbAH5qAFP+TtuAOPouaPMbhghk7PdGpX1e9YUP1dQBz72/gGsrVsmzprPxEi/D"
    "0t+ccQN8ZAirBMkOScFks1agy958T5HpEIRTqXyY0vASHAQ9Jmurr3KOh0CAGIaoXpCIggVtcj+Z/UXH"
    "B8SR37SO3/p5VY+JRH6+2XEhROYmb1b6uFVjfR8XHRWIyk8BtYae2KjuR5fDjNeoRDWvQhB/97+PDuwB"
    "FNudllLuZFALeuIqkVILW3+lrKtc4JngDRTp4N8e7saYHubjngsB9xv06WSH8ylr65dh7kpyBnN0Jwn4"
    "6je8iIck2gZEy+nc3z7ToXy/1Sfo4IWg1rL+EdnXKo1K32jnbwkxFHcwRRUNvce/LF7l5mUezgRRSTo+"
    "zGV9jBZWKruJCBPuoSccb4T6OzWWUs3BXK1xJeiwVQMID6rkCDBInfEorJxtq/7Xa+v/49/+yXM81H/w"
    "+PQNy+j3t7YOjuF5FghYDPiQjzncn3TdBz4T5p3gc586P7rqExGw4f9gXdHjKf0uqbrEc7IG+0U6k4ig"
    "HrLEhvcx+ZASDjmAEv/6NXEeREnn8J0qaCQna3/PbSAFiJcmWEAPIIZhFP49rYwH/k3Tz3MARYECQMag"
    "D3tRQ4fJRId17hjL/BC0ZmjZHzk6SJAqgeyhCcP8ma6AI66JqyoTTwJdenATjpJxwg1F4jCCR+wmFXuR"
    "1r8SfKsVP5PkIq/u5s6cwQbmFEDkR89pKYTrbylFFo3yw53XBrfLMyHaJ6KOVIoXdNqjtoMvKthUpwUz"
    "+JiSvky6788GeS6X0t8J3ahFHz8zJYT9QMsVSUkf9nFT9VQpPdF5r2IH/D4fZKN21HC114EK5IHt0+rj"
    "vGwRw9fu6EMfgFX6TmSWJgVSUyYrMHxtntWY308S4y55ezZfirxVNgSoZSCzzEGVV1j/914/S4w+nd70"
    "7hI7+ASitZOc6gDRGBuXWwpQFsrA4iTR/mUF1QhTbBHIsHdoWIDQufnS6uh9Na9fupQ3cQ0zWI+xOYZe"
    "vP6cz/Js/h5heuE/MzGZETnDYB+tHffRTRiOF8JpG9NsXhOLrsZCe0BfliJbb/d8hGiEw+hdr6JFTb9b"
    "2eRQI4+c3bzWf9oOJ/vW8vZj8VyvMbROaXzis0RkGUmew9UvjGagvx1+fPbSpC8SacgeMTbOxkxrQ5U8"
    "SLf8TspP/KVBX1QJSWGoc9noc9+njK3G7caCbzfU2OSVk54eAKK0YQ7PCnOPQisvl8IspzdL7/hODGyp"
    "n9zD/OrB0cSqTjtumCkktd2mKEoJc9HKevTtg1/pHQU/IsTjETe+rni2/0Y6w5DQTmtfxvXe/s4H3xst"
    "/aCXopZQh6ZoDC1dRepNm0hrAChzRsmrNO3H0C1yTq5yDO0tEFT0mHbN/phf54CPEihupgObaiJq/mAg"
    "DKoliJ2E9SXpKi1qlXCBDiuH0xpLt4Pw1jt3oaq+TGRQ3CB8is8q7mPKhDQhRukhAR8SV0o7kyCNWdqT"
    "PDL/0j8GeycXvHm3LPPSqf5FTj4WBRi2rYwDQDlGxJMAMsNlhOIWL7U8VvlzYLlWqrhKeCZVVd8UmJ8v"
    "hERM01wmffS9Wr2ag8+I5uBNxR8ousyZ5VceE4SO+a10Fwj7UBWWhAE6rw3EmUgHgpNFF/JvdilgZjdc"
    "9vU7TNo0aJeL2kKf/KRJ8mmfLUC1ClqVC+F8IWE3V8AmV2wqOzLNipvsR4Xhm0GeRpjKLOm0vrpIWfl2"
    "bR1Kk+71tRN/CJl7YWIZjXYAXuiUdqEOiImnwtNr3eMOyNkLkWtyDdwM9OECNRaogV0LC+r3HVsWYYvv"
    "j1pOOv/mC2qJK3ryX8WGGWYNFL8NNPTxsmbhOXILoqk16blGbF9worRVX1sX5Bxi2Rv9sYxo8OajIhD+"
    "ORxRPDMg3OBKvnPeA8YeP3kRV/R9S+f8G6bdOs924MvKFsuyVg33r8q0nqW0jqUMxni/aB2mQNpMr4OC"
    "tIdEGQAtByQaFul+LtPotBg66GOymRoYvtJ/Vu4djtI1sLj6Umt0BOxxkCvcj4h9+eGCA2nVBt+wLUbg"
    "qTX7Pg5+3G0g7VV9S2IUyBlnhAhdzuqZe4OHNVfGDr1bRThklBmnjQyaw3VckpOAhXxmSpYPkjijmnTG"
    "Swty3xuuUvLJoPUOQOGJCDuGt7/agV08F2SoyCavHDEyIqhxp0ZVpdliKyaX4lc2RtH5evG8TG/RlS1V"
    "4r/V6P+UxJge3Wc+pqOLBoLwPIR6rM+Rl5e9RNXYR1XopUZWLbiiAe3nbd8fHvRg2jF5uHDKVfrGT8k+"
    "/Iwa3owI+6R+mEho54jUXFMUP5P4t3/Gdwm22S4DyK8CYCDVF4+rSpX8QVl75yqpg6iRmd/ipY66SJua"
    "HtkYsXOyyvx4kt/fEMxEsxo1OqSp/lm50jR9PBwNZW0PoN8mfmQXYqQNvx5PqBORw4enmv0dRt1MwxT9"
    "8TZohhTbOnQKeMdW2Kuw2/x7/lQXyDf5Nvx4zGk+zRTWtiACHWBEgAN95miNPM8iWp+RV2ZMPfHgKGql"
    "3+r2R81mlK86x0TN4+WR6GJimvdVnZHxjIE1LVphU8itny5lXgwypwyKsqx0GBpLKZ3+irKOJTtki27T"
    "N+YrPS64iQpItBkHB51YKR+OnIOMynqv3SBdp7frK35YxNZcoW8ufSKIT+HLjgsLSyfLgW6umy6wE3Ed"
    "tfxdVViEZeb3/fA8d8lsfTGtLLKFCkyRuJPh4aFE2EHX3fvYo+BmQxV+PgPEEdJ+2O2xGhALlj62Jg/y"
    "xTPikRIfRuxl95pDMw5eZF9se/lUEVt/KkMwlirE1uo6TZZNe6xhmnf+HFx7EWI9betC4hhiDb5IYq7l"
    "O7ZnpFvsKOF5wMtUBLuUh0vQfgKFQblOfcMLR2DCqbfM2Sts+2nTYfdAzTI1d/di8xSYOH5qmoluUeR9"
    "w4g4yxZ/GLQ+US6EMEFIPKiAIzKl0Pgbcv+i6KQD0ztXZyz9wItPtAlamD9uAmTLROIc+xXrc+hjMZzT"
    "3YU2JAhzcOOj4T8vGHsTJVtTqiOtQ2fUL11Aj6EUisVH4DMtrlV3+i9/NBjDjZHnKXhy52z0q49rW6dh"
    "Ekcqw8Gi1Dl7UvPfqwjtx9XhhVsEzN4fxwnGwA9ykavktog3s1hUwWPkPBeoZf0KJMG0oPSrXEMNRZL8"
    "iiudtbNuu7qwlaE3E+d8gWawcftzUAxvLL+jIwg5cYqgVS0b0keU9QSRMVRP+srSo1fMD+J1u058Dtaz"
    "p15831x2dCx7rejqLJ0i9yuqyjHRm9zrFVowt+tEWL5gmRV7PAsKwJf95hHW4kn3VoOdr0ykjCaprstE"
    "U4TAXK2YNuMmyvT6raAp7h0ezaiB1UDHKyFsgC6RiILPQU2qsiw39/INdQ2a8PZYTfQIbfTSdyYRcday"
    "v94POMhYfJ3RObFhuSdMeroN6XSmQTwsTOnzlSw6rhmWSwJ/cGHNYaJuIiFeOdqsm0pzE7R2AWQHyNMV"
    "a+zFNJkhcW21sT+IwnRuiMUNiTQAgATjKUup0JyXu5eRv73YM949pwuct6Qiih6B9gERKkJLEFkhTZvS"
    "/ZQ1xk5yXcwoPdOeq/7k2TV1GAHlPmEJFQsp/O5/iWkNrFlGEKuuY6kk+osRBf6N799IK9trZ5nWXEsG"
    "eaeUT/RhoeHyZTHGWncYuAxHTFfPpyOOQTwTh/IytMYXh4HEGzYm0ZrfFft7nxFzfxEGo/Mci2ewGcez"
    "VnsGJT9Dro+BEgR7CwMoVU55guAn8v6c3NH58vu8cc1P5RP84E2n473R1/cmWV9vHu3OJJKoP2r91kYJ"
    "5ocC1+zZzMW4M3TMNWm9LXB9FC7VGz3VjPLqHO6XKm2Xi7ruZ1EM0x8Wstl1bmP/6lrJv/8DN5P+81rJ"
    "HoQF9su/TiiWyFFmFJADeBM/ozfsmwENSoLYJiK30ct5TWfKsVg5EzoHsjHJv8WnPowyK9JEZn4UET+V"
    "wbpX46bPKwYTGy/qwg09N3Vm92E1CX79raioAikH64iAp+1JICvyveeGC/Z+PJzf2UnGMQGepBXsKQql"
    "4LTbP5udjjMpuOMDiox2xcqK+TQwSD5LZjZblDhrnVZkf3GKmeUVog9tYq/P9P3N4ScxyYwRxL/9tzyA"
    "CLYQRTMnZDC7wJ3zb7sxrP4BuNE994+sdEsm+fn9t3GU2gvS0Xcy5p0fAHQb2HSkYY2OCZeOtZW4vzAo"
    "AY/pTg/fGk0c3dBnTzpz+qaTVyJbUhrm8sB+3DrA43mFUYaYWBrAnoRG1NlvScsXjvvDlg8f5GtRTu4Z"
    "5tAOwNHRt8jX7GOzD9YkfKfGMtrJHTg2089eRjhoWG1+Tmroakv412mXWe7uHuJ3UMCOi6B/XcWbCW5A"
    "/m1omc19BrmMd/tEf74uCwJJ9rTxSW/QHPq0GzyiWfBSWVBfMWdupr8xbwEUBqQZdR+m6WQ+NjZBQS19"
    "iQtmJbuzq7W6C+AuMkLNlkS/blN++4246B0BCdL31tgsnElzoW4ML7EywoLJjcg9TdWeFjKR36KQtTLW"
    "017JXC6HqHCIb/T+ICEqkClRNfI7X5i3OvmBrJn6AkIug6QGrHIO8dsYl7CeIsV73GjCyXBUtZUpgr2l"
    "5qCzydRnNPlSjjz4RUV7cMfv92Ldn7/U9ujsTRYsZzlVKedtG+u5Om1lFR/i7t46yDYxXC5/mzZfqlOO"
    "fP5FW8XUad+ce5u/dLmpkM8XqevF282dBq0BfWlQHxK9DBujYvVdHgQx/gL2N0BHV+sKfMAlY0DakIVC"
    "E/RLGZYD7vZ+g4fCvWge7c8jErcSHFlwmPHi5M4ROKuyDV7giMSIBDkq2870Q5+bQo/i/QEtt88B845Y"
    "dIRDedBb77kN4VUfIt8RhM/EJ+a7VhtXBB3/1cj1ET+cVUwyl4zf8CdtsKJXmMjbjpHsE1p107AYonP3"
    "OxFKaBVc0TciNvUjdo1xUnv5y77k26EnvCLD1/GiHyViy6tyMitOmNaKL09GVDI67EAQaSGsiGXRXj/Y"
    "N2LZZDxlJBoxzuXgZM9R8P6inx9RkdVMi7+cIql6ud/o5WRXQOSb6tfdhXBc8Q+6Os1AXx+ei3kjor3w"
    "1oXiKctOGQPipOq6sZXbNStCj3qtEoiPRxJsJ3xlprPWupKXqcu4s/1y0QpqiqvYh33nNlDCmaLXoz+3"
    "Ql4foqPnsK3GsmGL91dXxCXNq9m0f4SwefNUy5WhdLfqHUqS8kFy9T2g1JsVsr6GrPhp4D8kQbt5dJgZ"
    "MBm3iklyQHy/hTtwJ8YPSVJ1T/5tSqbuYJeQdgM/Lnh3WSU73uXrHx0yuCpYTPXSW1X/YKl+pBx3qPOv"
    "JYKzRZUsp4NXVU+TWRB4byzOtQTlcMVEEbpPSUl9UZTXzd74yjcMDvcF9d1equ326ZUnqejHLBwywFSZ"
    "76dUOiVfshYLV4KUH+KbnujDWdQ1/dLTPQwork5COgKSFc4OFuDmna+KSmSQ7ICvHPPsJvKGUzcOK8TZ"
    "JBf51CXJ5Yk/51LVVcE5OWqvipsXHr/oF4OX1Cxj04yjJ+BgqeZ58hBvcydZ051c4AGJyl2w35ycXLWL"
    "TukJu2QlV+EJSVXXlzh7BHXv9bJsghs/G8NvqhJCTETO261UJz1Lz3qbo6zLb58ghbdf9cgXqLanU3qa"
    "FF4R2LOxWDp8gx069F/0Or96phs1L7AuVcgTpAqAlppC/KRSBi7BPtyt2ObFQjS2epGA13Dy1imKLZ6m"
    "aksW9wWVH07Xiho0/twlQovqZuSYCUxB0MNCkXQH08kvsFC9M5fzwTNszZa4QscQYpLKldkTmXiqxVEX"
    "yLIBYeLJuWiuRqbeYttu3ZGm6HJ5sgDdo1XB0lj/kq4FVZbsWhjUwZdzDNFaQkcaaD/kAp/ha3RnJueI"
    "SQDLSTMbBt6X9UUNF0yp/fRxOs3RVIH2Gefj+ZM5BpOe+5mdJ0vR9yl2EShKEYor5SnkBFaeJVCvScf3"
    "dBT2ID6rVrLRibpaef6UX5pVKcDivwUwrh19oKCK7sPDzqwJgx7RrkfSk0GJg77Clx9O61aBQ+pNawVq"
    "MKikQY/1VD1Pj3ujY5F9wzQiOjhu3fqJHlsAYzaynmNwYUvjtmxmVDqGNPCcwaUwUH0gSZdGD/N4CVw4"
    "4N8U/zBNquDrd/c+ywQnH4er1xB2g/1Qyf0Jun6bvgwQUmNKzzUV0g9AMvlAF+BKPEgCjfFFik+Bgg1b"
    "pAihOx38iPzkK43zdujywFU7f8SvZtzhMt0nC38yHpjJNNxRgDasGJV/D3E/R+aq3LJpSQBrzzGn2i8b"
    "MMpdesqYH3NFLb6ihALBU4OuaaB7Q34UETp9wuakRkbAEzrG0dRqHq20yM9NGFrbYDv5+2WlZQODvHau"
    "blPcrzO6K55fQjU2aoCGTpeoLENybc57uECcWnP1ksFyebfApwAMydPKEnTKK43A/dmjaL3x7F+x4//+"
    "J/tFTNB/7vYeBMj9DZxQKpHzJJ9z3HlknKPvLfyaw9y47tVnzg8MnLKSatB/kcFLjsigSvsScZMNkyLC"
    "dJe5EhQVigxO14REbhK8UK6Mzo/jdKfRFWGCHkGpWLfp9t1ybu1EzZx+2TFk1CTigmpt3qq3T4IEQYKk"
    "joylPYEJeblDj/ILDuaP2rBO+OQ84NN7M3g3+LvS8j2i0j9D99qoTSJa8vx6y3abrg6sGYLyD40c5y7S"
    "hUIMRq8QhnuEbW3bfLmX2Zb6B9JY+8wZEB6LQdXURX+QbqD56Nt8QzMrvlnQ4l+4XBDcF+tBbS15oU+Q"
    "R3LQTFliaw1rZgFKMvNHOPctS4p09raa2K6Qmmr1Z8HLnvy9Qh9Oe7O+KBCDxXzCezHEPN3eaSygZ4cO"
    "tst/BTWtXsTMp3y3fkXV0uRHvzmGBc3mo1ObnaYhLJ5vegkP6QBdYumdVZmsCg3xlNbckwQQO/Zuc1OR"
    "Shx83I0/a6InJ0RhGJ5BUm+7n71UG/LJA0YvHJ0pfY+eflI0E/PKS2bxJP50xGq3U1p562zZuO4ttivH"
    "fCBzTD1NS21RmqbqlfQOTsL+LtSRoRWE483YK2tAABGyBAbVVcIT9B342+CVj7/WxXx9Tv86csJH9YFN"
    "f+udZ7f00jcUpqpn7LcQaeu3ngi3siNMr+EZw4sNlTCVvm6IMcUmyIABIGlPpnL2eZ60oyawlx86G+cY"
    "G3bGxn9sQ73/+u05Hm+p3fSJM1tm63k1KtKZVflKqm0J0sOnvj0BpY5N8b/gndjFpU0MAPFF8n84O28k"
    "h6EtsS4IATxAhPDee2QA4b0HiEihSiWVUmknyrQXbUBbEHqmakbB/OSHXWiymw/XnEM+vtt9ygwNxxX4"
    "CvAYwZnszzBZtER58ZHtv9GhX+HYzj8jubVG+zk7h9W/wGCTW/S6dtWrIBeDuKu8z6xNLU3rWhKLNLcz"
    "LdcK4Zn2ygqFumrN/tfryOHZlTM0MaPz4cbjG5aTtbvVIR9JP9ES5SKDn9op8N/7yOOcHHnpNJQMtnoC"
    "KMwqQy7zOYXPxc7fr0oDOIRgeYE676JFgarj3ygl8u9j9VOziJg9VPsY+000R6sfR6asg8NcKyFjlHY1"
    "UMwju0SJEh99dTIREAJ88JhTCqv2EoLOKMYbx8pX1WB6e90nHBV8r71IF4G9DaHBebg9HA7nDtLs24R4"
    "rb4ANjsCrQO8Kg4SE1W3eO9hYNdElZ+29YYYXy4r4Ke5untKIFgFzL0ACJWYPoSJ1/gj8zeQAj4hYq5k"
    "OBx+Oe7E5mXi18ZOhsATckY3r0aRuokGS1oEHJwN+zprCzxY8pY0jcF22fE56IAt88+Rk7Kzg0zRByp9"
    "bFTMZ9m15fJSH3L6isy1/Wgepl/fAsWa1h/26V1YO3XgpUo4RsOjLkPBqLJWPVOTe07fqi6aimEqg4Ij"
    "5L1x1wjSZr1i+42le9iUTpG5P+/YJHo6zOv3V1YO+uFayqUY+9YJFB6kV8q5oYNpOPVj3kZosYw8IREf"
    "moPR3VQEmmtnJmvimS+lUojnWL4lyz54Gfm+vmZOK1uL8XmVZ5/ieW8xv8oY6BKtystChqKhFkJPLfwT"
    "6Sl/33XvkzcruIOB06F1O55U99bXMzCPK4Y9LZJqM2nGvCIcesVhxSlrOqJf5xPQMw2i2sMbN0JqzAYz"
    "mnKo93cyXG/NT4WPJClLP7gs4qyALHPWjPV7NNVUNSiK19hrqeBv3pCRK1x+D3g6bwTjw/eoep/7nvoZ"
    "8KgSEBCKzp13BZQjjWK55M30h+ppBaIQXtgaEFnPU0VoggSSMouvtTV3HZHB7hMvlq6zMjMH/pLmjTsE"
    "sZfM+TPCPLYV1IN+17l7bki2tXgnPhlt7LXRpjP0VSFuwq37b5CVPSVhgcKeYBQPkhmR8pGn8dmyQBeM"
    "TDoHGUSYK6Yh49Bs1472qr7RDHI5oM8YJ+ASzt3DeTFwSia3FtiBp2S7WrTgnSNrtHZoA8tDgqTAqA5Q"
    "pw9GxT3hHnCM3oKHSH8Wx48YU2tI8ydEOEr5aPczHceYIxFItW9FWNqugAFI75xX3RCmmxwCIpzRf8wP"
    "4ulAKIFI+wB4OY4Ku+95SqNbwsK6wjA2WmXYixFyn3YrlZbBB5CoMzxKsW1oAkBy9ENRtH3phinHtZn5"
    "hPRiNPwBLcv+NV1VHZ/4UB4gVY1tfXvmYgTj86Z8jqALikdk9LLKcBucjm6/ROwYUPos7TbjLaKNMwJG"
    "+dptJIAW+N+Wipb5gLsJCZUBgciN/n488qK37FY6fjTtAeyIAZHYB5w66jMjR0VnnITW2T7dWr3qm1gb"
    "J8e1CtItq0WZcGe2Y5seo/YwPQ6A5/1jzQ48qR68whbiRYF8Wjqr/tGZpv/tn5n1IE//tjcZjtJ/fb8N"
    "gHeStEz8If/OcUJhVgyXlREhue5yTQWmEqSF2+3sVU1U15b72OfNRmIx/ra/jZ4ktN0p88zNHn+8Ou+u"
    "e6ozIh3qMv2D/HkzIHNGEhP7kBT1/o22J0kgtNLvdpVxxUQlaFrjeVJheGYovGoFw4UMQ2vCsxJx+AU/"
    "kE7P6KArFEKlnlOCNpA/QvntDC8BvumLJvjl7+pKHVRpf0zvinXf9WIe3WjMOqjlwcvF/0bt7LG/uI/S"
    "DgSLPN/SkgTrNDPx9XgdWbViLqMOK1LtqXyZOtQ2CMV32cAUh0qAefQ9PyAIsK9IdIY5MFqz5wd9TxEf"
    "UbZ8GK/DQ5R1oiSVEz/IYTIay/Hb3VXOVuobmAIy2RSuHOVKE40GT2yoweDwGzLyuKMR19ZfW3/HLfRP"
    "xT7m3mp/CpX34xvo4F7cm81jPQJPZZbOPxLZzNfDofDKu2mEM/6IBzl7mN9pBZ5xHeRHlY6WxPhDfoOR"
    "qMBFg3TfgFg/K9e57qLjzT7fzQLk9XEbdtOEOWJ4B1dYqFaEmNG9tbH9IYpfB3eqHU+Ja7eNWzuhqh1g"
    "xmjGwxIq4Hm0BqSO6TxVg4g7gFhp/7AqAQ91wV6x1yVNy+i6G6ihu1na/FsOJF/sPICvTdLYWZxomZPl"
    "0WUr2bY0dwXgCfmEIfeL7xPmvtZJNiVPyrUnlZuNIkiVp/sYHpSUwm/VPVP2xp6E8HHpUEWZPiXRDVx4"
    "rL8eOR6KkJVvOyOFO/2p/pHWOU5cUw/tCgN/nauPvdU1Rp/o0QoHbJHIZQMttgdfIys4MZdhOAoMaXgE"
    "YOp9vUhKpvj2DckMFZ628TXP9pRK5DRd/N0wC1SYaldN+Pt6m/eirvMzeY755BLDuM7ma18xcWBGlY/Q"
    "fpsKIWuSxfdwnzsrBWOeYUKz0O1/ox/5X1Tx+QfoE76IdkJ9rMT8O4kkzlenjl2Y26DwGSChKEL6shf9"
    "niCLN6K6s1NB8Q0ZhlWEkS83BCq/gzclrvd003Rj/p3HsHpwr+OoOUP49WFs12hzcrow5Yllg05SU8X8"
    "yl6OrHYZVk3xeuJUdQL5TVL9xk2Vwqh5UV0MzPg9TCgf23eXtkRnKp6W9Fg8EhZ5m4G+YUxFc+mHHmnH"
    "1TZa4CyJ1H7SfidSOQrP4DK0Tb/XB81BPJ/AHJnTwwB6jJQ3w5CfiOfjIqMLVbIJ+/y+qE2IcJ8O8QZK"
    "FRGbveyJ+Xkx5nn7/tosloLBZtuWs1eLKCzb922PoPMKUIFY9aU2Bnlq3mXHjMRvp9sGdPcJMKh15oaQ"
    "Kwf2L7bq36Kr4pKupE6O3p3k5N48pYRe0C/Q6qQIZ8bYWSCrledplpdh3l9lvoNmLb8wRbrfgDhSYJ6g"
    "YdHz+KqCiv4yANFwI5WozQEQYdmzy8EomvhgmHH7SnfHKGMgS7r/EiWroBhHiHpwF+v+yPheYeXY2zQw"
    "3fZTYS1Nfs/HK4btYD1v/RKavRtXRJuVzf9oRRZ9I2RW0VZkrZj9CAG3gP0piyFYnn8HE2bUq1VYZ31S"
    "H0rabahQKu08gIV+zUplMZG0zxGyRbIoQdDQJ9R4lKZULlVh5pyrcY/NHabRkou3p2VhdPtexUC2T8Xl"
    "Y3trrlc7hZ/cmQKdO2ggKqCfkjeWrAaJfFiY8z8FOrIzf0Yl+hOhjDlu2IJhHMS14xFReDnSLuugWJyP"
    "W1rzXzsiO2DWWx/mSx4lciOPiqr84iZ5xFP+XFAfJz8Xan6/sdX1oHOQeIUnJfhiOSrH/KEN32Gsb5zJ"
    "n/K83+YHztOlkuko7unups8PNf+Oq/d4vxNZP5e7IDw22nG+0l3/4nmRhEKsieV0SAnZCIxEM3/qAerH"
    "Du0b2jJrKLjv5OPruWYr1Uv+S/fHvBZcAAgqL9Z87Em5ynA8jWq2YRJ06X64uBRvlnRzQ/OT3F2D4fzm"
    "HuC1OnOuwh8O2k9ahF7W9itk9OktZtmLuOKsYnwn0fdLYo63odLmVSnz1Y+fhr85cAw+VaZ0KkzH9TLN"
    "Pd+UwSX5iJ1Iv7DZsuXJZxswT11SEyqnTdRvGFpqCR/Zxgy3nVlDuEKDqRayZ8CDm+O/j8/bFb+VLxv1"
    "mzzbEtdhOT2xzKd8yywtMfCSvQouodcODF+UR5WPoyGr1pm1DHcAY2eO5nlbJdZTWO14IKn4gCdcVFj9"
    "r8TG1Yj3jO9421YE1uK+6ZA29ycYDI5Ki7IYx2Z2WVoVCdaMQx4s4ed3juIx0g0XUuMyIQu0lWKkz30A"
    "dSzND3wz9Ylaa0F34sntOiUvy6YhrUDU5FpIzM5VYcrl0rK8kCGP3Va9RooMrgOaffPjNs8K3NBRhWq5"
    "5EIHYD8Uf8/G8vaMtw7K61PeHscBM87v4aM6MLGCCS9zwwZ5FgB/znLZVRIfG2cNY4uxN2Xa92Qaz8cg"
    "v9+CRlhLeYhydw0iZ3eI5zn60zP+7pliyMh1nNGinuaPv2cqvkhSs5me2WmJeODAR5fqr5Z052J8+REP"
    "1cN3+/C42XZwjE3waN/cOIIbzId6PLji172SkFU8/BYFm92Vg/IRItlqZ8o0Y571nUMeqfNZLq2UGIQ+"
    "T3YhvXVs9BnWLNIb14WPAvjnS9XlocGQskMwm80S3LgmRRSMktpOWR6TGfOTirkppd8ORRUezD/hQpp+"
    "7jndqc19VI5aa/5AlOI1JItVnBzKfYAPEnVzEcVqMt8/N7DbSh0cpGCjJmwqr5BTVyNTzXzvKj3FMl1V"
    "9teMwnuKsxxNTPSsMRjf6MBgSWQIAPDz3HQcA/r0YjC9ImtfMktStuoFQOjokRKe3XhPIWAl08W41e2n"
    "JKdnBHg+Hm3xBg7RiiS5RQAgxsH5ww3qUXGaQBj5s0rAOAFU9rf7Wotfh3lre/mtuofVpVkH4Bf9hcf+"
    "1TkItZJOgdmJqWdJei3g6B68D+YyfUbeZAwroenHqmz0hcbuZ8/Y9aW/dFABoARu4IfAz484yHPoGaOY"
    "4tU/ej/0f/8z+5xr/9+/d1iGvwD/2+dc5Dh6nnm/ptBuhkiSvw9s9Ylbcx1+cSRnNqWqS7EfkeTRA92R"
    "c7Pa1j2ITYxwKuLx7WeCNgSuN4lelCcYUKRKJihpFEF0QFej5vfmwCf5shIJHsCDWsiNIDW/s0byt1Cg"
    "NpTWY5L485gfRjj7SuerhxgNYDJfQhtBvowSB2Umie6Q5wJsRVcWfjwXgNrQeXCD4KqciE087qtKvyY9"
    "XehDqERo5iWI9lAXfkmFwj/xyFWjTNspFujrpB5R3No98nLdhfBEtKuQq5S+tQjyytQuH8kt0IbgD6FN"
    "2uZK00qHZf05Zzjkh8cUHr+1a0S72K/VTenzYvx7FZipAVjXlT9Ux47jpzMM5APRUDz5EsE7pMEdXnYT"
    "0QQvQIwF3GV+c4J4rq9TuboBjk3lyBnXh6uDslsGN76ra0L4o8fRfXIBhp63GXMwU1pc/zgh0D6WMU+G"
    "SDtvz+Y+dj3v6Ng/KbGiVf2T9ctJK95mmYprvnHN00eaUl5oGJ7O1YQjlLXCk3OVmFZ2PsqDjl1jVBsX"
    "of2OFpGDYAZ0GpPvp08qWduonSJUKTGf0LxF2p06FPgTHAC5Zr3vKcL8CdGRgvVMNpdxmnDRq7OY55xf"
    "ybEdTX9ZXoWD7Tlue1OBExPD31Cp/bakx3zYhG+uFs07+J7PiBtYcjVk50UYeBDRRs/9rXQg44ZWYOXX"
    "aihUlxnREp6Twcli+2p9GsFZW5DpokZehUAfZN+xeCU/v8OeCGkqp1EAtq9rN+sPO333N4laY8fsyUeX"
    "SStl6ZdjkK4RdbuKjEO9Yb/pWuGsg7B184Y0Dec4hWGxS6lVVysNcwBgVOlfsOa2Mhyqpo6VQQ3ydAbd"
    "A4ENIHJ1Tl+QaXgziXccW4eqmK+Umsk42nvTsP9MWRrWlCvjuNKiywVL7UDr3MbwS2dE69vxsh4gT9Rj"
    "6VU5Jo0Wlszjmk2hmfzHTEbVNCf1AB9sl4jolx5p+aUBo+35li2N4N4826exuPlGvyqm6IvgafuqPpJN"
    "aze9lKrBrctZgk7xK9D2qVCRuBZIMCHMOL4pgV4TC22/WO/SRCzgEF7bAz0FmTIiemTiTi/HwSZ1mRd8"
    "qEUrgpMykZXkjmYS2RX3SmATOywlCy2+oUEkpOS6+lsMMNenJ05PVDTlpkZoK3n63d+LZh06c1UzKUMR"
    "FmL2YsG5banuzVSd7S62mxqDj199kV3E7XsQW98r92TkP3NAHp6r58PJo/AgqI8JUMkgBOuvDzmMdorX"
    "wC7MpZnWGtkLYwbfYf3N4WiD57W5ytX2u/QAcBR8NjgeSJ2tcnUIEr/RzZoQuzgkCuRRlrTXIIRpaQ5r"
    "eVVEP/M+hRaARUXRZhmQVamGw8iDzTzrVyegor6bsjbfcquDDBQ8xcQuDU/3CidThOPET2UjjwX9UJJa"
    "4/xrqauN7nNg7knVV7MBUjHJ+Mb0XXFrZS5wXKmW9OEnIb3QW0Y68MqWQ4GtdV28CA2tK2oyYPrKIdrw"
    "BPDDpc5sQ6gDthSR9mnBQYXjrI9ytpXDYgJr7WBOFbD4RueJ//RY10XRyCHT7I5lHuJTPo8w3Qz1Ga4Q"
    "UYrodaPF+d3Aoj7XpOegKAq6kmo/RCrYf18G442Ji9pUpnIriC8d93vhzn/fw0xn5PvdDKtIXgP85XEj"
    "XwV5V4TZHrWPtsFbWCZMUDybqVimFeOQrsPlZUcoRazSlzI7fcRiS6e0jMGh3iHKfHLIKjODIXKwRGfv"
    "I4+JfmnMFkqWiV7delGfkTOldrpvYzmM5D7QztCFEm7YlwWs6cffZ0/jcLXi652L9UuhHwzQs7w9XzP2"
    "0q8YY60yMstBywIYLxXLybKH1IgfiIL5owGsjFdqAcRxDsSDzMID/XyauCDbTFh6pwVloUIfJhXNeI1Z"
    "aJU5CMeyLzwY5+ySGQ+AAIH3uyk114+fSByBwD5So8C2hQDPM5EhYZ1zXJyWaVPqTpZm3Cm4purIL11Q"
    "9sw1Xs0IRFfg4epmfewDqwzb1S3Nq2Zp3laxIKTx2BtisDr+JMUBKYX1kq16KOeKjN4znRQGE8LGmavY"
    "0BfEM9d1NbawdHbIgE1WayZ+le5zrMW5Y+REwAqQIdIGHT+F/EmjJ1LcjgRj2evkGj3jVCaCVZBQSZxe"
    "cIIAiQmvilDmT75/Ej2JtjtsWCBe713/As0rPXDcU1DyAuayMnwAU0wLvL26HHh1ehYg7+vIU6jy5PIp"
    "JMnjrQg5+Ik5eeJ6lW76B/d+M5xnbfUwv1gx2PiNmt1KDxFN53y6figlR4OGO0VQJS/XtgbBAcV+rENd"
    "kJH03sAMR7S7yLAu9yalUsEy1EpagFXtxa3fb4NX+EMuMqx5DLq5ll+a8hXh1zxf3ea8WFvCu6ZOJCqj"
    "NVIna7TGWsnSQkrj4wRzJbyiv8KnN84pCihI5hK8u6ne2tlRXhNmRabVRMLx1s1MKXRDoqNeRBSdzzx3"
    "h28vl0o8zUG13uLfcQqAifakg0mg+6X6jpmvHXEFQu1VZfnpAXGO+AaZdcfY+sXRj3hlRH0/ixi5vfb7"
    "I78J/37k5EMm4GcgkSXGu6JyhHBEAFb+s+RwFEBN8UFI+xEzVb61pFPwlqbTTp2niYP2XdS0Shwqw1SI"
    "988LTm1MdGW5Ts9kzC/p2wkyiAt47xOugYHNom/HmvYT6C4MoqL5sy2gVY7MeEWj8QPGzv7BLI408a6O"
    "+dZ3r0vyjB+w5zhvX50m2bXUtbOFKl3a4POVaPdEeTq7zCb6ctlTo4cXHE0OAQozkCbHVeVu4HhcdzR3"
    "sWFG9OdorFOJ2dSDSHatu61rdz7vMoPs18kL+6jEJwMkwUIKoir+k23QU9mAgDdEcMIYga/POHVl/iOB"
    "2d8tBxSNDX36/Cscqdm+wP4+vRvCZxO+nMHkazc5dKXXNevKLMS6KWtDV9RieXjvUr9Ql5Fn8O9i8ewb"
    "eDwl0oRY0tItlB+/8MHEME8302dtBo+8L8/mDCnjGOcJZcS9UB+AGykZtNuqCGSFvdwrWbm654TPxXhY"
    "Gz5pEY7lBSKSsmyXuX7RAV+rE9CQuyP7GRiAzrJX6Se8TrRrOVBGYOFH9FVakuuNr1VAGW9A/ZxO8l2V"
    "zUuBfI6iyGxR8y/TwC/WEcyVJZfP0q/7hIhFZtk+fNCiGHfxiUeLIrpPPjP5EUY9I43WTXDv/xPpAD/P"
    "fg/CnOCw4C8hwwd4CliDSPiNR/JHY51XW7CpA3drNgXz+Ijds5xSo7xyT7RjMlWUnmAom1gRY4JFWOQD"
    "pP3OieXOLP96mOJ/9DnHf/0v/9TnHPy/zwwo/2Wm9etC5VmUTZjxcq3pvPzGqCOz9tyrg/pGvxHe/hg8"
    "8f2HKvNMKG1KBK9HJ3B6eX67hvnX4RhoX9inIXa/9j7qsZkL30gtKsnp298v2aHPzkI+JPwv5ylmuG5z"
    "8kWMc0dSwKudFImPkWW9Dc6U0dtjMZ/n98A3fwadgFjuofYld7whbymaLaJts/Wgt7ryvhx6zAKe5mi6"
    "ViqhqoW2ZiOu1XBzZ5V0vd+FwLjzOEWM0pSZZRzLoKFDqOgNK2YmRb9PflA6rW2EI2F7DckslnFAUrEs"
    "H5sNZU8vX6ql50eBkuXATGpbvW1Di0NwASoCuCyaOwpM5xQsa8GJCOVmLmpll2VHlAA5oDb3VvZBJu21"
    "jtLbAL61NEsFXpRrWuRMGra++fMDsXIe9yUokfwUJacrdD3SqTfy9dUYkpZI4pEkRl//gCcRvbUTXn6f"
    "8jG9KB/JtvucY52VUDagmyQxi06avjv0mZok6vj4vkoEkDT9YABt/thpT3/EemS6/UgOAm/wY7JftaNS"
    "1DrPBsy+W6hlP7ye/CMO/LA+dZ2HuYuh2aEeUtoX3xWXOZlh3TDZgU+v6aqlpoHgfOm5qK7epU+WUWn/"
    "GRG0Z1XRVmnG+eSdxYUQxPHh0VMhV3zJrNHRz6P/jp25vg+BQaW0i8VBlTBWFWvfAZ+CCrsVTp4rrv7W"
    "Svnt4AdYQ+59UPioXzyFxuI0v9OK1r1BAXBS5eUGygZ4CA+Jchzewh/MMk3bZdz0i7f+/SnIIpk5EKYE"
    "mFsTJCbKFwaqK2Yu038pDyRhLu6HNPBtXEKTH1rA1MNoAaxYexjhI1LmIPeFzO0zD3wWPL/fkJQAEcLw"
    "ogWSWVdQCMu3/tmo1emOiMwQC5Jolutogrml0fYZUbKsoUbJcLY2QZkKzwSvV6ZC0DLJUg+LjnywWCuA"
    "wtDfdIhikbwPnBIZ6MMn7iM/IXGW5teJKevo6YpZbCBLbtrnq0/sxbn8plcewQH09kChx+MgTb1Yt3NO"
    "53m7os1ha9M0zNYfud4juuYDA/orHQGPNy1NvBypjv4iURwjbRxPai83hHS+s4sM54+iaULJzmCZbv4z"
    "HzDNsr8bHDUcYWOOZZ9AYLHCUSjqJj0b4iDaqhhGQCSElIC9GRGpWKR7KIXP2lZ1BbO1ea7Gm+a3ia8L"
    "aeXbr9iuevo5Ld23EULsn6FdfXjV5t06El1UI0Q6tlvzd4LlOWjVfxltWEPRq3o4ggauacL39/X9HDuL"
    "XsYtre+tV12/zF30mMh2nXo9l7/qzNrrv5zZjDi1B5dEni+tJWPKJRSJfRBPY8RBAfTfrpVHg5EBf5nt"
    "CzxwUs56X24aDdFQMZHqCIYaYINA/HyfjUxz+lDDtfEk60GZ+THDC2IR3DT2s3waqqOwZDMzS8qljUSx"
    "xXTwECwLFkmX9hvpdjkj6EBW/ZKvJVfsKgdYkO7otE2jhvGAOwaAX+s3df58HAw8mdsLpGSWsreenIe2"
    "V58PbYuI/ng6B+Bq1YbMoMU0RougQohDUBVKnem8nkrJUm9iBTKwln5/i7qZDetGzeoD2beQ4ms+Vmls"
    "K6hsyY3OhfvmL7tpO0uyTcPzpKAHDdpk0LcCMXHzoXnTd3SmEScWcAb+g11ZAM2XPy2+xxz60GoLCPIF"
    "Ue1ZeA/Mu3o8bd4ycwHapaY6Jpu1NlPRor6mZPdVao6UqoM3BtShnoPOq8KI9lUZykzeKoVaHUiauD4h"
    "CqGEIVGQgWOYqeLeawi2B/AV+cxuLls54SAQqevBa+VrYc7qDIPsMNpuqncJkAJWYt9dHFmedlE7YVwa"
    "xcrfket1pnax0nvz+sF8jrnhba+i2t2YLrIgzNZpnJXNtTeSTFN61meGV6arApLawZrdZ3cCrjMFCEo4"
    "hFdjnrtrmalZo0EY8Tcio5FHubyxwUV+YfhTZm5RVlcjM/Ltmx9IB74/KCcxqxbp3fQQeMd0WmLI6Iqt"
    "E5zupplYlenzRrh+FXKDbwh3zBgv7O9I7CKB2GZu7SL6Xbgy7G9SHS/GUnAMghQxNMF3p1IViPZQjJe4"
    "vYovzetA9BbhLLOWbbe/9Ga9xXX1BsG6AO5RqDRtvpbXdpgWQOuqI4mRir9+tc381PPRX/ygJkJIysds"
    "W4Lll0v25+xo+rYb4VFY3l1emVpOBwJBgnIgjK6kBt0cHxivPFRfqesoBnd+82oDRb6kF8yw9WqW+SOM"
    "nmksf5PyIs74fKPFuqvPYjlBEcAtbjeSEtOfjhX1TqZ5TIxVBCvLl8zcC5ckePrNB2EhZGc5IoGyP1tW"
    "aNcesU6W9dWqsK/xKL/S+P5t3PPFzn0hAVQgDztzGNwkAuAyDY346dPV07SytK6YW3qDGgud55mQHyYp"
    "vycXq2GUNQsLxcvb/dwk9Mw303kikpkQClS3r+fYXRkX0r6Ca+ebGjaj22/Q0uexPkEuBualQ8gzUX6g"
    "5nrJoxgN4vcDyc5vO/8WdVFuw+U6j+J4f4cafAPxj5Tk7ezgj+/f1+p9mk6U6rI4nGY19ncZWkhzdkxv"
    "NossggVvBA3vTErD01ORwVXY0M8za6j8FU/RwRkRgY6uYmYNjOxIklhXHGyzDj8SscuQSsJ9t86lJApl"
    "jBMxMfW4F2KzRoYiCa6DpCxy0u5EmujElzIzzAx1o5rCjzNE3JsaLmpa42o1orXoFn6ZD2X1x259H6IF"
    "Mfc4aqdmgKzH5lNY5Djnn1w0uf6m2Q+fTgawzBf4oN7bNTUueosbDHu16tFMpflsSBupefkNI/M6K/Ly"
    "JmvqHIPD0c/hXoLwVUYjCcstb1uWcWuiUldP0tIuHNtJG3tLWuOiLgTBuMpr2RKaZZH41XKDvjmQTefy"
    "K0t0owUqHTZS/yZ2Fn5AKhIg8dZuXG8/F/8S7PQ7P0zUrvLxVbKNC/rECwUPdcURj9xd01MrtGBZAgcY"
    "MICcuaGbR2jW4JnK4eUl8XqdEKwRpHNNyFIfas8P9Q/OcvnP/8z3BeN/m8kcRghGlYETSRZy7l+wz3FK"
    "TdKkd7XFr+qmsw0+oGhhchhhuxUaP6Oxfgm+xZhPdXm/VOR1GmJGJEzZr9N4d9ULHM1g6HfqaJUVIQUa"
    "k+nvOYGX17MC7C+8NzXHSbWD7BS2HEnNBFEwyAsAha2SAUUuFZAx4JOtSfBtHRt2Q5pMlWRZzQur9WEs"
    "Pg6JsyNPmnBJ4Y0rfFqbUOE71SQYfOBPhBOSqRSMPOpok1yudX3OsA0QWMbzxHxkyPkOfgvbCRG3sn2x"
    "4K0D7MO/IH+GHzVhJsuRc6QdCXQul7aerd39O6RCsEXRIbmqEllG6LzGbB6nhSiuALdIAldXd6k1cE97"
    "4thY9hdRXRQ2NoMJ1pvVnufCfZCe/vLjCUOMbg9+MjInyuWIHmTM4TJXnADixf8+l8eIR9IpMgUpssXw"
    "8woEqq26HCHQVcpWdgtgXCmVa1PPNvA3OM8biK87FXougqcMVHd67mQjNQ1TSqEjCiyDcFhSub1dhywr"
    "aThOmbwhlbn30NVa8KixRV3yHDCT1m+ktIHLPLEdA7sLSqzK6Y7fpdaGb5yz/YxqAbjyxDixwgsLDImJ"
    "p2BWWmZ72c37kSTlW7SEuc8AGAuwxGXFNQHoZoo+z+4DRrMrZ2ofknHiPkcP881LmAna8r63AzgVuxvs"
    "UPtulx9p1Nf99PshxpsiROWNDRQD8Sz3q7LmxQPd/zS0n8C6wGxyp1bac3ySgdl3h7Oxl0aOS0/3XpsE"
    "/iMc0ofJETYTuAVi0kBu6a7zv5zdS8vk4PycqNg3DEj9mhFpy7Ptq792ljnjB4flHunOzp3pGFSw3J3e"
    "JVBUiYCaulZliXXlzdU+KgOZHrxtAWkNPu5ItTfSmc5Ay6+F82r/EivoFSaa4cBlwAzZHezd34g6tjGi"
    "eqkxxbgTGdaqJwwKcHg8cehSuZZ8C1YAF/LqOm/yYV+9CCSepOfe2uSS3JGvZWCvpwyhyvg3FmlfEQ8r"
    "uBDH3KyOcdJtrFraO6+zJ+NVKMwqRZUT6O9INLRvw2ldwWM1mepIMixVTIBijIeC7EWO9QLovV9sLLZX"
    "jFWu1XfWL7z7kWPDkaKOFXiZkrjPkgFmThy+I7sIZbGDJZTFbZCNCT6Zh3BhpddhinoHRa+xwhPDJwQL"
    "U1Pa6Hvm9iAUwrcUXIIe0/5cRvZrBuj88xNyaj1u5e+J1YK+O0nAR4EE3VLgI763FppMG/pCzdFsIvuL"
    "ztGLhZdP9px//RtQaU9kPA7LtNcY1I+wSWyqG4r6GhBREhdxVk5vhohwHtgubdKp2VXkOobwPUryVG5V"
    "jD++H5l9xHdZdxojeNu2QgaLARblQayk7aG+UFdOK809mTsrXF+PAPx+TMgIMvz2KrFQ9wWq2VZ2z4+1"
    "AvkN6qRtLbYklg3qxCgpbr9zoYGGHgyHH6tCe7vQ7LK/fEwn8V4I+wMJR+UgCj2j6QTg9vMRrvQO5U57"
    "YEErWOnk5dPuD/0TjD/r7/m/mSL7pjWUF3yRyTEXXvTQpPjQwoDo3Vaga7gVFsAxvFtM0dr9AHPfT5P8"
    "yGyVmW3kpW/PvL/e3e82I7iGAE55UcfPtJW4g/pGi/hgaJtlKYl0Vu5tiAyK8rcTrIiEGTQ+4CGBj4YS"
    "j2pa5LyCHfPBoFA9xQI/0583F4kzGBr0iwzPuF1mI2q6Udzusz1kTaaz4EJLmMlciUtflnY+UjY2/Y+M"
    "ua30CfVY1vQg4yk6DxRFAbL1N/0W5ygejjv7LCBSfSN/63jdfgJeafby9zaEGL2YbbnrPWg+V4Osmr4B"
    "kfEIQSab+P22C5Vqvy7xlMKtlMKWDahygGVZkocVnbrnE2mFW9VMJJWJCePESHNwiazszf5qBZCILXc+"
    "yZozZOqVzoxboxQ6yqPcdjzuHKeBCpMsk19SEVESXafgNsBBWX64lmUz1+ZFZoi2Gis2Yys9wDCjPe7p"
    "BvNIx7KO/5ZPmXgxYKun1NJAzSSGfgDFQgbwGzcQ6dFfEnbCpwMooJCkdYRgiLLCzGmB06vS33AF0Qn0"
    "BHBKsFDbECrUuhcxtLuJVIHSq16/BlDPg1qet7zRdr9Zzs8L2LlnLe9XJ0A2ZA+IdIMGzjw/qJMSMR45"
    "+U3nXqzmSQzSdTSJbY7rQC/zzXYnWWxUCa4sfIjyC0muq1nArz1JqgXvd1HSzLOWB6orfA3TyxQLLl1D"
    "pntXeS1eq93cGm9rPkk+NWvaYWzhG0P60Af7yr/TbHRRIlV/HMmLREl9NDm8qCxgpl+6c82wowjoNBG+"
    "EWxf9cF1+JraHGJHkfs8hfr3LCDaYNPKSa8PQcwjePIYzsZbJTs1w9mHumpjymqXLE6PW+sKrZnsTo1D"
    "POP+qtWszitqp6MAkrRfdhDu3VY2dwi+Y1OtC8PIjI41gtMX9eI6RRo2/AYxPbfwHGRz81Qrkuuo/aY9"
    "XQdRfGUO6aVIrHSvL9p+yC7kL/LO5glvls4B4ZTXJ5vgIhV+AePY2h/2rdVlHKAkAMzbf2+DVdBJE5u6"
    "LgJKTXUpCdjj43a5k1HHI5WXEOfYTsPXkofXf/w+8P/5H//p//6v//7PECP5/02PLf0nwO8AeM6TPGrq"
    "gwGB1rHbFRf01xtkI8SMfEDg/OFT8uqvKIGvx8tTWNOR38B5Rp+5SDYdT1bDwL7GdVakvYR3xI6G62Us"
    "nTuG0D18fMxTukp46mtFvy0FnlZ5tt+mDwJ1okoc+ODkMxZf/Hkq4cgeJxrBcP3WyGiZPmFNhWK+6vz5"
    "oVTDQRWtz6dEpZainWJ6ifQZsMBCO5DcVc1lmjiUgQGN+alc7kV4Mlg6jbu05GJi03RwoXXWPDdBCHnt"
    "wlxBQedDN5N37pis1MyakPibjEMdYQDIRtr5Kam7zr0qi1PaZlN7M494MFqMi1CsMN80jFDjq37XzhYa"
    "uvkkGkmcJu+ndp2s4t/YTM63czx/dXvnaLad8gb86oj/S8elukONZJBoB6LIaBP2s+B9WB1028A47IwP"
    "5UU28xUPVZlZIQJRXPzaVTK2uGiLm/NVX8WfYDgXz2D8eGnJ/J3Petdgn3wbeZ2VBcKlfR3Zj05y3plM"
    "yGhUJUU+LpQZVBzABN9QPZP46cbRP97fBEz/Djxn0AydVHQBPdYPPxFE0z+OYpHs9sG3J+wRi61G8Iuc"
    "pErt7niCy5MSIz7kYs+SivAW/B4z77c4lRlRgOleoQBDF5NUx/Rp3Xy7nOnq3ojYzUG4JCl/E+jVj2tx"
    "UzWzDCijNrtTSenz7aZ2Gq6cBpHw+XzMWsQo43UKZd2Oc6YO2LBqn6B9jW4C3+grF8Ue2frFPFDucbTU"
    "zwc/2wHNBLH4ZOrhL33d8E+MgZ9cmprtzQrI1h+Vjkl0H+q1wUvd+C2o8TYvAQseGsr2M1+T1lTdkWq9"
    "T28ZGxsZ33BIY0qGFCKE0ogdDsoL8DRKoezVJOpblhxChT+pE5FeVbrLtC+VO5dmBNQROH/xYryCVRBi"
    "tVY43eAPm2l/gyKk38iV5ItVePEiuBaLwW5UnU54VwlSiv5qWWM7HaczbuA2Fwus6B2kVrn8clVF7Yeo"
    "EcfZsmZFSqpvLfdM2YXBXJqnOF4vVsbmqiXS+zI65i4xt3AfSO3CoUL7+kpRjIyB2x2q11IYhphcqaIt"
    "aSLPltBUyQxPw55fwdeuBovnoIKM9viEd5YJxA75ASAHLuzLVaCbu+3KWgRDuJKwZJhNr4O9id26voh7"
    "7lNfi7wxG14I0C7sg0Wulk3D7anypLISV/EDK9ApP6LzkjQc22bmPNvnLs5vDx7CnZSe4zHL0wCer0V1"
    "pNDhAHL9YpsWVOWc9RuF2/Ur9mVOrXzJQ1G43R1IAeZP7zua2GvetRYFbzzM4I+PWEWyZmfV9rkYXxhm"
    "iLcKshhm5QtaUaOehU9EeY5W9VQPXyER0R/cQ5QBVxmF1+NE77TST+NbOL+muq6qezNe4xYHa/SkyD2f"
    "8QP4bxAqjstpiRRjjrk0ubT3khk/vk2/xfDhe05/KmxKgZNsCheBSonGgO693FTfCxQU+qNCHa0NpjHG"
    "I6vloxgb9mVlpHJ/sHxgsR3PGRuiA3WR7gCbpArkE5hIVIc8s8+18FViAIY7bcVUIB+/Y4BhYBOsQfrH"
    "8OebzRXMKt0dNNSI3fMa0wtXG8+2bLRwBpQCsJ9c1vOIew2mqlOOmEKMNk1GGZavjFyurA8EQ31QQLuZ"
    "Xjy5J9ZEg2iFw3EQMRTSWLkI89TUC4hUEHHrIQyRmBj4/j5IVGyKwxlMjGYgfdgPnr44Jeb9sZaVX6p/"
    "wbWHfplQmXXkToweiD+29eHZDlQ2H/tCnj8ef4Itfq5O74P330kY6UBsk8q1mofS4oWxNFwoESo9Cw+Z"
    "DufPAUAgzuX3pN9ouwiAjX/v92NfWqE62Lf4Eee2tvInnK/HvOViqK+7bEjTOTx9d92Qf+v+JBADRWVD"
    "Jyypbqu5NVy9M0L1r5SW+wQIGvx+D0HHLMp3SbIABASWn14APBnyp4ycZuJB+vYNDk1ikz13vVJ6gYut"
    "XN6dlZ+LZZWPQNWjFcwnA1vgjgFTUsawtLWubOoLdrgU2QWXTgiYvdJUWH9xR3zQ+MUaRHZeC2aiBKl7"
    "U9x/kIBUxq+0fGKu6Km6NMVMxID2ebHjEbqtK+bZyAoMnGz50uE3bbpXmqQPqQfGcdR8X5178Tspx1vF"
    "nXZim0nVejJ83Ky9vEvsTZnTTXx6FL10Do4tCnIAq/3s6Gu5uBeISsDsjqmnty+3VuQgv/E8nyqX1Dc5"
    "UpgkfoiV3NG0IPkbiAmC1CLJ6F9iVmLECsmTnRAvGT6r5I7ga2o/YyRlnUO6r72lOiBjWpr2YRYQP4Ul"
    "oXvtJ/Q7jNo2ehJ/QThzwzPWE7wYJ2pYoFZSf10uIIrVXiPP16skQC2pYshkVvh9TyfNR3fvjWh4AdXc"
    "+12RhdpD6HR3o5nfR/S87gvcMrFEqAve1/Mm2EG5bP3lqqT6Te3A0zg69LyASVrWCtE2d9tc/N709JOd"
    "8l+CvGxuss70Kacw1H8VGn9Fe50abZkQOtuZxB0Tovo0Sz+KHLdQS/BbQSMMnrXMLsRvy2EDOZGvyP4r"
    "0OwewQd9ZJhPvDX9U1DI+Xm2vts/S3K+P+Jikn88HftE6PxRYCwrVHoTIrT4eiaQ5hEfP/lm1/TETo19"
    "vuEvTq3kWsPfx1uC/ErTdVs9opwBHVoGQZLUo8RSpGMjokxRjgpJ4yYw5WGp9Y22ifPi0PjYxDKAvjps"
    "O6xw+MjVMq001jC/It/ZFCJtukbKAl1+j03HtCXOeKlqETTYMFLPFg4XCxi89E+aXFZc+2P1j3c9/M9/"
    "gnUF7d92gCNRidx54oyS9aFI9CXLLDrJgoTXBj7HmNlyBKvkV4Pq0Znptnzvmh9fVWzzEFPBWsvX/EAo"
    "rCfNrcGDMr3FHSaEWYd+xFdMFXUDK3b0LptGY51Gbio90rcUA4D5+ZtAk1A/RBdjGV1J5SyB78j9Shzc"
    "ABQASalvhNn32WDUZ1ZnvQnwENJNUNVuPV5WWHZmdgIgCaTnSIvCsVqlZGn5eogReLa9ibEo/CDI+5Wv"
    "cCKf7bqsrfZ0XVaawqi2XzgzDURRJqp6J0KS8CeKUmfVZ31RM0MqyfwYzhwlE8LKmOQHgeL3yoHLZWlh"
    "18Y2MGhfZkdw1IA9XIPRT5o2MtbwKfYehdEyWewuDeostVV6ZV+8miLKYEK4KNC+DAVvRMdvFHMe417z"
    "xpOyzT1KVLC2xRUi4WkUavPUQ1KyAXMy2Yp09xwvgRrd96qqmj8B+WcV+1sH7rXKa8lf5bjfPvDwjf1l"
    "7qMsBJxQpPGQSZnQJzdIuBc7YV2VjAkQROZPiOhMPZMwYT+Y4daYEyhPKAKPn7fZHX6zv2l10swOIYuN"
    "vk93RvKZYr8a4q7kaHoSWnbWrWyuy5AzkmZRl9cpXgtd2ISaRJ2TfXOhKa9/vpQzx+RtdfRGD1vii4oM"
    "c6UFEsnFzosVoBPsnfxC9StF++l+n40kTRC5caIXFZIGcZeJJuPJerDwe6aKz51CVefJrvEHO3+7rTFq"
    "rD2/DLTWAp1JAByrt3oSQZ8MpzTLKe6pEllq3/NgnRaN4G4Am73CXDRSWgJuBvllxi/WoUnXA47DlMbW"
    "/02c+W4ScFg3wwQOv/N/20aI2b7MlveaHY9MPtz69+WDfRvC4McpYm8nL0xlNTH+4F4Uuad1Nq+3giEL"
    "os8OILmJYGSOJkpXCNADZWKf8D2fRUD9sDj0sL6PCzcDci4gZ1ZmNhb1JCiSnhRqKVRE8i7Fvx3ijAQA"
    "PcDbB3ZvYHrh0/dDsVjC+TYP5zRHehZHfPt8pkcGBAWwYCZicwl92sqHFo+EqSroweIwPGr74TM5HRn9"
    "3aWm2Yo3a8zBXCGsRBsCcESHH5NOHyOh876hRB5HAqZA5W7HQYho8TlXHabgB79W4O/Ib2SSOPJqFJIk"
    "N7IcgkigLS04Y3hflX6MEOTN+XD5GVBxn+64/D/OzltHYmDNzg/EgN6F9K7pPTN6z6Ynm5kAZYIAvcAG"
    "AgQpUqYn2icRR8BCG+xNbtQzjcZMscw532kW/9o4VDef7rTYao2YRwocBZN9otIJkzyHiujuWJ15jCqL"
    "3+2QwwQWUcHfFmITT219fHwlw3Q6hUu6GhVb/Xlb4qfTvCIRoMWlBh5rEGWJK6M9FC5qLOjj7eApe/Wz"
    "U282wDDwo3QdngcC/siTQ3YDsiFFhFWke3Ss0krhq8v+0Qcu79F2qQZ3dMex4wmzHhV5sAEmWi2za910"
    "UdFf+eOLD/+7eIWxP67Se3/3GBoyr/X9uKbobR+uRy0PNP6+uOxv8SmPZWo/QDPFzXZsnrwfYZzIjz5A"
    "/9njD/vpKbIjhnLkBVMzyUIn83WoPeK95OToOeiXf6UPwxHdVedN3E69g8Hy5IbxPkliY+4DSMksdAMF"
    "GPETMe3KipJz/DWd2yfMpM4lA08AaDea06FR480wGcDFdaG01OeH+TBzAOLIj9e7cEd3sCYYUqqdiDwo"
    "ZRN5mobLifla5vILEEM63ZeCDMdZPBsjOdpnbu37x3KFlp3earPaN0A/fTr78y/VxHZ6IzpZ1WhEL3Qp"
    "XgJoofM0gBA8LXPDHjg3jK4nBUuHPDOBJGR4HTwn7atYLMacXGoZlcit7U8QkHl1VJfidzzxwpT8Jv9H"
    "2tjvbcR9TP+UUfk0b0DEKqO6jBxQSiwbqP/45LZ//d//7Z8pKPX5d8URovDOcGf4W5nk8x2tKWvNkXDM"
    "n03PEKTqFah60t5pk9B5u7ZkrPAZ6yGkkcLWDE660cDLmnwSZ6l3wx9ozwxsrNInVeUtWsyv6LeGGyCB"
    "LQ7dlyc0fxf2zN41KPfvFgZjHAWr49oGBcL5NCl/XjfalUxS4AMeJY7CJSZtebKzy0RsOHFsmHpplQmS"
    "yo7bPu97U9eixfUU9CjI+tc0T4cz8Q2F8el4pi20HOu1HG9LBiPLhMoPLr1N1euDFvAXpOn8ywI+vL4C"
    "nwhOd4OwhVRQDQF3JRU9epUa2ICSWIzTjyjN1KKHmMEEb2jjiXwi8sSUeGKwv6o3OMYO32xBx/VMx5V0"
    "GCbmeIS346vnY2bRiDCquUiiMH/DFcd2ufcn5ifYd6do0Fq5x8J9Oa9neOw65d27vHWNCA+Crtr1ZosV"
    "clJ2IKMD6BkRKOHexhgUKcF+0dP5u4drf5yDsznnBWeO0pxYiVmh5At2YVSvO+S/sxfk51K4yxpqtgJd"
    "7AmEYGBVXlANXrCTkFMC9Jg88J5/RHZW8lk40GI/cap0zLGUF+9TA8RMW/pC0qcl3qBkZfcJKgi5tQEz"
    "YjZjtZ+arcU5JygCCUsru+h8dH/SuBcZH0IZGWbyPFCSRDyFuVBG7zDX52AznpZuHuOt2Ip9PAWK80kr"
    "GoTbYsEuqyOcg468NAcBgssrnFY8zfiJNqewumcLFJhVB710U0XwR/JE24KHWcIKdB66XLUVghdLjDs4"
    "MR1oF8MQGcR/WiqXRLOXAWeu1yVvNKbCPmot8lD4Ol9onzB0SY4CLbczvRBOZ9U50JYDab5PIWPlrGdV"
    "PFJXkZBO12Vxnfa76OqLuTD+8y69TdJ/7+iMymsgJkNdjJAvhpJ0TPNthb+Ne59997fpnhnsbf9cPSLW"
    "J8w7KOYq0ScRwurhY1sfTa8fqOIcZIk26I5o76knMHHdJODxhnadNEo2m7LCxDQvh8kK9gVdrtWCD0kc"
    "JmnqmR+T504+HwkCSt/2OSwrfql0JXrRruNDpZr9N3tQ1FBzc6PcSCYakB3RIwKQSJK6DroXE7tf/Q0f"
    "ecFCZNV2tgiuyfCl/SD9aC8tvlovVudUe5D46F8vQKQRH7lpo8nCpgQ41sAcuaFlRM8veJZAzMrx8TUv"
    "qu9x3rLeGcPgAA2BT+YS0+ngvJ3xduPEDq8r2lQnaeGA1qNBA1wACCs8U591vwiUPPwiDPYqRruf61iG"
    "bmL/dIrr8E6/zuDyWuQdr3Dr3hrxE34Bqwu632T5CBfOZH116MXnkwwMlLsQOZw2E7TaX+/N2j1cKpfM"
    "ugkX5WTJNL2hAKy4pJT/neLNS3L92aBYTB8Bx8EfRWcy2rUXDMoaF9J6PGFgtnNwMJ64TAO7Iec4MEU+"
    "zQxh/60fftGYfdstcSPkEkpQXeDeKePjSBS9KsV8DM5uyaZXLl50G+CqGbfF+rFY+98P+auzEfCp+Tv7"
    "cw4+3HAPWiv+AmkM++V17vrQvQt4EzGZwPCIt3daf9qoHzayvvctRLSv5GFZnVLBfVzBFGiGUm1ZzWBl"
    "pR5f9xP6PMYx7MwtL0r5lHIRcBg/NW8zzO+kuk3hheFKN+dg2BaT4b6kDPH4vdEYmqshjjmD1o8XAxgm"
    "U7QSRmIV3HzHLhgdIVLA8cJBg4qaCsWhDXAMNABX0o007O3fbHqUSJO49yPHiUSvX4nQo3MeIamG3NEr"
    "sX2vScfxrPKV3IVf9wKAG6xjXjlNw/Gc3Q+W80X+tRTXZZxaZ5adUO09+TwWStLqyTegKfNjOg1tSoV0"
    "aZLwA4LLRSeqlyGodDKVFSOwJgg405xbxXWYjhmwz42Ksz2+7eq+yEjPKrwj51yu8SOILYi/AZTf050a"
    "Hfh32nqEU6RRvPNQF/G165O/jX3wilZWG8EYaNI9XGggsXytEeHaXmWSioKGLQoUirM/1x3UUtZtts8I"
    "P+Cs9PoD3M15fuOEAg9zgufSrOp2rL7e4QKo8gVKTk8n51y9cvgceP/xQN6g0bmMQoL8LsEDaGBmbD8K"
    "Ba0FDqzi+dFo37fb44CfKb4sEuya1T7I6Nyx0vh7wq0Mh9zlEnEMgyf2hZvX22p/iiNPxUHvFootABdz"
    "Buq66SBMwKvSdmNgE23StX90E+tf/vM/dxNL3YV/V7YJZf3/RyZvqEen0vO8NOsZxHZUaWUa1V60TlXE"
    "7+oY9pi2Y8ez7hZKx5C+rOI5TAJhWlRPmeD36ceXy3lQpfDylDGQXMFWWCbuFY5z5egMaIueUmB96Den"
    "r+alNXRCkboBVDINEwCOoiV+hUCNymaTSk9VdHjYPwS/EWprtNLzfCvPMfG0mZwSs0BGYbBXLrvJ0O9n"
    "CJASQyE/QskPZuoUihaTmGPegzcrMTqmWUCfqnIKrBEtuXH4w/vCccqT3qd3uQ4aAc3BRzHwAtRQ80+Q"
    "HBB20T6zSeQ55jkqA2t5RKtc/QqY1YzMgwIxZ1q7JkmDQHMUlJzPWYGCBtJL+FcKb/6mv5Cc6h0+RAIL"
    "GMrDMV53BTdv+ZZhGWNKRseQupymVVXq/YEGZ30cdV9V76STYm4NiNM+E9ONBRv9vKn5Osk2nufclvBY"
    "rTNC44FB+7GxEM+V3RjRSep9YoKwzH+p1ZctiLIy+BfL9TTUVwyO2C+b5qorM3Q/z/rnuqOKz6c/uakh"
    "PusOBhC9XNStKj11oJNbx2moUo9veeZ3VHIKE1WIHxz9G0wYp0hmbkdnt5KD9KnWSs1PvchRdW+CN+gZ"
    "vUaK5vhRWwJ7QbLBDxPWAZ+hZLQQ4vEha2AKq5llE0ttZOSoCnT3Ih08LLeENyY2qhltfQt9qptDEanw"
    "coeKI8SgNaVlIByEvmLL8GZdofu3KGBmh5+ly2+9Qy0Q8jFiOAbuOPyAW9iOFfGjPxLDNrDMgMGnIai1"
    "dKU1EzFpRuaMHiFyE1Xvshg9xwNHtSnUJAqLOhZ4JmxD/5Lvv3hxVdlFeytD9OpJBqDzn+wfC/A7xBaP"
    "GFli922KXLQoq/2LoS3vdt4C/aDnHTRMayNR5FRWFBpxsPkkpReY33Cxo6pA+m6sqsz2aHx40y3Jmjg+"
    "jJnVEeewEGczn++XQpHfHSglN7zBFULvl7KWmSdmyLHsoaR9Tqk5qIT0ioH53xMqv9vrIKLISHZUVcFm"
    "uG8sXqIjPWPhcFLO9EPwfQJ+YAUrDIYk8GMlYBzhi/el+rGP1ra9pXhTsaN80ErE9I1BoSiKyUmkLtN8"
    "6uhzVXXxVfhLHqMCAP92L49/e3s9DcmHhRzsCBD0XyRS9aaLRUR2XzyzOthSW+3QOVdlVF9o1Tf1iUGw"
    "5f4giicOn+RG4xsF53c9DlE0+XWP/aaxqDYZV7nJOvjF/KGklVJ8bVgzyMUOYgvN6uE/COPJekQ5xLrA"
    "vFB8wIJULRkVhTLauk8Hh9VuQtrJnfidzww7xlQ1aFa9ro19FwnckVsgAGBc2syaPrwzzR6w6kgjlSKk"
    "zmqtzG1rK7CAE2+iL8rPS67071y1H+lo4dkvWfH6ZfjZkU+03wBObFpmncC39ZIlkwVMzykW8gLzNVl4"
    "Ccc0aH8sPNg741lHBTu7YRDhkDD9fvv+4DiS1FydmKS2VDHTyCjlg6ql+gMkGme9wXvEcSQqQcBMzMgR"
    "2sKJT/XgAHQBf48Y4a9lL/snj+/njMT8pvdNwSDvmJfhFqGCBG+EfCNK4Pjv5LVhVXEELZGu63uro5Ou"
    "UkpfqSvdqdtAnUDQQloTZavOddrqvmCyzlXCWFgF9AXSLmiAIXqKPZKhrv+yc59kYEiWaxaZQgZ7keML"
    "E1Lk21F4h3RAmRnq+weEDQOlSip4ebQwB/tgxA6NC2hv+ieD63vFv65ecBDTyoI4Spe0I70PHvhd0Y+X"
    "IzgbFJPeXdU8CnugJi6htQuAC87NjHRHMfrLd/QvMrVc/6ku3F0YhnRwncXhHnzp1hY1pY4EKWXGmjF7"
    "XYko1KnIptGWVUNoYJwU0ymVVoJw6AyxWRjX/HPmE7gQD5yEH5JAmYsPYRw7P85w7mWZ0YGFGlgsvjr6"
    "UYFicTm17hh5u+QhSZnteg7tzjk7Lk2Uw8Ht7bAIDiSvvfkPnG7ViOcx9ORgXmVSiHf6pD3xcS7VGl4v"
    "MDkfAv8s9zx/TG/hyLPIqxbzUa+Z1wOMwso0qNq25BJjHpxcB14zTIsKxpr9zvKgJ4TQrtozccMiu9IQ"
    "XUcz5VYA7bGlVc5djR/oseDtTd82y7M7S9Hmw+IoRq1z83ymi2fwsrTX6PalPbBz+Zv4M/djbqn2hJAL"
    "v4xD0WRPi9/E2pmMtj73LHc4Bq2yFSwK+3Tn2P0SAXyosJK8rCl3BUu3fKihHe1plNFv1v2q3Avgi9e2"
    "vo2JiVlUA3jic6UlM4Jjnd0rXZ1FIW09TaxF9hiSrC6qTq/OzVcOJAUTrW+PlUMeo2C/d18mNCq1gJAn"
    "FgxwHKQlLWuQMhf3iHPmK7VlVcbPSvyuBEjiaUhcrZB3rtc62F9u12K4AFYKZ6nJ1m5z6kfxOd9iruBo"
    "d0aMYaRPIQtGQsEnQlxlH9/c+7gRuoLPSvQNTdg5whK84vDMT56BX0mluFL47f3m7rk6lRnscBaoWDZ/"
    "aCqtPYPIOmnK/TSGf79t0O3JlOJnXLUhKZ3BC4Etk2J+QYZZGYgpDrtUaUAZV/B84KIWfNoNpQU7cTGX"
    "hLaHYBxFcLn1/VTFK25i0lc34GWgHTC4KzbXuiLntsNdev33+6F63GQjYyRKlMjZh/dZSDG/94gGusi1"
    "TstrZUwdgHxxWktJEv/TJYaxnNjSQQ8rSWFRwwzmHMhAw53V8sZzUjGo1j3NftSkDmU4lqfkdgpojAtY"
    "JE5sx23rYpdbB1Y4VZn1wMhHvHOme1McYeDOJpoFxc1pFZU/5mgeLLaocDOaxdMz2EybhUNLn1nGxjZb"
    "pNDTmUBuy/KYByo2/KGDawPQziN2WEikRGvrpD9e2M+8t33hB7iICN7fab1sYHaN3cpV6ragk4lmdEzt"
    "4wpAuPGFZPYK1bwTNO6PjeK4QKuM3yrdVNkchtXfuzZ58dFSDOKwFMVO3iw/FkIyX1wcaYDcSZVFEwqL"
    "qL8CHLibUDIl78Mt2Uld/1VpnuMc+9mN3GIruYNQpiRAdCAvMlDh40xId2ZHDVCAzhtwAGZa1aKFLfA4"
    "4Fz8tsAuPWxyowVbYLFliKH5R9op4k7tpQqGVzswVZ9x2Ud/mnyN7Dbi+AyZp5Ey8hGiPAkICofbLxnU"
    "BhuH+SiraDME/iP8MPlzbCh7FE3MEd/WnaINlH+G7iFeBfJhU9NRdnZ8Smj9+fZq/xJs1NMTdi1BMFzV"
    "K28pU/J7TBX+D1s0kVUEo/celN7beKeLmMRvqr1PpY96sqbeKDUlxJcYBbIILJ7fdSYLhkqjP27GP6Vc"
    "fw9df2FUOza9mdACDtY05bZiWMDtLJpbYWPV4DtSUcG2yeIW2W/0BJOoiyymmtNj8XyzZU/qBKhEq77I"
    "R7N5ikehjEgddAmE7T9+fOS//qd/ZjNg8m/f8G5BlCJ37twR8GxPXoLVUdLVWpRWKtHHLYDaZg9CZy+1"
    "Z9CvTIWQaLK+6yiqJrqfq74TB2gPFWYWlqormEUgR+ucVwAR315eocyRrnmFR+q1Qp2kDJH6cp0tY10R"
    "cj+Lm6SepqFL1U01yKtN3TC0YvTOSZbRaZJAk/FILla4g64gUIoQhlV4uthPugRQhM8sFDz27hX39+py"
    "IoRwdI++EwKf8rRFu15gnB7k/a1A8cZmBTbjpmlCNv8UKCy6hJvnjyYT5r7JepCmmJAAYI/WKy26QBYV"
    "OeUa3nCkS1wYI5QYYIeUiECwOL8QsX4pnK3kUbRjXIpGvrChElQ6n3l2eNkfG2Ol7LRfoy7lsjeUglKv"
    "S7aqd/5CfppeA2b4x9t6Y3/KZ3YVtxi4/STtmAMd2t3P1obe4R5Z+iEfJEynff+dPmg7wrtSW+c3JrFv"
    "Q2Ta23U8NY3HkwRGZ/oPoNFiWQm63Npvisf+DRHql52MswqbqjV9B/i8WJGM6MurWNk1DmMyGMEKfyd0"
    "+JnkB9QxfCZ3SACF2bqf6MSXLW4sUqdx+pMZlq25kgEIsags6ZGKaBNq3E25aZK5cN8b5jkWJbx43Pts"
    "ixJ7xsIpRt0tk0BBvwyxQ6KChct0IXdTMXYatluoGevmfNhSnmLfq4JICrpoIgSSqlpdGItzp251idp7"
    "JwfLkewcOpyTM7QdK+Nc/9h2dp0acZ6SsuBlBMfeT6N5+bKA9X3RnhNIQhYIcL+gK36XruMv7Dr7agrw"
    "JBUTKHtphUdSREaTMlcwcrZOMDqAkv7t5QdwJFOr36QhjmLhSIh8q2Y9MEj9E0b+jsify6Dw6tCfEBDX"
    "WsdYcIbrXJo0rBhpi8UeKCmnY+7xHpQuQao1Ya6i+UWlmCTn9fuxMBjcYEWpNKMiwlz+pXz5YRoigWUm"
    "3OgbvLjPBKcSwxPbQek15tdhes7Xeg6kpU/HfYAIJ+8TtBYoP2wLjl/wgAzShArwbd8nT1PV2i1R7QWV"
    "fzH6jym/pIX/kouw5H6bVbTMYX/F4z5EQaIkk/boFm+Rz9nH0DIF0a45/DlIfqJSj+J4chvDx7u9WrKl"
    "TpGe+YSGY8hQhIVuzWKb4lFljmH+YLSvXrjkRaSPnD7G9qd+Bq83nc7B2Bm1fMrVaFw/JrcsMZdGKDuT"
    "85FSFKMBoGCVjk2Wzqd36gHo9VProGNYQfuxPhzRWJtnpImwLdORQy/BTp+gQ//wlVN8STOQCOAla8Dx"
    "hJcIKWgFcfeOWxRKGQE3saDornAtrVt0kQQ2JrGtekIa1EpZ7K5hxXpv0yVn7SnCZoD+XDdjRxush9wT"
    "3ozRCsQquWz8214SV5ZTcirMSh095eORI0D02AizY8HT1p6cAxp1yohdBnnt9OWZaTJ0rD8/MhwcqbsS"
    "oRSgMtiuCZcQJPIXMSsXiV04FRJr9o1IcQ4xrnagrpVoYs1I6lyadatU7USrevykxkUBwGBYa0EYdhhr"
    "3c7QtVntdHRl3+Cn7RK59GDmTD82ZrPUFmLPUZ5Dce/PpWGx2sVMa3sGw6XarTcgGzOvzwszJhwP/i0d"
    "4qsZtjm/kMUKBj+SHwj6fluKWDuAjLlyf6PZ/lVGDmFMybBIB0LxZmAxvu23xlZYq5YlioGZ9NE526Hq"
    "tgJ6QFFsAeF8IJhxV29injH9Og0bpvV2prkktgbM+Q1WIlJWLeKGCXzDn6LLM/2ATGYiFTvs6qNO7I/i"
    "MdykbPzMfZg/YeK6NmQaO7iO+so7TNf4oU5KJmLh7NrwSf3BIMHRgBPlrcnzBqPDEVj34CClwNG91n4N"
    "qn7tjf/Uq81gQ1BDXmvzMVNEcanU4l9ZIEVYGu3qGMGL8ufNwHtCEicqZyCGr1EfIRFjF/cRpEqUTcae"
    "h0UOzWXrZpabne6AljzrVt86gKh1u1A76DRb4V8nPgzd1RkbMbyXCUes3EnXvyu/RIzktV9cGIiktuhx"
    "ixqklMziXoglPY/uEw/iJuLV5iunE+iJj2CGvlywFqbzX9GOmKkvSGW5axnZ2RYNNmSXTHGZWmKZzZCk"
    "OLrZYOidX/3FxNxrGC+6Boid6TLZilNZWCmhtstSiY+qkKZgtz6C1PSWvmmPPRipZbv1K4UjKzjsbzvi"
    "wrQk9GKGxMcnvMDTRchLgLujTvIZ7WPbEZeEri0LLlx+e97Hw9Qob64Ekg/uWVOCOrQv3LZ8ep98az9z"
    "fHjKCR1mGDCITDvazO5fOgADEFRVnE4M+ERWKlA+a3fghyRP651ZC9pmLVE+z8nb5PiU5tf9Ln7CEZmY"
    "GusHx8jSDp5oBTFUMY4iRZ5vEaIZOx1p8EW3h7Qhi+hsakQsiootWQWB4+gmZCJeCDjg8dDNJNpv5Z0V"
    "v+6YZiLqxN/vfsP4S5PZBO7TdkI2DAL0rF1/58Q2wMUmKEnhk2Oh9qScOHNz5M8mixnfQp4V6DgZvCf3"
    "M3J806x5VKnA1C+r00NpqU6ZnzC+oKBnLizJ4md5e5wqFELht7JTzfLkdJ47E4tZQ9q9B05EfCXXG3uA"
    "5SzCwrCYJw2Q8lxezfxP3Nj/cGPd//lnygmF/r/jxvDOYeflxhU9H2cnLYPcS6X3bnrY+4bVlVvUZFta"
    "hOYLaxv8vDS47yrD+U2VQrsKgwIXII3b+sMbym0xkLC1bSAvm8VAaIHv/E7jr+4wlB7jatyWZleVCRXe"
    "55HmIKlwj6C8iFlWU1WVBZ6dU2WV5MXl10YjPiDTicooLMPBmdhkVY4CD1BFJLzftxYRkEusuaEFA1IR"
    "75vjs2ZXC3wsrt94iipkvapZawSQMTN/iBTWTg4C9/ryQM3TNzOmpFbCIUKDCJhFVfRqDah3wsEcM+dx"
    "a33xF5FKPT1CH9Plludbpkkp6UW1YJu4hbC1GO6dnFkKEZH4DXsmt1R5UWCVRB34Y0WBjJLNEbJZNCzU"
    "ueJ4NGWP99vFkPsJwHAqRgGl8mQ+hwyt+g2kitMKLwt2khczivf5+XCsAk8mTe+HF6n6IKsODKpbTfou"
    "pBjVyZ/6XCUwPDO7DlnyHtgwZ3TiMzN+Ot1PwY/HQY7DvJAyDTpHRB1CU2i1sWZeIaevDjF88U4SlmLc"
    "bX2kxe7p4RljFQ+zyxHBkK2WQyvlJ6uCB/s7hmxOnfL43sylCokM1TnkRnOQvbjkLba3XypmOil/8AzH"
    "Mxobwvt+oolKVu+wLE0s2cuyqWwLKH2R3UQs6ShETN9bdIqP1DwQIlt0IIxwHgKYZnFwYKiw4cNfiJry"
    "9hVr0SkFhtjk7lei2hYNJgoWtH0x24Ek9kZWDGmxwxNEAwKmgXV+7sFvNqKJNeruxWotH1dycoNWbhWO"
    "AuLaEDUztvi2AN/lxKQWhKRm4c5pDaI0ZZ5CiqAq6kXb1St1eRB91zraPRzX6r+SfTry3Lvs+k3+6nYA"
    "OGd8d/fwEGA/iiSYaRiypOPUUemhaWO0n5QAosoq3Ffsz4dhHpN9l4tsUAmycq9wzCjq0QWVoPGPCVNQ"
    "3d8JOd3dj/+53/VvrKTBGjP7KFHrJ7bNYdJpFPxoWfBtTnRXqROlnE0/eJuyX1UJM2IsAj0EN2C7MXvS"
    "YWzFqdj9xJpvgdpCLavUbAuq52WLBO3mNLLS8A6h5F9IqXpmnDLqQ0MBbRFwuH9ogv4+ev4B74b85Qjx"
    "+eFlWMzIKleLSIgcWCW1r9Hwa9wfplIo57QCxb5M89vJVeD4hPxQIZ+t+PnjL+9OuFxpdV5QeuB5FlCa"
    "Sc0AAQNpBiAxLztXDD5MlCb9UEG0Lnj8tCBvfw09mqA7afKINY/oQUQa5Z8ftXAyJbnC7V2d+3dILM/p"
    "+fDap/B1D4Fa/2rHOiQwi3MsEprvi0I5cH2LDaIz4+GoXx4J0m0XDTdaUenZGNDjDB8269qf1uLjFq5r"
    "Bz/rV/Z3Cygcq1tqTDgzVvlq/cwjVmc18cFzjC90DaQpemcF05ftJv2jMz3jMM6lMD9mUHu/x1vM6gTo"
    "KFDZgdiaIvAnaVhbOZDYN5QWSmQw2qr0kxznEqV8E3wDjDDKNjx+b7y4LD32G36Er3fE+y3QVN6vnpYv"
    "1dkRDKWXBMVyhe84aaUwc1+uMqpbf8fmC7d3+UHXoRRjlkNT07sZls8Md832RX5zd1DRpWmN1Ayisj88"
    "EQKEzCW2nmO4Wpy4lyqXslXSA2QUs4ul3FxHsrqNVjpJ/FhBqJ+W1aKPZTkJpZEei4tgCn7CU610J3G7"
    "yCtsdFp1bWU4K4Jm4Fgc4Tr/0Gq9asrgzZJQE+fha0kX5vwewMqbz6p/UXC2od1955uZVBBtF9scDT6v"
    "UjN5JyhIotKxOuD3SWklKQseBQ3k1cXSGl/671Let1OnqpkhY1k2gOE7y8cC9pJ3ERSAIDzO1+LJgWxk"
    "TvshJyzmSbPGlHX0yw2U2PrUsN51AJJGAxZBTX2vU4MHcajVdMMjWDVUGxkV41RgHCNXNKYvFa8i+bkP"
    "N+D4TKv7y4PAXNLGLfbNq+hvK8IWNkV0VDKKtEubnAjIX7QR8DWG3wRcLNGD3b1mCPUsKQmYjs6MVOS0"
    "EAABg9V4OpWPBkBNRhSKWFhGPZO0E1/g00OvUxSzoc7juG7wdFVCwdgNwwuadAVtLCBW4GfotQAIS/9S"
    "6VDzk/srVC3NrnLQSLKrusKuAdzQ4NF1Et8fU47COo6ifmD/PYmo1kACD7Ycs98sC2hleud1I6m7VD9d"
    "hTlWxKSt5Lnu1TdN8OlBFCcDyv19Va+VBmgi1FXxvuSwj+WDtmYxRXwmaOKEEVVJ4CDUfWmzBD90o5S1"
    "t+f8JXXbRXx3jlp+3x3PVR03a7k6jdZnrF0+VYZ8NfMD0ty0U35eoWHN2Bwp9xBpYpdvlDnUO+VkkgGa"
    "IfRuIGGSJcZ52c8KB03y1fQxWjjSDfpIv3t+fXQU7aOre/aA3GuNoTwZdW6oeE1rQ4sjmeZOARjmMuas"
    "LEBNsO9okBpLYWOTOKBcQV1IYBjJALaZE+ZvP9vjEoY/HaZwE978KWeX0gJoKgXBP4ZNWYgLxcpvhbim"
    "D3QFirLdcYMuy1/AMpc1N294TDES+aF1LAknPgoNHu2z43TNFjAG4wN3p8pcSFo4c8J9KDFMJcddBe9A"
    "hThegTyb9GYEtnAZ7QXbIGfNdwQA/wuxwo+fAdiNPtRqBQQwCHSHesPFXSR034it1O62Lcy5UkqDvoxE"
    "afX90UcmZ8QY2huj7z/3wnLIIEL4PcOG/pHw7yLZDDkN66BDllFtA/HaPGO8DNFckxV4vi58orRa3OE7"
    "Mr85xJHKLst4nnRgbhQg3pivqXfLSvusTlzd1urz2CQSuLbUNEiJLzGoojH2B2sCcQRefa/5Ch+qZCmK"
    "KGdaSS2/nrO2na+5ZiM0GmsqerZMybFS2ChB3fUa0PhTSbYp6lvuacIrnUXvFKO9gcL2OR0n0/Xw0YGX"
    "J1AX6W74+3IWQxQErEH+Y8ERXQ5/z63/A/b+n//ln9n7Uv7bMa8HHKWR68POX/X0gt5++TOWP89TYxWx"
    "hw+i7YytsS4CqD9z0LfAYTmGleyYDtK0rSrTCVItbIYtt0VfIULJt53IYARXq12PUdn45Q2kKna1M5MX"
    "dSgUgKwrMce/wjAPMoC0BePPg6JlQZLWWQLPdVIWSmKKlD7jKzqKTFmYSVvQWEPb+L7n6WnnXgxVo3U/"
    "B6uBRAVqFWeJXeHvDbuNyoOWuGua03+y6cEwZxClJ0ZX8Ydiwczavhx76UfI+Pj5PlYZF/bKmM19QPdR"
    "Qw7Dycg3N1FLFNah0GjyMEmbIOiYsetrvKfL0kL/Or1rbN2k+2BbnzdlzoDYZ2j3le7nOXd6vRPDBfaZ"
    "WvYzA3p79SNZG/cCC2VqAGCYQxLd6KcK96yNKYYdJO4SvvYWd90E+6aURhigc+yxWQa9GewyvNfEbEO4"
    "BlgulEdnL+T+yejX6n1bULTrG3bUIFnOTmTq37M5Pup3PzUpHCDqsbL5lWVoHDWrdVBuM7aEH58jwKda"
    "q2Oo36NAxAbc6aa7d+sL7NVfhJcq9oYFaCk73ZblnoAR/stu/GWxQGqER2jPZX6//r9tJSytYT9nAuvd"
    "X4AjAmPqTatByfcaiUMzRQnGbdte4JCTjDUK7rwSNuy7w8cAPOlenv62aS3lfFskzx5QMj4DQWgK5lxV"
    "iuxn1r+Lry3526cT4QqNz4wGCxxbC/KaGTz31yHQZJkiYj3gWeKnejhvcN3G+KRtzqJEZAOdCfa99l6p"
    "MBBNR5ieKThMHaBLNIJ8c78/qLYwEHQZQpgC4I0v0dkoo+ppks35EGY9SE8esF2GXxspoR6aUL/EasU4"
    "J5Dsh7Ow8AlRuYMB42XS8rLw77qmaOHlRiw9b8LafqHtVmOOiBQS65WFb4dxppBTSfDzC/n5pMIfqbgl"
    "/nkjHzC4WD2T8VFagzaTk32x9S42MX56iYV2+UUB6J7lUO5eGYsxdOQ/SnSAUgFoIv79Ge/MYWOraNpI"
    "xwQKeDlNWL4fZX+TzgcW7EwIcJLau0bcyCb/K3urtd9F/OGRht2/mJIcZ5Ll/I0q82GkhGFOxBhXpdtt"
    "pJ54ZyxDwGzAjuiWfY0g1oMO0G+MJlj3pIo7LFd8hfebLS8pI/3cVvnLbHew9uv3qEz055Y8V4nAOxv3"
    "sv5pfdVexhXRUdMDRHx5JklTnT/qb5zRGe3mvi6DjBhEVK4ke1w8kwpdshqytse0S4Qtg4/ETMZF+ZHV"
    "ffkmgfMGczBFPWPpunNTO8zowWmsyW3I0hXXGRdHSwKm7UlDXeJ42ym+oLEOEdDk7QWThliRRw/Q/v7a"
    "R+6mJns/z+5CVWF0fJjijI8PvtgmosHl8hOQRo9tG4o+0E+oaH4D22UtS7H0HC38LXHNG0Wdgo/stFUf"
    "yxjntHTICYCIW8ZQWOr7hjZ9qRpAHPrEgTSvwXpo+M+k+GTVfXBRx5BkFE4Y/bzLcpffaywBxsjX7uD1"
    "fC7v2fhRddPVsrwKFulSZOV35bxobb1/s5CDVfOj3mOlZGp+Q53jmIfQy34sFYUxK/gH/gTy/IKkJ6Jq"
    "5Nmao2WIufawhbKckTnI9ZqHwmcmpMKYraXNHgoMyQ5Y62+tubOT/rMmoZaR/WmupSxeU5CYAUmWfMh+"
    "2/lhnZj5e13yl/6q6ihX+Zza4DNzwz1Ow1lVPzG2SkHH+1SFU/PAsOkDkTL0ruH9c3KQqfoCpV3e5+Vo"
    "HJ+DW7Lgi+YYrl/7MQF5YQiPD7NsF25O13MozEFG2PJ57RVCk0RY5OiVJBfL/+oaFac16vCYnfajCmnX"
    "Z1Jp/orCPIGjfSTpFO4uZoBCoCttMnHd0c1LmodFJF2Xsa6WIfP6ioW/s0eQhhJoXPBsDFNTAUu/s+xe"
    "Ase6Qsq0FiMxtd1KPSR4a69hk4zCoDGytJ902bebSm8lNJB82f78Ulw0Y3RmTXMQHWMFqh+JcjGL9Lvt"
    "tkjhpWnhYpgPg5TYa599PjY1LS6uCmg20io9IWRAVdUxXzXhIisjZrA/i9TbGmEZSFBKK1I54xBT6jzA"
    "QbsY5UEBkf5RO4Skjx+f4jWS5f4ZnK/oTX3u6AMGQ+yN66+QSkzzSS3WkTzS7nuzPDzdv2+Msr9F1I6V"
    "Z23CDcotaYiWPVMrKxROOi8NrgdexJPOI03psuKKjKXLwlnAnCo8vgD7rwp2N9fAqky/Xr+PKesfKk20"
    "YwA9hasD/C/52jkZ8Con/jiu1yHm7AnMIL8t2eVi/hkn/aWi1xREmvsjRkEkHnk/r5TQTVmJbYyUTuU6"
    "fvGn/+lFwYBRsCvWAX+W+XqiVWEgBb0sAUwQNGJKm0+OKVwtarTBUIRm41vnkviz08/sEz20r5dgrAJG"
    "2x1fMnktMETi+5hezjaGNqpqzihjr1AhBojjf3QO2+0SthL5i7zZCTreWPDqcV2FL3OU+fl0OYWS9PED"
    "Yj7NjuJMlVfbHZvvz9w4jQ/xAwh/MN/c8pk1uu9yv1/zs/M6fvFGmRIf2uC6RGDbENtRROR/MdIkuvcU"
    "ttNE76q74aC4S+MWwVPlrM9MuRZGnpel3mvAalKaLdgLh5857NFNbU8K7ZIwGHJv/7jnpep0RieSJxwE"
    "gq4wsO0vlhGhaMJG2+Uf1fCu6SMkJvCtJjFd0Cdiqql8ngye7Yjw0S8NTcJMJIUyhkU5O8iNfF5litou"
    "jZF1OUicAiOCwMsOQwy1oL+8PJYi6hOyHTCRSIL9WFYhV5Q3c9/Lqqjpo6R9uiV1J+FNTuh7bbg0t/I7"
    "S/cJkn3REfVkqHVNmj98WiKqFjmQzbzmB6MpQZxZr3gjG3imIUrB0oXocLoGVXs8s6OpxcduE2NIZFVi"
    "vojZ5pK53GMs0Yc8xkmpjQW/mHvAYv0PH+FiFlXkssbPb42mecXx1/n1dfnFUvomy00pjkp0r4nbv02T"
    "B4PhCeQNU5/c3Yxho7njVMU2HYdTtaL87M3nG7FPWv1gdvvEfZv6aKGrHzqYuC+eR41PUEBRaUpafZZE"
    "wihq43wctBfeNzS/J7yGqsTAXWC9yKsq5Qxo1qQNHnXU8BIa2OqUUt9f9OHZ0f37qwxtXJdz5SabDX7e"
    "6KT2NfSkVqpi2kKd5qTnVP7IEJ6IauokivuGSOCAWaL2VHw+1GafBpshoMVhRVmiARoV8IAj3UUCqeZc"
    "o4ujw43nK8wlPy4qP3dZnz5xslBvf9mOPuk3PvUwmUcibGicJnXPknTr3yYfkyr2e0OyvoBg5mayGoMs"
    "gPs6bT9LvN/4/qoWPxmx7hNkpQYNBs1jQVr4j/ar/Ou//I9/bue/1An//1C3KPzbsdLTKPXkB3DA9Rv2"
    "NYlY/SFQRVXBinkW1HH00Pd1adSg5dRDgcPFZloteLOlUFOiUuRWy5TaonV+82D1oth2NPi1yrjibhLI"
    "y9Zqmjzpsy8HnjtIxBdIplcIuRMVUA3YZuRwW0L9Gp1lMRbTiVrmZE1HcQ1rzchaQ8jxmypYhmcTTWYU"
    "k1HiHRIyhcU+zCDToJw2mPFlm2dnpR+D8Wa43GwWvkQMG3U3BkXMEGs3VwiIx34e/5bqV9obYyFPfB4R"
    "hu9v17C2we7Ms2QTNR7oDG6v8tWfmhHXg/2WzayH9Aq8fYQaclf9flD5hp6xIa4l5tFfH74W3Stj5/DB"
    "MgMSjZLFelNalk4IZpecNt1s/tiLusl60rWkijC3lAUkmNK5+GG46+yXOrTQ4vv8dKPqEZIEOydcfEr9"
    "ygksKZQxDi1Q/igjoyioQGn491WBzSWMXt7JksyDe7bIpTPAVCxjTZcuh8HhdvQGman15GC0dnpRGinP"
    "ziYBCp4aLBsFxnW52n9yyQNzsBhgfcPrvlnyiZ3jWRoVbnTCrU0krs5i/mdG3VOiFdp1HeezDFPU/CUi"
    "vC4XD+oHH7BB4QGRCvhaQQkhE56jqVHnOb2Q38TN+MMF/xTkrjswbX4VOeSRh5KgJXuWAh7Anh0IPpXq"
    "/jbSID/gbOf9AMTOFEGWrOe2v7IPKWSTHJaC/zWD35cqSYAEDBf2HuDFsuebzcyvbc5df2KJ50bs3nWi"
    "oY4YvMJeU79KH3+83t8mlyRo/5yrpyfBDSWbW5UMne12RFlN9O0RrZaukEoGNObiiXntmdXMDYmRQMrE"
    "B68wLJvtQgm9TrsClJ54zwYLEm0BiBYf43IS1a55iflglv58OR2Ng15WGoNxejWsgSTGigw96s9pXDUB"
    "pNj4M34ABCqMwAIsqVM8Dw35Vmv++xdi/WzLxMUfrd9qEonvwGQZ2/c5gFaenvueM+HQ4/b37/zXIl6Z"
    "46si/H6cjrPF1O0NrYm2SSoftYyfQQ2L4ByOK0etQB0/ojMa0muiyCcMc0bo2VDow9S0z3vk50prBCaz"
    "IrH+MZwWgmyxhDZ9xrVc1nziaRhQYr9agJK6BRTJJjbRmGYCqwn0+qyidO0/ywhJzixZ4Zviwn6fxPwa"
    "/eYyuiwKPiMYqF+UY20POnRoAWXeEGeohv0VLH2i8dFgvzbjZlN7jjMfzu9VN7/vgujMKKybrLjMiG9i"
    "XztjXqvbJyS9ZQR2O9790gqOzIHjWuKKgyT9hdrT6qrtUNo1FpzrmchZLePLmOHm5KVlmT+jGWa+JsPF"
    "hrXSJRkgv7MQy8P/tUzdw8mskU0sXHxdv61n5737q8EfdrNpTu0WahRBRz9dUBSn2CalGOyN075pMqZN"
    "/xSOIn6ghjH5XVEZBtV+yAczmF0lfhml6u/Y7wPrZAA9Pzake0zNptwV8bXVBKgVySksu0NiaGaYktPx"
    "HRg3MiaxdnUos3g3Utvrsf1t/cV+e07fvPQS/e+Wwy1sDsViljwlGK0/TGImW2D39wJWNwqAG2g3tXZM"
    "k/2Vn5Jv8B08RwTZl2r4RA7zeaxlxzpMnHsvcTQjJb3z7ZPCg521CkAae16sKxrtU4IlKE4xLFMrPFul"
    "jW/wJhIhtIjHKMNDLGp4sf2hLG5pFCZ4IhNzHJiA5RjD+5M8GYkuOJ6lV93PoFRu53a/IliW+lLD8kAY"
    "loh9o0HAxTh2rI4tWG/44UaFch21BkmWZ+vffdjP7L1cp9qI97plUHEzdoocDrNfqUvyz9wuhIGYDM4j"
    "0dpAI4sub7ehe6si69YrdnNodVa46pUZlTRnqB29F5iw2gL7PLvyi782lUYPHWocT9WjS+ul45lIvV7v"
    "aQbfEnYoleggxeKoPAknEngS9yW0I7acy5f/QepsvuMte2tWgjJFWs9thqZE4I67XKHHOHzsDIuyZarh"
    "7HpffTSUBiMziNdq6DnYjXypDlc6g0GLSAZXV6NlrZGyuP7u4TKiBBy9rK4RhFkDoHtRia7AqX72HyrK"
    "r8LS1IfvdNV5tel52cgqp5vMe2kqJ0tE0/HYv1joOLeSmdpAZIvNn0n0+4UV0YIAHlUS6fQl5oitbq0r"
    "aIAPFqdYnqJSgP0gworSGKWRV8G9B3ljJhPzpiJy1Y8yBSZUR+bLAwqFWsMXgFVLuu2/OiXW7cKFZBoB"
    "ucIH6kQTjFry8dWjbooN/YFD6Uva+G+P8OMjWlrmcOhBpxX3rJwvEyEFYpX9JUQxa/ch6//BQbf/67//"
    "M2WOvtD/L3P0x0S3E8kVUo3kQkbGFzewxcP72he+020Pli0yIeztKatUTCuug+gA9Gux/rrbOP318fmI"
    "uPDbKoy7aE0LvcZvLyG8KDPjCuwX6tMF6dOabXMWehpzdVvDAE543YuSpAm6gLBq7cr7/5J23loSAluW"
    "/SAMtDLRWkMiPLRIINHqH9p5Rq81wuwPHarH6DbmOW/Myiqy4Ebcc/bJhAgMrYvTgvEdLYbnoF6PJseH"
    "vZs6/ba0JGCtw0NjoPqVX7OJI/umFSuDhDJCyGSvOrG5hwxpfA2rbVkuYtwkPBcJdLp+jiIEjJpOAk9J"
    "txfhU91X6jaNP80KbOVATlRvqNkrRshv4/Eh5gr3epxqvwTEjMZvaAIdgoOQhKfUM5BcthbO6RuveDNz"
    "7UY3L5L14hGingNmAfmrAkjtB0WstE/K6CB3qo2d0TlA16Y1vVdw+mB5Jai+4GWlwiGIbK7A1LJmiNKX"
    "qCtK/xzD4KBkmZqWM5M5kPYFKh+81+NTOgiqGXCbctaf1/5Do+fEFjBya9TSjMgIiSvN3iU4LEOp2Aju"
    "8W9TZd1JmI768sY78kmi/hiddxPyTVJVN6yi9gINxYzFrcLbQaoaqM7nEEmqGavJvsrNFZcn1DG40NXn"
    "rrEqplTyKlkgkMcXKQN7by63TBJwoZAge5Ei1BI2zf5WUJ9OkvsKIm/9cr1pROyRKMw9QWKcUwZJB0dM"
    "0PsnCk5j7IgbxltU4KYe6GuYxFs9UCHrbs0Lu629WhX6lQsUoJsQAMcww9svjtfpLOn6N+lnFIVEVim+"
    "GqV+5lF5A2XmrsNs8SkGOnn5ez5vYotLR0S1FQ0/Rfl84MdYq5+lITrDhowfsLcAHd8fstna161bsfA/"
    "oVklzwTr1tYaKZyEaIi5zAtbTUSzsdN98y1OW9rXdjWOPeebUEUdc5m0XeH5cE45nNgQmVLNXD9Lv24Z"
    "hd78qKk1Ng1ZvbdeJgDIPTj9J+zXjZgZilnDJ7AfFJUcOGZVRgwRjXJD+1NIwdMkRXsy95iMrVO9dMog"
    "XIGH0OdgU8V2nTeb1L1unDSbCk7kr8n0asQrAaGrjngaEJjRQ77TDg5zBzrEAfyMR6rHXJSlvxgonK2c"
    "bKzslfU8RMowGgBtv/PgR3Q1/1F+zmdgb1VdJy6pLC0jh5UYh2iXutJVEA4odPwWPle7GbXA/5ri1DUk"
    "b5N1aYcfI2k/mVRq5Ttru6vLzDrApdiYPKUE4DhJ3MtVFwc1c93iMQd6OiS1HNeD7rVkYa6LkVT3a4Aw"
    "kJD0jhZUsio3dB0TkYOKI48bK918hewC6FM2hP6HUe33AagS4CGcuRmaVReJlBHzA21dJdReeym7tqiM"
    "oUQpIxpz8NyfBKfmvOt985ZoErZJHxOqpouY3961XMusQvQr8Repx6qi+sOGYg9zvxLOPSEfTc+QSkAY"
    "mZbBnqEuHn3cemxLfT31QEeNiejyIOEB9pbpFSYRwLycCrJHKUnHcx5q5GLpdJp2wdhglOxJrkt6lhab"
    "TGSPSL5EOI3cTKgUgFmyqjSAf8n2bgATeyoBpoWy9skTOzFfkeYovFbJSaSlPG0Rbm2OhPK17jpT/ID1"
    "oT7G9Td6hkIHGpZ8uTnbSlwFZAitH5moPMISJjT2aRuwkCLcsOl+9XSOFaNoFlSHHzV3qguHNsrmJBxt"
    "TAXka24cjRXF016vdqzqJqUkps86eH+rOlqMK0ulFUk/A1VlTnXZ5YDnHLM7XjCJdB754A0gGScKKuXz"
    "vY0Hd9lcM6tDbR3NjjWB4l5iC4Bd4LXl/WXPzueBEbNh+XplzcStiyczQehlLZTZ81TfVnwYu17wl33H"
    "4Qh5lvhpHbb9Bn83J5ztahi0Ap6QWlS45XKYCqbGVJLS9Op3D04eUZeX9D3MEhbXZ8OBk/pbFK/O5WmH"
    "SAODyV763COzexVeHUF9NLjwPKi1gqGT9Gr85ueBLogLPAeEr4jYBZYvtA9ikX2w6ZG6ugiU0G7A8E7F"
    "rHBVHfFBNjPEASgZDBe1//cTOv/4X//K5x319782eAmR683KoXSQETq4YybQO24536/rfftiW2K/XL+2"
    "xnGZ4/X1r5ZjRuOY4ecGdSCqLO783Ejy2PCzCwPTCHOvtOzntwiOqDXOD06QYJ4Cb0K+riyvqHl+u8GW"
    "e+o2EuBODKBar9y6hGeNBtLfy24an+2N+nQJgm9T6IjEBm9zXSInQwxSHGE7C3dZ66yedvtXguifhhao"
    "w30xIrdPECoIKwjg5MsPYDQeoalmuAyUnjn/Zgp4rTR2B3zDv7D/1VvBNaB7nId+x0wEj+db7j10tOxj"
    "jkqMhOkjI5SdyZVRNfkAGRfrmXlGLCtFsdGsdPcn/Jpt/eSRFoBfCtTDgsER2VAIdlqss7VN1gLLuJBw"
    "Yl0OBQhguVk8xfIF2pXUkdEvn7zOY9gDtMoXShqlSYiblNJhFDzVH1H1FwuE1ufjx6xSuncixM+UMzZ6"
    "1fvnIG4ik6cK+ZFuN535iA4qWKzoOMosYpEaMtPh91dasiTUobI1mtBbZ4ff52Xf3H7Q5TcKVsD5kYfo"
    "bQcQ20zlF68Q+SSCQK7XaIxWj6oiKcyFCXSyLJc5GPSjuAcJJGil2TQDwTXJIZixjNWB76k5EFO5zO3p"
    "hVXIimqkE08cs2ynCWd8Cew9efvnPPTblXE/+9wp/RDkGwIQ8sKM5wBoKhFMOons8ifNM9Gj65KwnoZB"
    "uBAbdQie2D7Pn+4H9ugH3ipcPmjFe4gHKMfGwQfvQEqS5DdvNR0KW5/4JK6VjuTmI68ExQ9C4hpMPLVA"
    "TrVrLwEUeREWvSU0lZY5jQFVZx7cb/+YMYwwv57i9JP8or83kcwhQ9Wr9uVuEP56QHKn9tgPwKvViaYA"
    "xHYke2aS50EvjjAOJv27Ajfn5FiyPEnhcy6eaQK+vbkx3kH4bgRMxeYdg8GifOHgi/2Ia+8gxKDvv6/U"
    "AsER6N4UXcv2kO9NEFNXzZFP/Ro5ig+m6rNPOSOD9+WWMarVGrVdZTbHWLrqZBKSk1ydEP9CbkjhW35I"
    "A64th5feSfhJujzANQFniqa9+1sXkwXZuTVpNVz9xcHPN4qqDRIoqvWlX/29zT8YhDZ1bLkh+2Y1PIED"
    "AWalJYpRQfhNRMyojVYbfAa52eQQRoFYjSBI1MC3f1sEX+T+Ux5sfpXd02tFnrisucFvdiIRY4Xk1wjh"
    "75bK9XY/nALzCnKPLSuYXjxO5O8l+G39tWzQ4Jz9aFb+GB66TOEPwKUiTEE0Oj2p9pQ60NzO7MMDOtl8"
    "sps0uRiJaboEEQgJCVtdhBSMdSN9nsaAB2qU5gj0FL/GiNtfbiVtgzoNp/GHoJPU8FNDPM/0aSYUUAtM"
    "TGl470BsD5lX5BXn33IyJdbYNR4i7zroOCm+h81gqN66yy4xqjhh9CnTLe7+AhgaqrL42KZFObI2FMIZ"
    "xPI7fR4gY4qO/fIpXZfzYFWAZGETbx+gGn63eZe92tti7y3I7KG9z8UjUhgR7ZZzEIXqr7EnwnpgHSYR"
    "GS2Bui01fRJYVZu5qZBZQxUdA9c+8kPGp8sVg7YKCVs26fpDJoGgzG5pbegNULeQ6sKIjN9iqjhXGX4K"
    "anEZiBw3BoDoGr1d7pO+P6fZun+pl4ZVdK1qbftgRuXn32T2bR9LL1D4HDq38u5N/hRijsfrtmE1zNDa"
    "Yo/3fUBvrTIRfX1HE2GAGU6aideSFoDujXk1Ct+j15hyj9VqikxPTdBQ8s06VWaqMe+wTAIw2ibby2pW"
    "Y0i9N/p+0UmwComlvEr7haM73DPpDVaxRN0T61VvMAaXFhOpJ8dr9fS+0uDMd73em7B1O0Enf3ZSfzAk"
    "PjNJocG0OtATRdNuq0In4+sp8v/WK1g9qcBIg862gSAsUji+vrtEMnGRHy5v/VHl1WHCcvGM+Qe40uwA"
    "ZPCjd9ekvCdrtgTWJEhTLB/M/1Ak2CdgBQg+dEboNo/XK5rm7PwGcVq41vja/JXZnbnY+ukBmiInyhZ9"
    "4FLdqqwDEU3igZi2u6m0V/8Z9nJTZ0WJuLu1kfzGc8CkRfKWtxE7KlHOshMGyjOfx0xh9Oe5ajdKQOSh"
    "N5wE1hcawTCgYeuBIBuZG7QM6BwhC/lGaR0lAjJmUrYqv1P20Hq4Xz0O0AX5ksq3mDvU9H/gqlm76/sL"
    "dOgPNRHAzc3cUsUji9OpihTJQmmRdIEPj6DolhbcU5EcOGyoR8vRBqOrKxyhlUuq7QCHiiM7IKuin4Z0"
    "hYqFPlGpoSMJ2VKhRUerR/huiGLRFzyNZgouRfq9LfRPl3L+x//8VzgIhv5rxacsvoLP9X9XfBqLMUGK"
    "sVjbR/daBMED87ddiftN43vh0q/7hY2ngJAufnksDTxAEj4+A5fX7KnXG2M0cQFozti+6vCbrFCe2tZY"
    "02FYlrqVruSrfdS4wEd6UIDCAqsyp8ilAz4d6pwVtmUjjqK2XYIRhWL5eUSMwldju0eye9YMcBxj7hHR"
    "ejKxifGj415sOJ9izvhMuLubWlv6gMmjE3rPstwhqiJeUMAg4tpGJFYSL6sjKrzEvzbOVesMUcPo8znu"
    "M4n376y/iCNuNntSxwHGa4UDzVs7sfYIqYZQgppyn8KYU58OHQahYyWlJEkMDsqpT0NobI1RJfhAPgtB"
    "EGm+f4tT6LIdt1OG5kjLVqk8fn8jWpDXLzppwi1zDkMJxzgCeI7Q1inGlOq4SHr+rUl847+hWuTfCbtk"
    "xQ5yZHJezr4wM8y0qzkp7JkrCAcTcRFHZdtzikOvti8MBIGGuT8kgWTpOz6gMECezjkckuihGgo/dZs4"
    "OOCMW5zsDgsBvcaCA5exM7QVa0LCwSIo9MhYIkY2Mp5KX+BcQ1YFq/MFt+XcJMWCSoo91h0CCLAkfUBn"
    "dBf76G4Pzc0ToCjLuXdh1Dxg6eLaRNhhAiuu3tRBmG8lQdCi+a1r+0aqVC46JU00PfR/Vb8UKLkBKOCh"
    "NG7Q0VICmAGGlJmf+tBUWVOi+qx9rmVqY/31OZP5tp9JXTF2z0bWBi9TkRGqQqtjdGTqA11LgVwq7Xeu"
    "e3TRy9HOCkyqYmrxj+Q/9YnfGGbUycB2lp6IxpoMa76t1xHKlR0ch0jnYI7SBKLYwxO2CCTnMPqzLaRJ"
    "9CRoF7ddOv+1QZ2dhFpJTNU93U9WWiYxrnZWDkSUTckHIIBXRopVPuB2zxCEN06oJWdSVQVWWk2ZHfmr"
    "UPFOTCUlbLVT8JiPonOQzARItmUI/loOhZioV5iPidEgjKlK206GqFLiVeokpv/midY4Z6Ky8JOrjL+u"
    "4lLafdRRqb8WjcLxWZZcvZuH0lo3uYaf7ZDLz8o7paoBvsEbQa4dxM/1iXn/iPs6wz8LyLJvZAynJkZy"
    "wNV2nDkQy+jmj59ekdHcrTyhm//MhOSJjMZceHZXnMq293dtRAML2ZFtSObMpXSLIKj+iprz3ZrUcXpd"
    "lanyWhGaHc421FPXKapV4d4API0NV/QYrrhBIHiSwTSM2mtTJ7EkqF5nstAHNrC9xvmtpVjpkg8Q1DJe"
    "8FU74Eix5jSjLyB+CpVpDHb4COprXDJm9hyhLwWFJNbeeTxd+M+YzRHbnF7k7GmoMBy3DDJ1Cje+WN1J"
    "tKRC8xwjDg8/G6t3ftcYXblY6NIbYj7c0YwgrKXq500TvGB9XkVoo/AhMBHup19M9fO08tFBVLqDKQrW"
    "Hwlt7pOVyaRD0zEja4jt5S3LRy+5zcosxZpz50NfrwwiY1/dkeLTzMnG41v61vee7MMWu/0v64r0FPIW"
    "9NaWYb/7YafUzZeVbiEbXCvdGmR96A4GeZQMIv0Qn9PD9jt3PyQYkbD81BFNk12wEzmqNRX1txiZICpn"
    "acfKe+XxqNxG++3dMW7LqoWeXBNGHPstZUnadGSFUTbCMQJQK6IX9dd/I10Mx2ENP44SNRxr+HX6lsTt"
    "db7DoD0rM/gswVAnTveNY95NUsv3AEt5gpzj42DQdJFCCIyUffiSm5RhRFsv8xUqkfT8Xr7U6hi30St7"
    "njhpRS4HlsrDak7sL9jnEAg4xgjvpWp9bmixqGl/tkxf17qwr4a2Ef013QvRy2NDOoamQKOaj4CKbNhb"
    "3IC/rpZwv4j2qwK3+YUXYqEiTdNoUyHffSHybUKrZ6DQHlkJMgfIqBLdmIbk+bd6I5BzdxO06d3MmQ03"
    "ByTrwHBXeReSf7tM6zM8W0cJ4+mR+OobyLUF7ZOlLUaof1/LeHxBoQid+lwEJ0I1iT9/zLCfYyq3NcMF"
    "G7o/U6YHCAfqw/aIw+CtEIOHHy2XI58m0fHs61gt3hsgybbfqs4P5yaik5TTmuVr4MK1zir1mRzZjqs3"
    "p8MkxqKWBt1oNRDNRp1/91EcAk6mWTTOBd4xKCKS66BSEqiK3+ICg+bn3Y/sInv3dy+KA+4I3aDnIa3L"
    "RaEIQNr4+qRZEUYDgVUysqcoKYDWx9tTBFD138q/6G4JjKl/v+wvGZoztnqboDmAPkhwkwNieeyZOr5S"
    "g/JXDuMhHhkYIwjgFoJ2B49fU4LMyoBY6RLaQrpvIK9+x5VXd/nO/b864r6J2+XBX7Z54uUAE3kgj9uF"
    "UKrdbD0Ntg0IEkGBRAIxEeTPIx/hd8OmdizqAheLXLwplDSV0LWZmrJBjlbK4cJJLIMNIoVSDPmsNpBR"
    "7MLM9mzJ9+w6/+S7pX/8j/+/+23gKETu/HPJAD7dD0jPZHpXLA25HFvMkB8qmsgJpTMhP9d7x/TNTT2n"
    "KJOitdswTU0+mZCBaNeVsGzlsXbvMu4L0NoncOvG+40B4zmNp8F+JqyB2U5k1CH08pJVhR74+ZyYcbTu"
    "Sm7XMtBhN7wQYZqobQkcPjlrHYpGknFWLYY/SufqQFL0NscjRTs+f7u2c/T5MsNXKt5o+Lm5DWk/z2MX"
    "w8ps+n1oSufcdQ/rWK/fZ3yQ8lsI4y70crSQZ3dn6RgtZWo8olggqChPgKlOKmQUcbRMcpzqcn+Vuiof"
    "SY886RrfoVs7DKOMjFGML00ZMY8zxmDjM2ln9qPQVKOjaUh9WHtixXurh47S/a6y769n9/ZWVqzMmGfb"
    "SqSLCNKeFLkewp+CAOyQykuoJ2Y+prtbtzT16zK7VS+mj/to9f4Kl5XXJx9f2Jf7MuAKOdYJQv1iuf3P"
    "JuAXw4VWfMVX2/LhPDRrPetqGtQQheQ0FU3ItgNTWLqEaetZVh0v8M/vJNgA5feS2b463zCILEz0WA0T"
    "rabGWTif66yDEmmsqphqEAKF4z2xC1R/jjiw1e2HHO2tfrSUthevkF2CnqjeZ2dtuBeh9UM/XCTxDe13"
    "s/8kGlbKrkBgjF8pOhN3gFr2YhqjzkCY0Xzyp0Dj7+yFG1w162zpsVZCiRGuGZJjgZT4CbGg6JsiIWjF"
    "+UKQEejIlN8H/1oDnkVwCcvohF4dwzu14v60EuyMWmsZ3pO2iK3z5rN4FUCJeZYNMClEy7MqYXRoUrLK"
    "PR3Wb7jBv7XMP31MzajBzIyx8L2w5ZJ/SqdY2lb2kZViOL5tchx6dDOHkmXCmxMGevKvRaiTn+g2qpRI"
    "mthrjMLUcV3vEcErjvKoGWg51WEHWYnYk3VSCxGWwyfB2JHLeZkrzM9b9vco666Na+iJyeD68FY+pUGz"
    "05ZyDAutg7SopvrzTQd7xxVnf+dAK4AosbXuCP7zBACT0/y08YpZJBwWx4e1SYSakqb3Cv9PxVTvKmVz"
    "cJrDX8uaQ4Kd2ZTUml6KXCHlks5HkqCaEbkJ3/dY1J3hVZuujoBqRsRaV9gRNtVQdbT4GzYzOw6lw0pv"
    "ldNFrHOpEusx586zPPrrxyqlItxfoTmMeL2E0YvbxhRyOA/nqxxVThi6voHJs74//mrridDGa8LNRWQQ"
    "3kv3Or8eaYQDDMv+mpi4GYVbRGPXWC1khM/CuubIrekJkVc8sZUp4tyZLyUjbIc5J92O3wwvn8G3443C"
    "UKmcBzQpE3C4LgJIkBWHg1YlH58//YiZEEfpiRg+iNRuzW9tON470D6AgoFdzkAyGU66sFzGw7plW/NX"
    "2tElTPB2uB+3YSp3TiAyVVRs8kb+HWyv+x2dbFKoWqLlwa5sTqG0NgnNF477apObGfrKkfB5sJtaGhkj"
    "bSZvjo1q1aHrCPIDZtBQV2phSMqAwytdnvinv6b454U3gcfWpTpWQ9UXdQgKVrT0UJUsg7Cq53rIiGu/"
    "1RYCAbN27YXl8EeraPqrTuWV0V4/mfpW5p1c+kmTIz150AIxhd5cXGyC/25sCrzWSKQlQSbpN+gHWFRl"
    "2blNWoBEXC+CZma02dnZAQCjT5LrPFXfk9OrtAosElyxRZgUOq7Ow8N1yBICueEZgS1MLrxjpVGKqANx"
    "AgLzWJ+l8xZewbW9r7TiIY8tlobhiw3CQ0XFYK+SJm5yIM0XkYR7OvO2HnntsEEVx+PLqivd+fFLT589"
    "KzbJF9KWBXKfWRwAxQ+EO8+NP8CY9gNq89KNRlP7UDhroksrXGp0Ub0ePV9FSHhPVhAr6O88eW1pJ1ZZ"
    "PlZ+HxUJAG0EmkBPjWgB8lonBHcRR4CJpFuqw3U4c9VQVzojKRcLyr0v98ssiy0s9IOSxFMh+ljhd33n"
    "IvHhPxiQIJWFHwMPwf76mgfw27/p8+tY0WHGDpsG7z3ebjgsfc+zQBd7xZP8dSqe3OANopNusv2t4kHy"
    "2RBkN47g6D/4e5bUn7bc1zZ5n6KwaLfsCzuzkJ94gGO8UwC0FJv2oavO0a8uyRp0Rf1wC58N+AE/Ep3f"
    "qDa82kovuBr7iiQd9C36JADh2loBfp8aIGAUOb68RhNUAVx0+BWbqfyQWC/1awV17fxlp+v5LNoM0qBH"
    "xdZ42zbYvR3/gyMMZf16Xz7AQS/0E1EphJ5LIgOt/1DvnDqMNxXQ6QFikXvu5KtWu7gsH9SuDrGp8vLm"
    "RgoFHs6XrXZZ5u98pq2GlPvrfOCzv8FLrXW6Dv4ZE/3vf4WJ8P+2L0qKPcHnisAxssH1sR4DXJmiqwIW"
    "8uqNCa94ttp6XREw5DowZZGv6WOMu29TIkrCFfREAqjs9/v9mAe0hZ0vmZo3hByn+uIWRNnK4lMt3LPY"
    "T8Gui2+sUZFkLHoc/M9V4WAgVDN5rXcoqmD6qKqcAokXULroveRfe58VAWDfHwPKObX2LRqEtcVIuSXc"
    "+yozYctH7MkgXeaLT86JN94H7gpD41eUmJSdkg/cCKmUyPrvV55jFLFuNJjqlym5DBDlaK2Dxb6s3lOr"
    "cOulZ4ol8IlGgLDl7oIMzgkZ9Scc7v2mxrSHkdGR3iquqA5/nRA95TDzREcXFQeEbZ742H5X/0YjFbp5"
    "NQb5qSccTLfDQ5ZtR10xgghYGK0W5ISqBdxFzJ2dkdXnbzcvGCHq0mZI7mVz5taqg1zAayqyw6fdVty4"
    "OExjwjWkCZap6MoHFsIwKO0A2jjI6lpuPPdbc0vTZbRIMgAwSLyDkBTuJREnxfaoLG2aV/rNVJubAAZV"
    "Vbzd2OKNLqPB3MpYGt3BLbC2shth9MFaq3gqq+pkKfdlg1c7/jWIO5Zi1Jmt+VeXpaiJZnPhGcD7oK5o"
    "dpCY5O4vdrFGSxQ5WyYuoNcIDYc6erFnWoFMJWS0RwvMnX0pbuxso9P84B8kT8v3celsHdoErF6XdFWb"
    "Hmn8hPQvtpcGofV0YV4I+bn17oNeWXM/g+0b2tmqpvBFPstnI2AE3aePHG46f5VAgbU7JeLlLlWV/WwB"
    "/E50rhAqAL3HmIBEJmPfOTR/8odrGFdiB5+9t0a7xTeFSjgJVIdnnQfRr/tEQ4077Q/CLt0xrkcMj2rL"
    "GyCFdeD849F4wPWLSJlttGP/+6FApS3D3AuDYMpHAEs3EJRu70ts/EUaxU2vxXzD64kpuTuEP74xYkGg"
    "vz7j/kisJvv3Upy//agKYntuN1DWSb31J0P61nCE4PNS0weQDBZRB2eFY6d98suFovY7PNvGguCyGTj0"
    "/TKCVYVjU6MOPZtFqGmLm5yNKoI75nP7HThQGu0vtv/abjQ4l1K/cH2ZT3K4XhD3lJcnQ2ieLPgYMjE0"
    "h/CYMaMUQjgJp+ymjMfqgOpA1zwe9GQzJuNl1fp9+zVawlA27OUwXL/SA1OcYIbzA6dB3FkUEMHdBk5+"
    "PY2U+Ovk2xQSeLs5Wad9NenXUB0XqH63Pa2fnMsqMMKrNFYcsOAVVJPNevMw7QG9xurvEQRIbKWrv8G4"
    "+XHxqfxqE2D1dWZ1dUvgzblEzlibTaKdA+DZcBpKsk1NQeCGdJZfJrBZiVk5JWHrUc2H/vwxpSRvk8Fy"
    "JuZpJO43YmA4EAarIGbX8f5Lf24wiO1ByCWeIUjO/rSFruiIm3+wMAjH8SmZj95nxyL+mFCyGgcywqZ7"
    "7oioVCUQamRE7RursmFPd1qBxxc5DWOq1S341VcoVEr2UHe0gEadMksB09yP29gkGEXu6wn5SegdnshV"
    "YXaWEXgLRxZPWyQnq+DoDHGAgBIodOAL4v5AUVnfBjOIY/qc3iF+246fcW32n1wyz+ZrbMXK35+pwNDy"
    "OsRYdrvz8epQ6WvxazR1r7PGJWnU2HSkWthHQgE9FIYL8Lu9eGh1dRz3421zuiUAtvyspsNotuo6BJVf"
    "fdvMP4vL12y9bWxjrmMfrqf6wMInyXvN21x+r0LQ6imyuJkkjbc4tGG31432BU4HeE9wXmLKsOoCLVkO"
    "EDvkhXMmui2vcUNF1rA87KgQF6jvqDld3NGB7TL+xqeIzWrnQqJay45EsYPn052Mb2M28Jl3xRznbA5H"
    "fqCOkX2OgwDDmSHlMfdkXZgvvJCYiqegH5hRoL9KFUoKTbkZ1ZqfAQGOeTeqE6/OGLHa+A6kIBDweiKF"
    "GRXmpbIjfGAKlWzQPHxYLOxMQJQYzwxWxbj41VJlRaHxaYQWPtB/bPrZawgjYMIEAewzkv1JJdSw5GmJ"
    "37QB+yE/ArMkL0nwijgd+J+XWEB7CR6wtMAxNK2LqtxntfcOwuUFovvIXj5dsO9d73IevmrxAl3rFUS+"
    "JJPVfB5cPJIVT5BlUY1+5RvzuMTSRBgjnOrvufkpSBW8u0GTXK5TQ6RI6KlrJ/Dwx/JHZ1qzGZS5K+dj"
    "rAQABMLAPQdka2ZP9AZL/Ewe8682ELKCOpdk1pEZGT6D+UCsMdL/mBZylFZoWXyZg7A4U7sTAg0F0fUN"
    "aReN5AWrxpgFnDFHlanrSUlYhPyDNQkB2qbs2jblRujGcb+UHkwDtGw+/SZyJKPthEx7NdspNB5hgq0a"
    "vck/Gq1Q73zdjD6Kk6QhHMjRFkcLa+o8sTN0UFJdtXU0BkXhC6aX7UZj2hBk1Gnx/Doo/XMTJ1ZPIKT6"
    "1tDIEUK4R2NTHN4Sc4HVTk/8s8+n/v0//qU96v7b51N+2GTI30p0B4zDG+BnTNTELdUOnNsRzLVxAdmq"
    "CpG6rqV4pBHLvTWIurKIUnzxIgxBXpIUheBZPXcTWqr3Y8L0DG4F3Wbxcl8gusuqWlQ/wjV6g+PGJB33"
    "8/nr5w9akbPbGXFn4aRAOkXa2ocFkOTzcuFeJUVX4PxY+rd/V+xqrrsl+5vEnauOMOsekaTB2P/5+v33"
    "+XNhfb3KBFCEs2Ic7amJihBph4VMQ7c9TLepRF9xwo5dXuB5+PpJ4nrZ+WuONY454ICBkd7RbIH1k9uW"
    "sct0764eZGUsudpRTo6KII9jEGK0r+BUlk6CQ5VZYUMmR09Fe3HvgX2V9jXC209Vul/dMPx42DY5meIP"
    "lJPXghSe0X/drzFJbPXUAOuFP9RYfdO7v02UMQeD/p3HEk5zOthWq/5KIB59nKAE5RDBmq1PtuYZLjYc"
    "ao0ZoMxV3FQnUZls+UAyPQlnEoZpgCzClogwkjxm2hp9EIzz5KkEVlQ1V5J+DskLynl53IifBsPIRsUC"
    "x0IsCJnvtuA/oIm5JyP/hEJ2/+6T4LLxJWy34H8FX1M2d3/7Jb1XzBh89WZaSTINm8WjIXik+ZMuBTT3"
    "0NdrAqa15YcGtKQ3wC++ZO8JLiyUy5Jnuj/jld5ZeGVSLObesCYEWfZdg4voQyNgeciDuZHGiILFBdh8"
    "w19915xYbmms5H7Tb69qgiCzhQgJjiOt5tMNcNhC1k/9aFOMYd1i/t64YyS89sRue2Ol2Mj8hX25vdfY"
    "VP99zv1Hi79aNi24/4VNKxPA8VuFBN1JAAQVMKc6GACrDTG6GKZvVMqjh5ceo1M4Lm9TDWqmwHFYuSNo"
    "7hvH8EH/Jq9NeXdmslPCNC+gvtA0/T3BwtSjMvLWmml3vUc9niLY9jO+Dc9dIXdxriIof21bywbgf11F"
    "ZXUpd+9hi2OHWT+tkH48wjm+LuP1onZEBNaJ8QBCdBXSUHgimT8X+JakiwYcGTbutkmZk+u43+TjjY0M"
    "lxPEnC9T1xfaZ4GIgXZ9eXPgTapbobOkrPqAc6FlZPHehzMisSdVOtwg+rVC07USxwi3qTmJr1ZDKF7e"
    "mupmvnNp3tw57KeE+I4l/s5KY34dcXI9hXunWagf3fWtNjPHvDZ2xFpMl897bCZdq8Jc/EfbXoexgESk"
    "DiVDARJyLVfijNDTuK3Kpr62pUGgSPrT55HgdVD1Mn2V+6Ns6q4YT3Qmn1UBQLJXY91gCYJ04WU2dAWf"
    "Z9E5G4ZTN560meG+4uz6gp59oCRKr508KpZTdL4OKsBUspubcJy1YvzyTtxKT5HtBzEYm+trzqZaFLAA"
    "Yq1HXSnubKbtt9fSD2A/FCg/DEPJcMWEXDbgG5h2acY/3Xj28xvHN1JLQ/M95PUiqxNrn9VPwSGenzp/"
    "XuY04IGC4Y5nm65YgMLjHC/8Lqr0QyUfqAZ8iqkHMd8rzHXuPELqOQHjMX2Z/aXft9lx83hbLgBmEcMB"
    "pIbmOpbYr7d9jmPBLf9b4mg3oBNVLyJlD6B8UeUYk3JcUMr5YXhhxtnnOaIa49hj+8x2fTPxEVVHtIxF"
    "imTkz9ze44Bty5JcHwEQCU9A+GrUG/zigl/MzczgfBmpfgfJGS73SJMRWpLGMDSYx5Q6F6Z1dTJBAVIM"
    "LQ0gIUL6vGk6n5+L6Vt/4z6JPiRFGo/xjPnRu/oxbVhDXONcXucunnv58faQC4bp5WkJbBtbklRTm7za"
    "a5NGmyoV0UG9YDnu1efDpsCOb04QBKoHp0CjEBw+eO0LhtcEjtzUviCkD8aeTIdlfkhUKe6DFbuZ/RFW"
    "9+JRQROxo8x7gCzCtRVZWnyQ8h0TZKaj2aJtH0LBpHUvUsrEdg2be0/uN4BtGVGCBwg1Wlkk1/jW4IXU"
    "bWuP1ycCSu6B5TMfr3GgJH24O252S8eWuluauDwBxZgi32D+2o3LV4R1LCUJbXXNOcYbhb7Q120D/23m"
    "FCl2+RXwAyxZGR+/i0PQGFMriN2BFCH9EGAmQyQc9sLnUrG39R3adI8HshHHLPqrU+ss27A1RjOsgNbY"
    "odmbI+OVzd+xfsI88tCURoC2bJ1OQczR70HwOF9UVBMAe3O1uaNx/rILTo7Uq5c0rY5XRLF4W39bPRfC"
    "6J8xyX/827/CJFHwX0wShE1A/DHJSB/JmhkJF/t+OnGVKiJvdbWg55wo2ZjVARNCMeDemTn/0kJFDQCR"
    "WYuqUvseXz7N/ZpyXCL8+RUvx9vYbyooDPR5peEbJM5lUEPshfGdo/aIThuJgyRIBNsu9daLxCWJAiYI"
    "oi+S4M/zTjCgIRl1UL+vRhZijhoPk/PcWatogeYLo5zbV5h7V97I/eQYF6NKJuaI8ghfHl7rPvipyRYj"
    "QIedhsawPwYWOCQrCXbfEI3g0D1kWtZhaDtDzIaiy8MZXzuEbZClDySOr3l/bRoHfQg2y8AR/jReSIEL"
    "jhuFWXmYoAsQMZcUGKz+Y74tbnzateoobA31hU4eyF6UfdlJPIYyE8Uh3GjdG3/1RLdf75uL34dRburQ"
    "B3XPagTNnhvV338YzB+zYj684Qu+wFT/eRfBqHvQVt1cG5NirDMOMw19G4evIX9QVP6bhDCQW5E9ZC3L"
    "RVeJV3Z3xmX1GurbMlsXDzKTs7CqTYnfepzHVdWBcIUB2aiS4xjIn5RVxIjZTacQE28Tq7cKFrIPUXQW"
    "ws3xvuBQD2YfAKxMTejc7adexddZw+5vcbDSRjOcBqC1BXaUOZU3dmdfx9kQsAKB8X2H7UeIjsbdAsVa"
    "aqMlkzQNA5cbpyP8rd7VtGtZL1Ogv+dNNpDJOglKgxWAXhhVjfx1YhRXZVsftN+Sjd/8QaFEwf3eMqix"
    "4yyq6wHRXSq4pNid8VD47qsQXU5P5FKUL1yWRZdgAShzBA34ntFZ1N/l5/6KiqR0DGkBx7Q3pJbw+ngC"
    "8nkEf9tsBrBfWC3k1a8+vGmSY/6e8DTPSMg5Tqgbhd0QYnI0g4XRcl4+BGW1isQyMaLAL7PcRvWy6enf"
    "pBoEsOUfrWIwIrd9+kqtwU/xgu8UfH+fNnB2shgeHNiwl+napPV8zxGYN+7q684R+s95m57rRTlbEU6A"
    "/NL8mex0ZAMGzDgFVMmP+WlS8/OhF0HFcL57E4LjzmBOHo9UvPevU1R6oWEZDgo7CLPIYj/pUGtCy52t"
    "tGc1OKyRMMkF6MmqdWB7jlN8Po7UooesBjJAaIKASqgZyPRDWNikmXGlJuKILuJwHqLxnXt7I/nG7Tdg"
    "i8hFDovL5DzhbfyW+oj7kCLqFs07v0UFlgpgW8QuaOvXyxiGj4pQiK8DcBZq5ZRJUNg00OAtl9Y6AjT6"
    "vV73jRwGxRuUecnaBR+COCKobu8AT9pvbXL2Hn/TPtzeykXt3P9Ur82Xr/GAdmliC+ruvE2jUOgs/AFQ"
    "IPyqG8I63J/fVc0g/KLi1RWrREOIcY5yJzZZHeR9E0Td9+98VO8IgDfdpTJxCFmN3Uzy6zCvifeO5CSf"
    "8XkZfCAp+Qhqq+YNG/M2AwImjsh+ETMhQ7ouBDBOadSD9DtYev99Vbj7YdaIj+Ly2VFwWt46Fe2adNIj"
    "KyQbtmkzzPA9kWMbzH0wDdUIAtwQjrBYnxbfq2CFAtvLsQA5fstChEd0TQKDtzU8U4zmnYYfbiqO8bXo"
    "6WDPQGSJJ5lczpevNd23txnBEL/yTJB+FpkJ+050g3YR+r7PFGi/6FNYstRqAOMRBKHGQ7ZRbzsc+N9j"
    "EfiUSffLWBmIEFm5vdBjKXg5f5xbh98GMF4YsCJNLMifGzhMbtvDk2bdhQE2ud04RVj95AVTYzIAbuK6"
    "9nlNR2Pn7TPRf7WZHoh+R22JIL+Vg9io5YksoaPDAKuSXjkWsUM0tTAAFR6aYW1y9eTN9SfwZtpxQnKq"
    "D5aJ8b9I2be77dAvCGB0YfP16VQwXQUbHC7w4ZusK01XnshvvVSCAjJzoYjSfsmh4OetQF3oED/eGn/5"
    "O7/SD1xFwKvElyxn255nUrOU2mUKk/D4qKpSwSmxrewQS1TARQzb/pcEUF1b4TdrOtubdFnNjUS8FH8f"
    "7kz25B3NPtndjKvb9PPyGdytpHVX3qu58vxxif57DkX6XiOGhwS0TtubN0L0DXVHcDwTRBbo+lAHpZ8B"
    "e5HFDOOmH8A8yhtyQ5TLHN6hG6iT3WR8kt3A5wYtnq0R8C9rWYzAEC9xolsCHEO4CCtS2VmT6m6OD+s9"
    "Rzf9GRKkwFOp+4HzR+/RdPPFnDjq9TTOkMbWN38+aJKZmf5qC/UOaKFjlrc0AHjUm2Pwbweh5VFFDQaY"
    "JbuLzqxWLB2HyPexH1pIqWgtvt/j5QyGSDfIHt9Smsg/eQ7t3/+VFf8n6L9/53V9/lb8hzdyRPkDNaKi"
    "NAymrgnDIHgmjENNpX0xnjHO/hkxmf6uyazQhof6GeqTqUsqF/m6S6btb3ZC5mmljKFztY/A6PVJrR2m"
    "KCdkuOwQx/iIVDj9QsuGk3ReFtpjW5zQbzuuv9p+PfRShcCW+jmbNAYnl+oSWyYrMLycILn7LLwjGflZ"
    "d8rLoM4b7swE3dpVFH6yDbAnqyicgKGtBNKH3koBjL9CoiQTfm673E/fTWfHSMAue5/S7/6zE4Q5OfAc"
    "Q9gDcjRilW9KJCHS0CxWNnb9rCD5ThaqbhkmbKk3zJdK2NPDmTIwklXwp6k+I3LJFBpEtkuhwFQstF9s"
    "4IMuALb9LWl6qW3tCDmlb0e4vByUZc0ILtUYHd2T8ywWULX1qQv1XHdSYn+F64mVpd4SDeh9lIMg+/et"
    "iPfRMJYuNiDVrChbIYdT4Y6T607z3L295LIBEkWK0NkGhpRExgW/YdA8etVzsBt+mbqyKr2jfu56jI8N"
    "jp/hYwbrlCiF4bB1H7uMmWt/S0Hq3NhnPUK9ga3vqavUb6ArUnc58iSF1BmQNhb0geGiK/RTA0dopiqf"
    "2jfCTvzQlmOp1/dqfmkU1LkGU58frOZFXmzxweM4DKSdLWOwFp5CRMbvT7hPZ1DjLQjsDGTQDiPrD5+J"
    "iwVXFFS++Qgcx+kc9bApSqUrvfPKxtxY9offZFWtT7qCmgvQRcjLJFvQv2eZASP7MmfACdlxxbdtyZ7o"
    "5ueLkYQXo5jaJJxIw2+2aHH1Ag/9Lq5Dti4Ep/PtyGMz/NxuE2CGkrYnFHm+YmwpVQVMXNeM05ShzrRA"
    "7BLGgqLP2+9AusGLRmT9qs0Au3z3N9VbGaws/FezfCrAWPmnLU+sYIcjJz4keSieMKljz4wk3aGs0Hr4"
    "NzbyQ583CmPJVIlGHZcwATdcI0neyRqAx7j42SIno7DiN1R5sFu16nPoizbvYOCmc7o+i+3U4bf4CLbT"
    "VWs9PD/2OdUvg1q0wGfyzWKOQ00TdcUsUkpKfjNNJuQdHorLTURO6vNXy9Ssc/L1wFrTwBNrD3DMyWRu"
    "y36513d/n1schlLQptkfV4ubBNdxSnh5r8WnEAGmW5HCn8QxGRt1WYAqEIqjP5iGQ07pdM2qocMH0ZG6"
    "q7n6+pGhcNbr9WM1jKt8AbXEtqYeBT4TN2qITg8EAeJXZj9f1Qq01G5ICX5b8v46kuKnxTVitzA7vGFp"
    "3KYboh5wK+RP0XeLha/HvGze5uYsEjnFbV3NZ3V3uh+BPUmWYwJ31urOuDjMCY3fz3/4b8WouaP64y/b"
    "lvijNj+dcjnJYaGdu+5WMLhYfllQYKwMcGqHwZaTrerH3kM15hUmI4VZQdhs70XgSl+hYtwAYBi7ZY7Y"
    "bTafW9trXIX2Fd9tPR08qj8crEg843d/d3JIfuJjc0hwp1Rr7m13Re2w33t69LpjSmX1J5mRTz1fsZrp"
    "K4T5TNakBCxXyzj/k3MI41H9b28B46p9SN92x8u7U3zH7vo9SD6x3BE2ZxieDsvcY4GoIipz4jscCSUm"
    "VB5IQgnM7CCO6ld23c4RrpBhI8aj9FjLVdJ6DYXJ0FWPpZuRhDhJDaqTsTjHQ8qHTXyXhCvKomf+aRZ1"
    "uELCMD70uREh8djFvbk5UuqU/6TCXVCMyAT1san1xE2E5zSY/5N6npp+Bcll/kAFjM7BRQoJsagCZN+r"
    "8ajbCaOJkdKlKss7X92gHVP8KiyxyKVF8mwE6tAXGArhzZsMBaAgBc4SyGPgAp/jRVpfFKT1TrUrcVEZ"
    "KGZQtub92me6sG4IBWk8DOPMs3ATh2Ed/ttJ0+PaDNq0mAkmmrDd+Ul1ePytyTm3EijNE18q1lau3Jbc"
    "UICobsIpcowy2wFCho7vI3Y4Gi52w8ypYnauvFXNDeU4+QnuGugrnSkEnAOzM5XTO2DX8OZ0uWpXOlAr"
    "3VfcIPJCjpcKkoIEvOT5qej/w9l5K02orIv1gQjwLsQzeGbwGd57z2uoVFIiPevlv6pSnWQnO50Ahu7P"
    "rAVNc+i8ipNY5Bk0/Z2HKMwO43zCdcCYlolsYWSkhWcF3L3D89tQz62d1lRKRWKrKzucTDxy4UqdKhOH"
    "LsTvYThAc/S7q0PxFwjfYmMAUR3qFqZdoWNETlAw94LJSFxyih3sKeZGdN8IXZdh/eqriJVis3Hj7AT3"
    "kKd4G1SZy+8JXOqWhJg/pZXBTxnOPjztQmx1LZyUvfisSeQcnMkXAW0pT2tF/XCyT3ULgOYnDCcp+oDw"
    "CTQ//JSGfLpNlHx7l7QxQkKWWrzTossCB/O2GOaKeY2xEMUtY1uaT2a+iHIo9N56pk/w9qv0HMieXRAk"
    "P15DBgUXiYHnDUV/ZdfA4QUKh53AKuZvfG0b/72mZlG/CLUJIEZ41mmVMJugmO2yoo0wbsQ4IikZQpGM"
    "dqSNaT5/7BGiWUUfg0r4Ta0cvBab3TexlouM4JPjlQaaw4VXCRfsswqZIxKGSji2wvBw0dDepRiWSSxm"
    "Yf3shrU0/UQz+a2+WK3swwhw+XGzWh74j1SzLuP4Cnu196A2QKLrDg3joMIXdA29J6qCzIqWFSM6AfM6"
    "84ULgKsv3zckYvOPB2hcS0LU+CaDm32sms/0p9tZloeYLOX8hyUUrvgVqUkgEJhTGcprJGoudq8dpQZs"
    "XywU8S/xQw5uHxJnecAo/znokd0fcP3sHm8MU91+jFhmbLZhNptJ+u4j6tmIenyzKwhFSmCJi7/Smwso"
    "o1L+tt9jWOQzlo93byImeaorjoXfqn3FI9+2Y19N4lE6l0T8IvOXZ7bqFg9mKlFm7jPSvbyVFOgfTTXW"
    "TKQoAlmkOD76PK7Q+1dTVK7D+kfU9kknFzmZMj1/iYRsNkChEWcNcIUDG+syrsTwnQOHnDkYS5xc9Z+z"
    "tKscnPVNIcmXBGAaAsl9TaUFaEEx7z4XEUxZsJwCutF3kQyHdW/Po5lXvBdzJMR2UQsH3YyZtgMWAfM3"
    "ShLap0BtiHmEU1EYBwgeBShzT7CHk/8tVKX4RTTpVAee8eIOnwWewFv553cs/9e/YXzjP9f6Y1fmfQcA"
    "XALEGvaCwK8H3zATQhO1kpPY7TicDZtYYPb41mH+Vyul9zkvy6wdqy9N6uZZEaf02pOvtqqamGJ8ppxU"
    "HT5XiWtCp6d5EzIjFSn6gR+CwgMXGhGI6Nc4jLtADhrfHh2BYEHAIEJv5zZx35DzRUpnQmDATUuZEkEU"
    "bfFaUwKiGd1emAF00fHtUT+G6JCWtYkurZa5+grqr5mTcHYerx+qo/rBBcyHTyfRA5J2KgJN6gYl33Mh"
    "CSqdxXz5xSWk9KoCBumUKqvrMRvTsiUl6EoD2i9CiX873mwClvpAP3KfqrINeuBBd3By3efIX/SWZ4Zl"
    "9DncoZOgWh9Qg8KAMkurMkY8Y9AgYVjXQf9wRDb3Q4yJN+LUp6blY6E2etv8cj++TQ9QnS5aZ28TC1kw"
    "fiuv5inJN2SwiqMEWW4ZjHE/fcL+mL2eDEU10AACTctc81wtVc5701UJSGlHEw6U3unrmzn1YT4nRScM"
    "1LPhlNB5vn2fJYO++BRKslBeUeDfA6ZX5VhKJ2WYGK8KhWkPnPpr5WNg5K9DiiC3MlrvR7jklCHeh1yD"
    "idcNb3iVmheJW2yisokm9Bs2fTwL5FYrIz/mtiV7VEoCN3ZBw/lK9fplf07/VPDcrSk2ektbdxsID+mN"
    "uJcBm28VWRsmMgwca/BVg+mZLgH0R9ZuD2HZ/gg/o/8Ze+6P/pKkMulfzRBWR5NYafZbdwtKNNgBbMlc"
    "lHsrrcBsfh+/2JcYRpY963cw0/zkg0i38xKtbY9sT9ypDM0gmYLTYFN2rm/lqaFRbQ3ST/6Z7ONtxfZG"
    "IsTdH465Rv3KL29zQKBuChJUq6JPyN/do6NhakncTJhbhaxuayf8kk/3TRQyLihkWpNFrvYMfRrQ6aoE"
    "1oRi3BvAjmUKgky1XRZvevRnhXsE9U2+pX0k0gVyLz016OjDSpMP+zHElPTMqEI3b3IvFWcjNRb/3ifo"
    "v/iaWo1ZqX+LCre2uRkeh3e7TG/517jxPeRgtxGUAsHSF4Jk/Q66J+nX41N77saoDHfeE7gY+CdZsAZF"
    "5b5OgcTrfhrqkMt9XKsMZUZFwIB7fkamq/jv5zftAvxDm+Pbfn00f4785XYyUJMLaub+JyC/GGQM5nPy"
    "hQSMoY+lAfkETl13zd4ts/mbjC91IcWHBoxCcS9s7Mw+rQdVCXWTGYdym1pv/T2FG88jRev0WdhAWy/Z"
    "m4CP+7PadB5u99Q+PTGfhlXOulh9IELqo/iyOvAh4uV+ywpEFvrnq9qcg3TgreNrxPOGihYq9rBrC8pQ"
    "ksBBsOj7UEFnJZTjkgzdJk7DUKhXh4/OgkDXuq3uKOR0lUkHvSPUq0TekUFt70VxC4DEM96kKUsjlRIg"
    "Qc1Hh9vP8YZsVgSiMMBPMEBUeCS5c3KEpgu86mhxYSRGf0SJ7IdzShdSDJDrkztPMqplWbGn+NWuXA2X"
    "bmmrmPqRAXHn5rc6Jyta953UzGchNnKcyl+tl1LMRLz6jfsXd/efgVvTMN95PgsZ8KF59bbLRfPKsFTG"
    "AIdKDtq/U9n/mEh4fclzQ7Kb39pr0kmO4v6cuW5yiIQwMYKrK6nC/eKG/1oBix+yVeo0krBo0QNL5rs0"
    "W1VUkEatODV2oxetOsrN7hwP6RWIqYEO05JfM9R+nfFJf63JFxaRJyrktR+vEKM05jwYLz74smyPGvVl"
    "N4RT7YiX5jITWwrtS42fhVO2+0smWx3twCPtlXTf4iQk7W/c+QYtItN1j7FPiTyS9hKC9ree+vUMMSlW"
    "tyuurKSRJqPsMuRVXGfGdvN1d4PSSMiL7nAsVd+OhS/kWXRZv4yI7YN3UNY7fARPXZU3Rr4QQ596Vyak"
    "vnUf2xErnx/436jjicyE3KQ1FrxRIxoBTWMwLD4PDhzikmHZVStyZSmOyhG+zukVetIHKWtwp1CFrn4z"
    "0cAsgfVprba+73vnK9ZjASToOhvWZDtiRFAl5JKeHbJNjZiDhIT/pZxaCt6dYl72m4/6FEqTYUt1s6RE"
    "Go945lBWArsSD37A7nwYRps/Iz1sg9LvLdhpT9+IVoXt/USIizyDPWjqH5s0PwZ/m/GK2nBiElnwth/w"
    "GfUBBpmPWPHSJrnOFRc5MtVbSpiGPm6Ybb8aCn1+6ugKksjVPuhNhOn3VL7QBaJDvBbQ1OwRWxU1fJ6p"
    "YWHCfp4vWJRL9ueMMt9yDVLw5z8ahiOYBjjUBKVUjBo4gr7E8xIlFn4FuoG3rsh3T1ao3Vnur+hIVU+7"
    "/cKDsM3dQI3R5Ns8yf2w0M9PNhAsO0V8uNgZxvbqFLOvKFBNnnAWTdHUEVzIsA8rEqXq9v6ns+8655Mp"
    "aZJCUzfgUA5mNJeY8Ca49snns58fSs0L4XMGldPStKvVONA1AwgpsoHivaYYXSb/qjdOY0nWK6h76Eib"
    "EtC7dhKrAgu6ReylNgNzRGDcibjJSdZKY+G19IvEV6eqCjnLEgpG/SRuu04WSevLst6zRff+pMA73DlI"
    "tc0GpwbpRjwaGsBMfHqLNH1g+jm7vFGk2SggMa7e8ki+8TWloHYVpf0qA+C0YT/Ue76EZAX43zfhVLCe"
    "wdMNqsR7vfl7DOCEX8BrI0+W0alDRFZCpBun2pK9ys4kzB4TR0A08A2dmcESOMQsP81Hbbfwc+xhBBg8"
    "a8lESl+hSm37IRMVqdNEsS1flD8S4W1s3PK1v+lvdq+umogZAOcLoTBaFj+ET6t6s8mXTAn1OwrFpVvy"
    "49lUcDs2+ICaC+JTilgH73TOggXnSyS63304+shBfhfPNEc0S2+tU0GOZRLuHgiAQaVBYElVodw9zu6Q"
    "BQwg7MzrUh+60fqHe+X/4998ocv9z3vlAet63wR4BuTokDurFEaYGVv89MxPYBwhDPyqkmURcr9qnX5K"
    "3ON891M+X5YhePeDj6c+c6pWlrPSZGe3j/rzkbjSZl92alnmE9qr0qoQObj4QdIwibfp5/dlv7J07AOY"
    "z+SAogCFkSjdfsQb7pXK9mKyVGxetBtJSz3RbuuwudQr5FktS0b+5yE7JtSVjwfmSyg4tFIyHZPNjbIl"
    "S3xR9m4DLe+2rCOmilTWLEl+ug49dlweOD1RoFvwExB4QmdzfNmBmBKWTKI8mwOAX/14dNo6Oqmn/Vzi"
    "/Ya9D1Pe1hNYAyoErvbjzFz3kA+wwxa4kOVX/dB01XeCIvjrbw0/EO5Pfumfk4+fZgcJpUht8mbzVPaz"
    "4fqVSaHxZ8Dp+fn0ELK7f24STZImasODijOgwICvieWzSNmNTLgNc83sTc3BjNxVWvABlxmB/G38X5Ky"
    "wRe9R9zHUX1+EvjyrfUzr8EPJvhoy7w2ddi4oDJlJhwnQUiSr4QAPvkryT7qezcarfoKOS514Ld+kOsF"
    "gCaxd1vZuXOrl7Q9qf5bAu4FYecNbRJnSNZNqWJt0w7rd6yoQ/Xzyyyew56h1QAQgLaEr7FsR9xfgrg4"
    "dvzMgG465X1vGk5ShNK0e/q3eZpRpN0ZB9aLE8Y7MhHF61MQBBrw+/1tjJ7oHWGYZg38997Y+mUrsFCI"
    "eJh8lxFXtD2jkv3GW3xBFtvi8RONzIIReAXkXZFlmALMBHzjMNqfgifMrDIYhGmAc/GIjN3UnLuk6Hvq"
    "0GSBdpRwnZjjpK9YjtLhhqNbRS30oDVlThZCqTojxW/o8m9tTICkj14ORLWMK3O2NWAO87ii6tXOapRc"
    "AqHRS0GUvo57ZJckH0gCcbSVMjTvmScGPvLusZZVF+en4G4xPdQE1TcnSUm8TsSLaR2uDheBqXr34oEU"
    "gzDphKltywqKaiAIJ6WFCgk62tGdut+JTox7sQdrysYmMZOW5zyWF8oeUsb58GttW6gFQ4zua8mK5YZI"
    "GwiFoTBlQMQCRFxyduAUiDvLkjtZ6pxr5YHqAjZIGtBuo/USmtSpEK+GaG2JEBlfQf96h+BfTpRN4Q8G"
    "F4kwDo0YRh3YZRBd15o1saXnZR7ypST8MXQh+kAc+NDZr8b6ZdCeVXdXnCWi0rwFmqELg2J/8cbT8OEx"
    "geP0q9zBhMvyB816C4zsj/QT9hPdtphClZfRdwS/0ZvgEmVmPvJb14b+FGuGI74zx7vwN0dRIW8q16SK"
    "cQCb6CMdUvj73F72Fpdc2ZhmYmUfEcwqfTFf/rHWCfOZEB5IS4eNTRVc6IJcksmNIZ6KZTA613oABRxD"
    "npwvFDo0v73TXttB9Hbrl0VlNqM+6uMLi6BwxShEm51t0UDvvEA7UnsC1yzC069hmGfnsQ/8LblKajQq"
    "YciwcXl3DThzt4AQoT0pTuIUkqY8bRzL4j/EsBco7vUZdn6i2vsIfuF92KDlvgD2sasRa1VOJCcGYjdm"
    "NmJ5k9ZbiASJQIbry2BJx6cCPYasVYNfivp5ajLgXxaBv7oKuD05tzCAPNvu12vLN+evRMJfNyO2WDI1"
    "9+E2esmi5BusP6VlFdbbKJ7/aVcZutwtCXMPsU8ZmCxxjSxCaeItM6xUCand92TJ27OWHduDecjn2364"
    "mR0ZcedlVyKvZix7zlgvfUla9wczOEG9l+TzMsMzkc67ocvoX7HzOLGTZcmuZteg6lm17/HGU+YY6iL1"
    "+9dq68kXTUGVHLoa2C68X8Lk8Flz75Uud+3aT2MlpokdnOsGjiLy18Z2Qx2uBh0TjGOgzzyaM2djjc+N"
    "CIzJbjPQVON3LBkqsPwA6gKmVOvnJ/QC7y4YrDPv8SXzlG9c2BBzDYrtIum9wVKAT9iwSvVuoRTGFc4P"
    "ltTdXPkKfMwN2M1on55o8qN/cjKXetOFJUVR3RNaNzArvP0Ba2RV/r6tdaCqMnaUvixYG82WVDYCK03b"
    "GV0nV7IYRSwUluMAfxJYmO8/jdgSaaMhRFLgy38AhyADTpH8VbMRKZhfUyNo0uOn+cgIx50KFCl+lY7V"
    "rME0TyWbwqfVmFcK5p9hDSVK8LUXh6gt0vGWjV97GenwOAzJPu4k1ldEJP24t4Jhh7O4hQUMBqjS0eiB"
    "WKbSQ6KVpsjVbrRM7mI4X3PTn86kn3pnX5le+9ynIbavR4+/gTuJgk47+/CAQ2cPUNdwiozjrYhzw9EK"
    "IXmmi/6bZzhDOWxHyO07TN6OgIHnHQgzekZjtAd/W+hkPRX6kFdqerzjOZO6TgI6uswD35Sk8B6gRRJt"
    "W8hARONL0OQ2JYeKXcKVQHXk9PXeoBCFsNijFF3TRlGOcC3aTPPO6TH5vWAQ1Gem7rFCyEDwJuJTmVML"
    "3POfFoIEwZRRKX5HdwWnKP3AIVv+bTsYQPdLnON0aAG6vtnefCSrvLhw1F+x6KCUQZmBVpoR0EYyqhSe"
    "AoP7TAxNFjpZeTXDtQpUgSDjbn7z8Ek3cBfizSKLL2AhcmXDvUlbniCw4jRP9M1eeujG/cs2xHZ2IEmq"
    "ZTNfKXN+5BT5UkRm7bRFfwM6h0jSCx/IT0igu8vYaxblS1iUXFJ6xRhimkQJe6AiSfhb4IDI/nKBXz/C"
    "mIEARPr21fMHXEOYXz1kAP/mgFuTylNBrw4d9SdwNh4YyNIdjWE1z2vxq2Cfovoz0V2zycxSLTOXFw2n"
    "t9qJA/naCU0NeAMjwmt+VesFvKyQOwBCd/+8nsuTwNjYg6SiNagzXx4QMtkIGv2OUAdX8Q1prONBjKd1"
    "PiAftu9Rx0i341+xwVfs+6WhUMRYr8l8UZF3LD6ym4Aepp2P3Js/FnsgwxWKYk9332UjHfl2xzOUA1Jb"
    "5xcS4wjpLy9ngheV+3+lxEWC36pLitzB952uQ2Q961VpftIem9nDMGwTGYHiUTisY9rTQTxcTXUfisRw"
    "rvj5qFuexfe8Jg7i6WKm0GBEtXHBPp+HDr+ycD+I5aR5oPV4of8tugqnIun21X/moGmU28X8VIRrRBLR"
    "GP6ueapNgETudz3sd+hFQxpvFCw98crxd+Y6AwiECkE3w2ETHn1iIJaj7Q6qr/UfV7PATTP0ZNhbE3AB"
    "8dG7CfA2V3WHqWY8ZArfFGMWye8v7YgMlnkyRuvjyP1XteIKJ2nC6D62ibE5kN7GG11P1mFtrwwxuYW7"
    "3GAkmRmCj70mFpJZksIkRx0Up/gSwkrYAeLYP73n/n//jcdM//meO/p1/9b8vFeOPu3V6zOt62Vb6S6L"
    "xQLLlDdoz63fcSQbI+tXFb80XMYIsej7fMNhWG6q2v0WjRvVDg7VZanagiP88ibU0tuk2uvF0GJOVpg+"
    "1UN1Otk8h5Ws4I/nqvpDI1kBEAT9yDSNHqSGWuDIg68VMRLHmKvTXN+yrBibr/ZmwrFxo9rFPxqRGRVd"
    "q1bmFu1daWmQjnMXhZuxQ5+twpDticvEYzFjJicKADGWbnDo5aqlXosP0xZftEz5ciWAZe4/jTtKXpSB"
    "JL6VFn7IXZ5PDr0cH8W5frgV6Jm96FHt4JC8o1Sqgd+0MLwmAJRXpqPim5tU9NvW/SBYJTA/tOA5F7nH"
    "A12/HuJxEK2USqswDMQk4LPdnYQH6qsiybYgqox8kOjRjAQHVWyTAWA+ArACeHF4eEtV4g3z5743tf6x"
    "9yfdEBptqTw0UA97oqSsWDk/SqXznd2yG716fsZVGEtUqDSiLgNZOj2RbBaExUGXXTVNBbq1seRO6ltP"
    "k9PKBpvubhDaiRSk7c0N1qXTKS/5maTyk7z4x88idey08SMNgJyH29wMgm+1L6z8IhdtM39gkzAnfZL2"
    "gEc7qzGUtpwwW6noG6W3RLDlDEquSsVTsqyFDi93PrP/9aRWIZ4jp0Y2g3EYdzvOSAOOZLJPh4hqvRqO"
    "bPY9m/GauHFr1yYZ445cOP1aVuh+9WBf1B19OmKHvBg6THOBkRQRlZVNrpzB+2AxJmME+jj2frfquF/j"
    "7pAE2ojo592AZ3zRTcVobB31nQVDyzacT+SwYYEgk8EwU0mr1KR8Uvs156r4/IiEBDNrHohHSbUam5bW"
    "PZlkSbcOqx5lOqIu7VoQJw3cIXfjq8pc/UQUJMrpHSUJH+FIYzbUFT5C+itfnGXMiZxREai/n/me1ivB"
    "1+y19op3ZYSGv0m+rpXjOq5BfH96IEfgOh/NA+UkAgNZoa8Wfb4JRacEA9XmkHjELibQLImdE/KC6m4q"
    "o5fLJa8OwYtOg3R8OxP5wsDacGObWnWIR+Offodl/0pBelPjC8+PAKH0uTy/c0jbG5eoDM8CNELGsHY9"
    "k7cuuyqtp7z1yYN3XFg7xtVKn483kRQ+r96rtN9WHobhydnh9hF6ysy+i9ZcygBq47pwNa8mM5KD6LYO"
    "xMj5bIyIadrCnT6hBLbKpxT0SsggI3Eeyad3YoOAFGfBq2nh+RlvL4KEQdUFRlF605AOUnorAgxFwcBC"
    "ItU42HNxiqtkG8DHT6nEwRM1BLXx2RxZcC2WPDHo49dwbF0rLyy1Iu6mgBPuiS6s7c294OEtMpreQb6r"
    "LHHzhNSQLMNOp8ByJBNvZjHhVkCq6ORDJf1XAUPGCAYvwitHHyxNFGhKQg7tnYPNJIq/XSLirqhi2CGb"
    "cvkwc5/jXx/aliAlf/QMmt5drn1TNY1qzCPni5bvdFrJ2Y7DZysyS71NoceWI5EZg/jkN+sVpMALpD+Y"
    "Vhi6XO3lGcAJcp+AM3w2uYF8zHbmviRjgtmF9/0m9ggZ74mM9ms58RfaDyax+J504S7M8iJXtuU2z3jr"
    "3q5Ib22yQLXdEOubBOHXc9xsVLgM1C49qCsVgUyEz0IUJmUeDeZUvgwDgVNU8cztz8qBni+ecqB/SR2K"
    "W+ASUSpfyD1qao/pYsvdKDsuykQyP7la7CUGOUjkaGADkhbGY13kQziwDidVZRBHTfuc7RtNuoHcW5E7"
    "Ozj6rEvMVeBH7sevjMHzjKMjL2H7thwv3h0lBaFWYfHS8XmJtMYYiX/jTS+6jO8IoUL6q8plw1j80MKX"
    "SKpMz5fLs7cnPG2GVRDeGkGyRIvz5n6poneoOVSDMbh2NBBo3Ovmyji739jN7W/nfJB4PJiugp8q5wwr"
    "8EBu2SbEcBAslkh6bPd+68EHSHCMY5Lr3hKyf23FCfKaFtwxmuA8bTPXlnWKwThZTvhq5d4yXap+ydd5"
    "hRwb05ds0tWcxUBEAMFbjIlArKR++8P6hp0fn32lw6KjWoyMkxB/I5KLcI5k2ZEHynQK1JXewk/4DcAx"
    "pSngGOwFd/jPk+6/G35PSiPEXk09US7CHGm2UPksrNia2zLKGnryj8nQ8qrU8FKhIBWZzC3gWdVO3GtH"
    "Bf540ix+Y1l4m90zhrytLDOB6iS8XGdIs0XBr7dkRyegiR9FhasMsxmblYbWy8rPeey/Uoh5W5D150cm"
    "OfexyojCGgMi+U7z8/JuXJvv5l1q3MZztn48QPkjI8CmMRiQGMYmlo6ScTEp2wy0KanNMBULQD0LpwJ2"
    "wu+P6dCXILgmH/OofbanbqXpfbYjU02E2Nh/HmCIjl844LZUzyC0J1DcM/7Am/MnQzAKnnpetk9GzgZ3"
    "Gh9VuDacSYMibtlXLyNoqBR/Gkzx7/Gf7/M77wcsVHpsgLA3ZBZBoow7FrC/AKGpLwUbHop+HkGxJ4Os"
    "XaGkgG3Oly8aXUKa55hYrpb/pqzB6pqBK8Vxw5yqPz7UjX2NXQ9AIOaOiuhGayOoBcFX9+IoPFSdLQWl"
    "xUwntiKsrsX6ygwwM32Pa3f2mBiBf/0CU244WUnk2kKcbt1WxNO3Gy/g285CganwovYQ9Bc09HocY5sX"
    "UtBkywcr+HZfFKFkmTaYNYLSbtRIc9T4w1JLD1FjCnUcDAL2E87r8biRxXTHd58dRyGQ8oaPPkMPGmxV"
    "CwXW+W3pr96DUtM/IEQfh/bOSZmMhBEwhIxtnyNXiZW9USorUBmakMOM39Y4q0hxqcyoMdOiYodLA22P"
    "Z3R70AMAZMSvzIhCxC0PD0bnGPnT1m4sIYVF8mEYTI4h8K30OHSbOYVCsJnSObG2dv92tU0iOhOgQ84u"
    "JwqyKWh/TKkhprQtO5qlSAq/Aw3qDJ0tToLd7ZoWm/oDb3Z1CXkE2PEGRBHdgb+ttgAsJ3ewl4LqqZN3"
    "MCR7/MTS9n22wtQOeIXJw7+ZHYwsr20cyCGgzylzEBzqfTQOF/yW9W0DYQN1JhpCm8Hr4syQRfhrxBHh"
    "q/4xLhXm4MC3QEniLY+IUEmu29ihLNK9w0QfSz5MOhQWtY5B9w1kJ0cVqQ4/Uinaj3otfavKnyDNk+6E"
    "kwKcEYpYpK7otHvfZ25eoE8YdIUD4TtSaDAAoq8c8IvZ5osKwMae1auTCTeNgvEbBofrPSvvUdFV+e7C"
    "homlBC/QQK5pcDcYH0BYfSeEYk0E4rNdSthcPlHlMvTRUM5zD0iAYIeBYeCUBq2D2uI9WuBDS6J0c3xk"
    "Oo6BCO/w0ZgC/PsArHCg+WsS4OsuRUYSRRGAypsXj4y2g3sMjWrzJ7y6FV8Aw4cnWSGglhxFfgCfE/2E"
    "YYQxOkr5j+uo/s+/WUeV/sf3+HLsSr0vKlsk/ZDkg+rJkaA+nuzLRtvKqn7z51ZHexMZ9HY3ZgqtUhM0"
    "sRRU3Rj5OquYb/0Z2+/chIjPuPB+lZBfC2yi5O296vEPOoqHCDI0iIMhQiMkGiITzPMBpXUOQaeu1+wA"
    "1cCd78GUJAsUXFPMvusPj7SObAVMKYTEhvRqMK+l9bnaOtq8OUbuMG7gBNbyReS+Ta8dv/ozLXP2yzIH"
    "DQnOYRIqDTYLtMDPJ+8gpLffer7b4/L67xImYhNJQg8h1NuvzljYsr7R7LMADXHs+ibivG9emrh3d0cA"
    "sQxrGTBYINs7ZRuPbRLHY8OO7Fa6sDiZcKXN/W0k3UX6tlwk9mHT/m9LiKvyYCz9ZW3AjtF2G4JwuZKO"
    "diprqyUSLBn5XrbzAJhC5GNukM1ogrDllRelEsS3RVtla5TpCwm/WI3CSFrBprun6HvPa5DAB8yrbPwG"
    "7w1wm3agVn5uY6SRkUBUuStHgDKq6hyvbgiro5K2wXcMJOnQNeAYh1XLiq0Ykse6ikwCXgnQlvvac7Cg"
    "EKqae9B5lgsftUYgatg/RK8RRJoAG54NftAlCSAIatIHRCYAS31Rgeb9hTE+U9gvCHd3Miw+YilA0r85"
    "GNPPVLVvP4YSi9vOuA5/gr2ExTVCTixe2otOGbqSc3BY00Gem3Z/Cz3xO8D4PVUUy59Zn4/8J1tpa+V6"
    "V4/S9+Fg19vTXq10+mc92PB65ng3FjBejPolGsm+s0Gmc5u2msf/29pcEP3Mt+lGOG/1EqSPwGp2+O1V"
    "4JJG55NQgDcNszJH6FeZc1H/QfDjgh6S15T/SS36l/Of/vPjfwL8iZc8BpgtjvvJwahP74PX77vnaJCj"
    "TopzvYrQWT3s8AceIBha5Le4uJXs1k5dVyFNmth3M++ms5tvTFM15UHWROgS8v08GGCI5dipCAwFgaED"
    "Kj3cVyKqSJj0RjMJAc9IcmGeFagX3+5gK/aiHjhzuNWOpfKektlgIuBJqcswZ839iT/7q48XyfK7DEWq"
    "DPRyvSFnm7XpgS0wT6gjt8aUJIyLW5t7iCtPjPeUW7i0gfByLWlOGdpgx8mhaf9cTM9chtMD7lr1QETN"
    "66ZFlPVZInAN+Wy/kCad66f92+pkY9kfGgga3pq4vKDY78oX/rCD0MLyw1TA+bZRrpR7TbJ77sRMiuK2"
    "iBtN9kOnej6D9azg99m+pxvXaErHv0U0B383tpfG15xVJ5kIYtNzrRg2OcV5xJiPzOWalRyt2HBwNSc3"
    "mKx5rk5PtXfR0NaCNvVy3aX8Gkn/kfVaOmPltyDCo0mmn4OQnP210s2CjU6jwFYutI8w/qrJZDihlO5S"
    "yLEZO3PwW/w69YoLJ9zgxg8x5zKWUHeZc67n+lNL/Q+ke8A5zIurtlTsrJTcGdnVPvzoViXIGENwWmZF"
    "6DIm8fWmmxClahj3OJbZjix3f1y6ulHyC6HfENtIi2+6gGuT+fIEn+B/LIy5h2rZ7WjFe8J3SlY/wquX"
    "n8K3zvGk19d4r1VNu7jmCIorveDiY8/JM0lSGP+qMoltDg05K7Em3e2KsyC9OIQCeQgxBMthG6ZspZpJ"
    "Gdt0vytLCMzECzyvFPxYgaXWCbutXd28jJdFPaOXcw93kjRcGBRJPcyMZrPIb4KHJ8R+gnaNFVswA30c"
    "6pXbeownh+pHqsbM1jDH/UL81scQypcv0SPceud51gQmKCLX+U24WXXzNqKL03wO3+igE79wRMarEgGE"
    "D+1LIWw7ncwv/egIQQv+SuLDNdjHKVHOAa6pd8HhhCtuHp4ld66ZgLvt3s+nVklDA7qCC+IdGT/zJRj1"
    "HcMvEBOgjWIDkuBblQ6OHwy9OfKQAbDGXkQBv3VIA7wGwq1Q8Q0YW2GxG4RdpbPvNCVa7pqwzL+S0twL"
    "EgXdGsB2Er0mAiys/G2vX3e79SEXKuHLF9lCm4kEFFkX3djHM0gQnTwLZVpS1RoM/IIAFEK1oVGIugna"
    "WjdfQNWX9mKPUppUUGS1p4bfcOZ3j7s714ja81BZGB9gIAdyfxuS3u/7fvKGUZ3nsbzAvNmvswhkpfIR"
    "arrvKKXvXTq3QGijsfajhz9TNnPkYdb6epdTc91KL5/KCTTB30foXI4+k4s4OnCioGL3NbwJgkTtltoZ"
    "f+k5AfV8DPD3p+2bCz9UQyGikwg87tGZvCT++l0wgNP3Mf7+4Ofmx19+KNoxuwcDTKUtajZisruGOxOV"
    "AeACm3QMjHG3R9fg9biF1zI5TOO4niSB7QeE0jf8xrQMyjdOo8WDvIk2xWDET2WY+ModQjxHssWBfEb1"
    "4vgGGelwwdhKPcGBkeMdK16Qa/2/50rPBswEpD6oVrbDUXFFoBVPPfTHkgAzGGcIdB2l9yH8X4IRsuNy"
    "+rjKL5nhC6yvHgOg1v73OalfviMaObs5rO60mlAu7WYpGe4yEb5iZFnetvcUpCVFnM7wVGdfWERf2pjM"
    "ER9sJxVsRBUwGXmvhhZuw9IMAiA2GQ78DvV6qjfFgG4Y+z4SZCaSH57oSJx2e5b7Yp9Zi6gVMrHnATPf"
    "TX2bA7v8UDL/5PezkDUlmVoGnuvyN550VMgkN/QYfXs1RA1O/LuzGn8+KEWmB7pMSBRr44ZfAW2rcIMb"
    "1TaeYy7pFIGEhmyKZVjM7AID02AYwfbTqduke/5SToNJuzbh58w4jtCkZeS6fJSkIMvqXKde6l336o3u"
    "aPj6gARWnoXMVWsOgvbiIaTXAI18x6nTYe0AMW6l/dRI/wEpYr0zEYUYBDTNvvpJ7P0iyqyOd27JrKVW"
    "C0QiW6d7OkKnDFkcqMccaBN2+rOfBnDkxHcxLf8tCgupod6CYxNMvGfRbH5pCBR0ABerv/kebAQApLPc"
    "oeBpcVZHWdTPiQujgmEXEqgQamkRmh1D90HKA3iQcYubu6QHTAnnH9Zm/e9/weYy9P+faXgvULAu/g3A"
    "IQdJcsO6HrGVX1C3XVovS842Fb/8kCZhQ89ezclDILyfM/8kYU3q6AqQt80yo7dTtfGymRoxuiJXQ48S"
    "zahAnA3r2zjHlmM5Gs7tfs9PT36Sdd3BLH8VaiiIq+R+wmv1N7jVeAYUKQneQIqSAxue1fP+/0pfx7p6"
    "L5iL0TvBPQSIe7Clz0Xtv0KDynsIfoCTC3yy1LiSJUI6OoCAs/OoMA596xP8eFMDgMGDlNzxF9nBHVmq"
    "bFpbybE42/OnG6pC2X1S4zWsCmH60AnTYp8Kc11GU9vfKiyW3IY6nDBrQ3jaWAplI5d6Ebhq+xuAzMPI"
    "NcY+Y8nEPJiAHwTtsaTYDqR6wnHwoQBc22ENtGadWsTEsBgOtjLduQ9WAKxpfKovrQ9vR+UCQOa5WaOL"
    "QhtxebRhl4fkRhm5avqauDQnKDhjz8f+5oW+I29G+gQ15hdB5w9BhN8AEUyaFglxxrDyy0D8l2EaeE7A"
    "wvR/+DLAEELfNeEpqrlR5wpuO2mhbwr6NLcQESSxsl2r5QhsfPE6sHkcyetExZ13t0w+0WLdtCJMZCEH"
    "MhnGJzlvSsX9yvLFzHK4WsxIb7YA0rQs8r5Rvjf4t8pTiMR1nbo97jFrwUG8jWxklWl3NO/fB2MTTRLu"
    "1K6JJCeL4LlvEMw4wqC7ixX8phojnCW5fK/eLmBAae4AUgcGLw2GABV4C+EawFwO3fqRkEqI50uyQ+RI"
    "u6ZPx9adM7O/ftv9zH5yoL3TbWNy9I8MvEMyAWFCxGNo/NJbsya2K8Vjdjahzn5TCwwFiZQHsphP+3vl"
    "woEYocz1FQlPilwhf60AHwIsbSrmShXx6QNh9uugZWX6FStDPcdUWk+RXj7kK+roAylhzTj35ve68GPu"
    "p7BXSSQoJNxv11ENkeW09egUFcbFIHDp2B8fdMdTjAdavOfcYUUPFW+Tj8n67LXrmDCtrok0L1jTaqFI"
    "qIDZcjEXJiz7TVuOZ/ToN2gOM0e60RWITPIPXbj+KpPpSxFhO23lxy5F/izdM25ns9LmoKZIp1BdXddf"
    "rOI+bNjUDnpg0t/tkcmDv6pruxFsKzTcmi3Ju2TLeJIyWIJxjd57JLt7iDfQGL37iowm1hWBfYSV1jMe"
    "U5Vg9GNxSXgJ+bGszPEEsTBEKkjsR3ZFibF7m6lDsHPEXGD0B/n2lUqPH7V3dftmxxJ8II8X+5l9Qh20"
    "5d/v88KiELOlU0oSyDL8aYg8cqZtHX6g0ymZ5/MaWjm1IiC8IcvPSataUAfNvJ7+Ot0WP2qwR4xABOqe"
    "ngNqdWyYx9DvNqgWE7Cr7dl2s7WT03GGrQV0DRlT7WiToNTQ1IbGuVA13w+pcubs2jVOYIJZFN4OokpB"
    "EcwMH4eNzIfSWPxM0nzbCf9JdymMGkuvMfdMFE9x9T3sULJvhqOe7X3ISJlyMpm1OQZKFG4ZcHSLMqSG"
    "6NCu5K/EMKEgjKUF2HVRl+IC/wBd/Ogc907o/oMDO+luEXhIgR9cMdfGm/x7cVwes3Dzqa/WBMWaMLMx"
    "4AdSdzOD67Xy9UoOCcrvnX16Vk+tMreKc/pGLcHS/M1e8jxEIkNZbqMWUlGWPdn8pdtKM/MayvKVn3KG"
    "ZjCQ3DJ+EldA9XcVCqHQe29cB+FZQuooU2iBYttUowmn0tNg6qZHz6Vwj3qEXYWWMXMn02BG44U7CKUl"
    "hE13OWdC5vg7NM4H3zLAGHirsYZLza2ZPL5RfIaa2ZjJYEHerzbtHkNc4paxK0ltboq+8lLmiojYwsA9"
    "ikvpuHpbaG43iwOD/hZ42NyIEg56DMfLWBdDCpWk2FwpPZxTKQVCgOMZo90VKnJYJphmbuyar1N85RiX"
    "dFmnnTmywuxZtTeF/tbhpIRonLZDrMD0SQvu5WsCI1b5LdcIm3/hBcwrvC/EyK6eSWC/CwTlAWgRokqZ"
    "DtnuwVoRn8WUK51l7JCFmcMScUNHkzLnX7Jx6i0M6ovLh2AhL1wyXmYaTSaNmVlUBhAzceHHpUwmBHni"
    "0PU+KzSRaGYIsmKJkAyml6H2Ey/TGejCPkicjwoYyRwRp8MBHu0Z/8ZeoO9+0mwmgA02X5oKHQVhbAUo"
    "y4hc4EjoQL3VuwJmN9oAdjFeqpmwQU5UhvtNudnl/hW7wPAaEh2w2ey1XDZ3X0em6hRfYTIjF3QDz5jB"
    "U4iIMAub9a4h7jTYTMwygQBxckmJZPtRzzXK76rcnss5qGfF8VRzzQ4qzZQ2nksn3BO7XIEh3obzfREd"
    "AeOXV1atdJnyW33DEYdusT9A6xOw9Ifnz8/p/cZy46U88bpWaHqcBnn2C69OAVbT30aiKVjFdWR3kRmP"
    "Xq1tKmTYP01JrEja/Yc5KKXGYL7PGTUKeyD0vxQ6gToy87g+iFVAUWtPQHK55C/v5CZog8d2WBpLmI7p"
    "eLiaM4UJEffZTq5D1J/kE7dMybD5qfC+CqJxNZrE+NyICaxz/6VxTKWh19Hq+kDR4AwgTbyuiKaU73R7"
    "n695RofbvhXifGhvESV3q8MXFZClsA7kGABwTDQSzsGNBI9XZL+ccuP8yl/MRSR1P1PTsckDGUQ7gdzo"
    "rJGpm3fjAZLA7mFPzX0u9AZV/y0gc4OQqLnPiS2GzcM+yWM+yREn+R6eOZdROqHjW3otiKPeHGL5LxjI"
    "tmj0NoJ8d2JoExjPTlg7nbce3Dn43cevrQwVnLrz+Y/3mP/nv+HY9T+/h/r3jsH/+x7qjh7wx24w1WBa"
    "6JtW9sDcXJWIoX99Nl+Yku/sJia2eITDwyxgFllVghW+idczxV8oH/xt+oX54rYvwo0dqy5pP0MQvsyR"
    "atsf/jeZNtkjvycDi/0Nb3Qw0uL3Y6ZfHHC5RaQmWOhHSj/oYVLk371mizoRTRPEnHqvgm/MXbF/JNRJ"
    "1xwbBiNkRvR1yZtnQrbWAwTD1x2Fu8gtotAVBye5nXwEKOatLvq6lCvBMXeeEii97OAWdDGM64WIObw7"
    "M8bwBmt2ZxgvURi1F2bMOSzD9IyUyto2Pht/5gwCo3pAKE+BTkKULw/RTcvvzXrtTcf4d0S/ZgaItrQl"
    "boOV8bG8A9AJ+SOKPGSTlw3KxEl6Wgdcsu/2h4UptSKmR05WOTTZGYeHoqAgsaA28Ikz+l2W3VcwibZ5"
    "TYfD+gp+xapRAS1x/TPswoOYOstjyETrENKEvzHea5nP8PhXCeZ59sqvnkJuH9kW/2s/P5uxzx+zf/Ta"
    "cLU85JO4R3kp7JmpZKJxFb/40TkGBDk69KO5TmC6+RGX6fly2vLzq01iA9FvU06aZrZUSmE45XodVEOl"
    "pIjTv59Lvmyeo8FEKL5rEvmOI6uO674VeCxcSP+0YbIIGI1hn5YLP4vi+dHFRfoxfwO9f0X8lhq04t96"
    "LMFbUrAfNLUKn+N1DS9zNLmJuSWPew9M/nPqR9AMRADJnMj4GisWqN4yrSGJHmpOD0tk3vhjTv5RdMFn"
    "Rkvde5m5kT5BMzyrw1X45aQYgMQArOkEc8QGBkj/oi7H8xy12s7LfVZzDrZm0qBDYaCvRSSApeD3PE5P"
    "M8SWuXyNIpdEDuDOT3cjGzEfUqBWwCvd5UWlvhR5yDdaW0yaoDbLkWam5+gqPGgxDBIScyX/THRDYLMn"
    "vTutg6/f48H7TLq+dI9BucRXlK2v5H0pHHhNGYHmmNFt0sQG1lTcCNwnWxsCpOrZv3Vf9LA+OvJSHyL6"
    "p/vEv6LGpFJ/g6wOxPBYlLaFi+XsgkS4RUsA/e79pfrZ9aftuEpAleGFvtfId42kL8dDxXZNP/oXFkUB"
    "HsfjAIHFBGCoMJPvok4etvCXK7OsAPn6O0v2OkJg9AJzsvLwkecxIY6wMEkx21kxRHnH9uaQ5d0bECv6"
    "AUGVWtdCSw2laeEr1/DHt2Q3RueE/+LsvJEkBtLsfCAYKIiCMKG11vCgtSpoHGGtMXkC+nRokDwc0Rvc"
    "pbPjjNER3RXVBSAz//e+h0JmigrptsdXTqYBhMiXbcrTglW7c10ZSW0bArF4+HFK+pxEqS4ZVwlpsz4S"
    "rlbAd5H1qLIIacSK43B5IhI3HJpGXLVhS2wS1egKRcPWMsAFKPP9O8+iAfFUW8ZOKSru9ZQQ0p6dQD5M"
    "bmUPy/zm9TfeCvPDPJ+nGs4XFoQKzDEyuSJBaomF9QKY1nqqbuGNJs3mV+BPSB7ZUYKVrmA0aqFMJVMS"
    "UkeXy2DT8Xb9VQUjg1JejxuFimWO6yR1Og6HGoI3sjV5HImndYtSgPFvZ6fPXbgnzB2ImI+PTZHngwNI"
    "0K+LhAV4018XAgz1sZErvn3BVQkLrWkLjHoxp1CCpJOYgL4yj/o4tAZVf8sb6dTxyerI3pSsqkMGBOPu"
    "EJPzhXQ077yXBW0JUxh+y+EQ+pu5HD4BSGbtjEaCCNWYLlr6iRuhb5AF1JZBFrlUbcXFR0s145b7ZXSN"
    "kLGoZ3V6aw+vOQh7+c6hmdiag3G6hbUmThZdh4pJBJKVZIC/TYsSBePCRFbsLEACgyB/qEpHjoRgG+IH"
    "xkfy2+drqD+NKjXSII+KNsUyNbH10klKU9EvZ7wNTldrX3wzhUedmSs3LkowB4Haj4OyY3JAbQhlBJXp"
    "vMxG5nepTubl4U91nnXhSC8HfCzsHQO+lp25TJCLjehVfMphoAgmOPi+5/+gmUThyliVs9dM1OZRHi51"
    "uyVQ92S4hIpwsX0jPYm3p2V0K2fTfMRYwkYuePNqr/ahTHfw+o87rhpjHYq4fQx3n8fdZC/50QCcYg0a"
    "jsHDQ196oMTqDQYujrQJ/hQ9VVLdEhxnDDObl1J5lwfF3TEI9aF/UyeaXozQKd83Obn+Ar+ct5k6KUEB"
    "+IkYZs6GHz6lTVljf4D/hBkJrUEgC4KMpRX8cV9g/KaRxVlsA5JdJVQSLxPl7sjLQ4itdCOwOM+/AOGy"
    "Mwk+H4pxSZAnhlDK57iDUWegKE5KuFesPnNbzM3afYDxwkkyeR7weThFuTX7GxKXUgXc+Vha/pQwiZQG"
    "mQXyj/Mxg8VyaaU9plsBfT4Q+vIpyxOKTL0LAslZHPLQrxA75kDPgF8vDRIzt02YZgKGukVXTFL/LUXa"
    "3HIQv+FdlDDkWYdLYIXVRF5+MfhPASMjiEPjEHNyFv5tZO83S7n5Pgmb6t9+4Or001WNpZLIYSlNk/io"
    "SF/n5UjpC4f0s8oBkOpxoRGACbLD0QPGEY8DJhLiBW6vgt2DPbMoUBRlIW72olY7iu8KTXWNVCkdSfG2"
    "Z7KbycuwMEY7DJVWuawtaMTjuhSmCFzy99UXwSYysu1aTew011WKyiTYB4GB/eei8rmiCsDNBocaE9B5"
    "RIcBD7HhM/T0R5HYIJ4ZrPxEcBhG4/hKL9dyPP/pAdmzIyZq0N1I874MvXV03XbCMcG5eUiJH3mQDx3x"
    "tdldAdtzBn8sbXnrRZHnUITXReAWfyTpD8D6clCX9OGZq78SpIIIJ2GAbND6/K/vsf63//WvPDdO/8c9"
    "1iX4Wysy9+1QLOHjyAiSfNTPM2bfD/xG4gaPXeAjJ7yzSHxtsdBCQbP3+VQHr+pJTbOumDBq4SoCw0xd"
    "zX4VjisCb3nIyBKAxpsaergXs/es5MRDW5lRcN5YHcF3jSAPlR2dwfsM9SUDJeuUcQHiIZAAMAnVBBAb"
    "4SPwwUo2+OPTIvBgXgVP+7ivyxKt+FtMhEk2BvslCMpTdvsmvjg8RCYIwKt9kjtuPtAJjrNrsRgX35Gp"
    "ahSo8SKMvYcWw+DaPmbenxyh8JpLo+j+E58o/0A+4uN/Gyc89BjlBag9pz6pJBZXP/LMiCNbk3wAfRPf"
    "e7vESJXpvtDxhcraxezA3e2Qt3l6fC/zA7qmulxf+APY8ihdS16ZU+9+8IH9BnBOliVF41ngNmjnxW/1"
    "BG5+lTV8/urV9wyEvodf4wPkagYk7AOL7HMfdHS5UKrRTtYFUIZaeA0II213GcqGv+dq5mDBTT05APTa"
    "r+Nnx+hbBK0YpixdAoe3IQi5Y1TH4ubcoWnhkPdzUz4AFGvCEHmG2mBQ/LAt5aeXnxpjUpOPuSUIL457"
    "iwGFW5B3k2/dUwnRY6vj5SN6Z+Dw1WLjtxe0D94+3w1Lmm8JHthQlOqMpwdm9naCz5HLAbmBF57bpPUY"
    "oqBBO7oYB+p4j9mmJMDvp5HEx7rDoD/nIo0gHelQ50OxFm/ahvLtcGb88q7/WFQ7KEN1nVyZDat+Yd+r"
    "3Ocq7rEQJJrLvC/MLD6OgymWkqa8rAdmnOIDtb6EheA9sL+Wm9zXMM/JO/ou/g2dm52m7I5KjoJUJe+y"
    "ckXtb6PkaMcq56m7dBYxF8HAVhHfJ9AeOq+n5veIjXkn+Y1gjsnrOlUqrCa6zAAbPpFpoyj+ieOU2wsW"
    "rgCHog3G1mTP3ZU8q0ueuneaei9P06qgyTHWYZ5o8+XrCabvtTq6c7k9P9rKb1+reasdPNqtU/AMlELV"
    "0bJnSgyqmKH6xnuwjTr7ln0/K61aTZfeQbRVphROrEwNy3W0Rjdar+WrDpOiLs1ygVQEq2VdzWkhLMwB"
    "9WuDfj+hk7fGCX5TVPAtYhKST4DueEYzzhGdzHTeaK9nCe/r6bcfxZRNV0k9Ol7pPUyH8E0y36jgNpSH"
    "Mpxt75SYUdNIstwqS/kXSmplOyl2FZkFNBKt8sHc3VkpLJUlFjraNWy38m2Najpqr/SlYYxIEBj/7QP6"
    "ROn4ZY37kuhpRqhzYGe2TxTT1+kRYSib93hHvwuh/dzxbwRjF6QLhaPwYGFnDRZ4oqKaD0ZTHHJmEUcI"
    "7qg5Iy3rAOITzBv3Ta7XigYMoaNPU9XWqREi2CD2Iq7qaCSyHQl6+8Lr1LKt5h8xldGmBNSsbHb5o02j"
    "KrqaL4vF+JK5qNGONSyRZn1Nqsp2DFzN9rfksp8f4c9v7MUqWfQIJdd9IKSTyw8YfihuzbSI/cRC9MPu"
    "fKrY8+JMk/UFkCiTJBjvF7kapHrfZVP83XuIKKiicfJIWv/6OY4DviElrg59mJo60x1H2N5nnuxO4kCT"
    "j4Hv6Y7s9PGxnfKZM7R1Fnqyw1dYTUClMs5NeCJV3/Fo2dz2q5ZmDXitl8bEcqgfHz3igVOkDHjS1+Px"
    "+YfTaGYtitu5oh6PcDYH84iDHx3Pi9UlVjEZEUrAvt84/ULz74dCbVM8av8VB/6YJwNZXEGsiy1QJ4wj"
    "rtf2OohTmfMDl4BIE5tRXgkB4YVaNJFE5lVQ4jNL73A76wZTF1mHxsqWm5D4AOYUMDY+hrN4Z6uKzqH3"
    "TRdadk29dbtgNg2FTNP+7yu7C890yN07DvRISD3wT0nI6ktB7etUU3eo2edcyZE1wnpNUBHXr2yis6kf"
    "P7/niH0IUL+WKL7uKDq0HX8A51t0ky3d4ha6Jj51QUs/85VppAJPYRa2pcpoxNETH0KZjeeLwIlKs4Hg"
    "SfIanWnW62wsOQv7FhbN8Uzj6Nr9jSaKpAnN/aJZgcF0cnh+u3KfoqdP7FtTLKpXuPnC20eIYTze79ht"
    "l4LhjHs8Vpvi9uDX318fiVMB/3ah2qbGET41HhY/ot/sjeaCdeLrJw1v3IV3vi0lXWZ4Aj/QN8eh5x1O"
    "0nZ8R3lavfmShHlLH+J3vZK4jcnSac3dt5klxzXigg3iN07bwhdD4DBFwQwqMLWn1vDfutygxbLlF0G8"
    "tnuw79OiL1zgJxnXN8f8fr+aM0rDQVSID4OPWxpoSqx1NkTL57s/pkpvnZzEqu8qhMEOWoEnOpceP+fz"
    "0a39RWC95tBcwR1bP2M7QwHh9ybn/EI5XcbCauu3AwinnuyjDzRdiCo3QAkPKfiVjee8peYyIpk+i3Yd"
    "wSxywAOShy+AKjyS7WiZvKjKRx3gjQOyoCDgj0lSmbvJZKyek8v3y/8tUThLtW3tpWjjn2CHt/IC0u28"
    "CqD3VoFA0VyF4dt0P+S2FOOrxDAAI78iLnwJh75ozP9KhKTf334rEvJBJR38dNiMsNx1Q5bdHuAKPH8z"
    "GJAJvvqF3+oR712oYrE9WAQw+iPUcXMYQO/zta7kE7xpI3exNTuUKM5S5Eh9B8efS30J9bjj70fxr1rT"
    "fvzwyKMoimGRLUqF4F8AKjlsBJLN5vGV0qykZX68e0gOxScYjp1Uuj3dhxz6n1gUcAL9ppQjnHb1I4X0"
    "RafnOQmL0SYTAVTIt+XM9+IXjsUI2tiOVz2/V8uQ5vsYrAFZbes8o4QiBgtcfGQyTylv2q3Vahrjxxn8"
    "8eNsQlX8uMkmSGboe5/q6qGS80XTwRR28TwOBp5rHy8f6rsqy5LqzXnGV0AmdWNHLY7DMH4oiL4/H+iK"
    "D3mXdCuCcrJgAsO3X8anhcajeXvzXjk8AvUl3/6FU/VEi2YkoEwP2Z9stnhWOOBTJvcw1m65LdrsrY9J"
    "wAP+N1VAHhRK5hlHDQ93QuGxoxnrBes88RuUxlMCSuf+swMlyEDJUmzb8YBwJCLGKZ4EQyQDQeYD3xcD"
    "roRydZYbGgUJMVQNJ30bur4x+uAt8UDEqkLUHnnSgxDT+L6or9HQLtXI13AZAEosuND16SxBqTscumCk"
    "wJnSzTQmERJ6RgfopWLKreVjBcJ7D0y6vcsnBnHjCOHPJWCSckokiRsPdvtlUZB2bxYxHrj/r/PFP/7n"
    "v3Lve/iPe987FBbo/f/2XzZA/LvH6YXh2sPg6t8uH2jQ8FJlKb6LBwwlqNInyFXWnjm/tTlYj7TgtczS"
    "1aUwkufQQqVNsmPzVVJLYz42NyXi5tW4upA0I6XvqLcKHNdw49G+BHnh4GAEJMP1LTAB4AHjew7gx3gY"
    "+Pd7vd7HgoBc0xu4F66kFI7HSZ22PVjoJBzaoyA5C1Qa599s+DC2JFsfq6EEz2Fc3IO76fVN0u8d6xZC"
    "TYcIWpJpaRm9ZkqAwrkdR531ILebqNlwh+yPdaBjVZaV3FEsjdIAIheSwfQzPzU+c44h6YbtFeJ5Jfwz"
    "+0ymGex3q2vbLMGhVCDKHB9ytzCHnHGT3FMDr2swTXPzU204iNfSSej5hpygHdusa4TrCPMaDP/71szI"
    "2LStzwRVgJ/DVEv8eieER32+4m0ONuF1mQCv44TtyHqHEIgCEobbFQkqL/NftziF/Rcyvc/eIq+RmukE"
    "HgUMmj6SPGj5i1rP+4HN2EZT8Zva4G7WUJXhzwfYPYwCs2OcRwYk1kadwLW5eG4p6pqjG5q2arMDgScm"
    "2NA7cR9hHnqiWqq6Ov92fesuT4QlEx4HaPD+ASkdmD+Somm69qc5H1GjSDVwQfdmSLFWjfFvc1nLU5ip"
    "RrvBdQ+FOi65OrZ8wtKvukxeI0/Yqi9ail+mG5zUL66piGb+9iLXLIFi4mjtrIAvvvyMxCVa4Vsg8ZpU"
    "Sy0r8N0WXdBT1MdvA9hzowbvEnQE2cChhm6zfEIetBuaY05HaqiJWxnNE2vbWx2I/3Ygofjr40Bw+cX2"
    "Y/51IEdlBLvw5CpVCdfK9NWzhqqhHUd9mEk61LnTAINPw1m/fyyjvcnbrTxFNiUxTuhPRKW2gZxB5XIV"
    "3gGI16gaVyUGiw2hYq4rsGbO2VP1gs6cJVYRQel7RV3pXtANfyLt5ul2bosfRkL6+JRI2ZeY298+Ft0n"
    "liUFEwXi+jeOQfNLCZGlEfWF8nEYIaylthvc+x+Pu9lpdXDTFp4+tNyclwFp0lSTkLxW01JKoDTh1E6k"
    "tszUXktjDNryuAiKo1dQPHj8auhCiByslzwpvPusQVmlMpYbrr5/9zY5UZhD2dJsNNhy32a56sTXpmqj"
    "bX15nR+CUid87eEEnmqqFfP4+LskqDoDlGSZwxaxwWIMk4XRHUBU7EV4NKVSUUYJz6g3D13RlfFdwdZK"
    "H4QGqVqiVI+2mELxrbxmk5E5vz5EYPhhRtkxxCt7nHJzh6ul9dw8pfBAZ/VDYHnVqzoSNvUb8cWwohgJ"
    "8pMaEmL0PSu+fS+jX/kGvL+2wljsZzFMUfolGZP/FIHmWYo9T6E+zVfG9ImvtAXC84b10m03ex9EjfdY"
    "1XyosbaY3oCaCgnIUX6JM/ngXF+bG6zrRWX8tsqFPy8pJXRjMNPe7U42XAGVpvNMHfFGDhSjzrU4o0Aq"
    "AJxxlK104HvASl/q0TQZEL3cp20mN6noEt4MJrnX4UFQRLcVvN3PUP/tDRlxlGRUE32jcmOt9niGVVHq"
    "XCQsEXT/7MR8MoPN61Kkv6/w5YHrAxcZW0zFu4PGOPFX9vC2dcuXJYTJFsta4PZPUS3+SeI5m/DYvspl"
    "+IkKMDt13TLP9P5qFyXvQBjw50CnlgcpUtrspVFpWHaaPCY7ntYMvEuvyi5Owk+J9fZSRmS5jIGvcGXD"
    "YVtF9p95/Ny9sPjuNEsKrEFz7BTemuvhxT0Al4z3VGVnO7nrhGRKo9iOmCj7a2r8T4dP0cmN8ZN9/IkX"
    "5w/MIL9VLZ3ctFihOr/BNLq8i9Cc3gvgZhiEMT7p52q/DZvTUvPmcEpjk2vNhDZYQIBZR4Gq7ds2L1NX"
    "ciTwWZhQGkgALrwmj3MMydtMu9UAreylSjg3JzMkaJdjKq2aI6czLmUYn76jJOGbfWHyWyxYMYRbRn2V"
    "BHh923Ebx5tl0xjZ3swNSynjl/kpm3p1v9Iy8TZwajnxNoIsqKV1XhI4mTLnlQUpjMldT7qoxFfw78vI"
    "TQ1NmFrePLVVoYBhwwzhiKrmXoJR7RC3csINnVWJ5mj0mHQxk+u0wueLdgo9tGMA7hdA0pfK7xilAL0O"
    "m9DQQCjQbo8WgEWPs9v47NX2xl4W+QjhANqBzFUk9J0KEDSF7xGQ2P774Tuabr3zJXDf7hw9Qa7VB1fx"
    "l63XokvNJDjKuLmBH5jud0i1Epj50Th2a9xKFZ1gQlp7BRe7K/ck/5NUmy3AgaT57wkewWwrYMpRsfAF"
    "h/yO2Fuee68aRgVvg+/MtdOcJWzq7OnajekB3QSx6T1IxopJFPuEfKPedON85FcUgVMzfaPgoXzGH9vo"
    "t8+gWSIu88OGZ/FV94vqh37qXJlc0hA6MKutEyKxcraZItZ+JbYjYOF02VPzd1pO8xurDErGqkFDoDzE"
    "I/C4X1wmQOUrB7Zo6pYuuqPzoy9GenPp59FuDpPZ6EDf4HtnkhSEUyexH2OWG1al8TjJypzD+xXcyNGd"
    "v2ScqZ8iyvbj0Y8rQPKP7adyw9g6rfVkpUYMQWHF3w2InhSx27yenUXgu8U3VNvgwC/L8bIxKBQ/wE+Y"
    "zUPi3nQJB7/c6bpXkOvAuV0ZBA1wGaz7jqVJ/mZdd59NLRGySB6CeI0g5Uxt7luZ+XX/yb3tf/yPf2Vu"
    "X939/7l9ZXD70L/P7QMf0yygo/hsKRZanzHifR7XbEU10kBC+JubslB7sbqK17edIs+Bbapri97I2aUU"
    "jEQVnrKDhyhydIVlMf/6DiGpRRY3anKl+JSn4km4HQVEFl/8gS/QVB1YUgm+k5H+ftb+eXaQJEE4F79X"
    "PfNSBIXDnq/fx7cFANUpz66952DRHzWUekkjxiIgqHcC4z09BbAbnAoGIHTIEkmks0MeCwbro/Q37IXt"
    "jIkiAbaeVD9g3pm9eOO7OM77/aXNmfVJ6SBbb7KKYfl97fk0Dn2HAAwXhN1i8jFtygEZv7gmjsIAaimM"
    "yFi9u76YQQkcP8SFU0KYbELmZ7bJlO7jDdEtgH2MLi2pEtEiJ09LjvveEzmMPO8/bYWmM8pULVMzaHPL"
    "zDwX05TOG6Ew8gBcswS2DPFeXo3Wh55ZK01wb2y690v8MXU2eQfMj2n1WKIEaG5/PncCw3VrgbVT+o2B"
    "95nBZH9eFiyKzZ0kojT5+edCvXpI98envqbopJbYtE2zU3m5fK+i+HjA350+egcuV7wuR7wf+IiORyPk"
    "Wkip+mrkVmosLqfc1flJ91NB5jbBDYchuLjAED1vr+zz/IE8T+Cqs/I1TqBLGzZBWUcbXh9AP2518xgC"
    "GQdEokOG6QCyHbhyW4hBAbYibmIq2gZp/WgS1e00asVx5OKUIli0KKVr/KTs1XGcS8mnlRsRzMntUear"
    "ri57saUfjDpmGy7XljwsUQdcoTfC5lKvb7Z5fX2P+wFg9Z2VjR4O8TMkdU47Fmgrp43yi4VPjc3IWDeG"
    "5eemvE3EKp+HLnVyzskahFYBrtkcDrFRRy4PGU5SIitrXgS7tMxlOODi0Ok3hJlDxDhDSiJvMUjNfHIV"
    "qlxCOk1hk77ypzeKhn8WIyY4MLIUeblFRKdOkuowvlPNoDty+4Fk58p/9wxP5PLU3/Er+5rPTQfVxAFB"
    "D57SUbjNbf3YgPLXKr5j77ySBKscDZb4/Xtzokqfrq5EmnkaTEJsXJV9HsmYnPWMJouIgpO3rIvtVM9o"
    "KOa9eMEZSPbbpxzZTLfEeId+1bp7oNYkfExlKetKqqrqJhB8+oW2UKalLiUwHFiAyfztCKRQsCjtLgXw"
    "r1VPxN9Ko8M5ER020f0ZNPc7joeeBAAzRMbZVVzWfjo9+pVadjKpglNvPjRREVo6qmdWZYxQNLmoqWog"
    "6zbxtezdwVwDkya9MqaVlf8EhVWaDX7KYoon+p55EvUT/IoS6v2CS4pzuZSO2DgapL05OeZXvXXo3dPf"
    "dECsP71PcilcVgmCxXBhiZ2YZzpRyQPsrVe+JA92UYl5oLgaWKgtd2ZaLzNS+xENwXhPMSqE/oDzb8l/"
    "wCE5eR+nA9bzVVW4gQ5fai2fr1IZBm/pbJm3+W14Fd4lj/22giw9Rg+SCBHQBlZYEbZk2gJFWUJ3Fsa5"
    "ik5jzWB+XNzI04xWBBP/nCcF7kb1luAOs6m6HGx7anTuT4gAA+D0o4VcC1QQDxX37aNOwSFQ67aYP4nL"
    "1Zm/fehoI9UAR63yGYRZl0KPQe7OGwop+tMzVB7gCidqXFSYyGbqnWtO3ULhGDQ36hEo5Z0gZUmQzGc2"
    "+6r9DC8CxBWUzL2aHEeI63cBCIKcRVfbNiwVfNgtG+x7GFWJCSgP5s/lhAw/7PYY+L1aR/XhPXi9MLgW"
    "ZHsG1hxf847g0PwE+PSUpKmjMQ06uSgwi5TMhqr0LpFqCE5swjr4QnAsCSir11maCzv6v+88ynUN4Sjz"
    "xn1I+zaIqcYNVa17g2n8HOpjO+TlTSrh6p+YQsx6gy2TS7dO6aJvVCfQo4SD4lsYcYZpimGpuIHhCLcO"
    "bX5I20ZKGMH58Xm35UP6BeS7HmkM+H5xxzMA0MOjHCt2Wp2a/iXL9AMcBVO5v+erIRhFFmV+kGRpA5uH"
    "zhXNyS4TUlNIuWjxfBD3LbxCbDswyjELLVCyfAwSpuLoCCE8hHX2hDH1uCC0JJTdyMs3lCKHqCUJlVSt"
    "ruBCNFIWKt/KVLsBKGiFYpNKRyPXHspsNR1GK7Dk2bnAZFnWPIjKyf9cRl5lVu7TCMDc39ZeOZenVY+2"
    "H9iTayia0xRCPriq+D5xb/BW5z3QMkGf8ZfdnmbOWGj6S81dufgzPi+8z46XZXZfZ77SoVTEIXRzlcRb"
    "AVB1SRCUcVtX2rJTcXk/ydbWl4+dXev97+AC4P702Pn3XSjJdPtuHrvxN5l5jdZEwfd9jIm1dfdz/ek2"
    "9yqdB1vRHAghiO01RIAfIoP6v2cY8mvEAa6JsDXzhLC4QqFA2pbSgZSDzaeSFWcS6M4If9zoKsiH5BNy"
    "B7F8AYCVoRAdK5CtvBvrd93S+xpW+sK0thwug7FG/OQYKdb8BzCthJLi6xgLKIQ/SSQB3TskPvjuCxbP"
    "07qSCXigz3sePURYETBAUFrtC1fG1EQvjT3po9tGfzNKNlwzCaKP+OkGWuuTQxFi418VbqaGs08u8IaR"
    "Un1QD0CGclrDmaFOzWsbghwJSn8taMFkmu2ClwJflKQfWVRGFzpiGLys9UWLX/a8EutnUOzjifSAhmj6"
    "sFcYAmWBPA1ZHCg9vANuaGIDqUfa7qE64gimFzC8SpPQtJwp41VBY4sMeA5eSKaKiz+CbpeD+O9tq/A3"
    "NKPJkeqtTlfv5rtCltzYNUb2dmPl333HWBNjx7Z3xW60NV/DerMP23B0Nim/zwi+F4cEWKj6Y547in/+"
    "HCR6QJdONDNfoAMUv3pfnh2u/XjUm8ZW0ySw+oITjMxWKEoPYBHGBEIFReogieO/72UQj8YLaso5Mkyl"
    "wTq4MfGRQruWlumJHu55i7sXQgmqV27mHS9tSCNU4DH0pDEHUCBA5hsktRaP3WXAWZTEQHxP5dnzsyfe"
    "RKeEFxvOe3UftjXz7cefTE2HBtj449PchgysWj+bCYaECyzg2SvKBlb5P12T4x//+1/hdvM/n0mBwgS+"
    "vOsKgWd9sv21gSC4zzYTeY9+86zBOdzafdyE8/RgmPtlqZfkZx2QD258iC/XFvbl0nqN10FGbM/W7CuX"
    "Lz4RYfWyw8G0wH+o2hN/UU2LNAqrlHBoaUHmXzwG3vyO4TpcV8unxudkdI+H/TxfUMiJE6rFQaDCvV26"
    "GpFlMx+1yqKQECLntoKkr23M8Dj80jVFsvBLtL40kxqD0V4rfU0vY3GDAJpYzbxSbNkQSkIn9JElCg54"
    "hqTbD6diU3DCIOAcM/D91WYcV/nOgUw9nVRU6mj3mmcEAcfxznOzlZ5uJosBWoAj5fd7FaZXdfMguESE"
    "OL4efmQiAKP0x/CwEvxpPlkK5ywctn8iQ4xoo9ujpOECnyc/vptCYVS0PjlC2BBYrssAKAeGBGzrCUKl"
    "xxMjeTpLX5BOE1weuWqtmJ3BQN3QJOuxOozcqhxxFZydFs9z8OHyiZdFsWMS6ctbWK6TpnhJ+bLXgRox"
    "Sm4Dmb5OrsyQwdw/5DLQLcCWNLlVkggZ1NzJb9lB21vxDTsB+hsfD8HoJsaKWFao28isC0XqKMVyvI6q"
    "NS27FEeo4EYr2WEe7KeIvujvZ8QKf0aADX+rDQS0V6N9QflZLqW7wqXaggwZmVIHtOyQcg7naDd8M3iR"
    "UOjxpQUWH/pzeuCHN+j0lNudv7XYen04yYkQ3refmwbfFjE3Bju+YAQ5pKu0Q+pvo3J55+sU9xT8ElLx"
    "jc9ALcdd8INqr4eGxkxDZ50iCFu9aWLfPLlFqFZlJeqkzotrJn4ovUBq8e7drMzYf4p65qyV8/wttJRW"
    "B7RbB4SrGyWW0h7F6/iXD9lA+1XcQh3jr9EfAv7KJKbJXMyawNVOB5rIrxlJisdzLkM31luHzMuTXdcJ"
    "lCDjT6u4+LVdABmhWduVOYB3qDopj/SY0vtvgqBfaH6ewZylXyZSPV5i+KFUoregAb0b/b44EmHKWWaH"
    "PnqRMJ7VMSbw4ygxeP2htyxJU/tHR4yeIHy2hIvOIsyv5xw4dMvdFQFnbd+dJGUPGCEaJTsVSwuv9JcS"
    "QwCDWoM/49OfpqmSs4cp37X4fmT6Wj7+nHJSjzvdnDiryeqwZX2yE7Wx06u6dG9Z+PvFkNfitrrRF6xZ"
    "Mnf1ajVSnXhzO8r+dKi10jb6I4ZZObqfKO6UpxjTNE+5nmlMj0eH/go+03RexUQWf+2to/G/7TGi7Q1F"
    "SIs/Yh8l6LqriWBT3CU650BHV3Ggsme2uynJH92y1gtqz0arYrdRsEEXbsOhEgUwN9yH/cH+KQj6cxhF"
    "CHbZGSKHc84Haesvv+otelXx+KGf1A6WCRE7803BJ/WmRqumB9NSCtP0KFEuKkNcw9SCVI4i3lK7tr36"
    "SoOqSjzVzyLk4t7d0+KMuZxx76vuJ5MA98uoXR+HO+nKyyladIL615nZltQG96ykDPGZolBjNgxMJpyR"
    "UFc8TTOddPU/FN7OUBsS+Lfo3COK4QLGzvHNHAW6e++Vdw36lM0W2tIuoS/rOTWjhepizFuFpxCZ1ljo"
    "Od1b3qdqnPxQp7LOxskh0hF9h/a3rCdiYxPlnq3+09Qrq5mV5QZU9WqQuDHzSpMUF0QbT9zu34RlrHeD"
    "Ol9pdmudL5yK1KUv4yvluZiZ35cN7spYfidKfFTC8H2ucNh4udcQbZSGsp7IyLaoura0hLU5FiynPdcV"
    "gTbP7qFV6fVT5KQSJBF+IQrR8yFX4qjWeJNO9a0fAn0rYfCzUhAu/TPX8y12NcMOFM+v4zwE9fEzsduh"
    "rXj6UVyiVEFVZdRpTbPFxYlU307zq6xQuCaHi0RTvSLpYaE30W6iPn+plOiZCMZPCqsSKqU0VcHsjLZO"
    "zN/WEILldoomrdZofLcgZZUcg4yDE2Guzg0DpqsuE+xbqjZoxn2rpF7tADEd9rGoW3wLu7JowmX1hL8C"
    "kUh+Dx5WmOK9l2Jc+ch5yjW1CnfGlSRIzF3HqmY+dUYn8gZOEiJXkfSGLLXSYvK3LD80zeIzSQB4FZpJ"
    "IijE8l+v2Hu6ztSGMi+YbJM88JdXw6LYd/23Jd0axUpqukYpSaODuaXzeZkZ6l4m0fPYfrnruPlHj0f0"
    "9tBJpKuUqOpyzWKro1828M6V+W33TbHaMp2T+ExPC98kWG2ZEePMkV4WWBheQ/7u0nJegWH8s8hdZjAP"
    "nJ50/RYFjv82ZIngx0Ru3nNwpshW1XZDP0yBdJlN+yN60YTfC5qcGBf7vonm5s+x/at/cUPYO6kxOk5d"
    "rzZZ9gIOa20Zbv1oNDs/nsbeqcHyD0fB/Cice4n8TmeIW4BMNqSFAlaqS6pM8ZcDoBtYfgg2aDaZdsz8"
    "HeKO79ts8JoVX+xpGILKFzXhtp+B6hKExYY1rchAvrpNm0/4jFeVPx0dzoffjCZui0PCRpaeOZP0bc26"
    "ZiE5fCLkfU5/s9WnJFQwtRazmxJPJ0jcKWzK0yGgzGHYnleej07LP9qlqu/ncSjVolCv60WnuzQ+nECx"
    "7gG8IUkQn+DSglEWC93XaSlAC4w0B+Sak8AWb3ej8aTKfUXpp1RSYyCXM4sa7mSNdKw16llWWyt8ONTf"
    "E+xn/CnBItErZKUJ0x1IEtbiRugdJooq8+VUPN5bfKhDX1XetGQ10CVasRMRLrw7XACcb/2q7lW6UDug"
    "OCqTNQDqagsithFe1Zs5iFUr9YputuLwuR9Mmq4mCXIYwyWPTsniR2onbLl/o/BFZqf0iqw6yIw3IVhV"
    "39cKQhVcAEt/XmSh4sSDN49Lek2mvXh5l/Dci48nkua8cTWSJ4MoeEuJukxjxm96piKMnpUH6y+wQFOL"
    "QayuI5/yQ5j9b8QskMqIAKxaQadE65/uGfqP//OvPOtd/AdXr35Y+rQHXSGIlGsBIA1eaevOW+vexHR1"
    "aoxkdQEei5nn/Yjog4jwCNNt0PWNHPefTUBeaJqvah2sq3F9+RjajmziQeiYXIs0/W+HZL7eBGmJGJmf"
    "lM4lTtoKoMrvDhIjZwRAU3Sd5xmaY2Qe8fXEM4DAv0hpmEWOPOfL+6iZJ6s4EvfInoSmUUJqjt1nU52P"
    "Q5mwiesCCCPWL9KfDAVLfM/K1kty8yBBMwZ/4RfU5u2rxqwWyZSy/BYEqJJ8IVuWV1U6wj85XiDVTKk8"
    "RhhG6C2+fk39iqOl+e0NtYm2BUquXCeRVO6aMB5jOI9OtpkbBHYLfd/AFceKcT7I7JO64WiqXdR6EU7l"
    "F4jpTE1Z1OwvO2SwGbJBtc0zeetyVtNlbATzNajQFkYDLJZzFKS7fqrSqSpXDKIRsTBt4rR8CkPUxx8J"
    "Hl/Xohbl3lzt0Z6W7NftZRJdmDUfU397O2HGOMEC9QAvIk+JCNFWxue05b3I0K+URFuK5NCVJWQmAgLo"
    "5Kk8+rc49A+CYsXpKq4puiMkfZ9huGo+3UFclikSLxKc39IonYylJFCcLhTP13takjHuZsEmvOkjTJ/r"
    "ak7q1Cu9NcwWxZVzlVm8ZNGXP36eztxDHVe0p6XihYgLxAyf7Rclf8/Eva4lSigg1bLjaFkUcdnAuY3n"
    "MeNfyNEyim1HKOp0kxFZjXq46BE9KA+v/TdhS7Fj9EtkvXxLaTftT9vdWqt0ELD7JHk9LfgDAAAcjxLH"
    "MFhuok654OC0rIm65pqxHa6XqwT/YaSTajN1nZ/rbdih+TjVx800131u+m2DhXqtktHQ7wW6xMBiUsOt"
    "855Ib/f8oLepZ8UXkmH+nZedv3SqtdRHkb564vW0ldIn8yBL4JVnSBlGIV2BLDmfg8U3GPd836cdjmuo"
    "Rpkax4yzKInXk7tQy0IM/57eT2XssP/GTTRITKNQLNVINS/N/POyusZWqEMJ9hhDwBkwd0ol1tJ0Cp4D"
    "5HBlIc9xMuXZ9sv4n8PyXJBa7SxGz55DMWkSuuTYSRgF3flzVYnQKD8oW9pP0UbvQPRQOMruonyUmCSI"
    "tbfecZmmdSVsA1iq0640sypQHm3zcluDQGRzNId+YUaTbMyUcVLX1GWPiHfshhQ2+pJEZdoZthcAmq0f"
    "09IWqAxFgiHE2dyWCPUUqDmM+9P9kMeHVBEEWbU0xW96+hTmq4ICaF7EILmcwOlHepNFsXe9/tbUhAEH"
    "S4T8ldLJz6EahxnscUb30MHCz5YG+YrPuY4fBDhGuTT3lCohaT55rVa2Nme/Y51nGGkWJtKNYK5V+xsY"
    "h3nGl3TBhu3adRzB8d/WtRtehP2rBbW3hTiWQcs3d+4t+CksBozTS/pDXbPSzXKa04UtDAfFYVwv1FcU"
    "cjcwXdPRHpptVJ0EkPC5D9k0k7HGCoDpdn7BBK4Z8/oyybLy+/Yxwzx8Ph+vlKWnJgCWZV7fuNefdOqh"
    "l7/BI6pQgy1MVZYvTqK1i4goejrRSH999V73D9VQevVL4I2amPela41gv5fjIWwX6T3ZfraC7cdA976H"
    "LYpG+bX8VvVMuUvTEmuIh5j+UwHNbyyHss5XW0P9gvyLN0owioHjwNfQHN3JZqSkWZifdvMNlPiKPsM1"
    "kn1B/ZIm1cX8ywn87utDvq9VN6ugC3OimRmBIADGTTZqzgCMP20sDqZPhENzHyJ/WAE1ebSrXq1r5r8p"
    "BbHgpeyEkk25C3+7qseWcwZ2+Ar8NaXCJZjXBxF6OfD79Kd+k98gVwX6wkw/J0FPc9TSTMqre+KKpGu4"
    "LxiroRFZgGklP2DxWuTJUobK37AAA5Ahz22IoeH743lcuxdFNR2HSf/eavMg2l3zdsWM57DL3ZECn/uU"
    "4PdV6nxUAb74XRmFihSazusTn+ijgb9oDQzpbSWqMsDha7As++CUf2X7uQ8niqI4A4rStyucSHE8iZE+"
    "OmtXWC73mNFOp8lKiml7rIeNHMijorwMaOZe6GcAsrbKMnbJ8889Rh3kg/eQbM7d28KytJv/gxrqje1U"
    "RP/iFY4U4lDPTv/WLbRccWFeYwuYyof2s/F7c3auV1u+OCEtGfVXx71XAKLUjH/imXTe2T1VRXl8HNBN"
    "33cvIPAVrEwDXQd2//eIuVywt7GRIEBdXwxjOILQGJPQpt9BhBPGtPtxbPuPby6q6QIGuGDjpKlX+jS3"
    "w5ppkZolJ06WbgSreNM2QmgvsnDU/mdNsFKU5vCSHU0c8v33zDJdZaY4OTv2UBoFv12cN0Thmm99UMTY"
    "zJ889EY+xb/fiiPA0nUNESdo4/fDQAFRcZAbUhTA3tDpvAn+92Ib+R5muGz9DCjrb2mOSZ5DogjVHn9L"
    "s7Rdld/hVt6+qxj+/NnxeoXB92tP5kWAtzrh68irpNoK+EX5Le/rthWOosFLLBV+3056i1FZg9S0SPN5"
    "EhEfRf8mcqrv48CPNhjNeS6gI7utRsNc4VSTaEoph4IfKeZ6bc4v7UayX9CvEiW9/uY5egi9tlIjIe18"
    "VsoVjBZtRYD22JzlNW97q3duPGZz9LLCca+4RtsOp640ynA2v150QNhKNfKHKEqVfz0Yzic9tGW5mmXn"
    "9SbF8ga1RDaQ6ouCKYHiyIzRkRM3TVVmnG8uaQuRN8PdGh/ChBEM4D2LO9GadeZxpWy11pH5xaH6xaQS"
    "fxODRWMJAluMN8xLwhJAZng6x7Oedn5szesWx9sUKCHLac2yYo5UongFJ9yws7JwEp0zrjLl40Ch5X2P"
    "458a65QoAn6QTAV5S+GsVIcxwhxKY1TkI9+DrOHrt+rnIA2Q7Y4wg22kxvIsgcvGOXqbCdFlDYPfk+ED"
    "f4C+OJ4HKbTe6ptrau5ZNAUq9g9HIOmFHgpTR4xFyTNMAgXjKupqbvkB7q8qFBOIA+BiG9K0pHet3A09"
    "CKPcJN2SZIH0pvzX1IX6k8+WJrIbZeL4cZzk8MTf3Ci/jwbx23XNVScN9hA36E+9ySNQ6xNN/wa1H9ue"
    "z98aotteLNCj/dKks8PFqZ4zJ8lrKmruSbSmOT6Y8XZXnrgf8P1jxQ0wL4/x+U7CQLyfw5evXXbmSJa/"
    "+AfdWNyp+p2N0kKA6t2/GtI2Co7EWPh63gI9tv6iVG7J58VPiIi+OoCG7Bm0NKrZlTbWayYaZyHUv4U6"
    "GCgI3mA2qF8R/3RgiIIk2BOv1yUeHVB8ROUWu1CQ3GXRdPZkeb2kuZQPlqMmjUF72sdO2DCDE9lEkQ7x"
    "GrZEUskT+KS8SbClbovNapQcu/6T/ZH++7/9K98pWP+5BksQFujztz+SaAJlMeT9OxikA6b8nsG8SpnA"
    "Snr5IYwmW6mSXtupNk10MhGgXyqvnqM87KU4uu4EGwtO5y9JZDXvrl/Qfbhhx5sr+Sx+sla0rF5W2O2p"
    "yZp7Su5YDj4UoxI1k44jCdwughAuUmYEjoDL92S7dejO6Ky4vfcm/NGBccF+ao7knzIHIdm5LYccnwEi"
    "aNBkd6Awxeayi2MfRl/9Rlvgvh/GUdn45F9tFXsFiom8GJ251Jdfr1OjrdcyHac4SsAIzCXyDyOiY4Ty"
    "N68nHmhSjmI7ev0x9s8Whj8dV4cQAX9IISJthPJnbhgMbW0vfsq3X7FyrCud1/QIEobhY9JrofMfEMDv"
    "n5TQFZ3PZejWbHIEjjnNKjn6X/dw4dHCcB++cvNluE2Fz8MZPstzuCD0rI4/mFe/7ge1WLQh12z3q1QM"
    "MCvNYiTnaHP3i8sZuHrmPoCesxLm4WOYVDxgsgsqZiajPtwrKcI0k3x5Ms5E7Zq21tQ/Wb4iJS42X+2n"
    "QwcOf6Rkj05Gof6YZITZauOFv1yynCxj0wFcSwNCe8ktIexBxsFRegvZBCY4EEcTOMjP+cHf8m8V7Cj5"
    "+Ug0y2/s762nMIunKoT4xOBF7edjacavWg6XqjpTOAgW+7cO2U78TWw/U+tDmq1NPVs3b7cD0nmpYkqi"
    "BWKbtBb7JhOp/tgEWkn9afRrsCFIzeBTE3JqIn3V9zgHVLyRgqyblmSHhwCpyIYwMp6V2cNMi+I5m9fz"
    "0eNxDE+1H25/R7HhUJ2hg1bMKivkXR1EiB96eOWzN59CNz79F5H5FuXU6UWKxWCFwHEmWJYYcx5rsXBC"
    "NDBrXaA5UjlnimFww27ygAdHkyVQ3nkqysro+YzM0W4RxCWucNnmLQ8xexE6gSLfKMFQ1gv7jJyL9oe+"
    "mqn24i9hW+zFcY7We1B0Km+U2FHBhpeEedlDzBN9SeBhO5xbYE3qiJifVXGTYW8OQX+oxDuP8YQ+rwr8"
    "7sMvpf46RU8SWUUgXnakQZfO1LlKRRqqOO9Nj+2e0OH/5ey8lSR0/u3+QAT4AUK8t4PP8DB4bzJVKVGm"
    "p5D0CHo8sffW1VWgf/Lbqs12h+nm2+d8TtPdZByQzB6G2xAt/RCJmzieru38cOvKgOYuHy/AYQcfGU4L"
    "kQ24KAOzW+CikuwF/zTM0c8vK2spvNt6z0yN5ZGUhWNRg7taP1Dbaew/WXWuGCkq8ZNVGGTc8Jnn3Cou"
    "SolDeE2TVuYdJjvBsmNRoXaA31NRBTDR6RdyAn6ot420CewUHyV4c693s40c+aSjsrHkossZ3V1d4v4X"
    "jA62gjIAlfZublI5Joh6LquaHo8k5xUtdXl2tm1RxbTzRoC9JzdXVujR9z9opAfnIvjYulmaDfaR+MUf"
    "iD1j6wi4yO2W4PVpPc4E8qsf7q4XxKdeG7//tOPvJ5gtvaYcKS4oiOzgpeKgxhenDGTCKChQGg9l4R5F"
    "x5TdHp9vG/HRefWP/2gNV9Kyuyc9O+gbKwjel1C2ZOP4lNKSH/zTAnaN6O9c7TfYZBa5pssCiogPU1ug"
    "M1OXs8x3pEsLtGUHTKn67B1bRWouGNdkfoR30JvAc5ShMSBvMBmVhetjE3O7IaAsA2nXaBBkZI2epsEX"
    "jv40eteNft0H63UV0B6YrmjhX0TgqaLkfXp45NPbQ+YUyDXJ7utQP7p/xrHYGrzerhur7ZuuZ2Z7jjzB"
    "xN8Fx3u37RQNJnni7cgU7oYnvba1N/FJFy+jHH80lkP8G3SNAqhylk4ZpuUXjMPtJlGqZFIz64xhPRpz"
    "8q7NvvVwq8Zg/0BwTkyt7bifElyWl01LrTh93/FsoydIDHBiAUKA5ZboNAnFO8O5n1pxutscVQ3Fshb/"
    "eNAHC8cBp5oMf6LlmUS4OQ432OlAf5Sr4wQCzu1pEzAebDjB//neFcxZpzqPdmjGQIAfWPi9OhaiK7rA"
    "SykY2odA6u6Ixzis7VTrKtX0FGwTMon0RPu8rH49zikmh9ZsB9LCTUNgJbMNuu+sjvVlaZCzgbfBdzPI"
    "oy7iZCbPRWa7cEHiZLY8/5LXhkeWyLKDq6oiN2GePkXGWR5VtF/j5LCohqPf6WPPzWM5n9ExYH1fI4Ts"
    "Npe0AY7Sc8pwiVX1aBBVU/aSyhOFCbZIs9xjFAlkrg/on6WWXSO6YWBmtuYEes+Pw8fBEik8NLzkVt4W"
    "fMGxvgxzfWTN/5CAuF+B+aS/CDGkyGfpwNQbyGWDZvZ/dv29mezaWm45frhqgZAJkBOg1k1zfaWk+9xV"
    "buiW+WY+1sjQSEaFYF4brJqF6heKrd61eR88iJ0R5rOWDH5P7HSP87rMcLJLOHnHK/iJY/wTozlYliQo"
    "33qNPKCp40+bsmPIi/tq/KLr47nFKmOIu4fhISjx1hDGHN9GeFASX6+8AkiwYAllAOUi6cNZSL7ZwdKB"
    "B3kvj6YwQVEfKspMcY+RfEjJgI9zXVkR5QYqrPnz52V7bVSuMbGk6xlOt/ujOrOOAiAKJPie9tNfVj+u"
    "3VaZr9BYwFe+298mZw9HV9kpX3sulUb6BKkAnzFn4KGsc6L7caDizYQEADhZERBG/6R8gsExfwj2jHuf"
    "5SOatC9/LKsc2paEnri9Un5utDIRf2uqjdMXTrHKkBhyB0HSePAdBinUGgQ8nxwybyF0iFPGWPs9Mrg9"
    "QH16wdEHIRLfspDFX94R/7dcimLfzE7paTGj6p7DsOVilKIwqnzLfSGiC9jFQwoeQzDVJbgWO1v3jRyw"
    "Dw9l52k167oPWlF3d0UU5YO/ydRqoop9qpi8QeyNJ9nZTsbe+rw6T8dWgNm+W0jGPkkRCItlpSxKYaT+"
    "ltTZWa62rIAVpwKx4zuB2hIIAX2xx1L8qC+OTTMgUak+tRCyHYsHINfc/2WyeU1GkkJRFGDBR23b7mvv"
    "dfkv1tn/r3+yxxPk/3OPZxhc2eWEwLPd5RHmYJqVS8W32QUT7sXu8oiz8txMF7I4FN0vfNAqtiAEstx+"
    "iw+/O/MSErXw7Zq3Pbqjqg3LGEeiNhrM+EKqKKPvRDidw6uDNph4y1kY5SDihugyoM90AoWR5zI9dGNA"
    "ZknyjXfXGkqzyEyXDAE5BQ7oC2eefh/jxCmTfulTr9Me/cZdW8YA61cyEJMrEOFzwFuUkUCr1muK4rV8"
    "EIM8BhK/6sy/K5qyUoQ8uHMVCdLv9R7aW4g7MXM+RkCnrAhRakdjIpQayg3ZQv6xiHhFssV4LAenYv7S"
    "H9B3tQfiQcRE43F78Qg1/OV7Ge+ARmESQ9+UAJYSMKwEfRVvuOuSXc9h1Adl292o2QlVAX658SV93/p7"
    "3PsUkj8FfY3jkyBJr4RIzONRtHdyNIdy1VNwfrLVTdiPk4QNl6ngFTF9i6pqlQCG4xwoTLZovKrNFqoW"
    "tYz7vtmYnlE4PjlAD4l7SEKhK5VTY8YOBUsmaI3l53MyHRlv2ScqiRoWfhDQ9QD6T76i/M3/d/DlO07L"
    "jiV8/GxHCNCnJJyAePa3sRDPV6o7iO62uwBP5ADJ6bcu031DEY3E6Qx7p7EdLLu6bRTIQId6r+3lJjLt"
    "6Zhtq/sb9PcbY8YfGE5hQRIgSITG4RnosPuXaZVpxFPg9p3DYplcbW/UhbB2gE6Qa+8SwauW1FzSc1gw"
    "4o2dPuPojuGeXLyu9+zPPjab0+8znJ8g5FN7y1OvQ9J43TWVovXhvZP8B0kLKyHX8VDjw2hmsZZD4vNJ"
    "CjQ1hgSI47oxoaXzg887MnjL31FZlGJTQ7BGVoJd9WEedwNImRjjrPZwy4Ku714HUZjhOsTn7xhVgf3k"
    "FTQ8A6T/PkIDRXW1eP07yNtG3okJKaVsGz+bmu03oLx5+hVIAiIgRbEiQUbpN7cy6+C5VUPTJIYIMHSy"
    "8ZhCltbUvBjHEQSrqk5xyfNlUwTAf/7+XbxU3sS0x4Hy8/BnP57S35It2NsmJCyMtLV/bFeFSOk9qtpO"
    "37MJWffrl8xZXRi+BIDxQzP574gUX2yB7fvlLClaxK0ZTew2/ftVkEDAi2JFEE1iMx56ZEanlb40R2mV"
    "PRrGbLTef0ajDAzNnk1panggeAkjsowYEDK8ooYbRqQ4UKqiGH+n03lE0jPuF9okycg3m648ZtGC3hDU"
    "q4LrMa5PLd04h9MPTjyc06QpN6+C4jhoj/UNe2ZqKOg8Tn4FQXdMHpd3hB/UORmms6UHgR5RY3lVSDXp"
    "c8RNZuVV6wfUDeca//aiH4YdU45BNW1D6usMnZxnWJ6/d+/G93KA36JfOO5XlBXKJ1qt68prCaYzcyxv"
    "iv82/ye9GPHrOCB/MAuC57fva0js2Y3H2hlmO8k9BHUaX++TY9Aa4Xsa2cI/19dSnvrCKsccfrfizT3/"
    "5w0Mz9OTY/dKE9sakzhv/VfAg7333WWXHlcMS5qRfSGVly6sD6UCTvHzf6yu4PgH2xeUe0lvpbY9LYEJ"
    "6kZnhes0uC3RHJl7j673V5s+305WcyntyUjTsKc6Ry8G3hhech/rb174WYnNlPJdrCkAYMV5HZd8R3Pu"
    "W7U0a7SIghuK960zsZ6wyGTQd7zuts29wYg9/+bPjCIdcAoo+9c0h1eTNE7mkzyq5MphKi1BjOn8ULZU"
    "lGVRftXS3SV34tu5k3v1EtlHs39Vdu1uq4jqpfKf0nqTbGMPEDVHDsNLVFjUtOp6sFEiC4DiJIqQb38l"
    "b6aJFmOdrj91t0pL10GCka6HRMjli02/A4BgRFVs9W2G0wbs9m/PQ/Yn369iehliiJH4xNcz7tVIecdZ"
    "IC5CxEkwVXpN5y2/ZVl2+7N/RO/1VkSLtzV9Ne2nnadOc4/6JAh1wJWtS4FhM7B+7CNGAkUvVaedlyDq"
    "7ERfc/0Y7HH6Q6juCGGIp9UiEOtOU3OfXJg8h6E89KkkOBmRLsxQbeuoQqJtIKPjNv90+clQY+/sWU08"
    "r5faH/roT2kAUvQ36axaI2GcZiXwq7BJPhohSMyofZRxj8U2HaTWdOrjAEGgaFcfXWkPNIaR4DLWsvR0"
    "dyxM6h2h/lQTv2Ev6gTcEMoqjwt4ViepaSzDCKJlLJekPsx8G8ymBrHdb1Rg7929PutNN5zNNebbXfpj"
    "GH+36Nv0g6TndbwlxvSzdRqnctXTImPTJsP8UOCDrx/qNEXbiUL/zW4C1dyQLKtTqV2nUL0AqqPGSy8c"
    "DRnilwRMVQOXt7rQT+6ycRl0W0o+pORXPxtpFoDKonQ2RsR9A6qnwk1232IVZaXTmzfcjRIU/DxN8VUJ"
    "CB/Azxet81DCbhnPhCrp2RBCC8zf+GGuzBckjGEcxhndtOSjvUE0x+ljQMClWlUY43nBVsQPWgZZcw58"
    "lViCzZ83Xx4FE8NL63cyYFhEkBmKVPANRoOZoE9eHL8bz/bjCuRLvU6TveWmhep89r9sdrHMiphDsi3+"
    "BN5mGkwiMEoDcPJO8nqEw53F9rrbffSacIPAx+Lq86LaFR4clblKOLXCxaZpByMLy/kazkD1/Z4WCefM"
    "PC2y8LibPK2oatjASCdu/i7g6OirU6itj1uWpUW8/2lq48f8Ob0egi7JJBItfVr2HatpTJmp0YPZ5zfo"
    "Q/WSb2dJyZ4x18Bu37sdLJLCyr+1ByDuh+E8eAHYHtuRlz0US86JfsQKVkAbeyC4pMwB2u4+ecYFAMOT"
    "oUuUBGH4wK+DnoVxz+7AgSIyJeoe58FTmr1zd+KLC8J/ua7mf/yXf7KuZvl/55ZxxofjUCzB7ZKOEjly"
    "yHDdHIFu1qroKnKFmVHkOLgYVvoyrhvLp9ve42My/XIdt8PP+ay+qNG4ouur8zpHk9vbGdb7TbD96DdB"
    "xsxPhZzZYWjXtg3JkVZhr4YNBtEsI2IVBSEa+jad7/YztYCDhJpBcBxUAR+lcxQSMjUHvbJ/Y+PjX8t8"
    "hjIeKp+kxXkyKOlyZUnadJIAgO0tzAX1oIPyHb7TRb2ozlks8HpA/Jg4aO3PfoThFCsf7/2mBQrmuplw"
    "T97OSC58fYfcnxqLpJRRL3xPFO6Vthcdmp30Xr6vdHgJPqPkYHNf5mBdJWBZmKgkzrmBPttXXdBa9GGZ"
    "r9u9m3UKpYiLst4UY7nTtk36ZxcZKOUHCMdDHvwV/eIeum+vWXqhmYW/HEjUos780gDuIbRTDpNCygCl"
    "+hX0YSQGdUHdU8NQpbOlMpjsOTEVmswY6zxJjllyqJV97UY45ntzQr4V/s4gxUgbdZblw/xyZGieNUj7"
    "81PGX0EpdwQkoBLCVnfD0MrdjyPVdgY9EO6xUQPL0cUiRjKf51yCul/TSXpUYbQg/az3+g/sNoyZ8xsf"
    "4XIaJwgse5STal2C+p/8u41FBg9AlYPS9vNdN9KJF0vfXH5e5oVCSBSK+/KEOXQJ277vBPDJh5WKPazY"
    "BGVdxpllilC+cxVLETRUVBraZ/Kya/k+Cs+uq11YNh5mGTVM4wXExSREc4RroX7UQSoRO67CLusjAG8f"
    "QEXRheAsXAgSVEpCOBi7MSokTaTKemMnvKPTdB7D/ehCF6y+orGNVrXuL7duxD4aGCUtAtwJ5poTZH3a"
    "0wmFm+1oA6PEByRAVevJ2oe5JMPzYP6UST6Y08doAlVzBcdWb+mMcDtQJ77+rQjBvuijh8ZAwayvNaGE"
    "IkQTK9RnYxQYBUNKQUGXOyc4rFpIVlYQgpVQetwj+NXDx1JSY7mq0rEWRBwQqVtksMtCfcgDDkPh6qq4"
    "i3hNU3+d1vs6U9LVrRmEUqPn/l6l8wv8qzIvQYcP/vbKAAdzfeAOxBD2Dg9O/gMfRLe4gNJl7QoOV4y7"
    "JY4eH7lKdTB8VU1Y/PuOctLFtS29UliLXP2Z/5asNnMofdVs8UAVWndvXMAL4RYKnLHWSE7MjllVfnDx"
    "kNdqseZPm/gVHvWpWXLWbBFWO4+RAFOf7wPk4CvR2+br2S299SHTFzLfi6KGbSFkFMs0vswMjOp5n1m5"
    "/eXNtt9UID/2kMA7+SNZJfM8WOnvdRoE7zwR8WYTtd4IKghiCEswOVWefrg+nseFnAR0XphkZ3fURTwi"
    "JDyPZp7BkqZC9VNVTBNZgKNZ/UY+FYyp5vpGf//rhTXDyJ6J4wtucEcCs8Crk7cKiYHjXmDGSRL6Gdxr"
    "XKGxyxj8sDYiG3hut2nWNLxpevianP2Eq/RBWj51RMkPXAWvH+90EXLnBT17WdRB+dywP3kzQ+uRwb6f"
    "w12c8ubF3w0AXvV8R+Fha0gdAqq8lE9oTY8Xty7KYeCm8a+oBMjiHy0ryqz5q/Dpr34DFPjMCHVB5B1+"
    "CDVGTmFLkyvULIh7WYrxkLoqW9NRSktFreayPTkf8YvDsjfsxPaPR0ZkMafB9nWnQxqIjyI18TECGa/B"
    "87AWNOKfS8HArq4Ls9keg6cQxda0OMdhCt1SOVXYYJL4m+2K9MT/XtsRhP7Tzji4xN3cu6Y2Z0pvfC0v"
    "zIxPF8uqXBA49jO3gGItB+B4ATJmxu7KxlQ7ZQLyHSmbqb8LOf1E390qcPwtGhfvLQfrONWX/sKpt/W5"
    "4GHioqoyy+uPpB2VmW/J1svbfnHuIEu6Tzp0q7io/219ZnVuW+ET3Z++v1llfcBXluSz5chGn7l9+147"
    "Jz2+ufTyiiD2lujfNLIk3kPfPr/Gchx55Q/FtdZMg1MJbYvsa8iVkk/QQRJJEWQWeqO4qA9MByIRemRl"
    "OQXTU9Er+RxR4BzfTHqoizAiKYcNvFgnM1Z37rUp82GnOTOVc4w9lG3O7IhKkU2H83Bqldtp59vclRWS"
    "NzK4IL9eRJDQCxeBTw7UkaxBgRiuSq2Lkt6nmFdjhC6DdCN8C3FjQL00f3Fpl5afkhMsOF2qCVnikJvz"
    "gM+SFOsvNovKmYtCi4TJE1PSt938fLmMBGt4CDVSPWuKRcNQ4q8ZznbH1OJKl3k9CZoLjMtFVFdBZKHz"
    "bL/77brQJt9I7opft5pQSqj2v9fUgeUTQFaZ1/vGv/DLNgtJ7FUmDdSsxD4fnTJj2aZHqlQKD1ZcI5F9"
    "2QO49R5lh5DohWG0GVwakohVLmqybAbMSB+dxzz423ebU5GZyTD5+lJn/LdApZ9b3xzDjm5kHvLm2eLS"
    "59eSmwXPe4v3utHbR7l+gFwGLSjKzCvOLQUhjmP1fs/nFkD+JjgS6hE0XQDBC2+4fkNyRo+ed6MiLvDe"
    "oFC3E3eyNI2P3NT+jCSxQayjQJJmMu+01jj6j4fQL3XJ6nl1hbVp8kGDxvQRr9++0BFoGT6qpZxDMQ4n"
    "orudpLDF/ZwLFUXuTjH+yzSWueohIrTpoXmps6FfBB0KnCJ5/vNsAAPj0cpHzIvNkX+1S+45D9qDEqfp"
    "2HQ2bMPXQ2F1ST2mYsKF1GO+OQY6a+4Hb/sxKf4AP/wnxupF7apfwfByJI+T773jywK8fbgYHCephqGl"
    "7SK+ys/CL5hW5/EDb0NJUcJXKZejM7OJj7o6FCZqRn8UFWBjNwi/OFa+tbzm6XzqJ+QXZeKliw3v90+v"
    "qqCYLpMQapS47K7Yt9w3r6Gz6MnEJgKhSNPKNTDQf7ULlmkdSUewURETORZDfalCsUMCudiDp5t0GyHT"
    "QugWBIF+OaywpzX84B0e2o0Gb2vDwb+/+Pp1PUUbOel34C7FVPpNiVkQZ3WITDp1vp2+OjowPgbnW+cz"
    "1L6VVWWK/ABZgCsmab0JVgEfpiowFxp7z3ObBFbRsnqgwJYKQPBYB8B+RUMrUyKwxvLvgiW/Ucbb2Gmb"
    "xmgadWif2hk1tri6ZXtH76eZ9FEql6LPxauDwcVEOxh4dIndM6ncyK8rKm6B7t8bCF+WBtfykAiLGqij"
    "EBrA2cQkCN7c/rmU6iSFJCKFT0QuRtgEn11qgOB39AB19r9rd0Fo6IgUXG/mXF3fLQkPLUiuzY4uNyxF"
    "IaEcRPkKGTR3n6lxfD65IuJl6odzuoIJ8KuvNQBexq+SHQVaU4ueHsLBIiv/fAEW2RGHFFMHX+w0peNy"
    "2A7OG78MrV0x7WP5oHEHAeKdg6OYHkfx9OX7xZTQMsWjSRPEaEwW2KX+cQja+twEPqlHSvz2px1MWlxY"
    "6j6A45Em5Zu5AHQApJeZDWYLwA6g6r/em/C//8n6HO4/9ibsQRhgVx7/nUMPHAT1I4ZHOXEdyftn6l7f"
    "JT078WXNt2tUjVlFuBqJst+KF3jM5lkoYBpB/zv8X634jjzZlbdJW+bd24xEtpfN+stFyjdFZkVg+moa"
    "sk8MkDdOGDtaGvUwTUiNBwqZPUBRph8KPuYDBCcQPEOQwAASgjY/tvKd01nADr8hZhDWdq++q/W6rx4j"
    "xjImI6HWdO+q5Qvs3HcsAdr6ANigkAXNjR2I2yU4q3fGCfztkdmgBLh096JP9acBOUQvQvHYvD4o1VLY"
    "64/6TJILICMKAOtw7dJyuuXxt/PO/0FG4VI2m9g+Sj1gQVFhUQ6mRmXXJ7l5HZYDBgAsxiCVoxy6EZh6"
    "NRrztnBUrSnR6ozxx0CxMYMzJCYJEx/t0ZfVvv+Mx24dIMntFFHgh+8UmQ05dkp60o/+Ke+YgN6k73FI"
    "ARw/7mCVY446WkAodOEKN3lynCjh4JO3VS/1MxwR4uGMbvtUuRY8OXVJQDNSuifsccb/HJ+JnqHHCfhV"
    "saM0NGECKKJtwQNVhvvrx2yOFh2O3caElKjorV8HqpCJTB8h9Nnx/lw4tgm+l1mXUP69iG+OyCzMdAgG"
    "y8FCWcfqwGPrti4WEO/+9PnTtDtftKgnmgpZg0KJOFRWlIjZvLh3orXGihfIL7oWalLIDQ4k7nE/iPGT"
    "dGA+ANKEEslFTV++SrY5rO+JRKFLoupKmomVyKnXMBDaZKUFgOU5V2YjewwzQ9DZxyjMsg7C2OK1MbqP"
    "7ZsNy/GBDzSIcDLEtpMkbbepUXTCGU5qmhP3+uyEKB3uq41nqWed+d7EyCaMmL/SGC+y7Lk7rG7Yel7g"
    "lk+NzCRzx0vBT6BvoQXAYvahNhl/ruWLtraOkcxzb4OkCHhtMxkgfWqJQ+W72wFX3r4DEZK/RmIaTqG7"
    "JICZMKTY1popJfWEHBK+g6z0GXmMzEDkBXX/YAVtCnIEh7Wu+NylL3yNaHciwd/o+kk794jTowv1W3jZ"
    "MoTrEdWOl9/QCTi16K4rJme/W8KNSh5PIiErzPmKcv1rxNS7aN8vqvVuDu78dIHGGzQj32fF0xlbvDfe"
    "yXO/KcwxKa2sEDrOf77sLA8wTdLV/KakSL9wFJjPTCU9c3pCycGHb/W9eDrKts8efvc+kkQxf0AfxHfA"
    "KFMVWM4+Wjjx3Kr6i+6St18GS+t1D5tfhYe/uFCfz1mWPj4blJRdmVn7PxLfpyTL+McRLJuEmRrKf9+/"
    "Z+YlH/ZtvjVy+3qHm4NBD4GnlJzrXvlf1f+Krutl02/lPpn080YCrT5sS7S/ajvhORp+dmYV14Xs8akm"
    "PaokawtE6tUClvK9ScA6EuVyEqyyRfJp8KdHzflLaV9+XU9eleWFzh1Zeg6RgEh/bysYwE+2+TChdvwW"
    "9EgBK9peGRQ1CRftrzCykvB+VOBoUlyjff/a7xGk3+6g7tnfrIkot57YXOjorw32v98NfZmfEe4IbQ9T"
    "jT9D+QK7mcfrj26SJRn5vkK5bVzT3PKwZkFMk5/KRvBXpVJ5RWO1WgriQfmZ4bAr/v0ZLPG3kDo+P9eW"
    "kNLWdHrMi/cHEozUrDzaKwqmwuQxyWK7ieBZUL7Sm4XiLBd6w9lM2nNVvNF+u4fCLzV+6txMeX0lpDXf"
    "MUNOjX6IarWYG9mIL9IQjEd+EOiQnG82Db9OKKxoXd6G/Bq4sfM2zFa31fXcaW6m6vrsuj8GuPQWnvZF"
    "sxnT6ZpdGiYmcGCJCpFv4XSXJuPp90Ikr6vTGLtqt1ZxJCND1YBAzF+18Seb16VZdvTpYPZFAt7MhHhl"
    "hDaBJuDb9KYC1A4ewcmvyDfhzHMGhQepeWHgBar1ce9yiqeFGCkuHiuGVPtmZBiByZP9RwLPniaKmIE6"
    "7qtOz0zmfUFScCuVXWvZ/KUTQgp5kE0EzThW1gPOCd8SrN0HMpGx6a5k9sOohh0KAAUeZbAvO/E8a0/1"
    "O3mivih/5wlK+HSSRt8dMGiSvNleWb/M50DXvhFz0ZPYC3BXFBB5kk6vBMTFnMIP4jjvzf0alBXBx+O6"
    "2Q/Rxe+G46kIDJF/S7SpcvZhTbYqstgpM/QLToUzSBLGpYpq9tcs65D6k/V7FeZ5CNg0FD/qinFevTib"
    "93Vn7aoxXLLgD6lrl/SyjNvR3uxiHrpJTp8OIgW5zS4HbMUA7ZUhq+7d24rXPGlrp716mkfJvfCGbF4s"
    "XUf/dsQjG06GfINXUyFpMXQ38FH5A9nG2e36tD86HLrvuDILfCeACvJHZ2TzLhgIyNaPEDqRsU6ZfEYz"
    "hf1R3Mjvit503xeSa+bzuWJ8lX5PQ/z8iGxz6j4jUD6EqPBjN050z2DJcafK2DN68GE+3zZ8E6o66Lby"
    "IVbsEc2wYwzO208EXKXwdW/QQhloVTW5NZl2clbRod3nVqgA9Y0kTkitb8coMZ67NFNKY5DZ1Jlu3ZVu"
    "XTUMK1xpIDaMkOP6KiBe8Nvvx/QVUTbncwVKVUBDCDi2T7Mkmy+2DA8LXVg7Gv8N2jZqLc9YAIdjbsDj"
    "rdvSn+9XUkasP6m8CBfYYpi/Ka5tc9oDAc04ZQkoDHEJ9Ia9mDFURqKgifhnThWF756bZplqERU9aY8u"
    "di5tISHJtVzuTkxzsMDHBFV7nmo/Qilj3laNuMGsVCfKJ5T4Qaipa6ANKlPC7YRLD+vwKtUhxDfE433M"
    "slF4ireFApKUaZw8AEYUPdx7lhv9V7AaeBXypHMqO2EL6b72GmVvDjJZQxVwYc0sTlR4CLLoc5q1iM/8"
    "hXHDo/5xdHnS2QjiM9fdS2//Sy7+n/+Ai0XU+49nC34YIJcHX34O4A/RT2W5xdaFiIbuC2eV9fJwDuKC"
    "tLGfeg0vsB03X5HvBwvrPsC8jX+vZBZ5WAb76eJLL/c9uxP8O8B5Xwmsa0QMLclsdnmVlAmVS09IUJ3L"
    "wuL0oywy1KaIRjQa/ZNu3UzsNlgUK4knCQA8GsHho5IEQm9tJ2Q3smMqte6C+reJXXps7g1O/545Ivic"
    "9BO+J/04BzbcepgOfEa/fQcHQnC1CICFGwxt+/egoESSBB+BaHcSWlGVibYgjT138LODh4VTurKGF0aW"
    "cHkidB/1skjTf1unVPO3IH5ZQqAZhHXTlVA7c70n8JCw/O0jxY75b9NgXn6AYSq+W8lb3/HOKYoikPH1"
    "7h6fMuPEfuU+DexAAoUXxbXXJK6S54/nsEoltIsauR6nzHEfdnskclXWqE4rwHkYjD9ajz8bbVUylAOe"
    "S97k2gvYrnxjNEbEn/5AeJP2VNBH3lgrdgQe4zyR32FFUz2N3z64+gCU2cbw2B/knVz5QG9lPr6eIOuy"
    "pQGcuWehEhSVIS62AoKF3vzXu70uzsjP1iIoQZ2tXEkWeYutLXYCZ4aMpmDy5IpuZjfrjWnMqexvD6Ox"
    "Q3Y6kE4w/MHzX84PA/G0xYT1civwOo0wSk7RNtVi3C8v7Fn0cZc0LMg/OBO1o70zy7Asp2R9uYyBjy97"
    "rvYxYbrIcU3hjnMzxizg1mIra7bP8DS3ycA2ldoxM9XMBSndIF3hQi3ga3IXN1OwT6y/IZVZkpCOcYF9"
    "pOJqph9oKzlvXImGUGXPqxiaDkROaU/66WhydFJ6xbeZZeKH8hG+kpAIfeXxCzUaARwT2dQugKn+ACbL"
    "YXHAWhxUrKlgwQY0IF8iUmqXDQQkBH/suraNKeGZT2fFW8oOCmidCGkQCJEfeObC9EPTzqW/mbQiAGLN"
    "PzEs1VYU34x7WhkT0lLPtK0zITrXHmtq3Fydf+vw9ytV5E59q9jR/CjRHM2pXPyk1U5j79iuGXguNQzG"
    "KZDoj3rC9iby02mRudNWIi0K0hpwP/yQhXEn62BYnY2/T7XRo7RMw33ct5FzsiREhf4Wtq7b4iZfsZ7g"
    "bH/nKAF07Xoq7TStykeORqus4HD1PFZEMOmoTdaRNcnx6aw2xKtfA0QRVzOuvw2kTUQfBlasX4zDi7Dj"
    "aNa8/ZXDXLkKaARjT4a0pZUubq6jd7v+fPIXzEVltBrmFRvIDaSUOjIaZBF01OGOtrm07f1WqBhTyMSY"
    "hqqNpridbATqa+mBoZaM8+reMtna5Hx53kSMXwT3IQyUG/AGmHZnB2mHyUbdt5GhOY39VYwuDPz44mGH"
    "qKNgG845sGJCKaOhqKofsYLwxhb2LJOQ9yhMH7j6ioaOh3ZRUGyuYTP6onOZBjAGObP3A5pE/a5zDdu/"
    "EbO9GXps4/1NaemCiO3G68/SyLd3MnI/fTyPZr5MWlYfuswYlM42ZuNkEz+Mst8cnhHTghoan5eZqa8b"
    "wiSStbsGFQ4a2vBqjBYfPiFI1cbmDKQBIfYH/0dkIa0xW0CR8Y4dF1lK3Zz6BVUrSqvZDC9O8/aOd9bT"
    "X8djLNpmAQIvdkKTP+nJSL8L81XgNwh7OhRBfWZG7814En9OUHuFyGnIsNqbD8+LG1PJVUNL3IpwkimS"
    "rBolLxSu31uzlgUASI5mDIp0zE6QK5mzISMTIHQC2/D7gxzzewwgLbUffh4ggkRdx3j/xBLriyoUVpR9"
    "WN9qmn6iVz+tbzWro/JlV6HileX5tP2VVkcOU6VE/y30sRzEYJatj+/XYSHE2NIM3fAi7vrAa0dFzmxO"
    "zLRaN5f5s3ERItenKT9ad5M/kT5vPpYOADEn3xzR/lRPczJEp41F5c4G5+3A66HMidLBVIQ3wVdUuJtd"
    "eD1y3dV/4gg10kj+hPngT52l31aBR09GzFuA0KfzPiv6dwjR609tIFyF4bMjnO2H+HulCssAQIzAkGHX"
    "We3e/BrZtiI7mEeHLGa/zhN7EKnzErTIa+R3gePaCVgeJ2mxQ/MaSbhsyM8tcx5IE4ozhmLc91AbbNMV"
    "rhjNrywWx+U1qb/9qifORME6VfkQBy506ZHkQDnH+t8Kxd7vHG87PIRGTu3EThRIvf2QX6uj3RB/Mv6r"
    "kB8qj5Zvg1JRWe5cY7p3waldJnbtnVvS9sFJfDjSrb8p2+8LI/RhD/sQJYrAaucuHyzBdtiH0cUNQ3Ef"
    "tQcAZgrtlDg42KT7cZMZyasN8O3oc5XxoSWJdeK0G/92fnZgL6ZVcAMAIKO4jWXm/be9FzTVOQ+TX6C4"
    "/HyGzIll7HtdI7g1h1b8uhf9UHuiEkihT248MwouYF84LhsLMVIMf4viO/7Lx4omOOPT8SDJyODypMqt"
    "LUP2r/YN/td/Mi8J/d8zU/793e2w8/fudh2kGpMA8t+qbJ1RMbVM8+LKfStPraS0/ar61hLJWHA21jmO"
    "ChvD/LNefP4gvxoR7XKSEERJZ7ge0aT5LfYo7+2WGCLkMq4jixAvp+2PrZsnJgzkKEgwlTBR5sVmc9cc"
    "xQ8Mj4GkwJ/nIAniyDAO5F9+Z627rE6uOvZYKvk9QIWVZEdNYjJJp8TW4gEr69824spmU2X4mQo0XY5N"
    "Kd1aX5cWH7ub7+QKZC86dL4u+wamdZdAiyUy8k1GBVDq+WZ/X4dWLl48gsUSzescU82q3SnDXl3UFQTM"
    "PfSo1xBJOfpDFqwzLiBN20ZIDLiZyPwIizga/7nghhCpkV6NCOh33PB201Ts+WYFq+72AllR1LJSyHxI"
    "LVXgOz3ACjwgJ96TF/MIg9bZA9QPBwobaTvIhUOIPUyXaUsjwcJPi6aj/SHtziD2z95VLKAfFdyBkNBi"
    "3fLrYh205icBD/OQNglEX0aYSqvAVq1bCpjKhi98CRsCx1uPNVqAyk+Bk4fCOGRInJ+61xLi6R7kmlIW"
    "n2z7eIJAtARgxj6/SLcL8UQ5/0CzS9SDLn2AI4YqIADz4X5+lPO3E/SFxUcddYwIU85VjjXTDuqLyQ/6"
    "m0gw0gkjKp5XgGYAShklgAVWJOcpGM9grmCUv+gZhEv6ZGnzZLaktTj4UEWgG0iKNO2ht8Zi7xZqdr/8"
    "fe2ojWqDSs4dK2hRGX0GM2Dkg1KhLfC7WZfrQOe+ytHTSTHPl23e5N7Z2uARDjAdyDZTru9K5Khz0EpY"
    "0+9HIfG4TFOtB6WiNBLcfxUjPP3JWN1JM0WBJk/3Bi6y/S6uA06OLpnt7E+n0w3dEByL0H5KYiYSgNLo"
    "0znp1ckJoJQTVstOmnUEon12h9WGL1Wr9goW7d8REGAyj0fi1skCozpprRittDS9iqTSe+2SzwO3zA0t"
    "z7STe6EjNIY8DeviN5+5T7+ZDTpOXQQC3oxHKnN8Wr9FMEAgxB3eIP1SV/T2qNT1ksICk8pgHObPgBhV"
    "PqYTuqpsyVJohgMunh0XiyXDgS5lZFK+ZxAqJTVePva9ivUoNY58clPcfCjypjE74OhMzgwQKA+LuWHl"
    "fC3ZC+roqPa1pagYrk6u9ZdXWK0i57xVKLBhIfzE6QHOrCsJuU8Ns+BouJVon2epLdLun/NA4eiKU1Ci"
    "EwveIAkIJXXDy1HSZV6N6pcqdcGB/JJLE0l4Lzg6msXOnPhgaxXVhLbfR4M25QtIV7dKuvBSyK1a4FgV"
    "Z/EiLjODCRNy8+rdLc3wnhMdjA7NnygctjwsgxZ3ixZ0twV4ckoUu91viJj5qFfPK+jTEOSSotRqt/7o"
    "rN8K04UfWfyIbaDU6vpZX9VhmctUiLqqXMgUTALjZ3q6GXB2ig8Vzg0TzRWjQc39NX3d0O+k7DbBDeqi"
    "+NEKFn4xDd5FKKi9MHXG9h1I8JLM6aG1O1Z87StykjjuxnTqX0yblZ5ja7q3vVH2q7XyIp40ZKkE5b4B"
    "0yjLJUzNAhp3cNnuHoyGmKRnIDwCWu0NsR54lGYKFQh56pfoTJLYj85o1h9YVgQtR4wau80OKhYt1ui2"
    "ZmmW9wwahGjqTbL9y7CMY3ryKSvQ3LIdjV43VzSyog4hZ02Q+MWjffTlpn+WE/sYRA/PFvFrn6WK9PPi"
    "6syoREx4M12VW77/dzLMPUCwLMvZJ82balMj0SO3k61VuYqTlEHcExrOohnPXD1H53FrqFKKx01S2cN/"
    "KqVq7z+J6VVK4EY+OoAqL8QbovVc2O5/8CxIjQe/9wsorUELgsD4GaViOKQ1AIAaMRvy1NdBZ8gX5wxb"
    "x9jgSdfTkeTWuWWaVpVNQVBlmSiYJE5XunXbeL6l3HjZY5Jz0ip/2BKXZQGA6NixXfj001JQ5uczL1My"
    "C9ULEHKF/UzjVn6p2Xx+Q0Vymw55jjkz88p+VqGAFJ4npFejGI8285RUxTWcBMuPNygCeaW9R7zkzopu"
    "dL9h6xf/3LIEDXRZ4L9jJaiw38Hdmqd+fVq+gr1KXgcdPvqS17Vv7kM9Xw1/7+H2/C4xk1GmtUFnvFVx"
    "Xn2jkqrC5ktnv7KKO5LFTEhtCLDPhD6a+6x6N+8VoiOcU0TATNn7ORih1GP0abOurdV5jj7y4zrWVTAn"
    "ZbmQzNDy37kfZ+rsNP0bYg7z5NTo7IPFaS+LaZ1mGLoLTWhsQzr6SdhF3uut8re1UNaw/H5hHHu+WBP5"
    "jqavn6YFvMz+d5ZkdvuQH2eZX5nYOwhZtuqMNJgb8x+s0t8qlYVbaOtbGEtCMYZRSALb4v2zGEvNK8/E"
    "/Ly51bk5nnE93DIezXkz8DjYs2Sj0Rpqn1e9B6zkxqKXOBA441do5xvLX5LTpaAWDer9gST1XpckqMeb"
    "Vquq4iJOiqdVSK33+hP767Mq0WtWxwJZMOKWoZu0yKeTWfDPVdFyr3G6/g00/2j896c5I4mhckWN1qfP"
    "7nSjKABASBrnxo+5uOLVpjthni1t/ta3PjS5wJC3r3VNj3m1+skCywzMJJSGczQcQnEDCgmwSE/r2hU7"
    "9au9Y9FxYwd/DHzEpG7nqvhTvnLxAH0RIHlfR781YG8kN2Yo+QLp1PTKx1QDrR7W3OPy3Pl9qKWk+0qL"
    "vN/ou85lXlNpJtSOVfj6k3BSwPFGdmZ91u/DSQT71VJM9tkzkE96VO8txQca6+WfmD83a6tttjD7IIMA"
    "tRcsGTvF4m5iKYU4Hm6HKAVnVHWvUodUo0IwH4lpB6kCx6AQgKKua0hdxqwfQcuELu1r8LOo2raQG3eI"
    "cVxaqKXZv21hhCC10VRCmuvUHxZJxeZldVNHt7wD4gcoJ8I8ZKZncoRd6YC/2ui2hyTH3ioTogl2QKxq"
    "mF1tFXJR+1y7xjSAuhcxxTea0BOq4m+mCT+wB7kvFkX9iQ2BP+XCeMs4bNIX4X8mKqXCxcrg3RpmYALB"
    "Fl4RiasnNeZspPbe3Oa6Sc4180c6NOJtsBIb2pJxlcqN2Q/Oj9QE6nv3PuZPfqA+ifHoZXIDDOhbf7Gn"
    "xAxuMt7uHqPs3xd+/3+ywX//b/9k3TcO/efcbBEyPu6EYJlTOTolYfnVFUVhBZrR6F6VoZiXGFNgNTix"
    "zWA+mkpWCZZVXAkCcfpzeZnMN9/aV6H0cbw5GuWqtmZHdC6var7tq+/SW5a4iqJheeTgJJ3dl1EN1HwU"
    "iKDArS/3MltBzDwhQD4BqVJpsfQ4lUk6hnP3yEMJcqg48dXFF4zR1+Iy7UzJhT08qv/iSgYdgoFGhHp9"
    "sTK6aVs0GjuqMmxgmLBpShBRSGLwPhdpQcO17e64E7ZNjL0TDyijoYAi4vbXn5hl9K5Dc0aobGQuuRBa"
    "6GJl6Xdttq23QsLPONScyMI8ssTTHhvwNIvKXBwIASrmb94fv8w3nqlDThKQYXTXx0D9G+dg+m15WLSp"
    "plAk8Hj70B3b6pX9QM2oAoyYYR4BHfKdU1+FrcsZJ4ZYSKLpemO1/BU7JNnRIffLbeLKwNrWu1qMNfzq"
    "A/fFHzMgCNSx1EGbRHdQxt8QQCey0F3/wwX/iLsQY6r5vn1vl+9Sb9kPrn7vUFf8zVYP9wZvxprQoqbP"
    "Kc8kq8eOb/5Li3KPCglYo3qRm3qOLQO/qdBJQ2gCh4uVgNkYywEyt8htzcH8tu1PUH3TYBxwr1eLwcK4"
    "JGnlMXU61G5i0Lps42KAZ7Cp67QJPiSUA1b7wXaeUbEAdrR2Q/rYGPyqQ+RvqvQqavKZQUVQs/wW+Yme"
    "S5sM9m2VOApM+hVj3+waX9IRFCgopMASiGNW1dpuAZlhvJjLBPMAcZwPpo2hOUvcJEgDcHADZAMFxXzz"
    "zC6fbTq65JfjlpYuNDuIvjfAXtNxKDUkn54lvTzXY6KkxEGcTkuZqRmRUmk+5xXUArOyGn/vWDu5I7Rw"
    "DFQHkHHYFvDAxX5cQoakRgttmY38r6557Cddk506gcYAvlIj2I4/VbJYqHYUW8lm6BQHW/ptE30tcZv2"
    "GWVmddeZr3DX/tW9f9y3A73i4mhT4r95EdfB35uq1Xl5q+qZ/5bKrafKwnv/LWckfhwqTiYxgG2eYYT2"
    "mQWxt8DOrhQmWu0tmzAbFn1jfZhJzb4qTibd5xR/qXiLlJtTZWONJGVdG0W+yYCFYAu9K9sSyNUTdTqR"
    "/85m6x+4NZVPHnuHdXw9bYD5JY2J7NHro07O+MuTWeWIXyE9CkQOCo9hvj+6a1mOYxS7/trj4xk88u0r"
    "2nval0zFb5DCoH+ufvs373D9H86+W1diaGvrgVw4p9I55+zOOecZ2+OKhhIhaGmoEEg8AM/DC/AK+PxI"
    "8Bfc5upoNKfwOOy91hfs7bVArpYjzLSZgJFdRFVFcGM0lqhfd0OaP0nLDn1ZwaFIqY+I1Fkf3mQ3u+Y1"
    "Bo4vsYHPOuRRlzo190RkPAonN6ISuf4kZXEb/fy8HMrGu7TuxfuON26w343xlcRx+nV9/0pExoxaN2AA"
    "2cdU7r4l1KJ6H+0B4jp/ZmRGAFaK3gGOntcf1pF4D4mo9UmNcWUWVAWm+V9JERv+QGkH+eGUCJws8oqi"
    "tpOIhus+14auX+xhRwj2wbFYlIo+i7ZOVwqcQjm1DhwhHI1n/nQ2nwz6A0igT8L5Kn5RnvFVlfh4LSNZ"
    "84YzJaodwvT1OftDpP5deq/N5vlYUw0IQCrrW2vZxjJ8UAYRmrEzQt+auE+IAdH5pyI/AF1kZu/D/IUd"
    "X/QaQZs2JfGALXXHDOMAKHx7XBBu0ULEjUZafwJ4u9sBV8Woa2ttcsUv2dUZT8xddGhpZAZvqhxVAMii"
    "ETdTBgorSadQIu8tzHksRxLpPRxITLUS3Qsg6g7MVvanScuI+grHAyf8ZTddfru2RYkoGl28odsgTUzA"
    "MNEBTAaZFJjxHMLUmoDzj7zODP1ggsv5bFcVEDB++gFBBdY4qn0mfaJ0stRDtSmPbW+OJ2T5wU/PnGM9"
    "DW+eFWtS2FAwuDm6mGK4cbpiZ4Um3xBVKLNLBBMa2iWCpee0nnccUnJ1XvybVkgi6gMRYuaA4fA+f0a0"
    "lmU5IW9v+mqtm1HwplP09vfwO0j/Cr4YMPeQaJkUEvNiV/CbJZI2miT4oX20V/Z4fT5J9HURbOHxjwXg"
    "bhY89ZfQR+ogovlr9PgXSHOYlTFr47ROExmaQ8fxxHGfALtwj5/9ho/IoXAiqU0bADW/lJdDwD82SYg3"
    "yY9ZQTAcG6cL7++FxehcLlLS9krGd4vyqo7JCNyh9/aitu8LgD5Z44iC0JHcD1aZdk2fZ27PnoqoDxpK"
    "IH1wBq47owe+UFfJr2B17j7A3iDY3a9BXGsR9yJOQpzOKma6daRuMLlRs8kwA059l3pjnf4KSJltIuvQ"
    "pCbLcrGkFu7BW8aJuzQOYdA8Vk22ekzb1cGnzscPlkX8CP5ooYTRnM9Qmvp9NIy1vtkO2CYhJljKqQLR"
    "eKR93aCnMb3TSMrVeWzj813Qk03RoN6mv3iEcbf7xayqMCXGiH11+8HFE7XHd4DY1wmJCAdaZuwP4hla"
    "sb3O+048Dj/Zr2BKh+23x8P8eAvxqArTMeIhcLSEuSwvehADLSMPSVwYm47KQvW03DTJ2LcrP1tRWWpM"
    "3wMSoPo7G1/H0sgvLLecB4LaGp8b8aUp5QARnIzDc+he3UaHyzoQuqo5V+f4Hcc8nOM5EuNOzAscUSDx"
    "9I/GcJXJ+aaU29JydPrLcwpvcPznG0Ag/Bkq6etsJtudstQr16KbEWP2QIvs9Uc9ZWQxp3j2NV2RV5UZ"
    "pMFwUtMUTKU5hrxJZCEy2tnCcbE5yw0Qr4LvSlO8dnW/LujeaNxellDvINzoFXSUXMNnb87h2t/vapWD"
    "oGpL4QXEUhrr+OnGQXVllsRroDaMm6YaayNY9JzdHZgLLoQAuwpKyLJqP0j6TdXuHVnf+dcqTtHQwAQp"
    "G5BB0ExVesASN1vO9+DyfuezghAHvay88OSTXvAsFzLDz68UZNjR1PEuxGRMe0ze0YdIvzcoMjb+utsh"
    "YlP2VVXNQDB+PvCQlTFNxSxjh41rRmZLjjUOe68/Za4PPRqB8y6s2+pJX/QoiLH5rCtyl14FfL7X1hH1"
    "VwyllRtbksG56n3T0iE9s0u1ZyR+fsKY9ILwgja7AI2GJoCMCtWtmOAPjHVQ8YYyps6G/coSLYsOoqBF"
    "fj8PcjgY6vIHjI/4zh9FysGlfNjNLFeZFY/BS2zqi8OM0iz9r/N6HfbElcQxMYhWc+5ge3FecMM/6k1S"
    "OAs738TLaWTmD0RHIf5ktlUcVXrHnxiilF/u6OcTb00eu0Mtbe3UB/v45bgkbS7XEa5MYbDWUeMOLnuf"
    "JA9VxuGPC5uewVM43aqQmVPsJAsynlzaKAF9R59gv9FzAzcVFe6LBp4kUaHWCz3GL7gxNjAZh3jHF4V1"
    "eZrh6jWjzqtSTodAUct/QNc1F06uxoaSV9Hu7FVXC+Z4zZSanJ/dLwKX2Emu3S8Y1Dn7nIWRqKkysdvP"
    "PG5FCB7pRcjstc+h/9W+xaJjlR66bVLQUJGOgv4zlF5wHZjgnrRZNV7Wwq9c06fi6chJ6YT6cmoTKGao"
    "U+L/vwbNf/m3/0wNGlL4V7Xt0b/nNDHw7OhJFvRhLsOgCIrivGRat5awla8sCUUdeYBi/A3XxkGfOSGg"
    "y+ytUno+BJ61n4QIy7Z1Nr7hjzQd9CAQhcxz4Oi1dM7BeUTzmVph4Rz5Z+FnWQGvKSNP1mEmrgFQPKXB"
    "HK2/AImTzxxbIAtfvWxULiDTIg92EJUZ/fFLzcgSOGympY2pl3NZVBQVuhIU+OC3IbU4JqUVxEPQC91R"
    "99mYi18VEJpntDUiIEBUuveYAnka3I78sfbGkuvGYs7b4f76zUTcb0rhzIjwJefeH7jmUyD5WEiwkdPn"
    "ga5kYM3Ss365yPV0d4ZRpX5+fvxeRNwFficMaZ/8TPMHY3O3LJi4fNZvq1LA2bs88Frqz9cw0oXZcgdw"
    "BDVA1Ews+a3MJXSfWgasdt9iAycwdDQe8SouHicz/cpjsq9celdk4Lb2OxcRzEmY5ZlHwPqGLpvQa49l"
    "TX35M0N/TW/5QlMQoZWU+4KYr4bty0da2IVVqniyPhZ8JYHswA91ojQQ+udCfnGV9T19GeHkugHQNIKb"
    "/5T57wU7skbwkfiRPZU3G9eUIGGXBEu4XhaEgthww+iLgsL8PRznusxhK4IeWfFzUcUIDuDINIfgeH0Y"
    "Hk6jc+oVp0pMMe/HYQTLaTiW6z+ADEHoXF8oE2gA0fmjr97gDzGT0puOSfkIZOj8LpFRtQ21zD2Ee/SB"
    "iY8pma7kQPJY6CQO3DvHoDg8tKzqRwnDG7yUSviqp8krFhK25wnrneGdpAsTFXxg37/Em+u7knJS/e0y"
    "oNNNNctw8KN5izKJAaNt9v1VMZTCsXvJeDCKEMPzxtHhXHJLv8kUwXq3ZtYzlp6WB98xwEtA92AiuOk6"
    "RjyGVRhEDkvGY9R7GLpkYc6/MupvVjFCIimpsKwYaGfP8dMoV2Bk28VPIH4QkzempTn+loHNf3UFBF8y"
    "+F+kW0g8gma5/0L5jK2L/FDwFM4807BbhnzE9UOuWad0TN++VKLO6VNnSL+9pP1RNIedkmtWX7yamIX5"
    "uK/1kYxft8N5fL+7wHF48cJBTVIYZlxZB7uGXXQCmBvJMWGq5uEBp54fMmdAgMUO4VfxeD1sF3JjoC2I"
    "dDffy/bTfGxdLUPQGZ+gg0xrUPuNwvz6RanC4yTgBl04tfWbRTIJYvgXA0V/sv7uO3/nIi/mxPowQGHK"
    "r+kB7PQ3ZPkLsTM13bN5yLNTVKs7/SwyYGE6PbrMbb1uZtN45jy1ipoNm5CQcHh7o+lzj+jqRBE0B/bC"
    "vdPJid5QFBjvFS8k31movu40NhS/azeqmJ/Cu6DOgyusGrepuqbdh6VwkTOmZ4kSKAuxw78H1JuWbMIr"
    "gW29kj8lAoHMsegvhb8RMg+hj3wDZ2ITQHL+9XLQReJpNxoWW/bpPW6DJQCk7YYsKbiuzmIPyzM4IaI4"
    "ZJK4OdN5KuSiIHWx0ML1oag2CCiOlvATPeinbAJMgj8aVO4unXxghMazpx1v7Njv2h3YfZFeRugIOsVk"
    "d/W27OxPXuNVnRZBUTMhJZDmxVSycBCSHI5PR3r8siHEZvINvLTiKUHlz9Y8U7Ad9RyTmZR/h6IEjRyi"
    "8iRIncXQ6cJQfioDfERqQICFNKIGOQoi8IOG1ZQwZ++YHVbt+5kPR/IGQS2ttXQeRydKc0CRcnnl9aah"
    "Zq1nw9dNuEwCIgIs7X1FOlxjv8P0c17fPU2FdiHY4f4amMswu0Km8o3doUVWW223zFoXSFDYzSZIzFqo"
    "Q/EVmvt6pHAptYFseZ8OwYaZEAXWebfctQX3gFyI7ZKQ/jFiVc/eNpYh13yKuP05yYAhCNWTD3ocmumL"
    "V6DUg8VfjHzVFFwM4OGoJyzOeEtAQkTx+76sGu3jFkURkb+Xfg5JxCj4vx6phJKIR8Sywvejl/EewzRO"
    "WBYGc0dInaXASN/G9ULIDGDzr4bNqNRv4mYxrx4/E4N9Elp8HP6qGhirWwAxPOMOZUawGY9asK1ubYWA"
    "EdzHxAYa5wJNpfiaW+EQvwa9Tx8TqDMvoISv6fqGQH8y67p+R5dOBxeIaxpukR6OAOHY9rljlLmKHfDT"
    "mquGabfzCFTD1YRTYLrKlRF0Plt0tBzLN8YPEaeZvyczB0IATEH1g2FJTIJn2vYAatC1kvG+BANfBVgu"
    "Wt/uFQpXuijI8i61GISPKROEAYKXnJlDVUtUYbHwAFmuLKg3GpTJtgL+Xk+k+uVYXhIsH+y0AYOHtW7g"
    "i6HbsTOCcW+BblbSfeQzUZDOAAk0qKsfycVidpf1MuuX/YBJaU6+OiFUTYKgLhxTZM30EMaYwxiJXQHM"
    "6+mfSv9bAEu0JHk31aN6Q6LQ2vz8wjmnu5v+RZ+zMEwJIDdfVNPIGWzpIQWtba/ut6WGqUKfODr+3is0"
    "0mDJNhJ2ZjNkjqtRTp5RjF0ECp6iz0Lu1YYCtvu8D4+4oAKAcgMhywmm4dbEjNlVqwrTrmGT/M2ZmbBe"
    "KO2nFL3+kGG10ZsGZ596/6w4aTbA0+6V/jgy3BEcWMPwADyZVAzkearXhZ4IpqUyEeJHZrc9Jbfu5DYq"
    "hIvZNxqLimwxf5DvQf8FaXxQ8o1R9Ed4fJK6SNhamKeGxfeIKmpU2yw+HH0rN79Rq9R/fy5lRNScU3vb"
    "cjeWx337rdnhKvamlBTA2C+P3PdmvZjL+eJA2HX0qEdaWXcpeBGSqenLMV4epjfut5wZU5UNKV0ofXuK"
    "FUYj8bUSw+Oh5U+2QQbJgjlkFJ1e5n9Qa/G//zPrkUrhXz1zgLni1bngHH/BGyB+NmsoiicqkMJMHqsi"
    "vraujd/BEJ1GpNMg/YximbUZBkTK4QRL63U8n2gh6+CmHr6Hp2z0D+IM7e0Js0XGOF5qM55pB4/VmU66"
    "HDltRxSmULS0QbplHFMYyv4B0Qi0zr++TQBQFChVF3wu+XL02dOtjuLfJN/yFo0zP9XPlPeT7yAWk+ac"
    "Oqsz7J2AtXye369bF2RUSPFAwv17rUnJKknXBzBqzx/HeOo/Fi4VY2ECw77ahR23TPIYILr4ISWSSNnj"
    "BXnKcXzyEt3cscqwcYuQYO0qm7dNqNkuaBYcanV/ZEtbawi8jtEg6Q/tonW1ifzCu85395n3r5WYawHy"
    "FfWLjC1iNDMnXIxYZnXV5oYTw56DXG0Ut2VZzoQkgomPbRkdAijAJLF6QEBPABlNHC1hfGWVojo9gDI6"
    "ELy9ug9k4SOxFyN2dDSCYIfD9iR8tBxhdtarwkJgGMPxlMzGonb1uDb1jYbRGqIc8YNTe1Jz/STNCWVM"
    "m2QOCy0raevjP4lBleGNMOiPAtiFWw2HcV/Rf9QESbJ1/RvDMh18SR9TRRC7N6AUylQWPTANrwvwBrOX"
    "fa0YtWFbAc8nIHqJYm36Wn7jmPECLss/vX9EPoVYss6/A32K3/y5aOFQpqL0z1clHVvF7sbLfNLP9pgB"
    "lZmjqthAIXiwoYkiVgeZn/RilUiLBaQf5vaIr1RTpTvVVbXTlUUhnvNkHD3XzQyuqG9pNyloP5iXRcWX"
    "l/60lqa2wNf1vM/nZVk0LeRNiu1vXN7QN7w/jRQMF5iYbcfAvGPUbMcl9PcFYsfau8ueePtvTUrWvZFL"
    "226LKUaviR3iSkEsJvMqYJbN7yCCA4nv01DN9rZJT5+yzt/UE+sbmsDt64RVWh5aouivftNjlO6BC4CV"
    "k9T4X8zwu8AKf9ecusF+GBvKLnnOR4lkdJF6ZKJb6iTAb2ovlO5xDi81+a2tGjr/QjQSy0/eZfWXp+xT"
    "/L2k7frBDKhBuEguEQaewh0imlcpyRrtOAbANHxZRWA3YXryg4PkATHmJByi5Sv5nlZ7kb79RCXWR4jB"
    "3+ASGhX9Mo8dMrlW/piMsRw+81dpa4dRm9bx0FZE+NYq95UJYk7vgFtvy3kFedqxX+O+I0iLmNQfEnkF"
    "OH3hOmjSh3f4OJjzjg8TXBwi5opp0dzgLimOlbluMMjnzF6jj0G5PEOt1ZfXFKekqKnhiE6ugxvJqlSM"
    "sm9jwjGshiSvs6tTzIox6SUsTBUsESs9uZKHsw94xzwYY88LGNK5WWZXYdHI+RNesdwVSfxCMpB+RG41"
    "85M0iV28fbJVzR+2GjdSv84dWuOxln5dG1qmFKm/9vZR8Ve15UIxsMJk5adVRoUbpHEimV4U3Nu4NMMV"
    "pWJig8bRyExcOzKhwPgn2NcBCfpmMhHbSFdbdDgAWkj+0W9uRny9C0AJLySLJqdjG39hPHeAz3VtnRnK"
    "Vx+FQ5CaIXCytfUKgoK6JZUM92scXN26rv8ep0UoCxcluPspvBZe3yo3hQoNYCfKftoI0Aqs+dSkkfnW"
    "FnW/KOxfUxO2jEdrHEO3UiSrvwArsc5Z1lDbhOHbJUEunoHXAPLqI/W/7HoRtqBLGiWWivr6Q04KBwvt"
    "aS1E90QTpWfQpBbJed9CVRgbbCdc+qcZmEDKo3UakOMiz6qgAKQ/Bn3aMJ87jrj9laRF04muk0+6WxL6"
    "5MSMhnsVhnhSSC2VA3avpeuJvw6O3kmXODRuosAP5yo0PaYB4K6zpGp+qyvPO6sBq8jFarn1VoMyJDAm"
    "VxC+wzIWCtMOkRCZXeYZVaG5TTJoCZwz3uZV5LgQCpZTj+6vM4Hp8iBIFG0hE95fjXqSYchdblKtlv9Q"
    "65CKLHZgsfHAs94jaHi+uZh96waK7JxXizZWtcBt3InhnCBzF4UTUIqgZ3VytIL1ucfjH4CiXhuryxu0"
    "bL+TQZdKMuGbjva6z52ji4Mf97C+BZl8nOoOZpelxqUJJZLXON1LdDiyjwzFcpzGWX1Pz3ASe6r7jYiX"
    "XzEPZOYYGxQIl9gY0kBYxDiwFx98AhFYGuhR1K5CBddnTExshHSSovuLd1wpdv51IG0hZ54tf75zCZLJ"
    "BwHx+8jhhgzjGorXdNfWLr1n+sVyO0kQ1K+/X0tBFPjoNUlvVa1Wp3WlBId75Z0M+PYkOgJv2cc5axpK"
    "+KheHbW8UhUAmoUe6mC08zWlICFNJNAT2jN4nRDX0/Y5/57ww4QvMag/u8aJVPBD+9TnMCDJqSLmK+Eo"
    "fNvhB/hRPPBq+i3ZVL7eCJ2qDwpL65GhXlbtyeV6pY7aDc2oe1PTngymW1f5Cqm6LKo8QXOmUOgIgSzt"
    "W69aWhPhmpVbDKUjXX7szHsqoq8LCUBpKLHvxiim8wNPX+KT6TuiC8GQ8/ApxBIt8fUFgHVpjbwUI/jd"
    "D3NQL2rVK2lxjhXRIs6+XRRRC9mv+nuB2bHJHRTDXN64zWooVnrPjxw5DpkdLZMcTLbWPsylxmC5PoG3"
    "2XBX55OROU5XW22ndEBBqDR/CJ2A4XRAWU1ayvNGVAd6okvhIikJjEGAWqPnUb8M9K85RVXVClQwP23M"
    "qBAw00HCGT1ak/xtgkKPxpW3DsM85tpo/T55pd8NgurH9mrzIzLpEYcsvzmkmGyUh1Il/nankCkWZ1T6"
    "oMFW7Q51H7uPkkj6h6IV6q85A77n198SBsRnbXceFRQ6ZYt037mcB0Ro3qy6HLOGCfId9jVKmay2SrOf"
    "fw2nSFI4SoshEvn2W1rrZZyK5ukKPpYMMY/fMnuglu72BFBfGUwPAhqfxzdK2+gG25MfF27bhnP4v8eE"
    "JEHl8QX/ngSgSxACr4JImorjn57bc2kZaiQE47o6xy/FHM1ULJ+OohQcjMGmmKEfsfifdpKvf/S+5n/8"
    "Z3qsipLw/+qY/BC6fPW5VCPnp6BwGhDJvIi0PEJWLxPW0Bl9jhGZ9SX9BmwsdPS3LhlXcdlNbchuCGWT"
    "oCxTVsWuS4Adxxkur4vT92h3xktI8FII1y8jDebdSdEtWcbc+cdMLdVCEAd/5Go+bnCOPnROwP1+gQ85"
    "5A1p/7ktMJkqxsA4l6imnR9A+XKPGJZAVLoIIZ9HYMdug6/kucdN5vUGD2eAp0z/cPusEMzxiYwYwUPb"
    "ZZjGQPrhRgRu88cvBId5XOZ1/6j1+DcNHryI0rUdqqRptbOhsfuMVrqld/eXFiHSOkFbtkre5w3+K74A"
    "gErP1uclQFjcov/SeO5JYi4GFB4TApTjlmvPklS1bVfKBvd8byoMny429N4+RWzOGB0IYHGlV6ODwOeA"
    "k29kxLM9ixgFSmsHAGAC6icKo98a1a62+jxocvRPZv817qs/IGtcYmWBMVGRADE75cDedlRbev46z1l6"
    "qO1NEY2Us5YHdlEsIagurhirKpOq1gfb2qn1opT/4R7nzFZH7wQ272D523/xhnbgpleqm6dmY4ght7l1"
    "rgfV+VetEqd9h3kTs7RljqQBnUjN+wyh6ZkuCOEvLPdfS5UjHmF3A59QAf4tdHIYjdCqTqIfYweZ1g/v"
    "Mh0IlPMwxHqX9nSeL8WroOfCflkzlDA35nOKPFDo4n6CA1gweSMVto1L8gajIVBw957NPsc8HB1l4Mal"
    "8/QLTEE/8jJoBWk+VtvATTw2yir+vcK7CZwyHyudqV02Yaz6sIRij3giLGZ9s7c2M1f6qck4aD8/BTGc"
    "qA/LyHrJRVH01IQlwZVeb0oKH0Y7Px8p6SwxArpM2nY50oEzj7mR/pTOuX0Sj+KU/riTvSwIELLu8Pp9"
    "15fHE3HhxWjzsG9JjeWtyX99wl+XL34l56wkKHDZjyUjdOCefG2wRGLDlQPurncHCgJkeiFe2rT7YtyQ"
    "dxkBxWvoFVRtRexcU5qgOsXJeZv/QFC5Fa7wNKJkSC0KARAjfbFYCJ2mS93N8oSviv4uWLOXtb0qDYOF"
    "CS9H+9MuWqUrTdKC8bTe53pdBixPCQe3riCbl3I57HEtlHHONbStsJef6d1zoHSeB6lHaoIVSmOAC6bK"
    "hJVLK45wHg4gG8tg5gi1tE9YZddJFW9sQ80uC3V7X4D3sCYHuS8baF5kFds1HKm2YKKLYQRib5El/HX6"
    "wdFrX+lC7n816q6LXK3Dy89Qy2qrVUkMlGyaJzBPwJkS0kOXwDEmP2WkiIqW/ctR9+dotG3yul0jABSE"
    "SQ6WeHam7KsVcVei8bk49djDq8gLoyuZG1FYLYk7VDheBTNMOzG/WXxBBe6dgujiit9GZLPz196Sh4de"
    "jeQPs123v4UKIsv4Pn3ByoIwoo2W8a+9QboWFMLreNPcrXrGsDgTRvkFw0lpMQMUcJxqcTX5owiaVrxT"
    "aDrUskVHoh2f1MoCNCfYf4/LUIoLQTr63bVt5Qg7Xz79oTTdLgz5x/fSbAmyI3V48JF+ploLJSEflZUy"
    "fXZ+lBzVcQv/YER0PVC3M1+236DSo+OpnGNtXDhLEQ7AjhfS5se2jXWY1AyJE7wkt8+RPD7Wp8bRhOea"
    "M34uYYtqdzT9FHoYkb5KD9UbRJ4Ejkap2oImD0JIcREun+cGPjzxFfZt8WfJ61I30olWY73B+Wvm+t24"
    "9HPj/Nxuv4cROI6Iw26iUToXLgnkBB8btUGyOIZSfy7WoJHZ7Vhh++w61XxjmD7mF0TAG6TEFzHrn+Qq"
    "Mpz8g3Wz//4//zPrZrX/ew8L+ZeaBvc9yyANFEhsIg+Bo6efVn/t6Qw+O5JLTwKeCQTcQ0xpfH/JcsEY"
    "mx7M9efpjdl5OFMaZyuJC5lnhkP4ZncbsC4y+a+EfP2oxypSY3YudPXBxMnxnUswcNHAr0KoB0oihJNw"
    "U1fQqHqG4AFpmoLvudGu3+i8ygdlJAkEKiwguXE5dCr+iQtSBCwwlOT3ShiEgQ16rvb7Wdr8pEBGgQgl"
    "JfOD2Ckoj92EfOcEPOYCAiv4Ga9wjqACWlEAplSMN9GzY4HSBLLpg4RDhg+uAOJBJ++AbMQqgZ6oDB7I"
    "OpwMKQh/1Q2av3599aTb2Rhs/QMpMMjywCm0CICLF0EjZ53Pg/FpyiTW0VWmCWTNMsCYtU4hFIR+vUR9"
    "eBE8OgXsUz1OI3jGkxVo2vwkYmGC7dYEzhjHCLCv/SyJnj3lQKrO/bKrcoaNe5UJgR3xWRm2mV1bx37N"
    "kcp+2GA907eOcrqupLkYYaJdkp9OAfvE8/GxohWy93MOrA7/lcUx/unPjANJ8fwKhvDdAf4ZJkGv+1Ma"
    "oZCjNzS3UayAURYE5LnIS9tBzoRmjwFY31Bjm+Cn/1bUkAP0b98oKkuLWksSoxGjxTosXmw0HhzYcy+q"
    "92q/A8Tj703XQa5hFwhjEbc9FIy0Ea/mQQa9x7iGRxyMQxayq+7h4XfjSPr5hS9yTK9ZB+fnTA69hu/k"
    "rFJ44sZ5jBmZpzAtRx343ie5Ekl6t5aIjomHVls7foW8iBeelUKdmpedkHCT7MNfRBHVqiEpPZdUoGjl"
    "D81YDa7GxVQGGQM9ZWuTz77WxPdLxcLR8DIPMf1nmpisXDfm73eixbbGeGfeNd/Elk3mTJSJzwvRU31b"
    "pPVYVwM4XnrtpV0lt5labHVeOTSrCjn0u89Y9W/VzfOmhb2GDwM7ALNxjHXQqmYZf63pYJX5uIW020Nm"
    "QFK651+ndzK3+L5GJrzRy2SZYGu/cZAPUzxCYvVh/fyTTKUkV8NurLvWi7Vt7zLQVPErx7K9UD0pvn9M"
    "zkGSr8ABibhVn8FbWslmnjSxSJgjAmGCnxuNPzrXrHpM8Omu1D22H25c77Q2T34mSC5wt5L9IOlz1k8F"
    "gyTFB/CxoQe22p5HyBN8ZL8zrm+mIXQIfZkiQYN9OsOP+9kUQyIrpHFKSOOE6Gar0sVYj2Ek9ZVBGNzf"
    "v6rlPc6UZRm9hjf+izBdKZAkicoGIwVF4jAoSB8tbO8V8ZVegtjBEWT49fD2wz6TQgtPNkl75lcBtb8j"
    "qeZm9+PdtQ9E5SvmlM80q6Z5zrYB4oAj8qo4rbkS4i6/nl4V2BBz1HcXNKGfRZE14zLjLe3pDx4ZlgVP"
    "PrYTAtPBVPIBQghD02nts+4Vw9njwTl3i0QE36yXRwuXvZMTV87737ItaZ863wiSnQyYWScMMmxXyMu9"
    "iW8Plh+rVNEwNMpEaPm6+qr3Un+9xLVbvtHnFIQM3fr2xRO4Hz+COwk+nFD7fY5uZX1G4pokmplXJ4+s"
    "ozScxEqB1rjT8p5T3mP272rZxpSx3pUQY0t3M4iprkZM9aXzQ8u3ev/de5ZAsYxOCzAZR2WzLFx+0fPp"
    "u2Xdjlqr0gapYpA5FYjZGrYbcECeJtdKvnESxnzpoOq/NApCBi1hByZEPTFgYMbGDrsoLX//Ge6HAgg4"
    "vuvzLL/IajSPPd6jFXINRRZ1ZZP18psMeetW/YcrDhygG2kxxXYoxcxK0tGTWtNcphoIRllj1eujYBHt"
    "DCbYWVumsq0a/9rt0F2NG/xpVIe2LIxYaqjRT0FYoU6Z/O4ND/qUpvC1lGvSWu6KNk6gOEkGDkQ5xmvw"
    "KQvfvg84VvaUSU5rYFyega5vsErYuEh8HAkSSVE/qAkWjxCDUdF8qZCKHLtj4yoBUqzIAkolyFan6moD"
    "vfbdbyUE6aEuwHekKWVG8BPHTBgTwFH4kB9rYNefWP+qWkxUyEWeMxoHixUw5WE2iaX9xjOFzN8vNqi6"
    "wxQhtuOFknGNwrxm/hfkifGwA67jqNBZGqEfxS84NYBEHurHqRRhUdHPr9TIXj9jYHYJJA0w/xMq2OAU"
    "gaGcZktY81iiYCUaw0EFhhvwXD2c1/F+fi5LhZBBbYKwLfxrjozD4FmOpX7RyKL1JxgUVqZuTFJx6OCz"
    "r0MXSkgUxWg42KdbRHdxD/TFfmFQLpYzfU2B/KLDr6pIRf1bNVvpMdorl/3+kwgoF8P5sDeMcyXgqeBM"
    "5AnOyAu9issPI4gM013j9eXoWr8o/IH50FLCgY9Y7Fodf6IaFZ4X5yPyCt6EqqwwD3w7TOAoqbQpg3xF"
    "kI57gukUpBtwtyN+7ca4nFZNtZErnC5wGWUKruR0DWP3DzV7IqvycEfu0wa41D25yejvcU9yL4MoQxXD"
    "xmvgmF4yQiqsr47hMCJCbuJYBlPAerwZIgtbOEknvV7NfgUYrHgz6wHheBjWq6m+0ZS86Q2rWXxNScTW"
    "bOKgOrRfEsagCbflv++XbDGs621bDmpBVwRH3/JZbRltsvsKXIHObBtBZj5PcJEUyl+KY+aaMmnS8ld/"
    "bMlOrIrjGkNvIhLfoRSFDk5eJ/NXgj7KyAWMZpdihJ42NNk57ZRxGD0+AbCIYDrewscpvQJExtB7dYjK"
    "mDhvPhsHE45E5DQEAF++0CqHBjFMFDm95bQNIQ12x2HagaHquwkNxn5AVFFcpmGqQPywCjdFZizXcQkS"
    "bUl4PYPdYNE58lq+05LaUXvczOq6zMVcx8ccuRWwbs3KPrK9SrrGAtLd5tOoPsEkEhmr4iZU35H6UyTb"
    "YVhS5HKY8TAmCSdfmqWCVWqQYr8NfAE8G1gNgvW92ab1RL7KNPZm4Ril1ev5Z/2pioPtyYsnCcWRvtEF"
    "pC+Jvzyf0udzQMvFsEpydC2kAwGB8NGzDC0jdKP1CcscykPYaXDI10zff8PUQM2nfoZfaleDZ8rx1n32"
    "GN7+6oZk6Sp5P2Dnply5Ld7BBNu253Mp5fDhboA2vpvZJxD+urjkoSBOMP3LsHUGtxD7ry+eK7h/+0H8"
    "Tw3PUpiiK/p0QXPf7aMfartOvZXy2k/t4qoZ7Qfq0yU6UBhn9NDR8fwgT769dr9CP0Tt/jQXR9E6hBQF"
    "6l2T84RFZDYVzj5xRKaf4Jf5kxMy3rHac37EXwDsAIaWpN/WL0wdKM0/umf3n/7d//of//6fWT6K/qvH"
    "6hnKBeH9V+bDAs5cV9vFN8FA6VrhyyyDIms4czW420L8Ft1l9gI6u7hU3TlGkZa593QxGBC1x4GVIcKy"
    "dCzw9FdLwd8ZYwpKh/gMlz40yqsftze43R9SoN/ymefTJhM/UJWvAtY7DtEphePPaVDkM9sc/Ywupkz1"
    "UeFxpYN0/3o/Ku6V6inQZS8tMG1hMC+BUNrJY54UhhmEZrxt+nT8oPC4RLb8RRzplzYoRwhOB7dzeMKX"
    "WBahJRTrdDJCxKHqjKeXqKy7vEJ/iEtt1HTeZ2ErLBG/O4Hnef5RN99xoN/HCN4zBl2Cn4io8Rc5v6fK"
    "0Mgr+zgEWwF32PTasc76k4HAa5NzeL97wbTXDAHiMj0iAF/8x02MnaqS2b1qokVVe5YPyhjPmF2KCJQn"
    "fM8AlACzTyHGkrxSTyLEGrSjIJkYJPn0DMWbsgtHJw99SYjiGKkvPw4V3q8Nz00yUEASSz/xxkKfyor1"
    "5mE/cQv8Zm965kEu4IDeXqQidAvQHZegSr445L8Whhda9ihkxhO5xlzUVw+MUzDX0YF6URFQTXefY3lZ"
    "hFN0OXtb5odl+k1ugQBbUR1dMsPGSkfTmx0hfw+nvLFzQhsjzX5aYMrQ679AikyGtCLL/TcnpqIy/l9H"
    "CZMRex9sBjG+SDEZo2lhOGAAqiZ+DgX7jVi/qGjpjRSUcLdxBcGmIr1DhG4rfSYPBLps8Grg0Tf8ChbR"
    "Vk5tvciUlsN8jLlLkyJx6b7m57oZJQtC2CV24xLqJItMu+XoYbHGxW/0H9JdU3BL23SITxDWrRcDHeSx"
    "wvE7+Rc3LJZfhJ57uATVc4u7Hldj5Ar6aJwYYZMCKFiiKKnIGp/h9QRCXO/CgVOT5vgMrxxhtRS0ZtZM"
    "fv+wKElllhMUs4yYknmiU8VcNlTTFvsUMQBUdi5q0VyPYUskrMEaiqRgebu3gtIz/Rd6I3Jchumddc4P"
    "wua4GGjxPfPdBusi73l+BCwYIs4UulkudrXWO/X9nGlZVcdAQjQIwobIKEps+b0XjqceveKgHhkBQZYf"
    "CZEJrTEpFS4Yy77UJwwc88uOzbR4ouHnObabn3QMpVv7CVvMk8hWIGV79QkSPX1QMPtDd8APyBLAHOYl"
    "Fr9zhM9fYWM9nU7FYRums8iA2dsPZRcizl64HfOs2Ty31nQMFeLXECT0yyq+W9J7Q/q2f6V3AlB0UJM9"
    "+CM94IvWPQdvle9SJJLi6auj0QA+M3Rym4aRLmOFGIE5LCSO2k+6PwXPiOwIyupJ1A6EHulZlbJRdvFV"
    "RGjbS1CujRidw31llxpIFr950EMoIl88TM9vrLfKsu3dnpQgvdjo3Nd2jvZUDJMskeWC8fQwZu+VyGsN"
    "18uMKQmBI4CXuwaI3oK8DeDWstAOQLe33ilFw25NoRERB0ei6qV3FNx7R51CL1hTge74rLvL0og/A4n7"
    "kdiVkAdLZkp4VmYSuXt5RqGOWKykqDctO637oAMdfzkOc68bJh7VrC3iRft5jBu8CQYMQTSY3e3kjJhd"
    "5Dh5P4NVG/PzxVfa7uNRT5rec1hm+Oi4Qtqztndf9iOZryvytCDNmHRRtPKQjkDFc9cNBvXYtSsoio15"
    "zE+PCEqbaNxlN/yP6TTfmabsYDYrfQPsZrcLGqVqMgzGiF65xTVa8fuMvGExKxsncCIrXNvsz/MNVQ6G"
    "TgyCawd/5asjS5LA7l+VqN4MMnRETVmDiNdJ4Fc3VAIJ2/DiK5KAgsvfhvIbpkmv0FfeY0o9M6mX+Fob"
    "VXAMRkYUvYkcP1KbKiE0zId8R+otROAU3pUmTiKAdjWSQqHsYwYjDnoaCUOeFrIT7juOidkoT7uWjPQ7"
    "bcFijGdNMqZHtZwLOJsh25lt31H2tK/3/R3H+QBtgBF9IQG/V+pi+qI9/GN2jFBjwswIl/cxzb5Ay5eS"
    "3qw1XYEBpDLW9aLDSm40HjQr8ItiGAiBAHo7MZox2qoaQ8URPxDCj4p1plIrsMuuUcfE8L5cNInhbsYO"
    "nCcxMW0Bkw2jqGuTiJesLIyp2IiwMAInnRzEvKYqLrj8YIeDw14P4XjMfuBFsg+IaXeXoKib9M33yIlE"
    "+R1KLPLoLSvni1UZlGRZIGvZotjZsXQuUnX0yrJeoYUSffg6sR+yF6HGoaa5cEWOD5vareP0yrYPe7wo"
    "+RH1TDOoq/GDZ2RZp1zT0CfAlg1njjACoOfHFJGML6pcMqevpeZyUDuCGuCwVx07yJ8GBjuJKs6p5gyN"
    "N2KLV71AvOc+MHTAea/NOQyFxRyQvKvpERijb/uMtpFmey5wz8QgbZvsDEq04xqvfxMCGaBnkI27Mc8B"
    "S17RHb16+S4C8IMQTftgndXojWfPyAtmtq27lAfzxIkodkptbunRyxpvvwUibTzCn26pvvNI/pb889oA"
    "bVIjazD8+/Idyl5H1hGdKLEcmnGEhdWc0WNG1WKZ04x1BPnum5ZOu4oNsDmaP6L0FERPSFmhUTW1d2lL"
    "CrQ+y974+nnYvu4mEFfUZT+D1hb2DSrberWyU1UY2X2NGLrwRd0fbs4pdIPgrrZ5hqik4Dv2H+PzCLq5"
    "Z8hv+6FxyjNPHoQe//54JXCLMV8BIP8QhIS3sOpcwt7t8OPJ5+2TlSq0D+rYFf2a+Q/ypFApPyA6vGqT"
    "xc2XXgCAbqoo5X4/11M6C19c2KVgROkkbKHsrm8IXbim3U7xHa0x+dB4d11HKh+Mf3Cb/T/81//5b/7d"
    "+/Xf/s/XP1NIWA7+1QtScdAGqLsC8LrRKZk8+VRMt0tpmk+u14CPNaSyQZ3K9s9dhEHEB2tziOKVpl3T"
    "nXzvpoETC2EbLEIYO1kQj1PGAbzVDtrYWL01LYBuzx/51fjfs/RIy7xPecYenqUBqc5t5Avm5GmBzyl9"
    "aR1kUPtyGMuqBIHR4h8Y26+NKZ5KvCbGaHpdGBJoX2NA8jVs5WyWsFeSAMB9dqCP0gnCqwc34lsD8Yw/"
    "gHoDxjVRyEsOqscNigI2nromPLBjjdqU4cZmQYBTQA1iRfN7/urv1P43NMMwhr95h31/pLL8HtVQV4N1"
    "zRIG5AvI1HVq3th94TTnx4K5Mt3dhCnCE5NLRiG4fbZ/OFcd1s4dPOFAX7XQupx+O5f2XtcOrbIyfMaD"
    "/b5ksS3fBaOfp2Ff0yuLfdPPsqoMknPeFfuwCcsZRnBb/qDHZeTOKWY4zcgsH+YSkutaNW9qRkndsmYL"
    "gskd00AMw8DroTRkBiTY1dVWCw1buP6qeGLbN1SGCFEo7PlK0igcCWvfmu7RvXRtekOcDkRs3kiJ9fFm"
    "glBwu2XTAlF0mQyMOeIMv5smtVqgc6n3njD3ft5tYVyoUQCkcuSzO3B9oqT4VyX3iNDcXHw+cVlOEQbv"
    "rxBnIKav9ngdaGED4LslYaGfOylsGeeqecKd5GxzbuB903jshzIH4yub01MvJADISHRJiuMJgtqb6d9+"
    "/ZsCWK7T2D1M8jCj6v5OqMd6OuKR7yO/QHt+cCmb9uXgKN0j2FBsMnKP9PIr5zgNIG/kCnrYeUsisxfU"
    "yLpl+BTYE8RXH1ltiaYsycDd6roxk+gzhgW51MNsTX0u3yu+wPHAW2YlGE0/ycXkYjteU7ZkSmf2wSlw"
    "hKLkp/I5mWSdpuQS3DhOR4X/0hC4MIg2e9PJSd7c5Dih4SUJ+6qdpypCGIbthz5vqjJl/J15hT9ICbvu"
    "C8fudkByc5CiNH6P0ITI90aI/aQyRguCJWRezRGJmzatjddp0DuMlXFqv5lfoS7GwJgY1i3rdoKyP+8E"
    "XYcvsMKqe4gERw2a07YLjS91XBaMYFRmSiCL2Tqb6EwqXuM2IylElii/wdwAvSnZC8vUHDrjuEEockr9"
    "t06VTpQ3Zne5oa3Zl9iraLlH/6vE/dJ0Ll0ue9kkDYDyAnn2gFdRu2g8Ayk/N09rXa3I6gxPuOIvW2bI"
    "F11DEXIYxVwPk6zQTya1y2U9r8wSRK+bjrA7EfKD6MKvtBpR0e629yDabul4dWP4vUb6MAPXMwVSug6W"
    "mX2cEHTjvAAQdUwFNn0I9IF6fmGXw2NOYSr+V7GvvZwvyn75zH/3Rb37J2WDOVHMkHlQaxdP/r4zi7lQ"
    "IT/UaxHoGPkrtHTqADhjgNWfmju4En2Qlm8+Afytem8Uvl5ryW1S/sAapEGZGTifS3yfy/x3srlNpcCa"
    "yvaQAJuSX2+yXGDQ7u+LaJK/868TpVm0aGTr+osmtpkO384RG+2SLiRB2oXTtk3qo7LQ+t16A8L6uarT"
    "OZ4Th7CZYLWN4Y6m+B40aka/YK9ueWfvxwkSW7wj5Zl9giSz+nvH5rN3KHuTXontW7c4UjiqjsYysvor"
    "vuzvG/MkPSGC00nBiFf9615Ce6XsLBrXykYJ869LsMQxmHr9FePtBKZnsJg7+Ii7CbbtX9V/Kz+8Ppef"
    "1jXbey549+AYnUn41/xepNWvF2YwLG3H8BURKAa8MIS0axaIZ/6jlrXiCocuYcPIvAb8lvyLVJ+JLLsv"
    "+c3nBwRbGK/ieSGqgV19V31VQvk6or5/3nHdz78XqQXZ/yC7OWtQCX5yLZvWlUsnZ2AQ/X9zdt5KkgNb"
    "en4gGJAFYUKrgtbwClpr7dFn0OA6DBr7AuvwEYlmxC7XuOvcGWOc6e7qzJP/+b4qZKa/CIR6r2/a/23q"
    "e5o+deviXSWrRAs1WDRvQXWgY6JYchqyp7g/s8EoTuA9TKI/3t+aJYFEt5vRvVD97R34/P6x2phnZipQ"
    "/84e1rP1iZxwYHPvW/a0fL/zdwIdNL79ipuQbEgqnHLmfpqTMl0G2vAyoGg+O7rcivs2KSwf3Ils1Lv8"
    "DpIslyKXzXJnLHTN8tYb+4len2deq/z4NlQvVhyrHaeCI8CwQQimfZfPZAXw+nUz3Qrf5B8mLPffPD77"
    "33MGJ2LBoqeI6Rs5g/xoNz/Pk6hPEfN3GCvyVToWmZYfJf2QafL4QsCkt+6wrb6iD9OJXm5IsiRhJ0/D"
    "euhjxQLjaHNhZZgf4So5dbsK7ebM6DumwhAR4Y//O0SedmzaVnVbeGtxJBwoY7qhre0qEmnaQIvdFaZQ"
    "oP1w6S4mQrQG34+Ft06xQ/m8Jj2r9px3xOSLVojIohvmXL+stmDOkhXth3XfFFqlvzW0w5DFiPWPaX1b"
    "47RnRb6hS5dXsmogSEI6zWgujyiqM04Gq/PuSC0Oy9bd3wZO5PuhjM9b24lS517QeO+PfYeEXY0l5emS"
    "D7gz/9w/17FfPagi7J1ZvQkHF9oU7Qw4a9MjDVDXKyl4bKOWPOeuPW3KlJRmarytq/271ly1PIFxyeut"
    "B2KToSaUDPCjKBnraW1tVSJ94TYUi8TxZNAzACxBuDdVs0nEVP94Q9G//O9/ggtV3vtPl1eHjA/bqHQA"
    "eZrDYJ5ugEN40i3TbSvHssWfJV+p1zxfKKPtaiNXCf8OWVkRogb/OiTcjAuh6mAv6e07Nr+gHX5nRHuK"
    "LbAdD8l0POsWI7vncCj3Bw83IMxTcJJYxf8J+YURHTig3DBQRA+S8PFqba1gofr5qdJX8VCNfSdbsWge"
    "BS3r23FV9lUVIJ199YYSvb8sZU8MMswKFnC/eiVVmaC207k5wToy51d6zdKFtIzEvaeBWlV56W2+ltTk"
    "zuftK/rg6oBo4/s0cxGHISXNyhKNqw60QHdsGG4Iwkc75X2XHe5w5xelOQ3nz+e3gnx+bGT5hluv+wVb"
    "6FO58RcG/RlV8NXuX9H5u8Wa2ld3FpBob7ZwKvqqJMSP0NUcG1kWTUXWp+/8X9TRB2sUzCsnMqe4zo0w"
    "60wdG9p94sB9s+NmC5Jkk5cDg/JNOnbR2s4vW33a7LITfPrKWB6zrbdKOBhgB04tNM+txqZK4EGibbaR"
    "HoMvky73wr9bfsJnezOYO32Mt1I7rDMNf/+2wWtMAsRQUey0trWyQ2phFcOKfBFGLnOKQqkIC8kYonuf"
    "rqxYjfDiuRuxp+K2n3U1N7hLJEQC3Mg38raqYSYKrXIeRacsu0qnj7TbZY2h2Ym2qcCgE1kwlFE21CpZ"
    "lU8qWCq/1KBICLE0ljkYr2KVhjDM+L79x1jzSwbxVXI1KmKvKPA5WKTY49RfZ4slW3VOT6YTweb5cWeY"
    "omdHF0ck1uJ4I522o+TKEf9yyjmT72I0Kk+x+GIqlFiYX6BGdWw3G/xeZ3WUXft6c0lyx1aw01B9Avbh"
    "QbBtdDLFwCQz2xXPozDqaTWT2W/J6BCB3dCLcCJtaf0Y2dfAOfyIcE5lHx/eKkWRVd0yU7pujSd/dfhL"
    "L9763agIlEqGa5Pzx0WAyIAJpansBfw4KxJ4DdYTF6RixMIhrIbnW3p/ntpYx4sEfMXwp4xznm6u8QlV"
    "M6dOe7Zht0ZOIhCu/ajSDQYGmQTKQoc9guXNMiVWIby+so5QuQRRGsw1r4dbf49j7aXyy6uJgL7HFH9r"
    "lk7z14XKd7BV/POmdPPVBkeTh5CuCQfRh+/vp4YiKt15uFzYI7KvvJxhDzzhujNdRZrMOMvGlx3nvulg"
    "2FksI9RGhqTHyo60cQFudjTepq7WR4lfeq1pfqNBz8rDRQm38mJNEU5brAy+Zfp2Dz5b6e38JlBmghVi"
    "Rftj9ZfrmxR9UMdTk9a+ChpXne13mgpz+LuaBKojOEMtj4t/4Y9K8LyfM/3NNLPCWc15eSOhtyBSr0t8"
    "I1yKS0qQF4px3vocaaumaY1vWcH6VqcjYsypj/W0M8UNZ1WE+7+Hv40rd27LFmcjefLZeYQAeJo1fpA7"
    "KevMnCZVeLHnprxLMV7l+vUZ93quzsr+bHVYwevBQX92h7Ywxma38LBBkJAQ7myyvEoe3BTllTEmRCs1"
    "0mwottJQyDC/RfG+0Bh52ymfv2TEcmeGujX0aAWWq0oD79QAE790/lW/fAOXTZpivaaCyzWHKZhWqgQ+"
    "31/kfE2fnoOucp4b8BkrkFnepvIXkl7fQTF9EsEjPBy/Q0wZwfKqES9IoBABMm2vZGT5RSmI646GsYUn"
    "58B8HxR8NxUMAeecDlOh1CWze7+p9a15LYe9210VcE+Ebq3Gxy6zJ5n3UBMhcCA0CtxsT7h59XcEpYYa"
    "ZUlLTOT92F2iPvWHFMu4rb236QtyWRnNz+jqhSLNYcY0Qse+bkJCkXffQROs90YAOLGCy4eBOgN+yyeN"
    "qqKbuuqBNxkPcJso34Kq56JbIhpBebP38NqgI95Sb0WTnIKWhK/MfUhsvYBUkE4j7s6yZiMYoWZjuM48"
    "Suz8saOHzpCTPBLvO9ClSaZ3zNQT+/FcbsYLSwdBszPaguN/pCnJLnN4rnhYuD6x8EfYtNCk+zqIG7uR"
    "CMXdr8x++EAavU2rpsasAG0trUu3Rb290RPpx9eQIuMTWK84eYguxXiUAShDJNkBZSF64enA5TLcrOko"
    "GMPrEx07r2QH1N3+E0VkjNlvJv06e0+caw50lFbScIVZXuChzCAWY5EJVki8CQtED8QaPoDioBS0fUPH"
    "bw5Kj2B7eXMQmJ4tWJr6G7M9Y4JjCOERwyrdCTnbuOVVP7413duMZbU1ZVorXLX+sL1cyzWzcIbNKkhd"
    "ZVaOJu2TIC5FJdIMQSrN0woeOm2ApcSnuhaBzFQQRgY/rGAu4b6OOKTl/EvF7ahaT2Kwndgqn7Ffr7Fb"
    "lCF1D5Gd5V1uKzMPVp/BJ2t5b7gIBzhr9hUJL3rkP57TFZLkny5PAbPXcDNMHGgPgbMsa4YuY+PjemB8"
    "5GATE4Cbr43skYZZ9mGCVydJpGo18UabFZDonBF53VrzoTZUDgSL/kEnRPHRV2GVgrC0FKNVVmMY1Ypq"
    "GlM1uSKOikPjOlUtPWnJZBlc/82/YJwBZaB3Bft5Drwjlsi28XmhJvir9BqEgNHk5ToaBBb+CqHbKZ8v"
    "hHMwkY6kQpGs/3p1XDppJ1b0i0M0w44AHenn23uqBj0rcLze4GTChkBe6yCgInzhYEvG7/ewfy0zTCcO"
    "WmQbCgPYVQe2dYkLgMSFk4qmYAJwXMM0XgIyUXkhHDNeF3uIM4XBQ0yZ0aUhBNOwPynlJAgxg/RVw4nl"
    "1ILR3HT7rTU5JL/5cm+pWSCY9DVZFdPEjX6EEjiMEubkj0SP8ji25+cTFJLcIz2jZDI9ZH3dHDGCUajz"
    "pEhB3IXaD7YzmCG2jkri99TPaF/Qel8Hk6VYbCZkfYNVImjPo4g2YFarQMqK2jkEDX9AeoxlvnFdnadD"
    "LnrwMhWMSamkF073t+mrgnzhrL3YL+fM9AHnWU8UyWYVQMbBosUwGHs3i3h/plKgE74NdgduSOJLis5r"
    "FjG0fBw/oVllIQJ042SnnN4w+VA4VZsm59f0Jbgvb8i0tI88EusDe2uAbAWTo4t2LFQsy0LfqdQyLhjJ"
    "4pp9174p3KB2FNY9NCnWQsp8AUvPEsZMDRmuotgX1S2KHjLPWLNYjJnxO5JK7ZOme9RvvgiPkrXWmo4w"
    "9qe2MKy/y+7F/9P1jUDai7o2YMkq82IPMPj4XtQyIe7T0uAn/fKf/Dvu/CMrZvjUxmd9kqL7gD2o9Xeo"
    "zK+CqDTGsl6VajPa7x+6pazKu5VIsccyYa1+e0FNAbBZwQlMxazvu9LT4oN2ti6gQE8On8DvghaVy3Ia"
    "vke8ZWB9B8fgFDkFaLhqwj+1RSDOmivmuzpRsB2Tl+TZS3SFoY+rv4Bw7TU5ZUYWMXSA8aj58xarEtFW"
    "edxow2ro6N0HRTYeF3ZQeIyuii0OAcOBzhhbef/dG8vVl9F/wxhDKAhPE/T2M4OalZPFHJiGOkb0vlkB"
    "FHg4v0srdChmkdoOSxgRAMhvQo7GUcgcGX4iOoOX6VLST/YYWGg6SZtehvJZ6T5hzidkK+dU9sdkwVd8"
    "n6mCqN5/u9g/dLj/+X/+qcPP2v/vcD/0z+FCqUCOIwXwT5496YeX25apctp25wiy4pNPa2wus82AR08t"
    "mo7/JGoFZUmwJdNjZBF3UNC2TD73jgx/FZHu9VsWqPIzzbdayX7q/qygszWGd6yRJZOKQNHFRPEx5V9L"
    "nLoj0Qb67egSigA7AIMHCIZlAfw9lj1u0+gngu7a1XaO9duV8ZQSEsyECRBoj6x5FR4BvEbLBtS8q3U/"
    "7G/+bB5vSxCiPOUiRUbZfr/AOjuCn3mg4ECaiLrDS+MIwdzHBGcnAKr3aCzaG5va9Azod+kBbDyqXNp5"
    "SHztgvnhOCwH1POEeodO9bnuk07J1H2aEhwT1qm0ncGqx1QzdxNcrD/NK5VEQq6SfLWoJ2/Rn/qhN876"
    "lBILCY8SGTfOjUQ7teQyt31f1hMeYbnsOzatcFJk5rIEnGM2t5X5gLzTf81OwriHlWu4tCBZfotqrupL"
    "lUubrDVBtLFIb/Ga1Fx8eBB6KbzgpJtM5Gvf9idPYJZL3XCT+1VhUz3rSYb580Psz/YrJiHfk9VCdeRr"
    "Si09q9SsfV8FPegoj6Hp6lva4SbdGwQdN0ZwxiXOmLG3p06ywr8r1nLWsKmH0/sY52z1zzFLOaRzvS1F"
    "Hm3gxBRO0G9obebE1Y6xiXgL2z2IP9/LZ5Rb59z51y4pYvx6IdxBcBeK1DBnRRelrmxk9/6lpyiOsFz/"
    "effGF8Ojb+TvWzMpAHgmjH2nPB0qFEGG122/OFPq37r/BgUKwXrsU1XEO3lBgC6IND51FqC+tdJT1rTe"
    "651uEeUnA805htCTutNGu3TPoUPlY/SScTBv9YdcBem5eWTRCwbi1T0TC6ApCekLheOETpDDOiwDJ9LR"
    "9dbu/FrPqn6d5RN6vbvXuvz+VC3yw4sRUro9ck7qzp2SSFiMtz05wyNETRSxulfuzn0dKpc0P4Llc+It"
    "LgW4oH4RLiNE+S9hD1Uo8PWvqApikV7bse2PZicxLFyKDeW8j3Lxybpc2R0Xkj2fiii8xHYZK9em8lOZ"
    "a9f4dm2wBNoDRF/4WTQUCqM7jk+mHswJv552fq/jW2A3FqT7TT7ujayYo+3edY2sPLb4auDXfi+DLYV7"
    "MUiHi2/etiwBbDZ1c0I1DEUztPOmCbuwZzg53j9YiD38LMq3c18DQBqWFw7AUEkXU/NqN+nVA/ohpbNn"
    "ItOn31ieLfF+3QxJhw7NCCfoF55JiS+uScM5PVD4AAY/b5P7u0FAyigtEijLkpkyuEi9ckWfiPw29uOI"
    "950zV/gJw4SBIC7BBsB9nddWCxb5jSYb1FsXTXNq8L17DeqchX/BV2Otl6JU3j5QuCHye/4VMWMvD6qO"
    "vDzLKn9PAie7R/HSZZYO1+O6eRj+nYCqcVSGBvfnxTbw+OR8CpA9H7O2i0aq5MSdInq7NPmVnLi0yFAj"
    "VpckPjpu1KujUpMUFBuqorM8WzGj5lypShOnsxLO1GUtYuJlJfQwYEW33SEEBLNozdaI9vpXFxhj49W4"
    "iue1K211socz9WIwSvkGugVJrob6+qtFLWJqmUGt5tvhBvku9WDoOXTjbTjjsyzTPG5bmHMa0fIIvxjm"
    "vGtHGgJWVWjNeQfG27LCMxevnUGEQlb3M4qI5mp48/oiWnKayRW2qESSk1x/d4w6f3uo3gab5MSw3wMu"
    "VjVU342eQMCFTdEz7z+dLDwIdT5ZG0U3LzO1OPx+vV2lW9h9IahezeE5OJDhCl3DBCMV5saqgFFEcwfv"
    "p9r63atX8MNchgTOUZbmaHNz2Xb69NNjkkDRqg1bz+c0JxxqdmsrpbMm/Abn3np5LEX9LtCXlDB0/en9"
    "Q8u/8jMN61sVkw9hL5KB2pi/BnZRwyW1FaYveb8XIPNbflQQjd8uI4CSPvoG5bZPpI2QqazVROw8s318"
    "Nv2GpYJjkDori0Qy+NEvjMlA8HQ8hYjQPf5antg7TAfwzSGRlOu35NtjjFNZ/STeHpDJQ/2lLu/7hnsr"
    "ZW11QlnGWg0Uv03dvs8PFQ/3y0r678ol/et82JDHqSpVR1NQqMYBkK/6XSGn+oA+6gzNhVtPHKXrp7e+"
    "BFVH0yXS28SvWc713WW1kb0gCj/HO/YLpM+4l2lzcS9nZ7/pAN1BENIvVpDB0uas4lmO0pHvmJpfvitB"
    "3fL3Se7cUqzumwLj+CuU8PPAOb7+XjGzHFPIhjd2WZW8jmS78IOEDpjOWTFFsW8bVQyYWk65/972XMDk"
    "jsChf98/uqaJL/2SVBd8maP9EQXKC6UApk5OV/aVx0FOuxA0OvrvIEJdJRuExgLphr/I0zq2E38forU6"
    "1mBETnlHSw0sjXjAKP7CryI4DXd2uF2nklIUqiWMVjqzqVmVUV5wwbMAczTb3gelJATJc6jQH7Fs1vz7"
    "mE3c1BXNe1YAO3022ObOtNoexqvIGEeLeR8TG3E6t5wetlxiqYbkkHz4Q76cj4Bg1CiBy+G6qOJbEmq5"
    "uxIU5g4h5Al2rwGWl1aYx+DjyLM0X1dkNgPqtRT1lUSQb6WeVavCmHBcQlDE/quoTAcB5MX+pviJIYT6"
    "TILgkfdsy3HAotY4hQOXQSX6AatFMbHGBxR1t+6qfWSBbZfxlQkzJ7iEay0d0NWvYC6ekiDjMdp3ydoO"
    "VABywbQtn9lWiVmV117OK7tc8a8P9zdp0CfXa1tRkWVSoTKH/d65NlpfArFf1cAkkQEhmIIqYixrb+Rk"
    "tO0KXtdgexQbpf+QjUrVpSBRksOSl1NgVf47o/kfP9XyL//9n7kQG/4P1oXDH3b5/hUC8EYQg7mnF+Gd"
    "5wXlFtqaPD0yb5eyDCrvf5syyqBtYCP4mxVRVaK458TFybn1py4/3Rd22RoRT8Ld9J0Vtea86uF9UZMF"
    "55WyWmCbu2dS7iTf9CBMlFzzTDyjNFJZl2jI4a2o6zjeX/4HH1JAe8JpQgW6Kz1z7QX1wjhD06Sh8myC"
    "I0phAOkz47jeUi1Z+N2ODVHDf1DpXd11GjJKI+ZZwFzrcuWkAmPAZhOtjsjKMRPkCxgPeqaZqS7zZ29W"
    "r9XdYvGs8B0iiV5IZOGGc9FFAfVTOrl+18VklUpP7Cno3wwsSIoCqC+KgivGF4TBfGz4JQ37XGnNYzcH"
    "ScWpa5gwEAvlmSz1RbLA9dVOapnErulqzZwXvtLvBB4hp8MPIOgWJMoP6uIBf1qRVtltwoU8BH2adhXv"
    "HdaFj8a+GO7d7iBS29Y7G8pv94eMwO73a1/0lIHxOe9XRLmZT+RjeTy6rS1hEFdOo7WPpXV1aZXO9SqA"
    "Ey43ZXKiSxAIIJleJ1kfYdIgcfkma8OtAcwDYOvK3mbcSFXeX9ktqp4KRIVmNVk3xeZ3Kq+05XlxroXx"
    "fY2zXXxE0xmak0tcHuOxL3lQjLvDlIBDzoziTqC2or8soxgVJC2duZd8DtMlx7Nuub/5zrjPM3XxFq8x"
    "JTqscWH9r1+vrTSUq/SNYVYDose/yqTskQ6Ydt/cVAhnvr4WQ/c7dfZW6dDS/Zf2h6DxZcfjlrH/yZyp"
    "7oY0rIl48WpWXhmCw4TT8wft7TGHvSGx0ij7ZAYxtcR8XbGBUPCUF17JJn3mM6Nj+YFN8nIB5bn6Myqr"
    "wmm9oEUuZp1ker1slDKa+kT+ti15rjgRtQKRspkx6i4dFTvdWoEkTE4blyMZirojaRHWyh4bhCfI8tuP"
    "GRZYh5NGf4pOrZSrqudpyeL4kslfnYFfy7boFxONz3KgVxe8nipXvO86SQaRb//8fGJpu9PHzmjb5IIq"
    "Eu7wEYv42a7j9yYQeCOmnif6BKEkpCjlvMYfHxfUQGNb+VuKvSHXdFnCZcImkO4DHZRM7Cc7/q4N5/3I"
    "RCu/MtrTXvaflOs2p4CCsqdn//UTotFzeWrhavJK7zcFitVQhp0NO2zKhopN68e2bM0uOzy0lH3FspZS"
    "w2SxwGRTGAwAZzniIEldUH2hv3JLG8oS6TYjBF7v0NNCCy2j1qqolrbKb6oJw8EW5445DhWWrGwWIMKv"
    "nOmyWhD7Ce53NS/iD0P5a+F1/RhK24nYglNC1Jf6FU5+Trdvo6NSwrid0k7HrZM3ixjJSMSwe/y5Ellp"
    "slZQ5xng1pC6EHUZa1Criek7mHK+bPceuZuVgoloiXI8k/uVe4NxuB9rRWArocyrkT8+PKl5sLGQiSVv"
    "+EKUKIGan7NseA4v+Wilp1su63vjvFTpF9BhdVpAAB5vvama9KRFFg8/2TI0ECGo6L1h/jrfcZYKzScx"
    "hE9GX+1uAenX4dyiDJxSx7US1aifbVht/5kphCQ8vBu2IYZiCUMQ41M0rcXP8xjRcvwjG5SwWDloz79N"
    "TgsGNV2xlLtX/GgGnnFRZmWbkpmMS/EPzQRm9neLi8p661RACZ4AGFj93u/nKQEVE5CmK6yvDN2AIN9l"
    "2rq54Md3LtXBQ4EhULBaTjzRywa3ujUO/vkkle8fR2IYvfwOCQWAC+OgMBUlDc9pxhA28Pfy4A9miozF"
    "v0I2boDIXV5K+PuqBNmMDAnX0jCf1hR2V0Tfsc/fSTlIN/LrBuy7YOK4BX/D47JASW8a7X5SOYorBWKw"
    "lWcqIVSbrvnx1CelfxGeh7XFCsay1a+39qztHFLOIfUavCsT3Rw8qQon4L/yaqwVtG3XwqAKhzdEFZF0"
    "VIryYbhEDh6v+IhLfYf0uC/zE2VF3+nR9TYwDDSPp1Figorjub+7196joXdlNuIsfeNl4otHNqBuhPti"
    "/pcaH5DMcyMiZXuweA6FvQ0EDRQVt+hvF9In03329wqeDQAQhecAImwnVeZ+2wdB22DVzZoKM0nanicR"
    "4cPwZJpUaWkqrcc7ekjv15LgtYBpjrlhEh6H/xaChu1OOjTyIL3SXtyDAayhEi6LgMI4iQ3CkOfB+7J8"
    "oqpyqW4wFqcOIJ3FowBrKtkSFoMTHl9FFv6mSFJjujQaSxdWqwT6ncAJFgmjq2ez9MqgBYFfxBRmS9aF"
    "1HE/H3AItwf7vNVAIWBs2Ue5F5Dwan9LfkuunLNgsV4O/FL9VWx5pZEAsKnCrrKrqXErwBvIbBvbQ6aL"
    "WifmzC38JYA/Ciz2gdvRLHW03MTZ39gJ6CWRk+1mgGFMIGAkSAJSGIJ/UAd2QqoB0C3kKms/jE46cxwF"
    "sva8EQzmuv6/PNjqf/3rP/Me4/Xv3DUHYYFcrf9ijQkUOUARGqUV67ahsUTBxU9IRn7iCnWsV5X9yfZi"
    "RF3r8KMYoXXt/EperEd/8xhGszz63PmWdy6xhaL29iLRSrq8FOnTmrztFlDvi9rAcLh9ipMARoGH0COl"
    "0gW51X1Bsz+GF6Yy4tjzPCRpbGd+ojwmjE6bzWjxdUjb3CgcUSp4kdQxOPv9fojs7z3I1d8BjOjqDQ4E"
    "dwh08Is4C+eUOAg2Pk6mlPZ5Qeuzyqg+O9jdw/svofHSKwmfHC4siGTAeAAXNIMkfA4s5iivo4SroGmP"
    "4X2eNTN4u6x9n6stJjDqWO6Pko2/JXTLrpYimgu6V0utfu4pj1lQDkSfORMIc8hM/G0Ndul2nP+9/clK"
    "SnxhMRFdMvwpXgz0CfKCsPL2GS2YhVsSFGyXad/3SVF9hJof19vwW09ryCfPARkOiX7HxvPT5harNw/x"
    "MfcvsWw7uYMahTgb9zTC4fAuX2uBzLt0SdZxzKoM43mUBceMPbAdYR9xSHQg2MUZOhuy/TPp4f6g94qA"
    "AigREpuAi8l2qJP68rjGkXjzkRXcr2vq8++NDGZ5R/+m6QUsf2orUP6oJVL9/J3G5zM36MrlZkcdjlaO"
    "IuYHR/nIja+o/qUmVe3VKcKQW8NoRyn52jIkJHD0zzkhKzRMcClDTrrLc/TK6f5pDxRNpErfB8YjLRpR"
    "vUp+EA7c+0SHbzL2DqTpFuM13l6rP75C72BNZNMirJaKMMxkiLnR6nBbBVfYdsE13cThHQA6dHoek8Ea"
    "rVpm5lKSM8FGvb6n45Ndf8V2IpAp/YUEcyUZFkwiWkz7wLN/T1N6v4UL6CpQxMVch0mnuoQmq2cWdsUj"
    "eYraQPY6pwXb5NmWhXida9tvVIQ4tfl6yUNpiNZWvIoCIcEWvIf2m7tauQhIAVInhmdyzthh9nnaMs6G"
    "DT0w2MCR2V8nTMfu6dclCuQvIOIrMo5SBMdUDggTnyf/ySD9kLiqpLO1U/7f2Y9vC7cp5GI97AkARn7J"
    "nnO+7c8YT3dQ9LQY6Cwev1BMSwSwe3L5fEarFexkXjOMLo8WrMcqzmuAXyyHV1ltML91BkfbLBOmaqtJ"
    "7GHUNrugTJadlGWt5pTNdzj79pkj2XqrJIBXPDBMnIH12kE1qEddaa9ogkXb5/H3KXJCVfRp2fdhqMYU"
    "+Gd95E+rcLoG7w65vwzAy8/+DT5CfZ0yc/HTb0HbeUb4H3tfff0yNwP6nnHAEzew5yl7eNQflgYmu/Z7"
    "VEwYDd1bhu6ZG7T0Zv+SgmJQFv1D3hCH2ZH2m8bBWmsWNlzWDQTcH8xhFOLs75MmMy/aPkSJFrFKM1Nh"
    "cX4DK7qKQ/pqCXECYQQAn9YXhOjjCtwv2C8HxvsSmzeFKmivxT6ZKqEnNnCTo+dKb7VDJlg+zB6xv2pu"
    "Dm0kjifc9eVP0zaioRBWIp3uKw+32fu+cyd4HU+B6kp+rcvLgcPjwQSIpy+aaZ2mhqbZcTOOLQp6h7I8"
    "BoLPZiFG+kDsK5g6y7XitlhhJBd5z3vOMrSMwIqDHIa5ap/5FLrfvinXlY+fTSBcCzWIc0UkxnXnI1MQ"
    "B0NSEE2bYqjrKwPIdMQ1JQVCuho8Oyg3+e5XKyTMZwV1DrmoCirFM/7sQvmz0/nAhWCPU/33DVi+i5Fk"
    "7D5HnBib1nYqMqCwWhp7oKxnUu8j6U5usmj+D8NUJfgeFabClndoKulNkP5m19wJqoLEwy+6OY+2Tr7U"
    "pekj5AKUjTrpT01ZiZq1BOtPQwYggdaZZz0+l5Gbcqu/57ZfsOH2ITBge2tmdvDZCPRugu9Hua1/MVC+"
    "Fq5fsnjFopPKfala5ij/3HAtEAIj1rMRqUREyC3nz9Pgvfd/npCjBNjdsYcKFrlB7lUDXWfmWqWaOOv6"
    "+aDhI2NHtjCI69nbNeeeDs6c8jYKmzCO3dGlm/RNVEMtHJ+q4uWhea0BCzVDl4Bu/Uqli01/DmM5kLD8"
    "YB4xcuKDPy4NAms78rCRP+889E8hKvJwQ5rmFuIwWEVk+lFZn37mMm3JznXMp4j/5EYjU+zRIPnm8/GH"
    "i5PWAIw+CWaSJAqXpSmffIb9i7xdg+3t3zcrkKbgtEgOMh+Nz2tuP3AVpdeqLNjnMww3+GCa4SrC50Oq"
    "uG7z7MhUlutynY0WgFPkiXD3XgGqvFdDAWy6KKYjgXKh2x8X2ZyEH59idt2ugx2kWqYggjXvlwWGZIJ3"
    "dT17+2GrremFnPUJx2YCo9Im6cSVT2wOSsCDbW8Byob18ffbtOdjascTgtSjHN23RmdrWvfrMwrDcRt7"
    "vvDtOaFb8CLAB0Lb32QPCBRg+MH44q7OcRFX7lIKQc7PWi8G01De2KA/4/NFJMB0jRPkZwI4abDFfqHY"
    "PNDfNhLy52TZ9CFSyoT8H2iE+gyaPHRprnVGZNrUKKvLSMcPZzLNgruiJ+kwaQzly2VJDchtDkpob6KL"
    "Ajfkc9AcW3w/SQeT/i+CU1RKB+k46smzY0OGzNMRgipU9TSRPnNjdGbmOwduLhhxnWaH3opRJk+bHQHy"
    "hbJ3HhPva7MOvZbIveN4Pz+o6dfUGk7GQEOe6bqqvdln1AMRqIM4c0Y855WCoMfhgd9vOZ8iLOCm8Pde"
    "/40wIPh3+EO2/O0d0A5RK2XTqnOSIQWzCmN8aRZGgLiHxmspQSWQGsEG4OfYpjBfOLz/+kDWf/tnLkww"
    "/oNb4fAXvJJ2hcAzbEe8EVr+6E0J57JAMn/7zF730WQn2NNRnoIXvlVX2fhy/n33JVc7dXpJIzN4vPPn"
    "epr65QcptFXDWrRbkx//PvPFYqUXnfLfxZwIKX6GR762eBiON4GLv3ubXMdtwaUFiWVACyNP/+6V2zWt"
    "PjsoXGGqXqaIQXlzBqfsnhGMfugLktgqaeNuD4EERrq7wvxqzbVmJJhe3uyvH7YzXRgkdYvHK+qjRUvO"
    "knkQ7PpfpSOLvI+Jo2BihO6sOKIFnjFk6vULZy0wSutVQA8OobYhN8OnbhQwq7RJmea0Vh5rBLS2rwMt"
    "mXLTb58y+y7g5IJLgyg1ltsCFm6Y2CdMMT6RLbGJDM50+fBeyMLcAFqtlxxiDsBELFplPjYqGG/8v2bz"
    "Kb4jcXx9xP9+/3bMCDlx5l9QEY265I0vkj83mXMVdABrH3KN0dI8XXlqSfGsii9dyZf596pFLM0/ebKR"
    "KKp13vJ3frH0jqF6cyF4uNUA8E2MgvXaoP05aKZUr0D6ixtCtLiSOSWmaBtt5E3wq83fsMN+0kPMADzc"
    "I3mXMe2F4rgFNoR7oSEC2ojDghfsBHtg1+ymCkh2rHeYhANSvyOvbAfMFX3xUjagdRFPB3sFtIMEi28f"
    "AZn9t6fILQDNIO9UTHPg+0i48pNnovuJvREfWMIKzwU/O/opnt8qu9K188Ujaw9jElLKKNk5JrTpbjeK"
    "CC4JV8T0CCW6PyBacm/uK8yZzl1gdzxO99YgVmtRLmfyu+FZ5GokbY+eqwlx4R4FfGr36SGiJVfuWKio"
    "R0f9RBUwIXf3RSOLT287NkuRZ0sD5xQXuL4NwUrS7Ow/o1W0drm42w7C9bf2xwfgTe0ijE9MFhBSWxaF"
    "EZ9re8Wi+yyUhRjDb8QgEGTGDoCJ+9ydSnWZ7lBRwFo+6UmF19fGTNNu4TVj0vYTcwrElhykIy5ZRtSg"
    "VeCLJgc8ZwAuntWkzeSzwuDc+GfEZGwdu0cfu/j75XiGPaP9Ozw4LGcPdLgI23Z/mDfgORfJNZO2bZjG"
    "lOhPvF3OxbwmcXU3XKVSAdr2Rnk082HtqkkJHdhNrwq1vVnk7eT/EqaYtulXv4lD/UY4WuhoBWSjD+7c"
    "NQ/14L+DiPcx1fmBJs4XoSjKc/JJmzdCMRdMpM7T7rcSa7A/saGfWZXsgHs7HurGHsJ971+8ZS8YbcYy"
    "14lBVJ7MWqrYHLWZHtH9BtTiEmp5PimmnsCVRt08CIT+tkO/BCvDHIb1ZnlawGV8/3jdF6FA5Cv3FIHB"
    "d43lEv5Bk3YF+vzNyL4eO5o5NfFHKjXc1qVctXTd8rfy8ifXqdg+7tjPBlwAqNYqpf25VD8zolRU8kYb"
    "67UzIAVYJDZxVrH8ZXYf7AMQ8d8HP0Jn0RfjMbpH6GV1uMYziRQUbL0tyG1f9IG2rqxoIPbNvULJPTAM"
    "SAi56gNVOdvfVXhJfSi+bajhsMBAD0oV5BG+JsRqcRP7XlQX2570Y/mnPKm11dQ7BHRg5vi/QY+VbuMz"
    "rA5dy3+X4Ve8Q8VM4UQbpuJnSPZ6+5uEX0nrHhjvHGyl2igEw1FUQtLTPW9d8hR3BmYHDfkolDJzc2nO"
    "ndbc/ea/I+uWkOzcFNuhvBIvht5kj1qfl5fEi4xsDozjiJXixFoUt0xP80I5BehaYFOaOH3KWKQ0qhoj"
    "1MEKKDHLGvx9iTFCwo7JSlTqppZ98p+zrxw9+BTUciKvnA5HR2Vku+Gs0rEsx72luZXofLOeIaW/w4zj"
    "MRwXNBIosTgwEJQwWreNDfXg3bKUsqoN0o+AKjT9+9lkcmElVhi9uGLGchXhHFnlOiOQ3ziUtl6Ln5in"
    "+1NUIgxTFHrk5a7vL9MxXGBYUuPEETEMCAomv8ODZRNjf2wl7Ii9zvWx+TG6bpa/NqDrtaRFbt2P+tC9"
    "mIVbfjK2iEF4OZ0FZ5y3Yf3V1yfufswPXslEjld9nIToVlaRu9btI0guwW8rq7JyxLe9zZp1vi3HQAH4"
    "j+jbQjK7n3wq5xH3v8HhVLJfG2h+2nQjpAqQEQxacFnQu5s2pNMPom3Aou9cbogcmRc4ODV1R5Ke/+aX"
    "anQin9GLncht+3JzRt80nb7Ndp8I8w7dYzvTzbqEDoEaMOFN4SEALDM7FrDTCZn0B3wVL0W+FH0e0Du+"
    "N3/4ozgZklzGyPdT09TovssZxfr1WQk6fkf+tL5D1BQeyreNn37yhv7OvTLHc/8rAXhrYaBFik8P+/FX"
    "YZTyXaM5Qo0fuvBwaeKWChYC/OARIqN/YMJ6i9/G6oxh6SR2mAwDhhblKi+3AvrGgk4CMa3xKDdu2wxg"
    "MECzbJ2PK9elY+N+wO3ttPpxV9M6qlEcQp5WKtMfCTFIhg0ZAwnJ3J87jFiZ7uecJ+nf9M0eg8VbXEjg"
    "ERkOvR2F2Y6iVCl5ppTFqbwqi/bpzQ7OjWHUiK/x/bd4bOmtHXUYKDoWBCanZZvDN2I6reiu843rfnbz"
    "ja3xsItlVgZJnr/PHxb6POfNKG1qQ39X5UaV1b/xvNBtaXN7BDJl0k/B28dVFBWNPZOuyuhmiDR4Whqo"
    "nhuqfoGQ4Io+aFAjBsJasFml6mBJ9OTRCi1DPTQNN19adsQuFgmhIM/fxQDHgKQ8ZPEO9EUaz+ozv25H"
    "xFPN9W+tKOtwxCMbh6fVYXh2pqZzAVDYYqlJb81RgW6TWPVRlP5BCSgntkcZOkIlsIRM8irDVJ1xS+8/"
    "ZarqbNVYiZ0e8ngUZhSK5uQp3Un7wqvAAUpdYhOQnNJ368OzU8rdqCV9tjZLlekKVP0aGOQb5cBKFWVI"
    "s4fthPB8A4B0fTPINNNfWXIleG8jkzAYx5X3P37W9H/8t3+Gp63/9D7wD7sy/9+fNX2Lznjlts+OKUIS"
    "vPwmLtS9Zl2XU8Utp+XSYotN2nGzP5kfXYBVlfPXKITnNLyn17rAc4pZ0rUNM1PkjJZIe9OvnerJvVUW"
    "piCpQ+OdSPtixQHg6arn2FylB/guvo/peqiOAEGfWsCs+KUi7q4E7Gm0d37guZX1xY0uibuy+jPI7/Ic"
    "MnhJZlI7eP+LuiWYcspn+oHF/lhriDwgXHqM5TLjpw6zW0apXKbB0lj8t5WaSPHUOD7mCKQ2xkMg2fGC"
    "4OlGpdQdbEojobltDtLBNiK92B/6MZgv4VIc+RIsmXu5+QEAMvV9C5aCnw5A+U+faOZcISNBTEOQJPmc"
    "dPeW7343TyuKmxLcoVhifXeihF9eBdiJw25aHwEzVHx9otJ+ADtSEih0hI5gkVKkGXxbFB/C5xIU77ZM"
    "RcjPOMFhA54fEtunMBOXET2Sl3mxSw0T4hC+Q0eRoIWiE0E8J3aDsYo03iBgS8y3t6Ms2ylZ6AdIySoj"
    "RZ4xM6Kw0Fc7nCyy4tiH1k9TnSn3uicYYL0R2lp9b9kwfimfuAkHQunLFoghe5BrSsGXo8i1xW/KpFSU"
    "UoZm/zvfS1hOtGaat7sjljDXKXvosQb5aOT7pHGrdWTrWsNqhSTz58U2gUhYt2AbIER/ikLnhBsHz4Pj"
    "muYoiIm54oQC84REiqFy3onRjQsqS4qEl263/Q+iIMzIsHRqiL9Y2hTNV3pcCcp01LShdZxOL+nLFWpF"
    "uvpo/qlUOm0VEdkXdn9EtJR7YEj0+aSusAWCPDYLlGQ40yS0TavVl2GlJwHiwUMxECGqA7pAIoTe8FS3"
    "xaak6S03HLDfJOOp4cmQSh2psUzQsu+6a3Hnb0UXDnx4Nd4XonreO6SPWfl9K86PfWmy32L3TBjPP4mz"
    "UzvI8M88ln+fttNoccjAiiRmN+C/4Ocj9/RCQsXQ/M7Zsztv1i+be1awIF9ChzKwz3liaRcZsGtyrX5J"
    "SwEbnNXif+XykaXCFYwHK9gLPC4KBygcwzuRX4g0yZ2+aPL7B3ThCg0DfCy0JT6PEOyJN0ZY3Ltiiqu9"
    "r2iRH5XsmKu+HDl6pZeT+/iWu1mO3ctY0HYWCjILU6h2lATwJOzCrjiTbQM8UYSovWMBZlGDz/OIYJXu"
    "/LPzoPZ67wn1IdC1w6A+qTOJ/O1BZVWdEDYHTGywZO8pgLN7UAGdpjNgDH/91kDgPPo6N2UqLTxY9OCL"
    "deFoNRE1xxI8R3Yr0pN4aR38/Gp93ojcBjLvfQGnw7Ty5G9YmiXWyrvTXl4emlMjMFr2R7Ex/+qwh/ue"
    "ZWN+vr0983E4cNdw0Ui1rU5Vpd7PAvjMSLnZmvQhMk7toGj5LAxVzjrCqno/1uhDknpk+AW9qa8ncdM5"
    "mTZwB6jw86AvQ8yeUkOc3HqQavnuCIqU/lFJm5O9t4LsB4895dJVJwgMNajehcFGOj0Immh36K7LLECf"
    "8FbsQJvj2EfdPuGMIfFU+1tltMjMDnmJNgLW9eQYwS/rK0ihnKUPiSzDt4ooa4e92ZLcT1xrIGvbA09F"
    "G0HAWA3GIJoQaLBb9Rl5HL1oNFOZYMAmoYItTRnT7Wm3zor3Wzp53FQ+EuPEJkWdx2zuBtkuNDGXDhNv"
    "dXg285mTvF+aDS6tWsI0VxRdzgfPPXcvisSIVDVgCL/WfcQfjWMluV7KZJZ9fhd99vNd3FFY1mrd3ERj"
    "KxnTGGybUBGWlJCJvEViOv4brYz4QvK381vF52h5SFcWanpblllFtMnD42V4HOuy9rLGpprAmThT1+1V"
    "GI0DrpimfXtje9PImXnL3xHGd/V3DR95Zpv6dq+Zfvk8qvkvc7njouRyoLFM/sGwuWxGM87eoikXUVSn"
    "hoduyk+VVrj4LWkDlhZCQRyNWWuSqmfPLmD1qPPi+8nxuXFplfPYDjoZHN0vt+RtJ85fzIdcCNbuMr3R"
    "Ioeo14c3XfK+19v4/dGXnJvamCi5I43r3YiGoW8L2dWqWn3mV4x6IlKDZpV5sm/sln6DgqzqqZG/53AL"
    "x3ilC/hqNANXIo93+T+fTFuxRWqe3cBZ1B/u7Mtv3HswFpWr+2WiFGNCz6C8GVJ40IWaX5BaVaH2giNM"
    "4Ci6HfHtN9UJn6AOGqYXglcsfff6uVAm+CMhMP651vXcZxA6GDH/c+fOMNxluAJaHntjoMaBIV3eu8bP"
    "Hgpfrf4OMmNSafZraMwvAo+hv/y8h3bZOEyuZ2+Hk77iPh7V8ZWCEWxo+Sths9vSx6+c+WVQsUi6ggmQ"
    "Ww0S4ZKbYZ+UTy1IQz5wT1EOYgza/AMG29t+QuldWifvWwH1qhLq1M2Wo+FnXaVvZnMC4CywSa/WiJfc"
    "0XE6l9LSo7LzD9OlwBHv91c+sXZ4DjKE3xWYFtLnwzyN7M/XT3MMMsfMJCyIo8Mbr6G87MEz25/AbMVl"
    "7APjfq/3sLc5Iv0Npk0paM2tfSq5Lhgllr9nWas86IGUHQO88H8q02RwoKEoMQybU4B5wfZRDu4LuoEn"
    "O/bD+VnVirH9X4YrVf40HarKMzxFUGC1FEbldz2iUtNhhrRlzxWY5uWU/5e9N9eVGFq3tR7IgfsudN/b"
    "5XLvrNz3fR/dhIQbHCQSQKREhBDzMOdJ8EIcnWTfZCcE7GRJS3JVueb85xjfcNnz9/ihjF/+gUi2/nyJ"
    "UtA/08HNBwQDwKFz1LYS8JOBWmxY6RHcJyJmRFrKXoXl0MNoZXsqLRJk2oq1DYlcFrrUz5DL4IDMMgCt"
    "tkQd4Kii50kXcN7sbzgrSIigcyBkf+RM+G1EQrOE76g/pSR5P504j4RpwMYl7DlWfNw6Aj+nftxYbuUB"
    "xiM2qcqn5+FsFsl++ADdtzgK1CSo9zg0GGwDJMLpQp/sJ4NNFkZ7+JBgKhrYkrEgy5WBcWx2Nlho4pwB"
    "Z+9yLRdU8WIqW0PA9ZvP/1ZjlP/+n7m39Qf9R/Mw5P9l614aEGA7Urp78PPZKNzofXyaNDs8BaX6sm9c"
    "gD7edBC39wSvpCu9tuWlWcPVtImzE1iJL0BjxLz5JcUVUarriLs3tfsu0+3QkMpya1FMnpU4ffiJceCG"
    "PwOQEjbSnY5+VcQF5iQd/8gXXnIQLfqDZQGLpwoKwC3o2F6lO0tPykpGL1l4RU9MxwkmfVmVJXvMY2yZ"
    "Xh7xK4ihUTzOwIJbflxbqiov2BikPK3Iz2yDAPucMNbB4KfejmOQIGMqaePhbO5qKOwhJIke4/xQY25T"
    "1W9YHcZYzcl3Q8Df3eR54hFKbi5FrE96gCyiZ1dZkZf7hwcYVzPy0DbEnwhlQjVMO1YNO8Tee7ZzaxXp"
    "8REirAiZcZoNktdCQGGJC47sYnbCVFR8BmiMBV55E+zRxfgx3LMhjMpUEnXeqNWp2CNmLYiWXTSor5Sq"
    "QhiZzCVeBbEn76d2gdLHnGQxYH6xgjNSwC/aNO3HuIhaat0vzTW962xHe9Xsx+eAz/jtVjx96Gjxco0i"
    "frZLI2Xh+8H65tpPET6DtS38X48mcvc/bphfoEq6rkUVuCy4Qs4zpYBvONWDqLEbqRMaYpxXfzcblke0"
    "jih5RQNhr+htef5ElcFIKdtuHdqbTw4Mp6sIWd1DS3GjmILxrjSTf/k8Pr0ULfDgZZr6m/21q/lmblYL"
    "SXhLdFSJ4K1nlwSijMQzXC6z1TyMDgVw311/Dng+cDfnFaBerJgZrMHShiXY4tFfldgJ1f1ubYCMbK63"
    "N3JsycD1K6Ojq1ItHX+lamH2oGEL64ECjS6RVZjGgAXozRH7yLQG4llPuJJAiTIQRAei5MqJFpgTbudr"
    "RRB4aLjXRw7tjleNJO5vrppmHTEZ+X9u0aS/AzW2ww16VrHyayJPAp0OuzPQyJVxt/tzBIk/E1HYDaLf"
    "KigtoY/D5ft65cMnq54pxGOmg7OaaQgkDSApf5mBFy678tuiTPv+4YOsXP+aYGeAz0DCxCEpkgG75HVf"
    "l6nZikmvoaH8FF6tz2oHJw2Uf1eqviZ7UZuHTiKToZk5LyhLSprDiuGgS5jRq5fctzoiE8hQAEykgzRi"
    "fumDPGVVG8IpmOLZDTy/9Wy+pRz2Bvz2jk4EbH5Y3WZIEbfTOkVC89FqdnBoSXlLyok9MUc309RjArUz"
    "CWnKMnfatCAI8ThOAgcFVOd+kG+B8VtdwHumZjUkUPt97EueLOy56sEIiOvG/kKMpYFBvzFfEa2WUf3+"
    "Pojf4E4qOXtmQj+//+iwJ7yZX1/860FSIuEHwi/kPBck6p0079rqIkzdN5wiwZohIK4M9VA8FKagqflK"
    "dDdVgxTGWnnVq1X+2uqX1/iv1ML7oZAlkWOQU1Wpb3T/M2vXlgdNSDbHDcU4Nvn4p6HsPRletRSZYHNS"
    "Gd1W6HwyA+2xJHDRVqUsz0GvBRNiAD0AfqIFHRDSu9HRlWZxI1FE5kfaDXoBO2ahRFrVTgXfZAeuJ9FM"
    "22KrtpXhtWmfwF1YF+qrqC8DWQB8PNen9yrj1rmswB1FVslFaRfRFTK2Qmre4Dvmrc0DwPp55Rzj4DqR"
    "lKQXS+AybkIAHj+wr7BvK52xvVkadc+ACtTTMjHbusTm4Ykr+ddnsghfM1B94ome/Z19l6lfr/mlmouT"
    "D3FZoIOE1agdqNrXTiMxWEVHbytgNVVazfuScoStderXTpRGMKGa+RiMKwjHyCkty3CCNBvzopAHO5yV"
    "hL2vN72GkeGLCV6lOQbu5xgOG1z2m0kXbJEh9stqA5fqnjQxW+IN1kpJugTBcr9S9hnqcShEVLFoh2Cz"
    "0w9JFDWUuCk+xGIFeFnT7h/0HbWk5PHyO6yNcicm8dPLQ1W0V/ZNoWjHymZNKw/N1lH56lsfThP5xiJM"
    "SruE4CxcOFAWWqMGc8nZNaxBbyG2Jz7VgFtXBVEps6+KpRpT3R5D9Kbkn1o8bj0ZZueXJ/xYrkwyiF/H"
    "OA23t6plhpr6+Foto0DK3ZRFYMgd1/RqyjqsVmF8kHJcwk1N0M1GpL5w6YWIsOD2ruYMNTEqr1ZBGR4i"
    "8BE+cuxbRywqbNoTOs2p6Q9EIL1Dn5KlPhNqsn/Pcn8qq9ZEfEkxTQdmJky1EcNJlELuz/O1d1oAsL0E"
    "VhFlt/mjKPooOD3fr3P7DclPR0kit00p6992gapQIZTwae4ND5LpJlSHRnmsfratLebvAi+aD6baTlgN"
    "YSa49fgPOeff/+3/+GduJQWg//xJPkduH/8O4Cd/ESMlOpxOHGj6Ba+tJLbMaclqmKm7CKNjXtPfNhuK"
    "kij0BqUnOaQ6l8pLYcwvQ4hPwM/+BzRmVCLCb38tlRc7Z3nrgZ3Wm/Nj1o10W7oDQORYQeDHi0/at4ML"
    "Kl1IEhQJfqhjox/2xkrUxOrarkN7eR0iJhcAc6AEvp+Zi+olWeZOhMignGddsRwP0apdan9ev5oM+367"
    "PrHEA06PqmqjS35okf+SX9DAw+PIw1jXTwaObN5QOP38I7uDXOt4AzuWnFSunvWXFBROcBiLoZ6+GowI"
    "oDodY8KfmGpE3WPnb5ObPnRnnDwyZihXoBD32FaM8FdmDwfCR4bbP9Z+qw4jmGDGGZ+9fZM9bYQr9w0k"
    "6g7XBp5SuBo7yhFakSQ6NtUsglzjkWe3XEtkBBLsYLT5MC/eKiSEFxd3RsWx0zPkStJvapyu5ISu4rig"
    "bEh2yhRjeVMgdDA861IKJveAWoviVlUjGR5EgSCZdLIMa7Df0wOkomj5B//bs9V9pq67a7HmR4G3cdTh"
    "2FJoGVZRbkkvBkZ1yP73EtFqbMAJMcbIAKPCcBYLWTV09+kJjiO4gTIzuQtWyVzaOs+QcMrc8+JZdZJh"
    "G4SLqJ7Ic7GhPiqhsCMW09cdU4ppH9JXrHikBsMgI/AfPSBRoFiaGtvCsyWOI3wCcCnRz5HHE4Thv2Tm"
    "4NfuBLsvg0iKa7dgq3XcFaZqCXX8mYQXv44t702KtGEi7kfK0ste9F1RHMBhIfzilG9c8cPMFiOaUeSI"
    "I+gsdifA7fL9lZTM2tcTqdD9JCD/gCoHeMc4Ydvm+tpUsX0X4YAdB/UfR2GoFhuw6ZfyHIysrLIdwwnX"
    "pv7pl20Xgg5CP0Il6aXOZFM8CVW6ADip/WixSN5J/7V3LsVBYi05tSnoh9ssFUAIymW/fAi/FiHBk3ti"
    "duQkim0vv8e3wx5HzJZMzjz/FnT06wsofss9CSCmVGEZTGiAxCeefmJ/v3x4Lsj2fcHH9Fm7nN4Btb8f"
    "6W4IdjSNi1WrekoHRDk9IqN418OHBPzojDUEzRCpmzapTFq1xjCnlQsdT0h2Lg4sFzhrd9XNpqzEe2rI"
    "jrPqEQNVtiqN36jXjK2pOMYUcfWa80MW1qYo8mcgTCTqlb16EJfZ/TF6GN54vMJ4Gug077AHAUtD8Cz0"
    "R+B8q23Ay4zVTtfuSKU0n0hjP+zZEsrAa2gOrD1IsNsEJIm06Q7CPHzL3sqKvNFWYgyH1AkatkC4OCL0"
    "TA2zq2Nh0S6Lj9nZWXxO4U2DyQy2FX9DMUDiRz4e6wCJmwbHgm5uJP1kmLUfH3QlHaKQiIv+oeDR/Iov"
    "cryM8myy96XOPDQQILtSwiLANzOhNPj7hJJ4gXIGFmHTwVXprfPz+V60D2fz50AEAqQLkyLfZKwFBNjz"
    "KUXTgXuD6+d5rt8L9nNhCtrW22wZ5gY/xXgNpwx5YhvZXOHM4cdH52tAOwaDKESnWSKEElzoTgfqE9Vv"
    "JW66uSFw0Xk7Ol3Wdw/riZfmGPp9qiHFYTiSoXg6HhG/v9DkvYMEQDGsH6FN6O5IWmD/GA+7g3oM80R+"
    "/gyviDc3XHwIm0msl8ehNZ3Xp6SdbZ0P72niWFi+H4KkdvXhMiCNEvMKMXiE/lAR08ASYHRUIGbmAL4I"
    "i4+/zkGSsCKiTnmHScXWZkuTCvqEKo8subzMV3O1a6ko52JO9iY938ZsdZRGIQQNcO4RL89OnLfe3+BN"
    "bMPrqC/6uMnxOI808pF8JFBCsGgloQG75vX6nqy7dbGBvCrGloa2p1G2w2uaEHy0hijCU+iNYT1lFgXS"
    "uKgyediIiXzsO1qA9s5EJh+XS/m4l3rWIzrVrT4i9P18v+j2g4TfrTOKySmxFwCGHOJ9t959dO2/AAjb"
    "M7HNMN1f2/UdGs67qBHHKYJYpk/vPE/BWd/MycvqFFZJDWASQOupIR9+ccQI9uFc4qg7lhhjRXUzpvuF"
    "ZmXgMIYIusPvG39xudXrZyCWnUFJeVhOnjbgBadLiHvPSQyPWdvEowR/x4ClNh/WqTOlVZV1osAThUmD"
    "JwJ6xHY7wC7TowZL+MvUmTqubfmaxTeUzXO6z3qpJdSBAzk6FJws7T7ZxqCJ8g6ohOP6Trg+BRzXDRcO"
    "SuzszjaZrfOms/BbfrkPN8QlUYSJHeguEdiPeCd4s5qZ2BnV/JlQcG1f9V0YxYf/9vPkLVxcI4j3bRMz"
    "8VZaEGsbWF5ouUvgA9kQV2IVfRemm9/b8CX3gWR7Oj24DFTmr4BifhD5Lh9+i/jYIqulWx2qeI9JiOHa"
    "Abpn1qAg3cEvitD1fj0mBgSej+KP4pPyKh+Hp4liXSVbEVbMcfO6y9OK5MwvBQyVSQP0UgBz018I+vnk"
    "gOWSJhWWrBARH7wGM4ouOB9CNBPxuU6abyCYvuL3EizxEi4KsWO9/uIRJzMjL9LByg+GMM71cieYqril"
    "G9oPHAzZODflHVBrbrZgZmU5urglX5KST5863YCQyw7Ugxu8yK7gRWS842MwR/CboApTiTjs0TRk7TLa"
    "yAYnzOYysg+lxnlqSm1QIG7RwHtlnhIfTWJj9qxY4szluiXoM/25qRVo0cXxk3YrZtIA1waWrW5ioGMm"
    "J6Gx8c0oFpPxeFVoVmhAgEFWOGmk/bweAQyksPNbT4j3z7L6DXcxI5euvr6QGFDJjKUSNAZ3wWnj9azN"
    "yEjOlSQulRkyAM2RDzAZorJDJgA9eX4+d3Jd6AvA4GUPKN+ChH/wP/75/H/5P/+Z3scp9J+NxnL/9v3v"
    "BDxgDzTkyqBIQJNKray/ftLjKejnLvLUCVmDq0/YzUyJqL/weZpG8IPiTjzHfuX44hSs/SZKF68HX81N"
    "xWI0uCgyGutdyWhIktvwaflfokxmcOQFBSKDldHP8MlFgKntmfFOkJoQZi/0nvkqrj7dNvC4Th9TD8w2"
    "YQZnWfTKZPEASDa89FV258gMBb3W7bte/PaQxTEdcPmS+qK1kiNjQ5QuDh7ZxFi50Mh/FZhox9Pee5v5"
    "QNT299StEfcnMcFCBLuehor9MK4K5awp9WshQtQhw+nRdGkf/NYETXV8I6FwRll9g2HEV/x36tXj6oj2"
    "hR6RU+ZzRufuRRdfiZulCSD8KTaeYdbMK2j0tt4xFH6D8RrVTt2XUAhK29fIJhu+EhvB5TxKamNIyqHj"
    "dXrEVka7wF9ef9RrYipt8W2G0cor45SOKSrDfBNsJejqfO/ZN0EzDANwo5l0jyZxI2a3xEqTb52X5lTh"
    "hPtT05LkiOWhmXumRnIuRUZjgkhl/E0EhtIRck7hGAuFX6KanWEXncwdTRYvsf6yNAM+bFSy1ebhXec3"
    "vAxrxn8PTTOBKFyJ0Gl+WmtIGdRYiMP2y+ua4jGcVKpo1h/XHn5NBUmcj1Ne8pzl7CBIkhqPTyhIyvSN"
    "2Ojz2kSCc7McJvcGXCFCxy5TcCI0CntdRy9A4ztEYmMenNhC0Lwkia7OBLEPSc072syPnUbNKMvo4pvh"
    "R0JjsyLk5R2spdWygtk2A3eWI3lu/yEXSL6uqmO/Bvr6JHF4KzGvzSp4GTOOk33yXCp6KvKzrcn0r2jb"
    "gTzPOJsTbJsNH+WdA2bX7oPf81aqOw7up6+0lEi8cHL324vf9fE3CsbXuyBtIXdZQeXUp87YGp8Neq97"
    "pfLs9uuJIDyaA2sOdPcghFJByQ+uaXTSPoh07DKcwpiSTQjm9eT47Gx3ufXXleNH0OIll4wfNiifBCbo"
    "hD5z/Yq0zZ8PpEYRxiuFRlVfnKDS/Te4va7eCfIGzWaKd+hMvBIqFjwo7hW4jit1mU7cvYWQY/OLzyk3"
    "nopo0MzTjHRWf2AyWFmG+7W4yetAG4tVhChvHd5/zQiziKS7X1uT03bh2NouTd3t+moIGemU88/YWcEZ"
    "H5Yl889iCzyrMDPDnvys70P/fEY4Au94JQ0BCr6DRavgfjEebLhfu2Ead0KfiKQyoJ2aHN2MNrH8BmGH"
    "Ij+SZjpp2oMselSix0Mqyenp3FoJiyptzfyeSL/SW7eOsfgtVD2UgZIoigUCtyYKtN+2RHDalr+Z4F2E"
    "7ZxN7jszVH9u1dE76TBwZYmrPK1Eb8U3+BBB1TMZXtbC3T6glKPdEuFf44zIJkp+NpWY7Boi+dDBR7C+"
    "jEgLDFXVWvoqhGlVrc16DK1hyO3akWdh1jpsMDthBpqZIfaqw+Cr3w0pz7oC+BEXKpEo+keLMIg++gI1"
    "fkcOzK/UJoZnfLm+U14p/7xqPkP+d4d5upTxv2uXh44+Xp1j3+WYreqT/nL6Q7PA5AylwSAyNVq/gcaw"
    "77bxv6/TAZbP0EAL7aClxoYzw9ODnyjsgidbRMNfT1vNcgsAYLKr4RtmoosM7oy775rsY1fF9k4NGh3D"
    "5+WgsQ+/eBzI7Qh8ZFPDbzL5UoP8s0u9L21IYM43eyNhmg7qEoIgTu1uvgDr4AYOTnjTXC4VY3L7vS5y"
    "4uVgblmY9hkFO/1rr6JCy067Ek/TQ9+19N5shfiFjlUaGTzXq+KOAUSuAdU6ydUjseDrRjKqThUSR4FE"
    "IP6BEl8zqI7M5DGqkanameR7dnMb6RrSTuEilybNnrjAJ29KsFuIUZgPXyncPOfMT+abfZU9z+86tOBW"
    "hVkTMPZ8huMkr2v8OUe/lL1gvQPj4QHAE5IHSTcdfmpMfQNUz476Nz7VUecB27G1ksPOFB4s4f7slr7E"
    "uA1nrhq0MQyeWQjI68+hgILTChabSmoqtRjOlxgTnFTAUWTYgnvAjwBxjNy/XjzUZRiIjrpy9LoueUZi"
    "Jg0xkAWu2KSbqajH32NO0BT8G/BRmiIeUaKJcfmgadOEbno9kbzI+yHHSaFqCMS+QRboT/qHZG9Nln3Y"
    "enXBc9TVm8dPsto+LR7oUI99FKt2U8i/xq8j+rFi7NGO8EwLqTrc/fcrsdyt7myLtwaJ9HO2SsNZQmZD"
    "zcMaOEsIBWLZGFtqx24AAJiHVsT3XqrTf/jngHp9/FYBvOALSc0FcqMXEMY9zgtflDhjLElINKK8I8vg"
    "45FrML1dPCV4rsIff3JZ6VsjG0JG3ifBVnwPEwFX3iFsHH/KI9W+/HhHQ1Xihrqwx1frz/1FQGYFZhlL"
    "BnCkfgYlo7IfqeCGr0dz1pPoOd9XHj4FlA/X8Tn6b3w4EG2oqkISP+S7YtUkJ8C+kPYnFALTA1ltphXt"
    "q9B3SlBrpaHeG3gXyFcFRiDYOy3HENqwOUPwCI3j3OPYcUtRxBRNKtGt+ecR4OFQLg8OAKRb7VxHzcMw"
    "UszfC3dfaqyCsg1Hvsh+R3/e/BNjDI5hPTGweeQ+5FYx00peDxEZDzA6G/cHhqYVsx5oYXFvYMFK3Lka"
    "6qMLlTPosLRs61KiIpAkBV/bGbFD1LVyZQwdGWtGYPxYapOH513Lh1AVqTUZKz1lPr7EUcjcG6aYN1NK"
    "UajpmlBOalAA/IYHYI+6Nc5f4u8gj/nm8sIkSL13pQRVKEaZ8HTb2600XSaV5zCRe07A0913LjBfrxoT"
    "UA8G4H2uyYKoTo4RuJcOGQ0wacg644BQ4Iq6oc/nmIXa5N3z2o3+8RaTP8h7Sg2sOCMY4cHSKBbALsdv"
    "7ClL0QOFc2iJO3xNoFj6T93eYUpT+wjASXFm72ol+ZNnRO7OtP6OPoNmL9CVqF7KSwquqUFOXVmks4n0"
    "W/wZKFIaVMBx1xtfkiy7ULFmrh+Qu/jaUuG9qSXvOResyDkIuWJg7eGnT/06yi/EerTk+drMKc3wbzEC"
    "1KUAZY3Tx8tE6pQ+CJFo3uj12mmltguwEDA8lg6xwDAT6Ea76yBVCtMM+Y6dtaKSMjx1+Kcdzhb6qmPS"
    "MArHKe1QpuTxC21Sntf5qUAAg9gK2a7jAHbTb2PhCrCT+kDiYTAqx/FfkyFAfSzmPwTRItr7QPT0Ex0Z"
    "OkiworjY5e57MqJOXS9Zj22t66vTgIcUglEYweZXSoy/HVHmApQJo0c/KNW1UkSXLcN+pVmOekJmAa8Y"
    "cgKDwkQat24CD9oherShCyGcELBIQ/AEZDL2gokGZ435bz2C92//9Z/rr6xw7X/GniJkvL9L/kcO7viO"
    "OVTf3cpPsPVJalX5miLWOYUpsJIonxD+V3nS/Oqe32wuV/v+1HfTZt3QQ//4PXIXIUtEvx+Yr42XsbY6"
    "v/AWCvurTNylMJHSnXuHcuEOPBm5ozIA2h+hmkHj/SAg2IaBRguSHgYMzCkOOx+lV4Xrw/gIWuZ5cvOG"
    "FzGjNs2v/YhXPgPHgoMJTVD7z3xyAnYCuhM5QTk/lCs4BmOHXAzHwboKVnWbEtwg2Y2nADiRAH3E0Q2H"
    "hJDu55tSnnjTXuxQunhLcujN1gA66zlqgktgBWHf1MUhXy3vd1sS2w4/a/sCQE8dsSwj5xxIhlEycgcq"
    "XWvCgx11zD5dhFATU0TaB2tUbWGEsFU9AjYzSk+y7QiVZBvd1m4nXl4AtD+nmrBr7cGL2rrMTKI6Dweo"
    "PI1HGljErjqM8TuadT/hPU5rdaYHqKXP7iB2j690/pR5c4Jy1L1eiRbXX7txcZ3nuZ2Ag/7rAhAun+i+"
    "5pfWcOaoLD3e7rLPcHOn2iwfYs/RPX9m5P7ogJcswKVxzye0RIF20qSD+ZF5Ti5htlcsHC5/IETTLHX0"
    "dXFL15Cqql05DSIaNk2CKLm8Y3O/p4r/epsBregN1HW+0wq3E/fp1Clz8sai34hhVFJjnPrW3z8/sut9"
    "hwIL0bU8Tblyjcnl/RbKtLe2Ey9tWfYtl1S5fMIlBj8H3L78fx9hx8XRb7UQ628z2rO+Vd5zJGNpT0Gg"
    "x0SqxtrQ35B47SYVazbDpzSNkwlVQo9LoAiOxB1eLNI1fLdonBIaJQD1RTFZb6VcfseAWvdgLzmbn0UK"
    "Aromma7pqz7Ltz6j1B34pg04lfrbbNAGSnw/redvf0N0N3ZLFVkyIkwLToHAn73d5XJISRqqaFTSetae"
    "+lSUoFkgmmtCdIj4WPCYu2bXS87qZJw4VwCI2WZNYtG3LDxIjJBcz2NxAZtbrJL3rHH2CFKUQN2hDMZz"
    "XYOowz/QpK3Yqt8SHDEy24td8Pqsl2shoMs1CcbFXfNEdiEOH5sQbhrqlouv2sw2x9tPmqLPRrz1RM+/"
    "F8kcznY+ENJ5LdDRmZs1vDyALJ9EUejM2Vkfqzrr/gA0cHpPH8U58zm4Le01gjt4NobslC5JFvckqz6M"
    "E7cvaHS5bMvCa25GUsous4GYiu19r6+7zySosIwyMC8tV3QNqrUhUfmH88WFeJSY4QgqOKLE2tsGR7kv"
    "oiMdZg2DPA8Tn4SGQMiMrgoYoVkPC0T4AsL4ciQLnFnF64biK62HWqK7Tq/wXA6Oinaen3vMZw+ZmeWv"
    "fRlfJjjgtf/en7+2UeYKTOje3/A87KK1a1P6LICVgYaUJHVy2IbD85AVBzwv4x/w95wZeNRfB7tJp8YR"
    "oSSJM/PBRm4QIW5Yb0ZOYyV3MiAdePsKAJAEhUWbZiuW/MCsx13SVgp4ELR66aB05cR/OqIAd26BHa90"
    "uPN32Vnjmsndhh4seRfLv9GZgODuRN/ANkQeHdFUztjToYf1clEVEP+y1RFHK299Vll32eGQS1R8xQui"
    "tr/M40M+6l4UrlAyBCN9NmhJc8NFa94UGLv8vUYEEoBjuhM2MX5PNqu7F/zgjByDF+pbHa3aK9mRD8en"
    "SCybVZNS27/uPTJsx4cMzv12RJylHXHqSFgtBTcFPmGd1LyMCBe86spXx6SGaSzd4HtRab9CoXG9GLdq"
    "lgSpX0NYp7J1meiW0pI7A9duK7tlVmuqYx994z1kCgYzftCjwrChHV56/taNqdgnk2jRJPUCwZRZVD4e"
    "KqMwLAPT6332nB6t7okagiWRigvcjWtCnE6cOoaimc8m7YOUfkkXFHAgZH1VdmVt7A4lSYJ/4M0lxNqz"
    "Z6aFZeDEvOFXSa62r/1HDrHP9wED4JX1djy+8cR0PzHoruaG06ZgPmhz1xX226by3JlVym5RNZaStEjg"
    "jXogYmfpO48XAB7p5Psh3ltsOp/Y6TthTz+fa7rhBZx+tkhfxwRYlqDwCRkr72gZJ6sYJbnOoTHBzwUQ"
    "Fjj4Me7+ArVWkc2XPPWuuIH3ThV8Zv8TED+vOAoS2xD0AnHpcDK3M+oSlXvMtqnioVA5UFXBqOy9NVGE"
    "IJ2IJl5U/3zhiE95fCG8myJoV2+yBQilvsuSd0HLVh9dyDJWeV7EFbAWbxy8NpJcJdnsyZQeU3PbsKsB"
    "GpNwftk8u66O55ssfr6/p+LCkyybPO9huJJn6CJ2elIzCvuRMirSIKpjH9+ZiUV7YzK8IveFDiJtXsix"
    "7Z2wuQ3qrMFMfQ/4vka+tCCwxNV1Ae5qqBYnmDeLEVjXI/+2wgRjX6VYRpfDuSPaoZo0mRgclD7xEb0o"
    "caYqDvQchrlRn09cFrRUqz+skL7yHh06kAd+ca35HlLAtjuiA65vvpOHemRQ+cEO8B0Lp12+EO1mRMmL"
    "kfaT6EynqMMexu/wcLeBj2U7sbW5yRK9lDckvJINY5HNvZzG+o7X77+lsM3491PbpYI7fn0rvVEQjsU2"
    "jy3ZL+Cv/CGVmWyATlardeijyXKjNIagJjClgcxf9xlOOIoNjSd6ANgAd+2VXCmDu5X8GoL87gnSrYHr"
    "fce4Z4aHB5cawXPb83XySJEwJTCVaVnH4CeAwpDjUv422Gvpb1pES0lj+4xHgN+tV0Sp8nrnVqrzdV/U"
    "Sk7Ch48UF8YTzH1yVO+fqh/bTKN3t1jvysTKnHKe+G1ZkH2+ZErsC9HQfvhOhC30Edl+Tc8Y3lLB3Y6B"
    "eJh2/QLwQbQjdZB5U5o+hDpC7NI//hng3/7rv3j4Xzz8Lx7+Fw//i4f/xcP/4uF/8fC/ePhfPPz/Xx7+"
    "3//LP3NLOPofPLz64Q+52/jrA8+xARvY96/rb79kDQM82dap2NnlvjhJ0M6EEZi+fG2YsRWn7CXeq6Lf"
    "OyEDFbn2OV/rd2wk1TDD2LzksqoXhXRMvtv2d70tOblJPUnmj5FJyW8PwafIQfR117Xrb8b1d4MqLvBB"
    "eyDFyaEwKBZcaVZCUea8XhHjPnb7FKt1czAiA+s1m6RrWmgjJTLYfxokQlsBWYOYiy2VOXO5iQOONhST"
    "+XjqDyrI/FoBUPa3jcywXANm+mgMhEoROS0Ymbk1WywBQTNvlBjX4K81Vs3Y9SwqGPdQRPT52NYWAHWH"
    "oXnfRxSfbwz8uBh7ZMbNZ2kZ2R/mMhwhFhh3NOmQxetY0rhwQOd5BHnxQYEH/DThMYD3MOyIZfGJSRYi"
    "OdUYuC0f3TloWSgjc2hsIdQWf1yacgVvSmeiQX0gLudcmSZQMFYk6DPJFGd/jeDviayuyBA7PCpyQQ/H"
    "ZxEqtgabGJK+sDFoaw4xe8KH+T3u9/ftim1sdm64XrSb2W+bQIhKLNlyAaTrN+b28Qw4Qz/xkTLYitqv"
    "26mlZhfgveho9KPKWBgHMkJ7DAxzaRvA54WvgkAA45O/CBOPSmvzEl+r7MLK1huxGk7MleB7MwhOoGM7"
    "z4p3QjCtoHGX2ZFiUeK5bkjJyHUsqvVPKG/Bgw69eebu3nxRzYzfd6JgogtBwMWxIjQN6dtz66Fd1IGr"
    "MbEA/JX8WkWEzXSmM1S3XRFZl1lZRCqgv5zpyYbPcBGDLoxhnDSFz0XWk2P+3WgEjsvUfHiAXb6N7bKn"
    "rtIiy+F1VUKMw2dhxkljNfr2nzQ2U8wPKUpGeUTWePD8iJ5hPjz6BrIfvcRSAs0Lvri8engaqrX6TeZ/"
    "d+xWnekgy9dfAo6vKnvWym/iljXL7d1Qq9VUE8q8XTEOyjK92ujxUo9SMQF7/Kidl7FLKkiwqBMCuMng"
    "Q0PhmpC98ARMb6ifyVIUgUshw7a/RQVz6+h3zf2jyy9p62OczEAIk+SxcTm6powRMXuAxULPbBodKFKm"
    "7iaENAJXH3pvs3bJtJKgclzZ6c5LR3zus8SXFVjBUOajF0QHXKWoEr4VQK47GGEZQi7kGnJKeoxkg+IG"
    "P54GjyTdC9dfDqcj/oOGSVNm4gibiEi6B0Qdreh5K93g3mkziKCN2ZhXhPGewyiVv/oTlRpHYpqvbpMk"
    "950BAjt8pCBtxgkQrWKewmb+AeP1MZi4ZEqwYAce+jVkTW4APAplyDekW/30ndeWGcGmgUITTvdAJ7on"
    "x8c42MD8my4TcEU2vZB4lhGPwifc21P4Sj/v21IrRfScGVIjtrTpi6J+DClE8yi0ke3pagmbD1xtaF6/"
    "MK8D3U5E8RpsFshuwbWSZOsgz4hir/vot/iRGwLB4Ilhf1//1Ie4/2KMJC6HVmEsbbDPA3YQIDPKteI+"
    "s+gDE/3UbcfzR0pDdMJq4zaMj1o52JawEiytHSxGTykadlciZH6DxCgU7wlvjuZzxVpEOplrjt2wjNQQ"
    "oHX2pcaw46Zou9VWYg/KXiPJUR99z4ZhDMZWf5pfBgwm7X9PG653wqgS483yYikfNJNfSmaYpv9+F2Zn"
    "9PmqZayixwB6PhkpD3ZcBmlm8E+K1FmP5V3fNi2ENT3cCk5uOE5jQAaeaGxy4uYpKuUp9lx+Soz1vX9o"
    "Ud7RPrFNhm7VCOwEbRxl5GtlI39dnOQb80lucd9OjntFfWjT/a+PBOOwFhxUr6gg6bl9ViIWJjw3IMlW"
    "ldl2LSRpwFM1mIZh44eifLrI1vlKVQ3nQPCdodTEJm2P7FyKjImXmqA1VUZdEKa2PsxvHKoub11B0Jnt"
    "i0DfbrF5dTpn1tvvQiNA+zVPhcXGjhtzcfqQUbVjK6IQrQJUN9zLsux+0xczIkFt1zp1KXPxdQksbgDJ"
    "CqdED9fG2m/VX1HFW7yvAa/EWhUBpvz3KyiMLSBT/AQyzo7IBUBj13lZWXJE9cYDbrOTzHU1P/wi9KwH"
    "tMZylQ8n7M5Hgt/u4hHo8RtsGYO1tTkM2YAfx97pzRiPuVHpaqiMWn4ZOlyGtbPED9MmT5WRqHbFTbV4"
    "ZrmEWU3iGsGGypJ9iPDj8hS0Dlqkoz5UlGKofngFD/zTAlSmc+S6kmG82mp96WjZIzqYDFWdgY3Tm1R7"
    "hNNxjF2DMJ/djJYQ+Z48y2G98Caz0FXST4V81OnzYMCn+UzVDofnm0zyKHh5/6zSgONUvVUjRj26+GWt"
    "5IIKnMXFXLP4jQ72eMl+hGPYI+MQrZeA5R4pzPkRTlBiIZgnv0JBvj7fED7/naPkcvmweZNgIHKtwpRl"
    "VRAGd+qLFwn4vYurYSJfIbx+F4UXh0Kwe03LH42QWYFXOWxkoAIhn8H7PW3DSuEbl3zbnnm9bnv+Yvza"
    "qM2Wd7pWUk1u6DusoR8CX7+f5rada0UPgJU24mFjPDKkFxXlK4UGlaTpsZuJo5K0A8Ahk2rZDTJ+qlrH"
    "9gn3assoo4dw96djgcEvwChipXbuziODJR/SyjaWTC53qc0aJhrA8OMNPUSybB61Aqmkty17nTjn1Aa3"
    "mvKn5ATR598Do36e08b5tn8bOOUgaS4nJpQS4+MfIA/ZMJrM6rOPShoWqcFpliBWo1kdoNaF5PHYzwp+"
    "8+/ugMzC/CJoUHBJHuHcAVE3P4/4ZTN43SKEA8IDzOTYHMKlUj4HUQxb1Thp40fgN+O6sQHLj4mkAeZK"
    "e8jb//jWh3//n/67fwJrGek/sHZH2XdN/R3IKR/gSNrqZcj3X4uShL/Xpj18kv+4Udq//6//4/9nH/0/"
    "/2//xEeLLvSfLdoc5PL8bwOAw8fK+JejTLOcPKm0BUvfWc6IcokpFZ516i8PK18ltN6Q9AiX8SMZMUqE"
    "N/aYTnnqEaZkjSNIEc1GL2GELy8yrVK4WTkaG291Bo6GRXw9RZU+3eWO5ZXMHf2ITzKgxecV3Ah8ZOSF"
    "LoHfSus7+kz4CVu+/CxMKFgI84LyaavlKPECDm/T2GMEci1ShLOSISOti61/F124UKzxQnRiYC3v3PN2"
    "j1h0ay48+pP2sz0qjESUYqnoqIfBOn7llYxTe/wRISsrSLeZMu6DsacZ0uRjl6t6MscSj8CLEF04odIm"
    "apw8kBwFRvYq/ejNEqkxT4BlIcoTEk/mLmNYfuitnTd9fQ8fv7BrPWbOen0mXmgRAIEsw9TaM/U9Szxn"
    "fa6XQDGqXJOmpdTrybl0ZYLz98z5JL7hTXnxBNmXDUqzQyN34pGVQ31ZBAOWeaKTTzxmr90qbOeryOq9"
    "hhxF+wpFqQWMHg3gqkqfmGixP1dUgATW9E5+MoFoCIZE92A0HDoNjPMHlb7W7xmwbtfQdQ+ZLvD5S4Lo"
    "eZd8TXPAmzq0cWBuaDYQZqxtro+zGCpQaEp/0voRJZbhDC4PSK6dkh4h53u+KrqJNbqDW030Tfwp7v56"
    "Pe2QzfbNMWvJjUiMnGeh+P4DoSFi/m3eol2YiK1fBi8Xe6cWLfC6vrfCpmYduK/zZXOk3A0r1OV/TWvk"
    "rCizwbEqULgX5uN63l/rqvWOtnCrMDwkgiaQdfFIYxJp+sNzAR2rFVXCvPqmlYFYHAWCMS8L4XPFK7Ti"
    "cEa6eokLI0evpXpF6yRQ/PZ0pskr879W9GdZv6tHj+Zw/CoCE7Exx+esuhnXWymKwA4PnyK4rt6w/tPJ"
    "jJnTnNegrXafWbLZXRo+bgqg4FlDTFV6FH9aqGiXOvhmLyOwTQ6fCO4q95SOnpjyfwPPMBALIyBUkda+"
    "e2+Gn4eA1SqmYIQPjLtu1xSXIhic0aNUPbDtUpI0VKnzJ4bYV7gxHubGM4ljCPssGXawM2fxJlOkIwlZ"
    "IIl2vOWOraYyfLiSP3vzv20KcO6xEPX7FilHfYXgFnHD3h/3SksK7RvHfYS65hnJTCxGdNCspQGi/gGL"
    "irNnuKSGpN+Bk18HntMyea52Hcq/V9fn4he7Dt746XItG2bT1oyWZocm526+9T4auB73rp7vviZ1uRlT"
    "BL/dXz1BOWiBbg8s4J7QSdo7Bp2WIBZgxerqoNEoTSyXjSurzP5nDvitGahDv8HG2IXyZNU1W1ln6rmU"
    "oPlkmwInfkbbd1fGABT1O7IbC9jWRBzoODgo/1mAxn9+2po/cavgdsR225LeVY/5m9V2GZURG3CEfOv6"
    "1vTY0Yl0dtopzHqh0DWFmzlNFxItW8AToanB0U+OmsZYBY3ZEHiNFSzRrn2tjsBsrFCGTBWzFk8bCjD7"
    "Wv3iZDU3b1V+DC7dOBQwbCE1oRQ1h4/TqH10XkP9ewL+V/dP3Km68y60a+AbrdZm8k7TTNmSqpIwGZeO"
    "Hfac4ebfSAXCLlmyXrI2mALCKlPXpN8X5PK9zkyLZPCVnnqDwOzm5p/arOctyxzipZgcM8eOhRy8hLLU"
    "BfM8WIIH+I0efDle+HpvZXuGPEIl741mAg5T3j0B2sVSKo9mVM1fAGvGrLhffjItdJk71Crcv42oe+r8"
    "e+baiZ6F8j9feMFDyY1JrFiGv5vy+ZGhE5a07DCcAes7LT8dC4KpzPsN5YGlex1QbDA3CKfRuBip/CSk"
    "JxcOIbAek7JhW/RmAeWBvHQeQl/w2pPXMnMr3eLYdzqFatixyVrgSQI5HldC26uwdtJBFlibewrhL//4"
    "//jC2f/wf/0zW0Z1/+G129+Fs8u7/tobrDe9w+SB9MdBdlBprErFn5XKITA7+cKvhHS3E38UMvjv4qZt"
    "DlTs7xszYf7702Hh53vjpfwk9TVYwW6XUItA6U3HiJbY3Pj7QYRjQRv31hblXuQxwwSKZhb6ISIE5u96"
    "RVRR/wzoJmfAL08oEn+GrC8/r6mBy1oIYS1MbxGxlxy8eFmoUfl+t59oW0dX5DvfPWf15asGs6ihin/7"
    "Tidl0R9F0oGadnd6vsmFBWaV7q/gnXjwt+eFfJCN6iZzMYS2M64hHLWxBf7022/7kb1d5hht0YVK4/j5"
    "avv0grvIqWl4+e6ymG4QBIDQXXQ0WlcaArO/h5sGckzOlTxuuOxX7OsVthkjREnKub+CGdmVyTNsFdwJ"
    "LXYPYgxdZa7y4KH0Hj41A1PPCVi5CJAakOMJ2aMfMA+Qz61bwopc7nlxoVAdl1DzNSvpVnqlDNOfg++1"
    "jSv+pmTHWiU+ffzLI3cUGmdYUSEd4snoBdy7gveRZSy6cljhZNdxXt8Ax3VdfziuNvcEvEMU+BR9vvg2"
    "nVeIwKRE/2jYA6JPQm2/VajJAoPIz57kOJjTpCcOj67bfG95zmIaTGnu8reMeCgynDXvLUE/dhNTGxlg"
    "a3EmS0REkT3MBssYgixVl8L/2ycLwpDpq8sSTDApo5e3sx3OtvvbDTmSR6bIM/y1pHtSKIpKW8IVT7TQ"
    "YbTnOOy6jIwTFonSQjfwiAlYKxUSlP0djZlCGjE1/KL8bRqKhzuiJqkxmNf7B4DRAMAQ9x3x8GC8a1Qb"
    "D2J0ceJ6xtl/MOn74OBh0RGrYszWZfcSMJaa2TqiujcT2gqtxY8dRcbe4m+QBg28qPQHmta+GHj7hyjt"
    "F88l79cwLwfyKwyS9sF9gDGummhEs6D0fnUAB9anbWwzOxTEYc5RiSxBULHZ8x4qR4KZ3hr95B0Wkd1B"
    "GtwSq0ZLB0E48gWcakmLfsZ3ffIGI38nudk8v/Y9km6bOoWLAcNG/l5fy/ajXQRjlp2rsj1yScj7+B5D"
    "o5oZxrBYk4HuT6xqnssrmWBOWf7cpJRxhw56xJkzIYzJkE7xvKMgrgYIr0sxguRgVcFjvEMi2a8zLgTP"
    "HukJkZQ0KxsE3zB9nfH2Rr4r/R2FMHO5mHca/9TmVRcNDrZS6Aor5PTV1OaS6gKUJ+Yivk8l/q6ild/C"
    "nN4+VuEcnzARyas2fs1rZtFmeQUYE8d9UPuX5uf7+r0ZNe6luBOiY+JuU/ABRmIInoEaBIWirhjaNkN8"
    "xenLSnf5Cis6eN33uchp4VgkbyOgawGlUTohkvoh5n1Tl7x4PnnUBr/Ze+qbh4V/fvgbA9q58ofaK6dP"
    "XBhZ8n+z9yapsoPfdueA1FBdNVWHpFBdq6daobquWsZNQ7ZsEmwMnkSO6I0gh5C6zzhfNvyy8TcYbO6B"
    "2zgXToT0ae+1fkuh+LZjL6LhwtisCj7tHwUCOl/sTiATw3IQtOIf4ASsuG81ug58j/Av2dxZqd/TZ/fD"
    "Xn5++UQU8gzHSseETP2ZnA61C/EJGctgQAzALqbJACtX4O3pfuDHZFlA+0ZFCVhJmrIcI98vtgGgyfkF"
    "jkA7hGsNkkyfDwpbnCdtbhfc53uZdv7HhF9BWtN94qfoOQ5OBCsh3ck0Ng3aTsaHoz3ZhgcFpIyNMWt6"
    "aCteFeMjpOjmj2uaZJ8Zi/Wj0WBRAMgJqJPnWc84RCDaNFo/ox9yZ7ILeeMe/BnuxTPB8iUBWgbxRvLT"
    "gXqi+MKL7yvXEhu1EVwAWgE7En2u+/QlNzZXAFO65cG0xirZgZLXYzTF+4cvIwBXKfgaIdgsQq9G6D5I"
    "wpZCQuotBqqxBQ2XH7m2uzEO7gIrVYHYBn2te3xXpSV/47u0oI9tkoeCkjqaZ3ECzgd87gj5gaxmtFvH"
    "USL0oy9HzqKgFZTPPRiyPXpRWDGJg9EU9baoY+SsN2/r2nIScX+yUgGWiVzJ9AmoPHPGpYPFs75itf9x"
    "rRDL/hiFfSKQaDXoCCp/oxGiTIa7eiFqv82GvrHD3xNiuEVvn5yyYt9oFFSUtyh7b/YmlhDpePQO2+Ww"
    "GUlxwO874AsiZhHaqEvR9h4SduzgMY7CpwdK5VeLaLYsdIzY6KDyzCcpZTxBuLWSOOb9XWYqJxLjVyM6"
    "WB8CDKMCYicImpuayRqQsV+2euwPYeIBWxNG7q3du3ACiNm2mNHsdjcnj1gf55Lx40DwTDuZn/2zds+F"
    "g0h3Qt8URw/LvshPQuHT7yrsvI0Pomyo1a/en2kIILvI6rnDar7DRQ7a9u5xvsHa5RHYIoCb/ETJE78U"
    "0udtbBzp0aXo1mlxfde0+Az0hTnPptHneBXbdKhcsI0niefQVZpMwYc0LjnnY5Sr/tXvn/y7f/o3/8c/"
    "/cd/+499C0XKhX/ZX7OIrtC//usMUxp9a0ACkcGBGSWbnW/NLlZ1VdJ12JKSc/DHVoLZtHt2UqHWSV+Q"
    "7v98lCp7SCO7AZTIqOsPH96T2o/1uxIrmGu36GcmyLJ6GsrFANDjUx5UBJYPw+lLpGygXLiHUqLo2tI0"
    "ehhgTHZnELzpruzedJdLBpyL8U1yn5nkUuszY39qNRnlarnJHtPGccZn3qMRk4ZRhCcsj7FpkzeaCtR6"
    "PM8JxEAd5TR0w20f5aCnRDhvhG3uigTBvoK8Cagprdkhr4vfphd8jsortQ4sdIDWjOxVJPVTFT70pXBM"
    "CyjyhwkseLheMp+w9g3AXP6Dys9lHd+lWSnvmDE6EHtzvywGXznW9yMhzZbenNRNj0HqIgaMbkpA/7gu"
    "9JUAH8pNUcGK4kEL8XqVQBUrokLwYtIUCxmUKbABgPqezUIU9bB1poeTDxQ+UNNYFYg62fp9zN7vc7N0"
    "JQPYDvCzHl0L9u+baEkNkiKPutK+svA6kx33SqZygrV5iL/cusoUWr4aw3bNCWkRchxgPoVPV2fJ9NUG"
    "mESGcvbKxI/pfdnftuzABH1qiPgcMEckD6HKGKXHmqCiRUACxDLEJ2nB6f2SsgL4agYw82o73we2C7cg"
    "f+SyvS0BzKRXb9VNouODIUX2vVZqsPeLysJ0aPT6G2BeaP3O6K2Q8Q0jfYAvY1fgQ77GCxt5V3Z1mRaL"
    "praA7kcH6Q18ELRhKcw8Sp73AOHpfVlXReMkjaEd89R8DsB2Ye5mRgdzgddG2OxIoQAprhhICf0xuugp"
    "2BPJ7I6OAybOJAackpxcsOd4zHB7XyPojqYLsg8Yop5kCf7V+BPhqigNQlBJFKssJPZwAJwARBwJF0f+"
    "u4pBlfviXF07oDNhGMN7UavhASAS/4b8UkYdMiM31IPK3KXQ0U+jK8TxJi9ylZiK/w0RZ0iBYbppbKlg"
    "AvzMgTp4IJIzoY1y91fd9yMRvnPr8+ns6yrwGERfFrZe5QVhrjMMw/Qkbo7GBg53+aX2PEAV2+EfATUs"
    "4gYy/LVN83VgA1TCvDV/OytAagt1afZZX0qDPy1suz9lcaqERc+avpWwnsEHJnGEO2iqAkq0VMwFuajP"
    "HbS9RDuqGeSu7dh28gZ/DPzC+eu8bvOSuGl6/InvT3bbumNXnYjphIHpluFzwj5DCqBg2boFCD3DkIUs"
    "BeEimb9h+oqOek71xHZ8u9ZLJb6COdqMHFFPg8BfA/kc3cr/Co4zeyvQDXppvSz2SfLT5KNTQvEBDU2n"
    "Qjz8ejUoT0ZlIuVqxIwbiYCNGhBbDO/eldrdd3q/cGe0uypqG48mc8HapiWvKIB21n9PelGlvhDW+dGZ"
    "c7/I5UHlflgL83oAfR4Ul4wNBI1JrkGKN4Lwf+bPCPxzLg4C7AAgHGXXzh0EhAM9Xz0FOXfsDu86l9Zm"
    "EJmcQfnn1Fh+xd8ATT5FuY3wk4cAG8U/H7ydp8ELe+ZYSD/dKh17+rJB3Jb66GPy4s1cu7Q3bf49nUpF"
    "fy7pvZLKE2SNjV86+SgI+NB4AEZVD4tseL/CUL30CSSQurLJ7VwIRh7RQTrBNcwqoQGWZnN1s4QX/c3Q"
    "Z6hRCKih1k6U7nWZn2id+BfKQrnHVlBMTta8Wmv0zAg/v/KvjBwnbmp7t2b54EJEVnAqg5bPM91R4vCF"
    "JAFqe+L+D/9NIAfbmgRlvz1hOqbe2jd7zS2TnVV1iHXG1isr/Zjf5beINI33/NoS9hFZzsCUXyPJ2qxm"
    "FOH7a2LFDFJN3cWMLbPXXouAMle0VZSc8mVNkYcEu/ewvyTp3IavJbnds0K7vPDnGefKO/5+XGHdK+nX"
    "G13F/yx4w0hVFzBWwe4FjCv7ePOCw9HQOG9fC8bV5jvZXKUlr3u0ieYq9jX3rsvYiK4XruPb4EzhBHv+"
    "LPeyRgbwb5Ueo4xImWRNl6SWRc4WHUVIOPzbbq4xbAD/FBBc9zcZhsLPKVKuqrjXxlSuTaqR6CVgGqHn"
    "t+O5zNhy+fEd2Q96HXGUe/kwhuvICfMA/TlHEp4O8y+LGLRNBhNzjg8nO9+rZUat9x3m1ZPHe3xI7Z+5"
    "887ZYrjj1wDH1cWmq3aKD2WqiQYCBC4TTU/aT1WwJcFw/TLUopKG32AWN0kvXZGlRbPTxVnQw6aT1uV/"
    "MhGrF16AA9FUgvRz0MVtdq6DcUdfpSHXxw94KHtzT1lVH2pm/dlr07CMDHzTIGdC3yzUJK3A6rfn/9U9"
    "xf8r/Pwln7/k85d8/pLPX/L5Sz5/yecv+fzvTz7/6f/6H7nto+Tev3zZMglt749U+QVAh5O5T/yeL5am"
    "/GLZEiqE53766HGS0ioCA0EfS8PwheVb/rfXNqQUoWT51+/FqZ7Rf4IgZZMYBBhTRXXUrHd8MQ7Lx+uv"
    "zAN3pnMS6JIBZ0xDHmV+gTdgyQESPf55FuDJh2tYq1p5l+JwbCR/BgKnNN0AEXd/6cPVe3P28RGfDA9D"
    "AQDAczmGHxtLYXyK1leHqdqjREYXFKck3jyj1wfdnJigOD7kk4vEIgI7gmQ4AH4thdPPp8KJvhOZruvl"
    "K14b3xYRFIjhe21d/S7Hzi95VTCVr2SapzlP98SfLAeLsdjnVGZJ5FRW0chGMiSgEOZvZULEfgrUjSES"
    "yuqoCiPJceU3byUJ4Qc0Vxz7DFSPzJV4RK5TSXopxr5OpXDa6xxC9Ku4bm10OPkFf2Z3j2gcPTMpOHHO"
    "amx95K04j85OiTiO+eKuazNzBLO3isshXiHbWWoZAfV2MlKtxgLFiT2f29dHFUGVPzs29ogHMWaVBchH"
    "gYGNPTlm/o3Sb9z9kMjYt1hO4WSKDRwaph0CTr1UeJ5gWINXWLKZAsMU2Zsk6PuLQqE2Qiaa1KyogQ3O"
    "VyHBPtH8FeNDv45rZt/a86yZEXTe7eK2VBxrVJ0dXXc12LGxz9vZ5r663O2yq0ncnweepI0dhe8ICAYO"
    "f29bO46q9y6M28MKh0LXrhle9uIjUFOeHaWKmSQtS6pggRl55EROYMZfLfs820mus5PjddJqGDozJWLL"
    "7Dnnr5rnSROTAE/lsPh01EXyuncr5B75NzDErhyu81Uxfd0wsmbHjkGyY9U+iDD8uR1N9AyrKX/mAu1c"
    "xN+Vus/z8ucucvvzuc3U0VwreKf7dP6i0oSF/+7EPJKvgNNSgemMyglqG4jRcFJ++J6Kxf1shRnAoIKz"
    "1Z+Q6UcrbucH7HFQ6BKQelrqdzAeyKZRx3z3JFrMJ1d9V8ZpaJNghHlwtZZAE+TAe2Ittq1bEYlAVRKM"
    "2LvpNE/mjFTGC4hwDcBkz8PulTLtKeZ5JZCi6AmsJOrtdptq+73HdgSfK9YskJuXZEuRhNrD9TISKopE"
    "ps34MhHbx33qSMjEF6jwMBVr9XIzuSm5siQv6ZK+0N7PoT4ui/yeBjO7+hfUGXlyztcfS/cLwIwlr1VD"
    "zK+Vi/N3X6pzvR6N4KpRpiybl2F/ueOnXJ8M8mSLMcmtQpBQ6U+gPQmgCXoilcGB71ok1LfozwR6Uy/W"
    "2glkvJ1M9+e5QmglVp8bY3bLWFHTeKt1NW0OYAiU5pDcZ/BCU4K00+68L/96DskTs9/AuDYoRXwu17PG"
    "UKGcT0Pxq++T3xQMGQ17zWo+m/GELlCFhwds+eSwtNxY0avCP8fvo4R2gG5cmVt+CCjsxOv+6LEMF7PC"
    "KY1sYp92IFoRgrSmhj2zcqvrl72e2Y1WVVgW0UQd7Mw8TbdHYH5DWMtL2afNzuDo0AEhtz28aZz8Eqrn"
    "7Sz+2anP+Q24UbyWsmVAuUr1Him0dL/UfKLHDY4QOrEkusm04GwZ76ONdz5fKiK4iwdUmKVP1CpJqTn5"
    "R+yvm1pQ5eI7IM2EkAB49YvG7udYeyuHhXSKy4km4k8aGDnKsV6+B11QaEHeY6640X39XMWHx9aHMuAd"
    "pX1r+Ea4Hh9YQUsfXBBU6AgzISb9rDJMeLVWExagOHI5gcTt7sc4jN71ntmvNN2F4h1rA+g+ZgQJFvdd"
    "HPoeWpcb76Z+G2U82FiZezgZWDKIa2K3Ekk5nm/yUNd1YtB1FVtIwvjhyNwnLLbZSGounx7ClQOzFnj5"
    "cNJGDQpgp9sdwwFn9RJCjTbD/CIJbyXMe+KUMVpi3GYMCA3As5DhcxLUok9oX1xg9dk4ThCERXH07deM"
    "QDmNdT2Qh0n5C0NmoO40IBxGVDOv4OJFaxwkqXhTc2/UjEoDeb83IEHpbMP3oBASLZSyJIpaYfPtchTB"
    "x6bxDb3m5dMc9s9OmD7oZZPB1xOk93TAPFgw6833W0TRpSBufCI6PI7fFIKcrX/l7QdzV2IBFx1rPJoI"
    "R6F+5TC3wrxsQ1gvsgBFSBwCfqr21nFbqMSd7WrPquttXJz6MT4z4R8XcA40hZhu51RvTg4DVH0lHQaB"
    "bBRhnEVfr3yvczO3qdvHTaLvn4HA1tCt0QpIm1dbhs9bE0NixNaqQ0UEOVNY9cWAkiTI/d7g4hOPTSDt"
    "SHxAFAKDhQbC2zS37nVu9kY+yNmGPJZpZLg9ex4eqNJVOmSDx75mKfX9FcnzK7XQnPoNXdEnwfTg86X2"
    "QFKVmU383ATyb2DT45s/6Qhr0S8Kz2W7gg9AV3RPJ3D9QQD/Eqp7nnzb4pmxBtQHTMIOwyVpNg/JqGH3"
    "C8HfXjVlpmkRfag/xOIVRtpo1C3Buu0xYzc9+Lr+soMsbmJPAKAcjVqD53zc2Q1KxvB7kGuijWnofenS"
    "zTzrsh225x3NI/1S5LegS4NerNPb2eA4xsYaHdRA1aaqITX082adMlxwZPZ+Z3VV1neu86oVnQgCLQU7"
    "vtzlkZ+ErCpxYizGY3pBx8477RIAVz/UW69iQIqJPVUo7IaDVZpJ8GZIesiAu5CHdHLPTXBqxU09m2F4"
    "QXNmKbYFtuUYq+taphL6brJO5hblEZaZ2FREfy4itToYxb17QML97XjT5vu3TKQ9Rttadh191V8+btRT"
    "9uhTAA2layeBHfxAABsw6I8sU1RlWdICr8PBsJaMg/P3MpdwjwVoUiex/YYLO8kY6pEAhIXp1kDAm4cY"
    "7s/30YVMbTjsmqJRD5eY/hVFIE2Vzi5vFJWaGlkcfLc2eAyTrEo+RrN9rjMDmHO0w9UKDpKmCBiiv50U"
    "04Tdy3aNARkQkEP4wRsaknG4c140NravM9uxEu1qXi6ySNknJx81JEdLo9X9+ojIDiMxffx+/qs6WeBF"
    "0dmQh5d3XnkmgqFEnTuV4iXgal3Jp8q7WnmUH+Le1tejm5dH7a90rf+85+Lr17DZm5PgiraeJo8T85Z0"
    "XLf0xWJEVU3/CVYoesO4gj92QhjoDiw1UZbdOuzFkWtyLbzK9vXvn3b9Aruem4Z7PozlqV5XCQdSnE8B"
    "39+8e4yyN1kMqnPyOMawR+03Zi+5FvOSBgU1VNUCa4smh4fewuCvjq8kjggJsrSXyIHomvJVEHtSlX4m"
    "fXw8be1OwlN7eczVL51q5n71AJBZSA68fY6bOYl+LfDBgR/UBhpDMHatq0ErHef8oCCysdDjFdvjp/CK"
    "mhydPaR/bdwX/edn0kGRWr/diW8OPRb/2j7z//Bt37/J52/y+Zt8/iafv8nnb/L5m3z+Jp+/yedv8vmb"
    "fP4mn/9Fks8/7zb/P/LJj8z+f/JPgbIebofgEB7vj3wGmSwxe3BxsVzLnpcM5hw5HZt+C/2NFMbPk87Y"
    "qa8PGXDs1jWfcEumOImTNBGnJox+bDzMyvFNnBqZ7yj+nD/NltxQrKUc2/WuoieELACQJveXi9kfzJyf"
    "GSgOw8yBjMKPMqfIY2CoKMou7REerO/h9tMHbYVVESPa/uDjjrd8T1zr3R22/bQAxoW0ffe1NVaSbJ5O"
    "x3ZkrIHbUPwXTYJReXfhqqrt+aIL7m83Lsos0x0sG+XJVxOOE0l3Yh8+mtX7KKlwpnWcIvJgqSBmSGE5"
    "Hbo7kBhi3b7WzL3r5vslal6aUFXcwugAbQgA+wWBYwaXJyRuBDjSAtXpjwvBhu3Ohb4vM0E9jvdhOC8v"
    "joC2xrro/TgfDqk5vN7rlmTYavymocdYN70nYEvaazxGZb0ZEbWKUJl8ZfkQf5cTJCMI3K/8DXCV3tTA"
    "DnbwZsXGswjTJs2lQDcy1Dzf97uBooelQ8hXLhxFRsM8h7fAU6NpJgU9ax5uNQ83tcxGMwVmcBcOwtD0"
    "M2MytBmt5YvGV33Gk2WZnmPHYEv4biesq4xRJcqHj5LeKdhjguztA/wzP20dkV2Wrx7UsFd/bNDZSPex"
    "IS482YulyyiHubxDuO6AA5l7sj85Nrk6PF69UbDEJ3DRFbxYVD+P7IRp+2dGJWrql1T63fLqrF55L9TV"
    "xPCyOE7lD+eMF7t2S0adCEYbo1IXItN/vohjd15EDbMLgANm1J5yGhMUHW/GwsT7RawOfxeCHDx86JrX"
    "GK/NTLTeGQQdBaWp1l8KikN1VMC4gkKktisOOwgFawPXRGv2S9QROxjGrVp2A6aRaXYty6hF6pm37rg5"
    "4pxYgJWkFyYr8kVr4ODyxW3uotHi3xrRd4bqBxf5XHbbVPgbJoezbvWyVNQxBIdn5cjZt+VDTCOyVu62"
    "vYytZc1yzZXBoz6950BMkskF3AhtDWmpHgPJpz5tzc4qYehnQ8C9K1iIs4Yk+E5MuxtlEpefJssfME9u"
    "XRdG2X/PP599Z9ZrS+0sj6scfIoNcX0hhXY/+pPBFPXpgDnJx1LblorHOnn44gyfpfgjsQZTohXB7u7c"
    "b3N/WPhrgfdpTab6+2bGtnGGkVb9vWlxSd5h3O9uYYB4+TnHW540hXmX1ZKIZACGEzP4haje9+Er71XZ"
    "138NubdTV/19UqqyOWjLLo8xvtt2byY1xqVYOTICYlF3PZlnhtue3v6fy9Zfn1jXI4D2qW7ox5F/aRlN"
    "VKQQP7mOl0Tu4bOkCx8gq3HfdzwmRP+81K+d53HeU+5sRXUa7FNjZvj4EcT0nc3APlBkSV87L3PxOMA7"
    "onF6pQiRa9DPA+RVPnRlaSJ4n4K5TgZQOpG082dMdQPVGdCVG9IMkFVzvbfwb0Ah9vkJ4C4qjtAlZMsQ"
    "wC3PmwdA01tqSitvcCAyP9sAUcY0ZtCgJtMgfx+3oN/0kg7Vl6XB1+nTDjURU0veyBFt1J7/GviA5wOm"
    "9+XTyZFxSDD8aYFJoHpZYb5TiuiopCBebooPybUrVG3bwGilTpf88/JJ6N/4aCZXzQsDnTMaU9XttNxq"
    "Ru2EATSl+cTtNvFxurYVo7Rtw3q1xZ7Yi61kPeTHL643I5jb5QQcjDRw22Zu5oQ92mKMWk4GzNu5dYMe"
    "uWtjS35tSQg5LGZICYF47Q1jIiD5VrPUdrDPI04MZMi0nHyBUdVV1tr9IJZjPkwsJ2eluAHTx9z7d3M+"
    "U4YlIA0b8Xa5y6cw90/LBZzAJgLDXV/7J4u2YpKW5o7geYDgKTANG/uYBaXaxsMlNbZWHusO/f67o98l"
    "GkMmPZXGm66gV0s/qD4j/5Z9+smALvnq/Rs0WdeM1xVaNhADtxxNnKbaFhakV2yVGDRzyAtwdVPIIw+d"
    "Rx/0sSuXY8F/Z4ADHhixTfhV7Go/Q35UeuI08qvhqDIrss81OPBxlAlpva81Oavy9E36Eq9/F1lDYPQi"
    "LlTiI9GmPYotx02V83Urj2o/OYhSc2GKenNgfKQq2l+VLs3Qw5L4Z9VU6JdM2dbeqzJUBF4HKvjbfU1J"
    "Brr7JTg4xiSOTIvYiATKrO/5yyJm61oBDloDiaD0VkcvTt8l5wAUon6qhKYrONrF/dh9Ljf0Mjcig4hU"
    "DGKmlHhIyX3DwMtuJ5AVBfLt7iMAwzfcASSolB/OeWogpDYBnX4PFmrzUUQBwEm8qeKm2pSxM+TUIeC9"
    "IYG7meIHcgoBqC7BOFcyYz+xfghhahLIl8eLuJQcKQ+U5Y60RgFmWKpEBnQMf9vcncjRLMxIpdvkhpGj"
    "D299GBvEZ+NkBbBDiF96fI1cD+Yazcxvhynyn7FhX/Fnx9uwkfKFZFeOO6XZ5WUf+hN4Ab/e92VUlJAf"
    "BGrY+x7QCPbP6L3S1Li01dmacDKq2sYAJdiErNtppJLG6xCQ4fCdh3XtFGWWO7vm9iTcZtyyCOyckIky"
    "Wwm+6HWvVl4i3X/b7EoENUjs9aPZgslWF+EzEsvsaW5Sm83h+g30eD+tpAkAe1Um0R4caOouS/LUB7j9"
    "uf0zb185J5wyeJP9gVA4pLO4z5shzHugwc61FAWlFhx739zoBtb6fh9HccrCe9BvFiuh5UglMUN9OCTw"
    "tbiaeqWHLn9R4uzEFqGIkWxuJWp1jtMfhcVADzXHx/foSlgYHy34mzaa+c07KkJ01jchuYovFErQhNXe"
    "AzFKGG1R54U+D1Je2cD/ohS0Vk38afbe+4gYE4pwDi4BuM+gAlZrnds3QDrn1/r/mcL0D38i8JeI/xLx"
    "XyL+S8R/ifgvEf8l4r9E/JeI/xLx/wZE/O//3T+yT6Xz31h4DUI3onL7CqQBNv0PmC/xTmgXTmI/yJFs"
    "j5Vl8Xf+LhtgaqVYqT0JES7mg9MSGqryXkai5Eh3cE6sZkUWgttqFY6rY37D5JaOqJd5DWLO4BpCcXJf"
    "C13IG+a95v4+EJOb4uADD5txgjR+y1Cq04/ePyWsPCB5vdAYmseMXHHz6hOqVpgZrK/Zk5lbKQAIABtK"
    "Nie2dRluLjiaaK3UeHG+wOWX0TVGUamWWUOC5hhbSLWkVdpOPr5cU0GWxaAaybsl02LCS/gJEIL3VB+j"
    "O03ugHxKU4LYWBzU8jv8ng02f6Jo+uTDeLLBaiCJyYaI5lDW/v5salIgvO4CVLCoalWXNSHZCDczq0ql"
    "PJMXe8i50q3trcxV7Z9xwVT0LUEEYoWT+trlzXxQ+hgIVsJG556PcULYZx4+68Qw+MmvyYTJJSezZaD2"
    "V1cNmlEDUiZzKmaODNCymYTx8WvjCqfLddKSBuKgmyGdglmrP893WIpzBnkQJdFSck12lmWcWcdRLqvO"
    "GbZVg/U3fcnheTUi4frBW0V5x76Zq42pWkqlMbB7Oc5GL+Y+fxLBIo2NbuHxuvkDZqfjLR4hP2FEsGNV"
    "+qDPGY4fVjDn9pKsGy9RadlcXLQkWpKDBcTNiwR6z8druRpeX0Qfkha78SasctA41d4xojxQ6h77brX8"
    "cmVKRUfJ61JvL0dLal9NTflaiyv7aALeDpOXBC7FX/LC3yoCo1Xu4zIof5OALsLq1BhQtqpmbwz8s9fH"
    "5fZMUWvx02CA7NzlKLit4fy4M69Sigg4nT2tKH3ZkR+NhdNa5ld8r9LoEOGyvdMVEZa7d4g3FZEo1BQ1"
    "JSJrG20cH/pXku9Zjqubs4As8eIToYFHIObAPb+iUfLfqszCNFISc+TIBg8YZVwGiyis9ST1r9CmWvQU"
    "XZERmYIdELBDAivXc1jZ2SnnJkf5EqiwWpWG348Xb3gAzJr/IEz609+LZSkCPSigBIT7yzYWBAAjf04P"
    "VUEwuhLsJw5o8FOWOzl9iSDbQaKJ/cVRGqJvP29xYvDAwSFoHAAD24vQJnDTPPxLDi8U5C9hjkqQEUVh"
    "qrnqLrE89vYJ9s5VCNfe3efg7oZ7TJz+avpelsrBBj+bhmdJ29Uoxi+iPPHxN/mhoRrEdjZ0eoJDKqP9"
    "Ek2QZjeyw80J06yNkGvTZXKJwAXGL2n04M/YB91nh0HaU3jb6nUaZopw6h978fu9fQhP7+Bvfj5PI0kF"
    "Y40YtwOj1EK3LNBu+5LNkeW4jY9CpMPKGBgWjtj65d3uJFK6QUNu0abi3k5T0gJbCs94PIMwOIEwSnrD"
    "gyYVmagPI1q+BwVWfF3V4+MiHXaIhR+0acu7v++E4mtN0n5QcRyYI9NNw2ulXomjbhFLkbkzi4B7WjMb"
    "hTqNhvx07QxnBX99T7MPannzoZg78ZW/Up046sm0W2kLv0362qR6uPgE6YBEFgPHgqXIOtQXjgTWshNr"
    "N40SnbqLIO277ie1HTaIzGhWnK7R2D8Lbm274zufylwAsPOxEjmROU0cFHjjcRUiEkvoh/ssr8fFtOgz"
    "9plUp1M94s/08DSl9OO32GPLq8w4ci9koV9f/rqpQ4SsnTx46D+Ur3BEJbZcBLy0kKmBxakyfoH18qt7"
    "CLZFWdPU3a5fAcZKf0H0CNkar3M/8amHI7XyubZ/71SrL9xfulv7KBsCYEKojL9X4HNqe7UfA8DS/LPX"
    "6QNcWw4E8xV2zlvndXUaICxRilwZ8k0c4hgLDAxz633qmokHR59xggc583EcjDpZBiauFBK2YKLuPfWL"
    "OrD3aRmtvjSKL2ZzgBBjEpk6kQb43/809t//IztgS+p/23hgRcI0ujz/Gj4lUGYZAGorb6ZLvkp8MC6d"
    "mpDsIjFMF52Wd8lJLiNqANo9lzhX8LX6vm5+3OAtKFZHts5fEmsDMnMkbpJY1W+dnTAd9YSQGKM/lFC1"
    "6hJJffIFmyK7TupxpSJEs6CXeFRxPHJHzZUC35+iJM3DMkGM8PeP9YbDoYMJRyuLmwsLR0HCA8ZL0w1/"
    "oJyr9MpTGC8GDq2WNCMEYxdaAV8svm9uRlsRWt3CPb/RGaUNZrthwvM8HTSGrQz0FACCukjRvw3DPBkv"
    "h4MdjGqgyQAuIxlaPIPaUqR8BKO1vD9TIJyYK5x7N8v1d/obOdFgCq4GNNnfEH4cCuCXFCQgzuPomslG"
    "ifdMHLj1YFB7sVEi6iC7pnFxK3jEkRZei1Ncn8dL/iYgRcJamsW4JqxNWf55M+F74Fdycrq793J+hYaD"
    "cihlrZFPFda33xh1WthAYn4JUiuVDuiyLXb5hUdaVMaammxZaG7s6W201B6ZSOZGZPdC4xkkJvT1kEwT"
    "86j3aC+YF9gqHh6mVdN25CVQoJy9LACtnK7MHD79RpqXbdVGlbMhg4oYDEX1GV41BRbFVwTxLXZJFI+e"
    "gIZ/3SFM7uKSgBOprwq3wff0m1FMRJuc7PTP8MYxEAgclPiS8DMTcZEvZRKDi0k7bG/GaDYoQXAErPvz"
    "YWLPmaREJI4ixxpaSUdpM/0iMKPQOiAwxeG6falSrfosLVJ/hltK6oAS9FB7zaQSb5LbIscs8xzqqFze"
    "FuJbPkiMhqspe2fR17YNYJvHvT4WNagi4i1bhfN8p4U4qlUrq62TqFx9kVJIjszkqBBefKSCakaOl5Hq"
    "/Y9Wa3/dWz0XlCjH0eYoC5KZXZb2EGYO5RH9m0AEj/m1fVR9vhKic+tLyu8SjArjJa1lmlGnNSChxY66"
    "85QuG3rTm75pkb1wgOMefw3rQQwTjMhRovcrJU8jaIr191WcmDgtOF4kVBJlVbn4LS1ccFeG2wi+rdb9"
    "3OsWNcGVLoINTpJ+hETWvOlizKcqd7fXClCD1KYYEr/0V7nT7lAgKzE55isaqzeB0sNqWbantmrSlikw"
    "5RDk6c4zaS5EOgy521QqEV0KHzW+JCMRM28QZ528Kq2dsYet1w6/+ejFEX+/RwFTk8dIsIimXkkd3SjO"
    "8bS4sJFI22BdjK3YjlMlZZkQ1BvwbrnfOvxIRhaWdWVEb7dLzthXEbTOIguRt+rODa4yywNGWKhszYAc"
    "wzGIZZJd3+Z2DcYQ1tJxmAT2olXjsd063I7iBT0K0fd83KU5Bk41rFt33c6J+pu3Va3DduwuaIliyebK"
    "ze+0Nh11+L6tTjxBtXL0W6BTs6ZiQaDYGHI+cUe/WqENBNUqMz4cVz6oeWKCOG/2bC7+Ik7ei9iyzJAP"
    "9LNm0bIEN1olgT9ShPbVza9+LGaikYXqvfQtUfaZIBJJadCkTP48uTVMdyTIV/HPk4V34CSMfF4DD5Pd"
    "2CucO75EXehpQXgIW/Ozb/8eHKPzT4ysw7dzWqI0N8QLkU0PYbCcjHxHl0vx4SwkC3SjTReSOWU0S2S4"
    "1LOUhHlSZsNVIPoGjwvfejL/DfrurUzreD+nFuYuXY4C7Qipxsp4/7wpC0h1GSMbyZIiEHIBVZ6iNZBF"
    "xvDvwp+rDcDSjw13KInTiYrGW4+msbwBHuMnVux+cb/vcg2vG+NzYpmm8dabqFYo6X5wak9vSCtSUmPY"
    "HfbHSXdMRmPuyeeWFU3XsDLQdHvKDVAFf9cN4kqJY8HoB6dIG85D8c9w11WPf823J5mvG0iSkazjJFP0"
    "kyLnxrgQZe7+beTaeO73ysybN8N/FvaXJKSqjdj6s2X8JPJooswVCL7+dj4rnAB0l8lfPV6XnewhJNUX"
    "sb1tlaKR30bl+POuNKz3YPEYiz/jLZnfBBz0sMRwKud+g49jwl+8bC7s1H5tswzJlia5MQZtkRREOCfT"
    "3kEPEU/9e6x6hDcF0FhjDLuizzHXR8xY+XLu9hoMW5z4WQnqDScPMxunIF4PJp6gq85OXGNInaAljFl8"
    "AqNK0B2hoqDfppZ+UJhfKcCZ4/gLnTP4YoDWmM/9XQvAQY5w6RDi+DNQSmhOlF5osIQkwKQrEAH7TF50"
    "r9f64l/J/P/0n//DP7gJJC78y3SKADmz+PIAEPF7EibT1S2ASyZ04nGU0VMxjut/X9ZB13xS7UQl528L"
    "pfap+bnLWdDnPIefCPM4K9NO0oqxkHpnl9fW3OZR3XXGJauqus7MSEdz64TX9FHLpfjkw5cmv49JlZ/h"
    "zxOOa6vvXDHhqA0OBqDRIH4M2ptoNdXNzTE5SjnGBUpgqjPMSxHG5M8Bi+lO9KEnTW08U2ZTjMPURFml"
    "AwflVW1seoVhPnw9p3139p3HyyL+MeKeGtrHJ15V8d62B1R0LokPGgewhcM5GqjqmPPu62bKdO4bllWp"
    "5KUOP+u8RarDygN+X+gkRBUdtcd3hvPn2pzR3AmcIzheKuvMyLTZ5xdsfXSr83Z8CnxEyGX70eubUc/5"
    "SshPin3VvXDUe1weJCyn+uB23mVoiXVHAv3BSxrCKg6n0nxRa8Y7SNhZhqJrnl8Br1SrUy2DYwmCODub"
    "tfANKnQ1PgE+J8WQ/pncwXmv1+bK22/xPX8YsXaCNeTSC/8cRE/r1OTgTejDLU5XEVj3jN3Kf76ogX2X"
    "XrS2ZL/ADMBMDf5sQ7G1wTiv8h5+T+5+Wc8XPNs3BGqIKtB4vhDS9OB0CJ3kyI4sOXAsWZvM2/qf2WMM"
    "+OtesD9QfcbBAkRRunwTYAnf8tF4qE0VVeRdv8cnd37C9etwFxjAzfWbYnOY3VpdS7w5HNiBiEjxIfYZ"
    "+ik6hWmpAGvH4QI/hY6YarV/YWRZzAhCYMFtABrvKUE+xeq2tL2t0TFKmhCJG93h397IDDA4jgd7naKI"
    "P9Wpvv2g9m2kyDlPDiVmdHSWAv5DwgMC67kP+Gi4cSSJwJ2J0maa6ALU5ICUE+Fk0cYF0nuwf9yDcsPQ"
    "95vbjpWsXyqhk/kuTLgW/OAArR9ta6tm/yzCFXI/OV9B7VVaBh8iIPQNck6SZ0o+li9mTdb1DW7GWI76"
    "a7pTSu19HZIusSFe3mz+5nowR9JhB470Uzh9cJufGGdqptNW3Oaq9xf9KQ4SadzT4xg7UuvC5Yp8pgF5"
    "w0yHGHD5umxfiJTY4gSpfxGNYhiTycn16/c/7KW8njwWFAT3VPqmALAhyFdVbDU17iZzfonSsCrr554+"
    "UVc5uP2S5xL4klHuQ+GN0+wXxlf7FZ5NEoVFVBVnHFoMbzHnpR5O0e75cHeaKTMxI+Vszr41Zd43DVLw"
    "nBLAmJzzvCDRIsrRlA0OF6E8djoOKZCFHst8CpOg4pff7z11Xmg5nNW+Itcv+Fm6dj8hpU0Nv0DTP1/j"
    "JwWJN3iY1C0JcTzdb9W+R/uhGMWyqhHKPyn97C66Ed6VlCZfH8jwMozR+NxvHjJ60A6KKu+BCD2UZ70O"
    "VH8VE3FMFndF4zlGemOI5qIAx3DVDEyGlpHOFNtj5fGkh+agKROSRefV85DgSHfp8a3DW/wFHue04bOx"
    "zhrz8iVlfIuLMhMwTDoXv6z1CSCT104g+oa3WVm176qbe8ep3eKAfOlYSAAPxzUwe3IuABF1Q9h8vBdc"
    "N1m2fYYzap+RGcfxex5/6BOUFhXf9th9TUD8rY3GpuiTNlS4ELuqYu8By5wqOJPPbttv+dZ7sQ/mW7JB"
    "Bak1meQg//h5AHgYzyjepDpse8qvyb39KqEaUjbWmZc5ciThhWUinzmvVw+SXH2k1PZy5Kz5gdsjWRiF"
    "k5ebr+H5Xm5ZPLM8BDFR6TbnBj4us7BKTG04SjKvpqJB6U3m+nGY38fZDGV/hhFrOLXBoLes2H4MX3pt"
    "xXN0Rs5Vqh7zL7ww395K3sq30M9gEDMZJFPCimriBLgnWukDZPeatml30uPb640cs8ta8mIZMLfQCowl"
    "0TSC3eS9hR8xD3TvJ1vWq4iVzDXE24o7chkwoQezUyt1mAu2FmGcJHYeKJr5AXZkTpsAegLSuOr34mmr"
    "ETYF2+rZaD9sInLMzXBKZOGm75l+y9tKSf2qjlUzahA0AJwuxFj6DE4Y527GkFn42Dud28d/V1sH45Kf"
    "oTHtcW7wF0QX7v7svmHBXnzkEMgg9BLT03tx6ex7Q+rNVBVTCZaXjwUfR6hHuFQBAF5z46MBn3qFewnU"
    "MPFSc9s3WZrOhRXV9/3YnLK8uTMQHQsZN/Zzm+NUioEkM6XLx0sPU2LSxxPzJ1QxS60QhyV2sSt06FFC"
    "BUnIZ8NDP5Mc6ReFcMHN2eFNv31+YZacB5v57ep4yk+HZqYrQO4fk04+9VmKJbnxy5J4302uar75+rH3"
    "LnzLspwapJ9ocO/MtSmC0sKGW/AALA4iVMIUXvwmfD1L6TkqU4vw6TZ0Wn+9ek53oTaBOzQrCepbediM"
    "XNNdMkgErY6c7wDLfkR/PnTslgHRs8V5SQvIeqXBKSr7jglDdIcOOTsplfAnE4+VxHhaOgrJo9drl/97"
    "d4ZeEvuLYX8x7C+G/cWwvxj2F8P+YthfDPuLYf/zMez//i//4f/8Rzhs/X85DAkTlPVhO/yAyF7CJIL/"
    "rE6oho75cZbO4xLlSqyc1fq3DP2k15fGkfZccKfI7CuScJutUiDX7Nm3GBajY4jGbVYxDdBv72KgLmoe"
    "/a5KX0sX04mcr39Pp5WL1lwBAHh8nuq7xDrZcR+AvE8NdN9RGF7Ig464uPsZDPYBYeS1SoPfljTA04eg"
    "/jycmASv/H5+huxgJTiOLlxxlYmgeyL+MpDa+RAeKGim0EXEOYP4vKueFsKJVb0gmUtCqSTZo8ewndeF"
    "UpG/YwDSk3kj6lyWAwgdYR89esLjWGUu0V5v3NVhuR0yh8OtvtiLBqfvx+Xi7C0+QWAoB1k8NKa3jjOl"
    "LexOkyFtz7/CY19KCoNCbDjIGG5co+DJSGHkMkQ/S9jn2wGAEkus868xMyC0FOMyq5InUBrIeeShSgBY"
    "QoK3+LOJ4pTchwhaz6NczMtr9RjxZIaQiBkYcKq0zEfEDywVjm0+eWE6+8978dEZWxnM/Fn2PQTrFq38"
    "DpNxaSZPBtB58RxDUPxKYMZ/ytP/hm5jKAje740LXLqNa19XRENkkuO6vovPt95P2KVTr1cmtWSm2Q2Z"
    "fFd76XU23UinRzAZlml5TcQTPc4jx0DFE5DaD+6wvhaTS9DiI3Qk2wpnWxAPdWjaiPquVeIpB4MH+cHw"
    "j56+qJbMxClFJB//2LFhEHxejg7xlpD+SOXoZPDLXTFhcGTHfSJahWPLK7aKvyaLY76RIBf90oaAcbHL"
    "bmxff6VfaJqob/lEDHhq7Pn51VM4HTMS5u7dlyCSMO4eRfLgXce+2i68xx/XQpXmniSDySw626cv0jxg"
    "oesNTqx9sQ4eQzKhn1uDHQv6miPdlCagBcNus+TZZjirPzWe9bTXGTUDCbNnWZbhHYEplAge+8rM7+v8"
    "umPTLp++woH8FVzyybJQ2hyos3Bl5Ld2+lbe5aF0kSVFS2Y+NjLa2Fpu2Jk81/q3a0AKkMR2Bztq60Fl"
    "1Uo38vCQBgoeSW1G6GJMGm98QiycwS509Wd6PNagujEI0CCyj+XIX+b3rlzfT3RHOs13rci2h+Ic6kpZ"
    "YsHSQRethfGrO0LYe2vDxT8LsLBb5vpmKSrMW5IOo9yKEgOak7VcbvZlz5V0J8l+B0055lsNPvS3zh1n"
    "JtHPE+B3aAOG9WgKnP7ZFRte8O8EvDChU3dQn2pybcYrhr8dzAhVwXghYr4v4Wem9VC+W2Bv3shxjTHB"
    "mpsBfum4hLVYYA1TcRzTDBJF9yfdZuE+29QYxXvOE+NBfPDnaUqeYbWY1UAgIEkwoynlbb+u6aPG+ETK"
    "pZ5pKoonjoLllmlHgE3BykUfOsGol6E/kG9LGp2Igt0w+dZKAsPz6FykchVJJEVEk8iCAJXt7S/rkPJE"
    "PvT86q+lksuKwEsXANQGbtlbYxVCs/Dla9WPYUsmaaGHRczzWMTvxs24z/AVxliywhS0e+MnbyVBXRoF"
    "oT+PA9e/1moRMgnuaI9nvFm06g2bzkBAUqMSJz33cxKB93o+Mrdb6LPHLR8yTlvf616l5JlS/AsEjOtc"
    "zzPFwEbc2bJCzFrqXYG2r8EZ50fsFbfWMP+H4YIbQ6AogMXQlYpuJWfEc99XIjiRtfkuLvgCwtjOslGS"
    "YZ2T0bWMPa3qrWyMZj0GLOIK48ohQBYQESVyURjm+H/YO2+c56GtOw+IBZOYSmYx59gxBzFncgyGYfwu"
    "DBtw4UG48mw8EvMrnABfF9eNi0/Ai1cJEnX22WutRyIPmwT+DEw0QTV/vHfDK+IbiVDKsXeUUSzSEi+J"
    "KsQHXWSQhLA5agBXN2BUofxoP8yRhLjipVqiWWkRNabSuZTED04i+33/2L1ErOlMwAFftZQCCLLCeNAL"
    "GxJ9VNLW02Qh/tK+P3m+jtiejehY8cl62axRQ0nrB2IqQabCsm+z1EqWfO3LNhXfalnfniwcMZJ6q+ko"
    "S8/6dCUUqLUuQglMx/LQ5biB7kXTdrV2yn0+6C/jVoAYtB7AJnzAAygI9iyrXqs62vPwa6bOlwrBx5jS"
    "5S9VlkaTuzEZ0cGV/owDX5G51SbiAxOTn9/ARR/brpmW4Dm/rnqsK3N+oi/QklYs8nohg40VocCU38qq"
    "E+mgBwGvYz3WvMarjBoM/eUCt4LT8TXgR8JGNbhCc6l5qfkizHQSvGY0EkVZtPWeUunisYBmi6CGBzSD"
    "e8YIjWfHzTfAY0TplZctb0kSiOsJc/DZ/PovJMZyUksPNepv0jBttp/h18Y+whm65AOxF0VkrWn8ikYv"
    "MncOCs9qlq/OOXokMTEz2iND055gctkTJy4zxSjeFasoNhPyoE4wFMULxd/qhmELXpkIlDRjKFvUcazy"
    "tWbyR8J+gE5cnu/ZSV8TmQxvkJrspZ5glKTBcgzZmkf14h+tNP4v/+n/6ewqSxCWyO3/2cnJJKlXQI6i"
    "oI6i6+SKSEeWW+PovuRmUDnelaNP6+19/OvlIEiazIn5CRIfUiOd9NqGljfyA5OENsB2cbF+du/VYD1B"
    "s253mhqzLB506zehwBx1CqR7dexoTRO7AqiIazs9ZREsSpJ4ypQYjPzdkAxnYuvybQmsqo4jhalDGaGE"
    "xdrYRQN3fnh2SV11fvwMRY7afVCjVAqRy2FXSfNkbPnrTII5eaM+SPYU9uNXWnWgj4G+yJUa7WR531qh"
    "DvnpPh2HuoMTvl5YbP0geAxM55PZgJURm5rbAswKUNtIJrSIMnsy/Oa6stwFkywA80DFFgf466f4MGcY"
    "HwwVAYEMwgxNarlVD1VQQ3gZUq1IKeUM+vsUu63puao2CpKG4Dosx+Fc54QQ8qIAiU0LUsBZT2FM2TuJ"
    "aUa4+PAs2DYfpZNP8h50ImNoD14iFHcWPZsfV7dndPsG8+UH5jsl7A4VIYvqb2zOnmLl9KLyu1D1c7oX"
    "U2fxWJEMYSDtVKZv7AVWW1zw8tU6zKG3XZFEc7eXAtyVDY62M0CY6DWIR6C/rGVEBPAlE73ilDpnxfxM"
    "5c8Z/kJhqsCzpWsFAvd8DSshr2lYP4hg9tqLMYg8Gfhcp9/EK4F0XYA0JIA9os+NmsA5y34+mM7eskQW"
    "pYwlfKJCvu+dDUBSyPFgKkKcn/5h3c9oiQf9vhMBmdVeM/jnu+YHM5+67+g4wQsvf85XaIXyYuYr08/4"
    "fB4kwJwfTyY9EkQjtMqOtWLChqn4+zjlR4Qt8M1i3EeBlnO9Eavs2p8JwbFJam2lJVXC8ZDc1NzIBZPN"
    "fYizUVlyzuupR6WcNKHXdT79VwLrb0N9uJJxI/UuEAs4XxcqtQZbY/McsQYQrB0/yocRCK1Fv9d0jpLd"
    "0FmlW0jDp3QnyR/+FR88yyv85wWaQGtmLYuUhk0ODix0MIhzI5XFZKnlKBh807C25WjW8Vll9c+JT3RD"
    "ziz0hM70Mraa2q1sHpXm4jhAUH9uCn7xr3rlfbUlmcWmO/moF8NCjdR8Inqr1p1D38nKf4Larr+Rt9H0"
    "x7Zk1mY77QFVZUKzZ5HGdh0t5dE3Swi7pxLIwK6rvu217fV2ngm+P4DfRjguaeRz43nRzgtGY9TPvLUz"
    "yhoS2wLZavF661Vyc65hQ3Kaw7lD774e20IfN6kgnFS25aHnVxLxYZs7nZh+E7zyGBFC6he8k9kMaqjp"
    "6Ac3q6sc+A5eZPz1jkAoDSweMMTI9Ot3qV9hPLcFTthb/P6eAOfLnyuKLlG0AJne/eoFEKPTnRZF+E01"
    "eAa3QTcHezovOMY+FIhNMvbdYlh6cM4W869RepEqQwG3QR5B1T0cwzzVION3THE1roinLX/qXcHwCeae"
    "Aj6tJELCgSYZXkM9O0KJDfWe4sbeOSqOK3SnZMo2J31AK+Rwqcp93h9DZaBihrctvuBV85ZSmYv0FZzk"
    "WDPcZtHY5OPzkyMGAuNwFw0bTST+KkTu1R90m1vBU0qyv+b5vpfTAGZj58t9op0NOIvmctFdgnapWZ1D"
    "z+FXYElBjbpiv0Ihe7rvt2OneyuDwE1YWHdQ65FAszQo5/E3al+TAmIk0J7sseI4WjJcr0r52z4gRR7L"
    "IxYfoT6e/QLz0Rjh7EYxVWppHJnf3FSmjI7JKBYm26+E7hHwpB7ofAESrjhKWBYOCtgZCJ7JcX1JuW8P"
    "j97PeFD9fuXIaK3ze5cBcoQ/fCNB3ReJy1+dz5Z7WReFcuQHSSvIhtCVdqdje60ofr8ekG9x3fnRxyTA"
    "x1yEt2SgNSKHkhIsPmoBwt7jm0DKcIKZ54zqfsPT9falNtTkfWWjlajSdOLrIpKfn/hxLRAO9REoG8rp"
    "scWRMoFnZJc7OJjH39XXC1M7YrXV4T2ikcGFzCc1rGtMYGPJ0PDZA559PK+i7OcBVq7yFPF3aPLzVUwX"
    "8OhfMzB5B1mrEgRTp2BOPb7xTQ7DpS+f2L7laqyAY8iPpOwVg6T8xadC1Yp6+8+xN4IVmISU2IwonDTV"
    "Myt2gMZqHhsEflF9YYW7rsD5KEtzuIslkUE1dj7eyemIP4fK5MwhC3UOJkCXMQi1z+dw+SM7/slQveu2"
    "oEoHDA/t5EULwp867aLJzu9iypBPwmUQGGPLb93uX/shZhD4oWHiuvVBclX5i0C3WR8OPE/x47rUbYpC"
    "pq4XyhgUBBphdK2A+9NBvQnl62P0SFCBVokj3jqVSK8G0T/IPP/6P/8TmYc///vBUzscusHl+bYLPMtw"
    "HMVPg644MY5TCrqu+jLxKPG2fr/Nx9M+H7oXXX1sTzrX3zTNn6ps8U8lh6p+WyPHJ6zV53WWCFow8H6t"
    "cezjODkjwY3CIwn7u6fMJA+z3E0H6yXBxHXCs3jAjI84J4ijzAnsIp7lp1BUKpHPZUwWdtevVPawNN27"
    "f2v9wISWUocs9h2BH0R79LxB+I34CC4VhRi5t4mGs5UX6w8nRtHmFPdG9BRNY95GZUzavjfN8KAgp4oE"
    "U0DWnov0s+Dj9JZVEZeZ8F/qQ9WvexRJvgUTIi+LxSyd4uGS3wqPgSqvEE+erWKQSx7ll2gQc8LpLuGU"
    "3xAOo7YscfU6Surf3rV0qVTEhgRLKm428gvxP1NZ+/n1MA1qOf68fszytZyOH/UR1Ag9vrPKalhHJiZk"
    "+d2IHOLaZetqb3e8T2uXxsfcK6aGNRstpLCK+4SNzVv0yDMWrbska7oIX7FXj5+B1L/tF1SQlWkSHHEf"
    "varsEZzyL5zZfDI4Q/556yVCepW8bGUjrh3M9CXZvE3HfM3TP3bs5F52ukZudRaQLCbsqZWHbJbmpY7W"
    "a6mPTv8ReEeTzpNJasA7FZp8AvSrZn5ku37I9j0YBB+s1Zxd0qKm4blZcTpxvE5as2EBajw+3CIMeCuq"
    "drfs7q78AXbDnmASoL7xTcZS+4d83JGRGmYQyFI8HPMbz8ID2LGetfTodp8ceCI4N0IAMGRtgcjzw9n8"
    "u3UBz6k6+8liGCSfqSVeG+5FPu+Dx+RGyGYq2pv7jFNCV9lLQoqE38ftLI0sZD3IyOczlwC0wjpI2nGu"
    "T1VBqUvKaL+2bYs0mDV+kzDooBu5ZtAPlcGYv+rzGga/XwwSKuUCLOg6tJBp6aMy3GfZEPbas7BF0ZI7"
    "mSp4M+oUd2JL/KQ/zzHMs9YhoGNV4ujvvMS/HxLKldv1vhsk8DRfKKIFsPgyqof9MYAvDKXfqY+ei1ZY"
    "DnycFbi23luOfttTF2xkRjFxtsmE9Q3SLk4B+ZDP1BYs+se8xThYeFdbjGbHCfUA0ImggOMbtCteNCPK"
    "EpOjVLNUy8FNJyLG+i7zegTBtXcZqg8E+rXrEevF/MQuZWZpz3GcIjnc/hr3BCukGPXSXGHgWP0sll18"
    "IynRfBz6JLDQ0KHgFLqR7fAmhwhCh/ROVptRZ/6MWN8/ScIi/n3aKPLBNFtoM3E7q4w917WlOd05hkSm"
    "jQkKaL7qu+uCP4O4eM0s2KIdUhdtR2QdKS1FwEAUSHVkbVJ1vqzyjYb4+qxvX27B9bnY2nIkKrQVhwC3"
    "3kLSr9cosGad7GhPDB9oK4JF7whcmVgSGP2m/HgxXGtS5iOsFf7jHTnjvKLvCqp+1NNqNcY5swlgYmuO"
    "UgP2yahi+Q3QXSHtbIfMGyK+7Lz4AdS84+40T/pJaodYUAtFwTeJHa1Bbevm6jj6BeeLKwTQDKjIpwHx"
    "E/jEeWDg9whLkNogrHO/KJbfl/Ykt8ScGhYWD5HmYJ0jpd4vxPOB2/0GTtjchqw0uhmMF/xY4oFMtJGg"
    "ea7fS2RTbUTl7iMtO4vvPrsAagPwu4CsLzU+z4YMpvKh4at76PON9s62HIwAHo67fMWpJNMHZlKao9ns"
    "3sP9PqxnKCFdDv6s0RnBY+T9A7/6V//mn1kKf/rvfjUFYREyORX+OQNqjnZEOSapWKja737BS3pkZayE"
    "LqEfzzo3eXp9y3O33XI5WXa4XV4x5xelqixNhsU0udaggpMxK6l02K++KulbFZiwfWx99U7Ski5tijYz"
    "QAOsKXOKwnL3wD7WL4G/sUk8BPwQ4ECVe1GQIFKQD3pi8L0tdrolszaXlGzAiUKB5YVU6nNUV7a99GTP"
    "Ya7393bNSQQNWSJp8hhb2WaQCyKUHgMVM5yoooojR7lZJm8y8repm9UMnX1qhv0c9MPbHFBoVwiSR0y0"
    "cp6keEyWXqIVjCdElUEnRDC9NADUuba7RUlGCZJzg2kc2nfqlx9iTtEqAJSglOvflw4znh+NIjFb3GlP"
    "Bb8VcsVG7UvZ6xqrZ2HN+fdeW+AZPeCagKs3y5B4Iy8eZZ+EDBwFONhJT4BoUo9dffx4AladF/vf/sUd"
    "3EJi6EWvGJyA0NybdC2QzzJ2otEDK6KH4JArbeGRCu0uteCc0xJ/cSMH+2X1icUHyMwBVDmxfTX7uNQs"
    "uyY1AYy9fblppuax98fTuLr9/qT0D9reALegaAUoxWAtDUKgr1cjQfpUygi8LsMEAfj9gt9UCGAdOvk5"
    "y78uVW/zcR2z8pDnU6hQgKDPhTNyG0i2eX8OT9wT8Xz0IghlmCyCmupd8Oxfu8GJgYY6Y3ljfHs8QAK9"
    "mSYmT370aG4sSvVG8wAszQAP9JIHeyY4p3H8uluGbgT24/TaarCp0CySLCKn70kdHRF+oMVPSkQ/TEqI"
    "/DGIeROwGSW/Q7mW6vH4IU5eXYfux5B+iqc3trb2Ou9ga8MVLRBkORyvsj3e/L2o6yCG9jfuNEeH/HhI"
    "SwKzxvu9aDepc1z0Q7bAr5huDP0hOgcFtgouCIFQ/W3BRCIicMxMufBbRzUrAg8GwThGJaCsgbcXlcx4"
    "Zx+fWYVk29k4+opIp7y3e9bYAPdj2aPEXumr33wyjbgZ1pdYvH043oZZE2EKksGMReJaeTgTHdzQQ597"
    "jilcoOTxSpsQLxUxrd8YIcms8+Wi2jcFi/Echw3FTvpI0c+mzgb4BYo8xbQgS4d3SoMs4FIUFDXPbtb8"
    "DWvCMcpPaIQb4zKrWNtQAc6Gt49OV2W48Lsy8jjn9WabH3VlORwaLk4e4RN+VHIebaGUTkZvWnEYB65p"
    "p6mbdAndEQoGA1h20Zi+3IA/+iULZEU9F+IF5s/O+UGJaYjt5iHBVhQKn1QmdUEIRrNzNy/2PrqvLuAV"
    "K/760ISaUb/VRGeEGWm9t9N4QuaiONYFu+8ORydQDZCZEwcssODgu1xcPi/3o/2oCRtc9BZB5W7BY9/m"
    "HveOwONoLKSwb+51QujCacESX2Br7ySJeBk0E96CfiGST0OSShnQaB2/ylypbXs7cj8+o9UYi1N77npe"
    "0z5tRM5LTR0/e/BXQ4Prkv+KOzSB66wVBB65fTvjATkNYX/9QlQUnvtGLY6N/SKC8JlJSNcLWKoJzoVZ"
    "RPLmMfBs9e2M6Uydecdjf6uaHKzWOrb0TWXP1hxOUCWPpNmrRDQDwD64q5g/Vg5IhINWvwXQxFq8vCXt"
    "fWBHKcFh+Wa1ssD7FBgHVSz2WTobx8JKduGWsgwhfIUmDm465pg5bjWvyrGdDw3A5PRiqY3f8KeIpY79"
    "+BsCKYBQoRVZCTfaPPQYwLlKaMdT8D1W9bPQKPXGPIRul14JX1+3jyp2/UZR48+W4HEpoXJHWlBiw3gL"
    "bycqV+zgUJlnW+P2QNl8mCHLZHrVlDMjrFV2LXfZ9YsJtRgERxFqxR7E5JA25hQ8OeC9x1P7xKV2altI"
    "lzdrWfieM77ypz4/+4XU70hDrNn7633XQj9foTfPr6CtMkQyu3xwLRL1c0WKXVeYujGCH0FKipkGSfJC"
    "r455kUHw6LVlErVwyAKw0+WHbBIHyhp1tTTC775xrb15eV4mW3dbFetyQDC8rt8cJgJy43J8CThyPW4W"
    "cUHBjd7UQvFykJdgRP1cxTlQ1F06MErchdz6EB4QQL4efabgN3Ddduxr0+5ker19Q6zY5vbBEXylAxUn"
    "/TbGfqllgMYHYlWtBe8ycFnbLrACwYeIPkfBuHdYVHYAqJtU96RB4OUXXRWF84wa9QLmW8Rj/3gAK+GS"
    "MVpZB0B3x+iC0Bo5u5hjBuI/g5p4YpYadWCeKA7ryWuxDt0urnwI2g1x70JIm5u5GaNAmgnFdYY75WYv"
    "yOsxwefBAr38svvFbx+yrH/yDdZ9Pt1nVrRDwb4VdpikGF5y/kNS9Ccxi7zxqEvrakLBRzxnswKGWdDl"
    "3KKTO+KJIXUa2OOvElxmlNTfk9m+LDNDXxUKAftI5vvNcxstUWt/7+mRXqvIERJYZgS5YUbCocj1KxoF"
    "x8hfcO4VEhizFO3KoQs2z5RewtMKH3mqJzugUXMIj/v8fomyBMwuPVmSL6tW82nTTUkoYj2fariqa+qn"
    "Br+4IaP471OfrxzprPerDmOpApixKF/PqnHdoWbRZOpLME3Aws2gx+TIcL1U0uTQxVWfnpZEXrRo9hIW"
    "MDFvjpacqftjAa8a7XnnD+DbphA11FLHoTmYpzcU8+TnxMLfMYrU1exQS15mCeXseHsEQKUpT/EXwxyq"
    "rUXquIvL/arC5K2pt2y4P7UXyTiBKDUaWT5sIpq+8DFEslmIW+OCZtTbIdPQZxnMNb8++NpKFvaDqfO6"
    "CRAMa0y75+CasEsZ3DjYdtsko6PQF2Mhj+Vu7mN5AaH8FRqEvbGJR0fw8lYxdP1P+Pov1e6ZGC4MMncp"
    "mX+Zh8faJnCWl8Lihg06p0Ce6YoAPz+sPXs8pP9Eab6rhB66yHF7Iax/2hk9AppJ5voHJTyiOQVjKvj2"
    "UYLNE1YGAwk/icvCw1nrBa0VV1W1XQ7gSeaFnAi7In7fuqZQ9EXSmZn8Sft0rxC4vIPbZAYiwl3h0+oB"
    "Aba6AoY2h+R3/kTkmwR9NtguIs1sDrNl64rGWtA8LrkIMdJ9Ve7uQXFtL1Cp88OHIDDrl++gryj8Q2QU"
    "1DT5pyxiHauBucPSBZqhn6CPuo5amlcCDd/mIfIVVm5RyqGR13tlJEfZKCBfcCSSBgQKaFHAmoekzm0N"
    "jndQF5fzT1Tm8QSSG+SaxqSLaGsY2KRDi7nvXTh9jA9xwMroDmgwwN3t+TRrWf1IAyPz82SNZ4pVC+n+"
    "ZPCI1O8apPdrxN4U5VEZ4n9J8o65DDUh7EQG4uoHbDM84ktU0Lm3L5Sxmiy8QnlvbOTFUi+rvPSJcyva"
    "VDD7aoAIfrkNmVR4eV8tn8CsMobSeNBiYn/wPIBvApK/hLMnHYjD0MexxGdqbmEJgdv/ri28AdtB+kdg"
    "sP/nfcP+5b/8MwskFf/7d3wZbIfAs3RovJ8xQ9C5cf7+/KghsWzHT0mVKgPN01U/pfKrUKqyjkPC+XRf"
    "O5M//4SWXhaGcQQ/9de69pLOea/N3zcY0/QrcdCDtTY98pbV/N7pgBEw8WylUCBgc9o4GQn8D2jtA1tv"
    "kgIIjBgKgKBO4jQB8617Pd6f9Rd8+57KzVLPIRnlfrf8hcygoAWpPV2Q+sTBdyAMB+biKR5/CpPvqfQb"
    "QKLhps+OObz8ZpspfXJwBZbyuRBCaIZHgz6DvDbS8jy4/p3IbN1LlCiPfk3a3GJsm+cNdQ8yVTg8+WvT"
    "WjW/lrZHYyVphcoDAEDRBdcBideZKX5GX/4xDgKm+jd/LV+qvvKC1dZjQOwnmtYPy4iCw4kQ95U+H/pT"
    "024xih7L9ZWu8Wx5p9UbCrdFr32SVBmgBAJJSqlr5Rfd/d3jvPnYoJYRkWbR+KkwmhFOtLhFVcy1mqhZ"
    "VGqjJWqL0QDVXTzmXE/mWZcXfVWEBi5F4vVqptLh8HtVLeLVcT2NnqJolhXRErfip/q+avWrMRVn2c+y"
    "SmMz824nCEfuz2nW0b5FMparVXLE8g3NLfhDVZXIyfR2imtc6Ygqrm8Qw2zaQBmFwdymZDqF7gZPYRG6"
    "pl/qt/IPU3Qrp8bnRFUCwdP6nUvQSqu0RFMdDK781w62dLHEqolr+pmZw+NXy9m4uzMNXs7e2yFQ00K6"
    "chJvaL360m/1o3WS0G6+EtUJiJe+l0Z7poffRDhl70TpbvNiYecCqzj3ObLGASd8ornwFaCExN8RXGkJ"
    "E0UONNRAV2LgoHB22OEPuchdPVeAG4gH7V0aYuXPYXm/S+G6/uwXZOWBd7vpqNL36srlwqaFOGirlV5e"
    "tctp+VYw2rliQ5LtP1/kQgQKsRLF8j1b8cFz+6rGGWvYNmD6GsQir+HXR2hLKm7i+7qtzLhBmHJsxagy"
    "Zl9GVFW0gVfi6XqqJfLB18BHIsf5fEjEyc1CWvNpxGLOdd8DNgjHYcO1ppJ+VZWknEMXFvel8wSakzlC"
    "w1+XOAlszxpURVdU8qNotxakQ0Ub/grq/SsmHCLGwIsPmFhIBW8PyFaS0uQlKobbo85tnR8gAXsBgmDa"
    "AiAtTL1JAyhNCnFA9ji2pHxUxZQS2vXvrpajoIFV+nfnT/rF10UztmU5WKsJuA5t65V+oR1yeJcHUWzG"
    "io4oB/kEPkU5pKFfVpPtgKJPpPXNaAfmr92dUXZbcT8Vqmqrovf82O+8P5glXyEk/zyhMFFEZ2bbk1Eu"
    "Td/BNQfdVHI0fR4ILB3g0aM7KYnDzwxJ9IU9hucnmVEw3k9Yjc0jfP1IBT0IgX614cbacmTMH+MRlh8R"
    "wEE+bBtwvtRLuBSMgzmBdlgRfnC6IEHzkSW+JCiQumR8YuMHwBvliRnaxox0lL38rk9ujNseDzwl4HSI"
    "HOMszJxShTLS/bV9ZrOUyXj0gZjteD/JLtIruYvl8CPa91KhOlDUSPUFHc0pwXxfzHdD3Lyk7MXY81BS"
    "PRwS5X2EXc5qqmrsL2CTBNPSGmapxt3bnYK3Zjq2GI7nH9VKeEbQNnsa4UrpA8SgG+mWARzPDTTKkO9x"
    "PiwaEi7UdWCijQdFfj5mmC5HPU9biCBoEMG25ztJFbTcBdQZRSnIuuO3e/inM9rGJwlXzgM0Zg+FSmpg"
    "5TOj/a4+2J3+ngNEn/AEv+/wdRL7drDWo99jmaoQ+YoY1hntJ3iLBnNMSONyvesNkyIcb7PMeAr9LkVp"
    "Bba618A6vCMpNVA4eLzVvYp3BJ7qWz3iMvxioxy8/KA8Odejp8ijbf0cia5xBAV0x8HaHAPkFyDYVKpy"
    "Uf2AT3cFOYyQN7cZLmkvYBGZzwGolErzL0fuxHwfIDlQAkjnJRayoXm54ucfLLD0H/8Jj/5av/+5wFLw"
    "uXLf/rPA0n4/FPYQUzmh3PTnMJkqqMaJ9veJrzrxW51JFeVsyfJJ4zkaqkhOYteLy9E9w1qj1UtQ8mNF"
    "kSE916Gl89UUvqaVrY7wTTdiIzRz7EmH/cgTczqfGumIhBWmlj3iINy3Iy9xcD9AMC/QowrBE5EGmXib"
    "QbZSAHR/k+x9uap+IAQsUQUR5RnffOUIqrYe7MrrB69VEH/pklB43exHG0/QIWppsiqDl7vtM3Z1nzCI"
    "PSxxYNW3jbIAs97qJwFTnMXTqjABQiKCmkJ9fkhALcsDYAJ2E8KFwuBxnKk1r8atYSQa0IEVrRT3c89v"
    "GjfmmiRkgmrPE+MD7kqPvdit4XkvqSPwVAhz8DrhCBdlouo40WunXB3UW/Dmmk3oLjT5UjNXBNNbNfNH"
    "4n1mRpMD1ZH2PcH2U+szVJROYDwYSEXBO6lujJodv1kJjR5XmfNlJRmhnv4iO3vKieWxG/pjljbRYGtk"
    "Arx32036DviNAllh8d0VqrbseW6wQYALfBfhOHuy2z5wubq5VUBs8bJYeTyFHwemcHXirL4YxU4yzUdR"
    "0wp5zK6U30jy1pfaC43dzBcCieWO/sEz674SNC2MsDf+tIuJ8ngXJGFneySoJwIKL9ZiPPKpp/WZxeI1"
    "8KJktAgBePMTaJrjNKVXTfvjHCKMHDC49T4KB8EnBoKg3KoJIXPzyInvQwrnmZvB3UGznKSn8/XPpfwt"
    "yE968dKJ+lZPoydx1MS+x8J6n0T4LPxaEA7h0RKb5k28D5aI7FOMFpTlw7yqCjwFeKM0XGoggbCQXxjv"
    "ZARXSX1A39up+2RIX0yWSRuS37ZKK3jlOvjBFzZ4rjQZBIjij9Gpwq9uPMrLNhql+AScfjuQMZGq2juz"
    "80ha2v58fYhZTWTLl3wFZqJukkK/Y1gO9cYkkDd/KzMZpysPeUHO5DNiyxWHcqnd6JHbFR97faI8+/1R"
    "QR0nhDTwerOOOLf/yhvwgUo0TMOB8KhoRseblyIxuZGnIVcoOMXJlk4AxgPIbwLwM+m6nI501bI/JJia"
    "RXlr/va3KyrwNARQMx36CEsGRoBIAUWLix1+GoOBC+V7adboDyxXAmqFgX1Yt0WzARE/Jmr2vH7YVgwu"
    "5CJuATXnzgPQUHvDJ/Rr0F7w1p+AySuaJB352Qc4kJNk+C7H0879EXy2tYDgCIiFFjgjJj3+rJx2xh8Q"
    "EOMW50J549J7dH3uzVgfJP7lPIb4VwdUgNqhVHt3i0BRBFpo5CfjbtD+Ylgdte0oB43fA6+SucPFNPuH"
    "ohW6wvSHYuYtaj5ZqhbKz4QLQtQZQ3yzJ1HRDRMbstOi8H5pb+4PqY0Ij2PmwNeCJ5ly6ofOeZALB776"
    "QbflrpZ0Ysx8ZN/oZrkgWGwvDDKdCvKzU+yX/GsVhYSPefjoSLSy6FnQ9SXRGv/ATRHMhxxS5kqJxFhH"
    "O/zioW2lLTEX0u/ijwIj5On3IdK9FeL1TizOoVpRAidTXJ1zNqVFWbbv+fplb/Lxc53dI6A6eVEwH06n"
    "XGeMMYTyTtF2ZTwbo0C/hWUbD6YY5ZN2hkhAehJ5ig5W6LPLVK14Xtzzcgpq97YHf3Z/5KyvJIugGCGg"
    "r3qMynZ7181IlhmcTVU/ZWoVzR9dgf/q6BtiEI7OTIxgy0YUFtdNn0zVFFhV8VwOkmUXcB0pUNQj0c3q"
    "vNVu50zIWDwmIoN72CuO6oA35LFNTF9xaUHlIHoKi/FLDo0hFfbtTgtgu7qd+TT43F2VAVdpYtslb/Bi"
    "0kAmlHDOf70GtcklXD82xFGsFoOdSHdM5mGDzrPTGySyxhUcMQr4n7a+OvAG3pNon5rDra6K0pBuOpCH"
    "4mlVfmLnr9nRud3xWrdcMNciVjXFBmktGXj/RgiIRajuhS3AWfJPkWuMcEAAVIslEWnTXMUsdG30A3G/"
    "7l74EYVGOewO9QdsaE+PHSk8EoaM/C3dOiAa7S14bSYR6izxjd/YkwOXUxtf0iPY8V35sa97vM+Xv+i7"
    "RbiWButL/3burTzPaGFF6UukK4emCTFQ9fnCkKsHxq8v1FUm3p7LM3i8xqdl1Uw0EXQ8IT88kUtWFaLx"
    "WZE7dXhVtwtnl0IYq/IlC0fie3w4O0vjj5T0kqQ61TPJBYU6jF9JU1xkNmrZAssLdf5Ccwn6YTzHVL9C"
    "Shskfl/EwsHpt/LI8LfWL4dcXDSD8W1T3Moxv9hd+/DadPxTJys8rtKHA1J54uyTeLBVbL9qczz1G8Wl"
    "OO/gV7hronV/nPfLIbix4AvzNC5gwGp3CDmQbXb3ZGzxXnlxJEgKccxpbvuTL8uy666P4gFZiputcK06"
    "QtiVqNNkhoh1iif8s36SzexidsqVJmTAYjEGGSEZ6Q05RvY3rLu7hW6QHG5ARkoSo9ir41sXMI/RFzlN"
    "x+e3newDfQWMzI+XgRY9hes5t07kcGRJzgjFih22QwknCpeIpNlgTznx+imazAAKQRaS8rQ/2m8ASnIG"
    "z6B1aiI6h6/7WP9oMet/92//uZWtZP1/OZTvTxS0sZdI8SUpMIB6CO8geiJFC2zfAd3oqTbimsT4vJhg"
    "zXJdT4OtCQn/Wg/NQ2QlOS5rUc6tRyQXVZbZx7xl/Vgp5ZlskJgz2rO7cmtD1pjWQPn9ln45BcLQAO6A"
    "z0KF2xuoa0lxEsX4PPuUu8PggoDUjC/VN0qkWQ0vynQgcAG0yjmWgirA8jvhQbN3qGSYXx0iDA5HPhhO"
    "giW+h+mecA+BQydptNKz9TMH4Bz4ct9BOR+SPN7/2MZTCIgaHws8kNS8Ly8HyAPXgzvev96S/zxwLVEQ"
    "vl//Sc0DV90y237dbIL3cIRreIA3F0Kn3o5PPsdlX4Iu1lLnpd6yooTh1mF4NBzpbg7WaIDOEz+YhS5c"
    "bdi6eKb8MDzV7a2fch++w+MAiUTfhfElyNXHQ1NtH6rdXvDtWGIdWhnF4nX9hfkOpiAkW4phm8O3xd/8"
    "pw4UjKIgMpyD0hXmw5NF0XklCB3LsQOD7733FsUxxxoFgliX77+XZFwqZCowSWD9onCBQWao8hidGMD3"
    "fXEQJGFJeIPEgXXppnY5fjAzGtwliMMoWJDAgvkIsaAuR36xrx4eT3Cg1wqT2/Ds+MTRMKXaBfqgz/C7"
    "wDwvUw0EzkysQdDenftN2xSZgnFWpBCe9AB4YEfNdzf+jmim5zoGU1iRlWO3oQSsiZyYm+5dGRZ9Fpox"
    "qPywHAO8UuvcUIaJhheocQqwfdcDHj5RgUIPur26ajboGlrJc2/dgGUgALdYrqFtjhAeO3jDxvkjGLot"
    "nBsugpApnhwbKnjbB0fKY4uA/AmoMi9RrvUMY4LL7Ys/hdFl2IYTy3pqOUF6/i+fMYqC1gC+htJMY+wD"
    "cNl3AGc0QcZquL1SiV11xN7EFMQmOjAPZhTq5MFNUoIzW0Rh0nuHMkXoz5ZAANp6Adg6/goVCVPeAgPZ"
    "TSJrbCoCNFY/RCDzD4kYwjcAPOa62ILwNPiyPP/bOWR4TfzAabojZ5u+f14OTnpIRLcbBKg9bY7OVLcs"
    "WbbAcJN+qHVZ3NOaG6k+8H5kHKf2PUS2uN6oMNRvKAMCp+YTyk7FQdUX19kVr5h1efWlII1uR1eEIoHV"
    "VYmGoUgW2ymQlL1heMxRAFa9XRPmtnvjbZHnodrMqeFxJzkMeDN6y5p1X4oJHx/Q/rCVdQrzwvOiIIWI"
    "wIpbrpNEhwt7ecHzItBzt1kKlMhwLpEMhOz0HcpSo+jObF9PVbP7Ret90ptZlFPIIWkdvf8UnK4+tI1z"
    "+DHB65cZmMnok6mykzBGOXxV7mkOJTgNMKIt7reqbDXTVIWjwU80XwRbdNiLoQ/HVoCJfk1S1ykKU4cD"
    "LH/O5e9u+8n9xTTDPJeRCz25wXjIPAvWwQq672JoI1b7idLljT2aojZuwlXQSWPphva1qjf4QUsWWIEz"
    "8/0d2YY82awbjEJ8waAJh3RCxVOqHyJWYkDuQS0/+0wCpOkq6pylDpWWA+KdiXSbQu8EQcZkosTeMH90"
    "d0Nm/6sx3XE+b53rGxEGBZvcLYO32r6OXv9kXm8LP2k3YnDAbgZhZw9WRiKU1Hq35U9DiRzKTGBB8w7/"
    "Z5cIsGYAkIk0/3xQlw+1RXQhexrN9LN9ovvTpgBbiLdphB5xdSGXYhMbvkGFrGWopUuImb4JbE4WG1FY"
    "bHGQ/R0O7mUArFwAD7L1CZgS3oFDNSDEpsu+q/NL+5NfNG/T7eRZ+TH/2dg+xrMdrPwrC09fdd/m6n1x"
    "ncrnmH84hnXoZ6DtXokbooLjtIGt5OdlbNoUAnqT8rmQBT7OqZ0F9yhyKVJwbtIeOBvPTzlhHs62g95V"
    "YvnQnai8eY0xK5Fv1qjMfZogqpwGK5H9RZcezy3f/7RzSWGzRepoDrdAAC+EI2PNN//sYCAaRP5GHTHl"
    "w0Yx7oRgVdshdCjLgk9veW6kxUorwxyPxwt3qquMKy4LZAG/B6F+BZNo5LIXfPC4s+5N+PL9o3tr/372"
    "Cllcb98kAfquvUKhA+KDNsMQq8xeoUE2t/lx6JUcr+2dNEqcVvIRArbNufEpjyBUVHfo2jnXarm6vLck"
    "0Ap1gJvL/G1I/xIiBa0TzeWjn6lVW6SiYc18xOF+g7zoSOcIuaMjWzFFjkoD14moXOAnlZA4UI1QyvQC"
    "MRXQnHaLvGLELTKscJdRkpv3UQ+jI3OT2nUBxZ/gZ8EQe9UIw0ncTlNcd6xsfFMNfu0P71LiLbubVJPu"
    "MzSs9lUfCzlW3EErcFP/7cJFfB0hZIRVLL8y4AMHP/IkBs1OrOnpofntlbCB8bFx0w0hYPGrSGF+PTOg"
    "jc82336GObOS+KFXF4/nxvned97sVJaxIibfv9nHAeTFZP/MBUVg1425ODkztx8Fiz49wjl0vbVN0spX"
    "1/5zforn1wmZ971+pvE4Li/MiZhhLpkeCeTXdQsJM8h+ZK0QoSsOiTgbeOxl8Ljr8jxSrWZ9oahZA2yp"
    "1kCsk9A4JsomvFbVo+2VsytFxL1/I5qNQ+JKrnG8Phy9JtEyVmB9c5DgRZNcxaQydDrWM+SQ5RaSGK4h"
    "xYTppUQpz9cqHjSpMUFLCRaiG0chsssF20zPLhyNGWIATlVZcOdGKx3JQSaJ4Juo0VOvn1YlJJCGCOsQ"
    "gU4zLF/NjyBC7qVegTubG3S0Xhvwm7Dky4cIqmSHzNLVAbmGj5HKHT/rF25putFtk4WvQ396lv34IzMy"
    "MtvIjxXyfdq0ytVZztYvSehnBcvvbvfV0HT05aYU4HnihVZlryzrIwPFAVzBbtD/KnDEmrd2JXE30cUK"
    "HQ2DXv5NOIlVZx8sz/b+1nHytEfm5eUxl8tUabnBEkg0R23UGNlXMAPCPi1g1ng84wnrroVPPW4q6w4m"
    "T4HoZWmfbLckml0X5QOQpPYi7glpi7bDyI1AcO/Esge7Nm3HOAYsRbm7LEZlOUp4c/cmkZ1s6c2fO/cd"
    "2DKmQhyh+OtDFjpNgSbHfa+x+B4EGjK10Qza7PgaTrjx1NfS0MRAN6dp8GeNYz3oQuSzBGKPaHo3Lyac"
    "YBg4fI5fZjGSbde0TKJkhsFYH/dlb+07Fiyy73AdPbjYJ8tWXIa7UeeqD0vqsqoCYWtwCUDAIEYI554D"
    "IQh3s/x5KuuX05hMxQkTs73i9c7vz+n/kD0JZgQBdYbjCBSQzx9Vms3pve5cj81onhxXfp4vja1m/X9B"
    "lL988pdP/vLJXz75yyd/+eQvn/zlk7988pdP/vLJXz75/4FP/ut/+Pf/5C8o5f/YmQYOi8+VxXYI/tnP"
    "lCTaB+FLFCqG3RnXTU4TuhJlJlHopKVrhl9kLugra56hwJlsSxWcz2DFb7E2dQxeizDlkSb0xJXWzTEU"
    "nmH82WK9lerQZB3BndAI45EhIgcIDUyJ9kscKXFEPuDtYGziSUaSGIqWBoHmAANW5Rec1+/DRqzmojkC"
    "T0u/KSDfKrQ4vOh0i1fJVaf8wsBhvjl1v2129qED0E1U3M0bVfm+69mSlW3ZnNKKp6f8kYZvzUGk3h/G"
    "p9auOP8G21qs1SLgZLml0/7bKKifQ0HlMJfeDdRhpKnSm1uleTqDp4Sl2QQhqWX2PeqAz9Vn586b/VUA"
    "b7ze0x4q2/YhQ/6Rbe33G+3knSqm1V3dzojKFDomWs8klhXoIi9oaS/LiQxe0+funHfBcxl+E7eFTIRq"
    "hXK0Xr2VY36+shU1FsqiiF6G0Aeyx/G2ZoHgiiI2Cn4ePf4pvzC5e0drUlFbqScLweVZxtXVkHhfECBH"
    "hnQwIyoriibpEcyUJ+PbeNWlXdj7wTcvrlKCbS56YTwtcWyHvdLPh8B3wj+LHgVVN14THoDUmwzYkgLE"
    "DpknxtqKFauF5teU8OgEcfSDEyo9mwpOF6QpuqHavhICF0H41QDz+gn7zaAydVjHNpY3cCnPQ3xGRGc/"
    "ai9GX1ZkN++rZ5qqv+TnlCrgifpViDb4POr0EM6GeNN6qPnMzzHLVlspP0jEE+USvhmfUNem8Z29k9nE"
    "ieNYlpbwATYPygX4+RzlVZWwL0l4A/ureCovagX0HkVJDsPzKcpj3HOOxBDlIX3dD/sy+C8cwYaU2WFM"
    "4Sj09HwqzpH/yfMBpN/psdITRSjiAQBAizGhNYbGdH5848ib6MdjSxK7rmi2+nHSoCWj1YcFRpAX4Dot"
    "cIcsxcFmj58wP1dj/7fsuD37RTNzcJS8dZ8w4TUK+mZspXby1rKdoNkqRHC7X3xLHzzfL5hn+yNoOA2W"
    "LJOeulBl/3A1sT+f6QW74I2X/ZbDWFJlgtb6yJ2yUE60gXyYT8edKPfYvpvfv66QAn6c/PYNuFFzZufK"
    "0aY2ik/5y8Klu8ECAYd5fp1IJjHJNjooaBLXSf0GDAAQKhVMDAFJbwPxkaPey4bOs8eM7lf9im46cmiL"
    "/UkLk1KBAYiG/ByB3TCSRcDfb9eiYBQuC/+Ivd6MMoBEL9MQAWqxuIEzL3eFhlkX7p/zRflgCj8LUQ0j"
    "OgB5A6I823rxmCCbiBB2/41wPnex44NrJndWjvWqnkDLSntJNZ86FrMo5VfFd7MW8BQaV3sZUNcML5R9"
    "TLwY6gxWr3smStNdnrnZXPM4gNsQW+b9HJPr909wfW10VdvLztbpzUazdzeVl+oZ6HOMgnnVoJNuE4kB"
    "94nba8fo7JsfD9TW26tO2irRDPl8orDvZ/+ez6lJkwlO1fRbNQLSGBegI1uINXmmyhxBP11Np5b+wmEG"
    "5BoGAQaXG4wZFUbB+Oh6cb+aNfuxr/PzCnB/DznkzwHBLk/8PM6nbvFXC6lC2c8AY/6Nx7ql63OJX+AY"
    "44gpejuxj5d+Y6kfzDFiMteWqA2IDb8zGDVawyp6Cq93Gkk279eTrEQI/lPl8dQJ7oL2L9d+4Ah526EU"
    "1cPUXCIBSC8hs+ztOGTbXzlfEWd1qTKQ6p9sBT9eityonzbUfHQmGQNMYe/ZIMHMVWTO+bEWD1DB7KOC"
    "cvRrWNps1EXJDlt0w7658b+xd95K03Jtdj4gArwLgQYa720Gjffe5YqnpmpCVU2iQIFCJXM6OoI5BPGO"
    "aiQF8yd/okBf9piqBva+77WutWnY9qomahfKm7emOpHu35S5++JDDO72lurlHEeNkeAqOZHBVa19qGPO"
    "RBajaeKGpNl+GFxY/Ggo6YU28cbZBXRN6TcPE9i25Etl1cOaGj1u9JVx3K/AsjXxDgz716G7seXT6weB"
    "B21xUlq8Y3M1hkeDL1ec1Eftq87adT7026enref6Zd1DISprPLdYDKeSyksIecoEbd9lpFV/5IzWpqB8"
    "GIZ621yI6Fwx5EiwROPyNwGZbi0eBZEBWk+1Gr6c5LisSoK35lXPD1fcFohiLbWziM/kPAYl96/vPgkA"
    "i7CCsD+1NzlJcTFrTfDInyjXBsZk8REw3hP9p8zER2gxLNmweAnoN5BDCo4jjilgY/SNa/FwZfZrT7Ja"
    "pAu6fBuBG1FUVwZw1obB5ChFDMOdntN9i4jdfsy20sYeZi+ef6wuNEs6UiRX4/xQjJlweU4UZBc/viAk"
    "CEus8hRW8bMeH2nEUNOpQpPyarDa5bNAV+Rp9X/nF3Y7ei+vXleduKqEdmFHNCin9sKW0YOgSXjbpW5n"
    "h65XgoyLYQcPKFp7+FfQX4FjS0dPgqr70f4G2mpcxSZJj/4t9z0zcuZKtw8PC0NMFCv5El0NpzT5hozj"
    "eQ7m1qxZMIDPNakWy1az6DaIzpyCuJ4a8oR2liC8tX818c/j6fU7D4X+9hkPvbX7Z9E0A43nc184mkq3"
    "XU9wOy4dkczuq2cPT4mf6Vd2FEEDCjyFJon2uXfx0a7y9Vh8Emn5Xg/GRj3v/ugl/eW9Rl28WgH8ohdx"
    "+ejSqbC3iT6fZlx3ZPGB56e9TGJ+kZchHzEq7F2YYvqnIj5+pMYkG2vCSc5Heniaj2x5YHlekri2xMWx"
    "ZC97hKfsbUgu1F3e5h9hTqG0Pm1UKsDafGBiQzIFvmxYEFL5nsNJ55PdfxA6QTL5DlUJbZPa7krZryO7"
    "bD+RHmmnUvHqfTNIIvrEpr86jfGTnyhB01nn50xgb6tYe5/zJtxIO/8dX0qB33DQ7asX2po/t/SQaO2k"
    "2uD99RWnGtkSDw/xrX3O4a/f8hzlewqAmv+sng+Zm9DrltBAv7YoHa6xDKUsHaxJ/fvZwB7uKwiJIGlB"
    "r9/NGG98+JIwhmq7vGvdLoLNjW0JQuSgKJF8rLc7/qa7hkbgYg1rMteRGQYBjNT0JRq6pUdJV+FOMRYM"
    "88jDzdrB/IdgT5gXyNsvF9g+G2Ul4v4bp/izmcUSvYKxF4FTKx/4DRjZ6H9G8ChuY/np9BHmYQ32YBFO"
    "I0mHi38/edp79zXOmQFpwXqXZOVpQ7oKpeQElHO0koabMORlr9No1zBsJ+GCKFj0W4LN+OjDn+Ilu1x8"
    "oTIC2j73Mepr5N6Tx89gJ8zKYUsH0FlWcCHwJEsW7zdaLQUOXsPxuACw2EtAAUb27WE+4Pt88PwHXOLJ"
    "Snii4lntZevv784jiWJErl3QzHK4nosbK+L+vHfS1WpSlP9suW4KYpsjGC5ankWZ+2PsU6VlDTN/uTc+"
    "DjqRt1G6OZEpjJGYXZp8J7dPwr+OsSnm1G89cDH5I6qUiYMg82U/mli/IQj5Dx/4exPQX/Hnr/jzV/z5"
    "K/78FX/+ij9/xZ+/4s9f8eev+PNX/Pkr/vz/EH/+9Z//6R//nmep7X/PP4sfBsjlwZefAfhF4tjwjZs7"
    "6h5eFPHc2QSBh+bE9lodbCc6UJNe5/oO6MvSl/00dRTrSIJzaop6kjarFZJ2nitWuNvbkqQJ08VBm/l+"
    "mWrLutjtF2FvmWR1TtMn2aCHQa45zDiZRfIcqgv083T4QqYHag7rJ0PKX3k7xBMPgDtqsf7AHcrwiBYZ"
    "0si8uecgEYCE8mJg5SMTZoCxeu1t1TW+3QrEENoDk157L/2j8XxhrTJMK3pk8O/vnxLcQhBh7ZYcPiQh"
    "fm2B4aJtXBiivJU68FV9wsBfaedAEQz+7/5KRptOBdTdallNylV6zQ4AzFIg16pNGCeqDMQQV/+9I/Zz"
    "tjyr3NoPFc7RXPjDX78mEEcd4e67PKKMFUma1czsnOYkWi4or5gSoGEl51itTDXGbFhnfpWlay1djVN5"
    "c4NELmwjAH6j6ZOhPluHh9yEkUKMCQEg4Df9MWtuo2/GyrJVgznQb2WfYdWw9CDOCWWZe2TYc/rDpd1s"
    "fdLz6VdwQbeRQl4UYYt2YLpTkBQCA8ZiIXNYRcg2JPifNyw+f8e4WLLkh+VEAIW0sk/FWJnXVNsqre0/"
    "p6c4sBw7o5McIHwsFvqGwOqz1q2Pk9U3griWGUVj2n/wGHEg15CfU684ES1ThUeYm7F47wXZn/FRDRsj"
    "elwlPhFq4yvXlMLv7T9Jap11xjMEOY+AVimxr80GMpmyFSyzpJ7ZtKwshYnTuSfsy8k/RmKUk+Xsk2zz"
    "UJ6tKY5fL36Uz0NaWuF+ETSZN1nb4LWUFOYBPkFcEAMjVw9RmvYs7CAYHsGLABJVz6+MWzGrpeZOMQ+R"
    "XLHiFfKvRGkzoYKNIn8oiQnjw0xlNT9xWVfll/usRfod0uoI2y5S3FIvzZgFOpQPSjFKR1Nj3j9uk8c2"
    "yov7LwQCQYVSmNlOFu5tTMxAaDBYED91kMszoDlXGl/652CpryfIOiK+1WaV8tz7NlSZJtRg6JEOj21y"
    "p7411tYtiOh8kDCQ9A+UW1HUxuza+xqfD0eWYF7t3otkyie0KRjLwdPVRN/Fn1Uu0CG7eLthRTsoj47h"
    "eQgw0EQkeJVeLKnPFUuf5h76rtT5SIwkTJCqAW7QMc5v9Com9wm19munnx8ARGKrMztzlhDfSiJ5sm6Z"
    "zK8+UE1iPo72hdu1XmXf/EB8dBpldR0MWZqu1ozS4lEsLeSORvUbHpV161XeZXSCcIp73rMaay5pLptz"
    "q1e3SXM3QT6HOVaLs7DQZ26UI12x3QhRJJpwdatwrWsPUOtJEPhaiS0NCZ4Wc/5aT0GW6lmssYfk0gvS"
    "Fs2H8PZwG2OLlvGliJlKnG3trQV8qyR+w4UVyeNoPV8RHINikN4JkszkPCkmWWnOdbAriUT3zJBpKPCL"
    "ajewlM6avgBfqYCtnxa5nbCN+oB3Tz8CL2EoIIKRwKdumRNBl4MYnAVqxUYBZ94ChrtE5wneloolU+tE"
    "S7EfxtM/GsSRbErelixL3SIkvvldd8k5NcGlyNoD9Ak9nO9J1PwBdAFJIX4KndgJAPufY5Q+IplKYh03"
    "dzM4aAFqw1Fb9EpYgzOSYTlwdlH9nR/0GIx8EzFQySZS0ohSUJ9do1w7a3GBMSnzlJAqdMamuxrTR7Vn"
    "zSpCdLfxk44PH3W2Ofq9Yr01ADjpw692Rq/i+ju628TF07dyE/F4eCZR0JtIFiBBaSU+NLh1hrm7EtFk"
    "jlnAal0S8Nmnq3BxmnTZS5v5UocCXt0FkLf9GNuRgOb395bgOrkVPQFHUHc0+hsVy3OkZrNHw5YYB92a"
    "mOvrVAspmlUitHkDBVF66mcSKIAKv9OEjPCQ3HlSGf0UXIj95oUmq2e7/JjPpGim+8latUOKdIMuJexP"
    "0s3VAIWO8yv9LG1ZbUl0fFSP4GoSFVZlsCJ3RLac31DVSVg0PU1rfBoQ7YcAM1/LPB+0FIGcTlBd+3yk"
    "nAXUS30TaCjTwWvMa2Suh0BmRNh+5J/3cTHOdDEJYkdl/gUtLNvYSj8gKoNrry9AKJrdyxDSJIaBSB8B"
    "U4/m2k8i9lssz6a1FvVRlE4uNH9OdrR0RgNMNbA3RwAt7nn6YJkP8NN92pvs7yIQ3SMtPep0jTH7Zccn"
    "ZEgN5SDvZGQ0+9aBZYCR3mjIS9COQOrR0c/20SzHp4HCSkkC21GbuomdepMZFKYhVdyNU0c572xFhhXb"
    "LfwRy8hAc8tNXnwH+ujYHdTW5uUFHtIriEzdw2BD4VSMQSoJYJFc56d0V2FIvSSQYBvRebDxSYNKDZ+D"
    "pd+HYSvBuYSl1aiFbkDS2T3M00zIXh2MQ1JoGKJsSGvPuPPQ6NI3/zfFwoDeKLSB1oUwFfVakLL4LjfX"
    "R7PrrbV+vTB8yTGVbUb61ZCwA0nvo6AcHX6eRq2xebIx+VJgfH+gdIfWG35HxCSBIVdGlf/+GlLVJIZn"
    "qM+Iiy9e/7x8Qbvx+C53tH0E5JIJRDGazB8ncENEKGvaqBqGDqZ7GYcBOFBQC+KOL3ge51FgSgfUQReA"
    "/N/a0+u//T17eiXe/9nTKwzOlwXDb4Fm/aGuWrf91G3LCkNoxCuuYEGcQ6VshE2cVAcec4sZzcabW2f2"
    "TJOz/+yC4Nvm5njy/XpDLPmb8cVrnurYBP5AbcOrfFpRNYTww8pzjJX0fPoxQpVkFFID8/wPL/+h/mtO"
    "O0f4kSta7GAMHDlIDsh6marGiAL3ec1IC9lyi7Q7O8E1uHmWXzpv7G7qUAfsEaJ92xCQMNJsT6PlG2mI"
    "38U2rLseqn4qjBJVfxMJ38tZehlzBikFRcFfbDH2z/cUv+Xny6GR7q/YKZx8US6rshP7MPuxP1Sm70X2"
    "K8ELs3xUob9jPdT7J0MZf2epLVh82swhT0iV1v9Yp+YLsec0+C++UBHTnqBLN4R4DUdzH4bS1sfCOO5j"
    "QWa7bu2P+sZTkrcLETqEiVlXAtcK1/QGhZplWCt2y2ZFwXfG8JBbjZWH1E18o53bdHB6AXw5NgBB8EAd"
    "RC/Hkqu7vcvXgBWzN+v4taw3CJikpfmcQJ51qfho3GkSRw3kL/cPQK6SQCLCakMO+HNe09LwLg/rQLqh"
    "JJ0wilHpMqtevE5+em7vfuwzfDzGOMw4UcsPYvIABO+Cjt9+koA8tYAVgGu1nUpDU4t+LD8jaeDwWW4r"
    "AwUNJGMcheqB/54DuCCK1vrn/pZNXZ1U8bypr/ZsQHPQKeimpCvVUEfI38z7PI4qOOsfVOzL1nlcI/DO"
    "1CT/toCOeIx1DYAjv7/AxnK9fK6xOQBQBYUZgUUF/rdrzmA47AQFZPxXI0cWTM1G1DFEAkQRZc8W8e+a"
    "A7KeEuymrugo+Hz0dOtP+FQswRF0F3rU8v4haUEwzH1Vn91c4q2CvdMBgnuVqdkYaVOIlShbEXrVuUoq"
    "S2lfYvIBlpIbv9HXhjLOswB/+lYnv062VZedopSZVmiDur/jiC6EAMeheRUn23y0AgQb/AVZ8FmCIvD8"
    "zA1921F+Id95vXEUPwCOPb9Qt8eM426MbU7x/DS4NkUJRc/r6414Sc+Z62N5ckaIuJ943FJIokTwAg3a"
    "LPlFbWS2mR7AOADc1MiTiWgzfMcPQtfBldIMCLQJAJq1XAhM/jVgAQaAYES7Gzcj6emfDdIeBAXC7sve"
    "66QIS79zw/0o7Kzz4yFMS3fi+oVvTAXD3uDQb9gEDx0UMkiiTDFeyVqN3vw4X3VxaCQPB+vYpQVALOHS"
    "CABtt8jdrsF+U9nw7BHtndWXyFVhV/B04W0xueGEIF4Zkckd4KauhlFRnnGnJ67aDSbf3AkB+OFw8pKb"
    "9hHwJnOV1yyOmaFrl9dpNYC2x7/jQyKRwk3W4FpbxmLMb3OWPQUF88Ru6am2uNa7xtr8JGX7qhgorxkO"
    "7EV6iFSofdZ1iClQrQvMlGVUFoz8kz4qSq4veNqvPyjF8J2I5Dz4/OUCa/ItAIG3NCB29pExOods3hUY"
    "IMZkmgqhCnY/oAg8GZx5PvTNcwbjmlfA4LYlhsOTMKoaU4nEQP2kx+UXFOWda1qufOly9A0ZnpPHZGzI"
    "yxVuXYJzjwZ3Q/Narr/tb3r65JFq+SZ0pvribKSa6U//SLPiDPHnjRQuBCK/+GufSufuXvAOc9x9LShU"
    "zzDKwWLfnEcFyrVkT+yn6Oo13lPVyJ14kTBdpG3n4D+FEt7GDQYhNZA46eE3l1j6ncYbArjO5G19XEpJ"
    "hC20FZb8YbA42lj3jSQPuOA0AN5OW0lstZtXLhpjECO0HG28VFOsh71+tZEb6Xp1XIu5xil1St8YVoQQ"
    "LTf+7DsW9ZokBn750GCe4NGToJsBZnqmV/1ZXKLPoQoPlKQO4aZzWgSLY4c7rWqPluow77UJdA/VCMaL"
    "EAd38qVm1d8Rp/UF22KpcwgzksJHiKQ9qQxvwIRdl3gnrxA5VScujCiStb5kedKdAF6Xd4Zhr/N9ORNG"
    "Xb+T4qwp7x2avSG9rlsfDCAp4fSpJfW3IEvD7qZBpjc0Ier4XAFAFAVpOqNw6VCG+zfIHsT8IIn5uvqM"
    "mP4U+mARA2aD4VQUQXsHIcpGHNPPYSkWRj3kjY/D6DlQjffgccja4t42rxT+lKM7+bZIYi/iQzOuK64g"
    "XpfymCI0Wnq0M8cWqn8cDy1IjsMEkiVMmzCl0mUCi1KZArdHRDvFpfPVL+N3ieeISGptJ08F7zgOLTZ6"
    "LVSbGYt9dYuNIqbAJFKsxkSp41/Q0YsosY7DEBKZIl+zkG08BRnx8hhQUhwcpP/Getc//T3rXf7/xThp"
    "cGfxn3cH0hltUvQTDguBvjqDaEvSBbAmRzcn8p+kDkRRQN44+2udy+M0+0NPDc9pfYGUxcTymi030ahI"
    "tdi6sOaN1+o61Scfao5LNTUxlkHv1ikBhrQYTDOjgVz8pXMALYyDv0JCqfdLWRkKEu/8LiD1IRFN/yBv"
    "agV2BThpaHYU2EGP8cyjjT1TmXGa4XVp5rTokjHJGyzmVH4l1Tge0VF1w9xS6OpoEP5+DuooliCnYq1C"
    "RWp+pY/WfQrPduR2Gtoe4vwbG+DVCpmBjuuwH0jsEVC8e2E1RufnlZYFtIo9oVkbgH7NZtDj2WFEruQE"
    "dGGh/s3FzzCkeni4XE5+QQT/OXS2yFR1PhWLkBtPx/an68DHoqLW+YKEno07QpR0GpWzuSn6FBI/tk4g"
    "Kh4va+nmfFDoJesVQHvsrCNP/Nc32M7QWCkBC+YEzAQQTb6FCBkjx6E/UqL3cIl9ihbnJG2mk7Ma6j83"
    "FoHkFSyVtQmqWIEFfUZuzZfEsdxlTgep/RzkpSfFJpD0nB4yPfKIzNvfT2iYonyF1ofPXxbp5T6Cgqvw"
    "s/wawV/8uAA6AlRQxA/2Sa/Yi1KvfRh/OUoKpbPdyOH9OIpuJ3pi9N7PCM9TWs+4sViGL4lJhqGwFZtX"
    "D7hnwaVtwI4R+VHmsPQg0Vt13mZ+04fZomctik0krqXQFrxmJw0BPD5nWH6MiDfinPF/3BwgVclUtrHK"
    "iQRjsHEcc4AH4rM3yIjRKHqr5O8zUomemyfPgUzeZPv+3WejuDn2N2Kl51pDK04HJcrlC8JE54qMNUYK"
    "YoV3mWCthW6eXbABe8LgpEYf7OoOF+Vp19dpgkOTKm+BCXQt63kgkxKmMmHiwg5+jzMl3DwNNaIovbbn"
    "afl5dtKWUqq0X63OEitINOVDPzFc6T20bWfgfmdWFS1c/CL3ZzMPeFa5WDoujhh1YMiOuF0YK55vFSOZ"
    "2vQt2u7GCa7UyitHSzt6prllgqc+qbrS2orqXyn/RE6LVdbCckrIWPc6n1YKlEF5OOEsN0o57sUZuqVB"
    "tJ889BRInxKKIljFI8ytWGnHFArr2adpY5dflzDvOaI0mzNgh1Xh6Rx4O8Te7aI9jMOMXgcbDnPBqC0A"
    "dLjpneZ559STJY84SjKhI3JlaInJb05xVGM8DuzknxY+R0rNVDA+szJROcs4cvy7PmkYElDNvEIVqeok"
    "usx0SC3v9p/N4Qh8EWwsZatqeUYooW3iN8GujYpB2Prwy8hJaGPat/Ne1ScjwZtR7pH2M2dkLdlRYkbk"
    "j4Vbb1jGiDK9XMcbDYm0KRwjddf6FObAvEPEbBto8lO9kmNbEdwnrqeJCsHD+CY7dVjRE5TfatBGaDO8"
    "Bef30ecDuxrzO91pNXbIJPomk6ZFkrZEA7OEcFAdHKlT4PGh14QYmoaI3LC4e8xaPLVt1c0/5YLt4Cpf"
    "budu43VXSl+EJysOhN7zvWwI0GmH3JM2ndgvEKY5ou/a/1ajsE8SINUMmMZElomQc1oEc0Y+OMVLUecz"
    "DpZKuoYZmLGzmyXhzzUfrVOFlyZXJvFIEWGE/HqQILqNXTGD0VfqDfkQX1OkDJoyTf1LwtD+9FGyD/tP"
    "bwEXRUwpub42y8y1EL+J1d9rRTjFFaO4jGD9rTfV0ujh5oU13GOySCkKFaWqAEGHsPJscP0EmQzwxQ1+"
    "9x4gJimbXaBT35LS0IA0zbkfC4YQlLw0GPriHCSsf7txfYfb9sz6jTCzrXWdyfOMZ5X9InR5ABgUt9p+"
    "6CuqK2MjCYAAaVbNurvHn9VuNCQboYgKIiJ6N3DQvRguH7ivCNW1gVX6p4y159p64X6EduZ/Fn5Gak+a"
    "64v6fBNJ4ofKfoXdiv1a1TXnlmvygzaJJxMkX+zfZMYrTcYw1siCcjrF131JbBzAgwNCBb+3x0VIMF2N"
    "gFBxTKlJAOPE0DzsO2iny+I8ex5iRbNUsTQzLiJTDSx+8lOEHKjbF7T1EoCC/hkaX4KqW1Mj2PCeBUt8"
    "mdXpw1QIaaBDfGfYw49dgP113qpheee3A+/qR3uhESVBIzmGsqr4D3Zs9Wi+ZcHOkz2zs+DUkd65Ze8e"
    "uYWAGq0PV6sCvvN8z8t2k83mxFZqLMUTjwvdzbrnbOOtAw/a5FYibolCJ6i2tLqscGAxj0ZAIJlEphXT"
    "UmoxIMrsXwSVlwqR7BNokaiP9JpLoJbgJZYM5oMy24Os02Y6GpqkYpzeQB1WAvo9ruPWok5709DT3BNk"
    "PRxmQ04G1U6HprCORGbmWk4cC0RFxg0K2+EkGZi3tIkBEHr/fkkAeISyJ4pTn/SUXvuj5f0xMWF/W6Lt"
    "V1ElKEDFWIFI2GNyMNEIN42T+L74SMAXibCX30ZWm9QV8mngjbNdDMYFBbaE78PRt4yMp8RqrZYCYjCm"
    "iyxg4VEc72incFDxuvruEPSQsKpVV7/6yOWMrjZq/EoV7pWHXHkhdDzHwHx8Y0rApsCoL4Gn928Amqof"
    "JbdBlwXYQOA+r+HygeIvgBn+cLCg5OLvBfzesWP+wzWw//Gf/9Pfs/0D9L+/DhqE4b99HXQQCxoofkjc"
    "xyCAcrCaepvSC5G9uhE/F7Dk1HYe6ZvMgKEuu9ItC5Sl8qUHJ23l8QsE8bMWqZeTTL1Sz2LzYSPBUq0A"
    "UdNgQRBscsicRADUILU7NvKCPLZcXR8zgzYY2Ua02h+4oBqyoJ7noEjsG7SZVTD2d4vWBWd3cB8y9IE4"
    "SiJgUoImj2NEi+6CjS68UOB8WbuDCcC1J4WTfHMAilKaeARTYgFhCoA0FN1u+IEsEQVAy+l1qBJiHHI4"
    "VjIIAt06ojF/gnJoU61fR3MSmXdygnpo8RtTvPh6s/suzTsxDWosGp43NRvv88bHe6zmPf3Jji/t8p16"
    "0zkGq6Kvozk8M8nKSk7uK6RZLESoF8hKXatZb36Q+wqqlrcSY5pQU4O5FxePmfvIUJiSY4KnZTHet483"
    "zqU4sDX6ltUfSa13o1z6qtf4yRsmsOIr5otMtK13WrIoQqTcQYv1IK/p4bABDr9uputMe1jKBU+aFgoe"
    "6Djnqt6svPIL15edFn0fsFm9IF1iWFAiNIDOXfK38qL7NhcPCAYpL1U8GyjQQoq289qnfJhnKXSAQSEV"
    "1bpdvchHHA+QvurY1BnMXoBzBya3BhNYQS1kU9MZc1as070ESsidkSs7TpFiEsNrmBelN5mTjsQu1kVW"
    "E1Bvj8NTJyZcasoD2fgFxaLnVX6THFnVAJZyZu9yM61LRNR2Zo14uHfQ+RZ5CNw0V2yz4E1eT2fzOWIy"
    "zAQAXfu501YwQo1J/Vxo5W3dhsTgMGhqPnJ7jLwqpvwUDQ5/m/IqikHk3vT5YPEXUcmKQ+wpor5a6ZYz"
    "ZaiSe/WZ0ZY42dF5uXoDbcE7sQ381/3R1qfNpfd6O0EONQHxm2RH1vxALpTfU2+NL8gzhmNsFgyjC3i4"
    "3rmIXNF04axGyMNcvwPGzbdpwHeMkRNtah8YfK1I6R6u6rj0ccNZtdDn8miQVaRVVd4W9KLhIsIMo/LG"
    "VHi3k+3B+wIEI0lfSdDri3K2SIh5aD4fZDHEvEdzF1iTLyhzqVt9kM8HlKNvq/cBwHld6Xpe3wMFnJq3"
    "I02Xv/qncxrqnLkXbzdqxAt0jQEtQXCnjv1yeH0gOMQT4Q20L43SOxB9loycezp9QD0zIDrq9B/cAOGW"
    "CG/JxwFGuZ4V2zZHaU2E+riaH0R66/Bu59q6uQ5H33RaF2gKjjfhqK7ti+xBPiSH4fofwYW/e0x2WWux"
    "nNY0JUDbC7slpaooBk5HMcnl0nlPCpZnkYlqxG6QhEzTbQ3hHlaY83GYaoHSCl0Z/f5pGW512lsLc+7O"
    "xyiuRe6y9rQCiH56WAmiw6keDhza0sNb2KwyGJvPlfGSh4ckZRBnuxqiPaO/PDZRfb/tPNw8fCI408GD"
    "Y3hB9A0loDaI/G+Fg221YHqsEHYP4Sn+Kp5pgsEHqmiG0HUbFGlZ4pCPkeUyWVGGzXNOvSJLSrjs8wOv"
    "Hl7IWtf/PGK+BwAcbxRpAvIaO9dgu7NKceFAIFL8dLG5zjHK492BdagY5hvKT2uttmgaPbvhgM+GqIZW"
    "fDnm19zYuMJyiPSt3PU+lLToyZW85VkjIqikOx/YLbcfUDQhI51rsAqO9Ldytxicu/Xk4yNsWTeSUX+r"
    "rkboawC2F1y6GXlOmRUzzMJPvyDdDdnwW7hJxTbGgarbHFXGi6HAgMe589f+jA2LjVI5AykGXRJi9yXw"
    "cD7Qmq0EqfI5wqcyoDgi9Q1RGOFZqy1jBGGZTKNVbIvQwDH+xDBRKwD5CW9/fSGEeam1v4whlsBrAXk6"
    "8m4OkS0iy8c+dMHbWebmmNsh/Nm7IvG7nsO9FR2APaCfEXSpj/YlAY6Pv7O436FLKjbPMkjJzJ3notMZ"
    "HDxHrcMy4MNcn40G/di+2ejS5XTbN8WWuGGu31Y5DqmSls8LWeBOcrXmq6bkg4d849LqNGY3bhEjPMHb"
    "xQNABl2nEdEWfQBwilqmXVKcehbglgrVNkHLXAzyS8wYYALHaX6ob6CdUhQ60t/a/v2//D23x3ro35eO"
    "4CD0rhS/OgDdQfIpee2rH99rqq9WsJYqZ3lb6j3V/rlENraz/I3sIPpi3dXx5BbZDhnEVW7H85O5+szL"
    "ldjqsXZnloJgRlIvvgLPVSrKSjSL8N7q7OvKFeMohvktMwu8gOJAzgAbWwSlkpzOqDx4RcWkHnKgrJfY"
    "t48FsR/QhWlFiXuvHRcz6vJqcizr9ssVH2w488MQzgKaME2crnfFmvdlJrVlz06Jz6DPW+n1GavyxO/k"
    "bd9MwUZjnvYDDisdjO7XoZ7UyZaL1v6QHvU16LqJDADzKyNzdPV5aRXGDKtUYif3qc1tjyT6o1hI/bc+"
    "FYDiNvmOLCwr71jXjMElU8cTQ0xEQwzTY7qTAGwg4rm3jBxr8gaJERDXcEwQJ9CVQ9A6Tqw4/COwtqjS"
    "qOrca6/O+4ZHni9cTVRL5GVRrVefHU6D6PJyTpCRR5cawIWmWB/7S8QmTi/j35kbbCMxsKcWo8z5WrMI"
    "kln95zUSRXx+SogMn87FQTuMCahLPG1RP5nDPaWsTj+v3hmZSd0zVdfexvOixZExfDFOvgFwIarBoyFZ"
    "VePuqgd21yvgO0ZOacrd544Y2ZkZpq2Z2sDIxoVobR0owFxjVHEhe48BJWyCOcYJNtaYjygqzqcdwJzx"
    "t6zshrDU1Jyd2MbyFO6H4ZBRoq7OC/wma0LyOZ0xSXp5CWbqx1pSYWunKmjdyXDY/UltY2hFs3Z15aYb"
    "94Poo6xKphnz97mrXltVH1unABERgIoi3cCu1+DnwRDYhDQNgsTHH4Lt8Ecba0+ilB3LVa430xlg2dB5"
    "peqHiaqmbbJjWhFI6/ysNuAjC71J6MgpYF5cX/B8c2hq2NjZqo4OTODyLlayJ/lq+o+JWJQXmJo4DWb7"
    "aAtLP5C4zcs3iu9jvTOVezm1OEBKQU8c06bes1+Hhx352yzPV3WM2szWdnK2OO15O0897sdCmHIeknh6"
    "VDggXIFChHzRJvr1ZauMzG+V+LSVjcWQIqDBHQt6rlslom9tJmK15LNSj6Yq3TT9AQANLWqQQ92WIdSq"
    "ZuBomgU5dTUDBxUusH3ddvxODu5BR+1DKOO8N3IDt0IA6JaG6n57u9muIIywGDhz8GtGwjDBijpeAImy"
    "hu+/jMJu7mwmDUm366tKOWIFs4zdJ4XryednO3fveyEgZdtuGfSRgsTXYt2lDTxB2K2hzl0n3d+/oyYB"
    "BvkTJE832Q7vKSWm1hGwf8yARwY+bCe59ePddzBMiLHv+Xz2z/n8Dj1RpiAJCZ0Vv3Lmtq5ht3/eIKiR"
    "Bh4sPkEnb4dvXAKGCALH3Y6iAORhoWReDRVd9K8dMGnmrBpb6JDZpDoHHGzKwSJtKlgDSRTtKpSa8vrn"
    "1D6zCoOGXrW8lUsnyZOO6OxCtz9w2G+FX7lfL7d2GlzHTADbBYDxhqoTzBHzvI/XhR/Z/OOQhqLiVEeB"
    "B0rt4jYkXXoiuehSd+P23w8odjTdqOxrecVCFbbkxL3dSYr9xhwWkwgmHcA/pG+vKD92lWbjcad10aP3"
    "2owDSTdFgfaGumjJ4S1FRgIcySkJuuIr3+2YfKsHBJ9E+FQEO/V/blGp9f5WPYNe6+/Lvv20EDGF4h3f"
    "Jo3nYrfWK4U5oK8hk0v6fMS3zFKFayfJkTg+EfHdHthI5/ZFd7Bl301V24goZM+fWndTELoY82GOc6Q6"
    "b8SXBHkZqt5fqy282Cmxp9z5UBC8hBm5floS4rsw6U6hnEGFG/Dt+iB3Fd/hodDfKmkltXXqoLkbRPPb"
    "jD43Zqzu+/7yHvOuWIZqqa5Me8woPYbp5zjuu2jSeSgNfTwHeWzu4nGex3iTq9WpLXf5c3vs+aH6sKc9"
    "3rzWIuOHOMYVdwu8PJnsuUrcq3dImm3vYUIOA0VKdzEAbXhEn6JlXtJMLldGVjyeLwTstSYkDvwueYgC"
    "PFUsOHLLrUuPH1/e+sZlZDBfRr/qIyP3457SGKJ5m4Wyb0Iv/ZYScZ4u6m/UK2Tn53kGRbaMdu4TIjW5"
    "sezJIOa4YFTaUDZIFir+AOGTY9MFfmqiy6RW0l2/UksXdMI/suePuraECZn+ksRzRXLOws/LQlOrCdUv"
    "lJJwUcZFKVexjKWLPkgABOFJdbAtOsDcOKM1l7i2g1cUZQJzPXXX65ie6d4LrAPm7GXdGaq3Zr7Xo5zi"
    "A9tXaUH6J271z0muTNC9E+PHflcMNLjYU9+j4QK/P5LG4wHDRGSdTyl58im5n/ntnIYqGtP+7eG3QR+5"
    "fdpAWjGQui4nBGAkJ42CEkuaiWzp+kDj+jc46Z/++9+zhkL8X2soAXL9/CsQDzJEzUZvnqcxzADmIMKB"
    "W9z+cV3TSZWj+yxXC0m9jb2eeE7ruFDgE/zGYms3odfnPHndt3OlY2ZXkQhsI2w94mOu7+4yRC6zmT6C"
    "rN62ETT7FT/X8GwdSbkcgruOjO0MT28rjnQLeIApAJNgWLbBbjbMB08V186xQpGz7IvXKelvmqnzmN4p"
    "E6AOR0fOaEqupPpsKjwkx0/BJE3uew3WJ1HcZ1+gfqJ9z1alMxhdObNlsUfgcUXA5pXyYT6vaO0HIWe/"
    "gFZuE3dX8Uwg1HB+WMIKnCDzDO3dWCv67+cp0Bckion/kjhgfErz/BJnkXDh47BgUyNHgqykv5q0e4Oa"
    "A5roFVxiv43GWKBnsplCoNmZnEgO81lKmF24CjR0MZul/AIxavYLl8J/QHJfi5D9ZAmVZ+by6wUbEDJe"
    "my7fgNvPbzMms1UB1COISZlo0q/QtnUlaSiLEe7w1LJdKYvBXlZVSukkz2SgC5cEbaK5HktuRlpTPbSO"
    "VSOHjLktnDWIkh2Mw1mYLfcl9z9UlsG4V/tdzV4BO4/AylSmQG8Z30spCiTu0f0EogfG3ph2NoFW7bGa"
    "KoInSWD0oT/ScOU/cvPe6vBm0CDZJd6QBWiwi1ikpad3FA87ckNXjsU56XuAX2OIcvB1mIu/IgPS9cTa"
    "+N5+PaklsnrU73gQH/2N5nQAPsjAqVu5XiofL91rwgiaFiKXvagtwyv95v+d/Aq9IpeDDDka5GI019X8"
    "vtfpQ5ydxgQFL7AnQDuJoungmgQgSWeEXLtjmQ7kK/Z9hm7og50wDlBBjC0KlGZmX3PXpz0T/UQAZF3J"
    "LkAEXwC8LzPUQlmFaW8BseQvBZp9Lw4TB2A3o7u78cP6EMhoZgSaH0EjOJzQk4WCf3/VinJBp/zbMrBD"
    "GBLYUpXGguvlnMxOm6wPqqsB+gkMGC6OU/f5WRX8p4+flTBwcmrEc2pCqQoWwVnlFCLZ/qasTWU6APN3"
    "1x6XYFVsJy/x2K+bDtOktfKfzz0xwJyLNAPl7QRtL2hyVaItjfVbHOQWat+SrDccgum2bHqBXTam9t9s"
    "f+ZVjRbIYhLXMEfenr8f4qvjLSpk9RFijCMv0isOv+P45XjFY0DIBly8ubAQw4KvUpGjtpQzzQWze56a"
    "LnyLzNcoKzIek2TdtJfJUZ+5+FqFdGh9+Z5Zq6+S2f+Ip+aUuuVQ4qUqgWc/wReC4Wz9Fio8M1wTJ3JY"
    "gWSp3YzEaYcIMjL0yKU/S/GeyA9nxwfNCWn/wb4m4SzIbP1qqqmGYOkCRnSbhHrTOClDQGW3ZjgFJTAS"
    "tr8c/Iy8BAxBCOhl2zVW3C6Y3+EekltlYfI6GqeQQwappQg8Hu7K5o40Vz3Y0gMgPGAuXJ55W/8ajSLM"
    "oEyzmNe9fYYnfQj/DS10ZtIwf+RBmfzhnkYHFSagU38IxR45Azc7gjYnVJhwZhZwIA2C7xfk/rzX+SKr"
    "sKhEqG8XlX4PolEbFy/iQEkqsKdf6PniSOqsRDh8/bxDMX8FcVPNwtOxJJ3O269TSBrGratnXixkQF8t"
    "A95s/hDeGx3XNMQJYzBumRF9W7Sn6BNqtGcm97dtwnCIq8Uk5y54WdmM6C1dinkZVCYsvtQPITJjOB51"
    "9HZ4uinEl15gbq3n8PwyXsVDl0wwEha5Dv2mCZdiwxKRLgHvRohdSZEerw9/LgnvBkg7oymaKgYE93Il"
    "WoBLrQBfMINyHpvfLCMhmyGnf0JhDDsD3xtpYqbHZIof+0y+xRxf6edXGJ83JwB78tTb8LxS/ttaOtud"
    "rI2DHtBXLu7MHGEy5alaXsu5LWFZvknYwHvrQVdsZZevUr60q7Gu5yq2zwQssIxT0fcgP2OZuwR0fQ9z"
    "YZr2h+LG/QzugG6pj3cI/bAtL1sC03E48+IVNnW07JXAXMmSE34fHAA/edEMvnoibdF/ke2CV5YeMhhN"
    "KQQmExKNx8OWkn0c+K6Uh5K4SBH6snW7pwU9nZEYzwdIx9iqOgox0s2MwjReJbzCmN26bHF7UGwVffGf"
    "c/M/5vyPb7/8w7/8fe8j5MJ/X2XZkXBHJs+ym29Bg1rK4aJEWWrAlhvs/CRhEW+IJ6xNUkvrtPnzlyoC"
    "yNg0462st74Y7J7lbElRF2uuGRPpocePeJ7xJyOzQa+5Rj/71dSAkHxAAvtilWTEZ88otcItzVPTa4sL"
    "48Z/lJm9f3k2NYpKdJu0rz0qwDRGHFbsj24NQfoeTs1gWOQpbuz6+VkMNy/liozlr2eytGzCr5hz3GJ+"
    "A+1TIY7c4YvbAN/+9M4vg7wxgXSg9mMzsmdoe4lLlbs0c74Dq5QUjCdv96Auq/ZJf0F5QTohXlzXknur"
    "ohPG1Yqh+DF7MPP19U7AXneVP04jPyk7TExM1z2UZ7hdRm5YU7vh5Ogit67uOHwwYm8wRNso2Lqg+VWC"
    "ZdVe38SBZ8S0Y3I65x6klrePDUhm1gDCwr5G3mal2ToFiw+j84lqfqGEYsdqMCvdW53doQXmRNSF/FoA"
    "nIWrZTwXiilMFs5PNKFj1OOG5RKGade8KfXGzy+CqcOiJU6GRNtrvtZD0TFPOszGbp6YJIyhlUlEucwp"
    "n9cZfg7Rmqy4A7vehY13ijmDUTH0/Crw+YXHWJm6vpJ+EUhw5feXKc2QLTKvAiX87H2VQ+vn1qIvwV1M"
    "PzlLpUXVEI7jBamF2TGGxexjGXbPFzR3LQ+I1krguryVTKOuZ4Q8ze+WRxPBuqpLHU90cxQCFmUYjfjG"
    "mrOAM0g9dWzko0SEmI/e9TU9r6tcEFfhIu55/E/EE5kW2z8oPsnNh3aoct1ZMf7zWG4GulMeaDzYBy5O"
    "lvuejDCudPFud3AGRaWShCFOLYdZrsLKFiezBYb6oax5Gcu/8VbQf/iXv1rwrxb8qwX/37Xgv/7zP/7X"
    "v6MH/6wV/K8enJE/31PN/22Pa/qH0yBC0WGYIYuCpqN2C9uL9JKvc1+Hsj8xX1FWwKxixLN+8zXGrwTO"
    "FVzTgKRFptOWUMW4bFRswlSrdSwcHKpOWhxNXcxd6oYHOrQg0AMcNGr+8O4Ck2dIl1lhBiNsAdTI8fAA"
    "hwIkQtwx1mHCcoT+2lGUfCsw/DxHCNP2wDTjrRG8hOApCKnJrNTce9Q3AFrIi9bvfyJ/7ZYmin2v/56R"
    "FdoNED3qm70IEUUP2tTkBiiO5/uZGdP90C674BhOJZueDFB0q7+qrdSIuRW3Wp3B/GF0bNQfIcjMA1wH"
    "msSEnCXfcVwxgysBqmRpM4T7gnw/E8RdGC2gbYko/iQ4lrb83+IrW8jPRWHM8O8tFd6ObssPZF2erHqT"
    "vaVmAM3tfr8vXUFUoXhlrHy1HCG3pN/22dwauXwC17ZVtcUcfs816p5yIXSIx1Gk8uOLDKJTvFBvD+J9"
    "SNSvD4EDUqrIRzfr+Wl5AY2Y9PgggdpRmj4MYLVY79nhnsEQouocHJvpnto1amDpAEESSDig/NOI5nZ3"
    "fLZptV480zBU2ynPwT0wuN9nraIN1A8dJwFy3w6UBlPi2XZURtqHqMpD+E1n69iNwGUkydrfxY+GuhKX"
    "tVw7x/DeiifrSz/Wh0mCI6X4gHvpL82vNcxcj5bw55jxqE6cRDb1/sgYhYFWpAsV3NWnXGH9vQi+6JiC"
    "2rXqnZA3C7lEDJLNBEuZjP72fRuB2YVqRvupTEH7zaPcltRVMQ/xHB2ZlRQSmTxbkSF+Yq79xplXIiIl"
    "R7WA4WMZ36YFNAdWt6M903d/9CX6ppPMUFKD9uhGLrjTtVQ3R2GCHtMPOg8iNfn1lNS+WwcCy0DSZjQS"
    "FyEW90PLeS7LT6BsrRYL0rTOrTcFKlxVBfJ1T8qCP6xcZDlwHGTm9cjqIaUR8nLn1V1h+ysaX5ayqrKG"
    "JQ9+C0XZTkKtTO6zaZOj5JU6/yD9lT2hfYNbH46tGI5fSB6H1AyQD7sspWaQ9OCmwedAGU6ssJ8g8ROU"
    "eHAwsdM7BppPkchh19f+gzl/tkdcYpKQk9qPp5w+U+68MQQ4636Uwf29H0tX1fZ1w2pbOqexO4tLyxQJ"
    "o55dU/5koF6w0tNWhCw0kgtRg+e5goiXlP/J2XnkyM50iXVBHNC7Iclk0nvPGZPee7uEnjW0BwkaC9D6"
    "xGqgJQ36n3x4qMlDFouMuHHvOcwwkrYw54h4uhTLMcJKbzuldmhpHccSZcDqwpNgSuVZ/peTMJhSmKoy"
    "Wv8UmyXM1wo758tR2bmee3Yx2cr6gPUU4kjPwkeT2uSde9o8ec0Y/MCAP3/lkUjEFy3YwiB0r+BzrR6i"
    "VIYHUIW8B4BHXLPHmn0/34E1hwOxLGeBr+S2AuvVAU7z62UIHKu8tRl1xRf7QNh05tnu2zptpF2pNG1u"
    "GSfBt/SwAKrBkGjnxVvPmR5T4ATbWjCrZVsVVBWmUxVsXcuNKRYgtw8OSeFvs8fw/NOI176pqOiTpRPo"
    "w1YUt/xdfD1ZPUPmFT69uYUdjpIlpqqrEQwautehkC6fo9EnzQeVGTDP8Cc7pq0CtZ37hRcxrITBdX1I"
    "LKXxlr6Hpwp0i7BHuMdV1AZ7VUzOtymKPesi+XphtJs/itoGOaxUZmQKzcw3swgy3MP7N2M7V10ifgje"
    "1bCaInRcgKLliwV3GrzrQ5uYaPRRlQDKXNOkE9HRB2sgibTUEo5g08OXN9eJKwcoJB3G8VcE2dMThnz6"
    "voVkOccP8iOqzfW7ooA/pEFM/pwyoxLmkM1IxyIaRxKN9VD/vRCEW15nhWBznDWIJ6uRbHNr878VO5oD"
    "71bwLEbibZn/pUY2h5iSRCJMl4ckE5y+nS+THTK0C8/9FxOzNDOU+cnsBI+7jbUwuENd26tPy+KuFR/1"
    "xkVCPVxzc1nipyWEQVZtzMaYJIf0YQUQHA1BpqyTuKc+ksXNpRkNILhnXFfEfUbLjcLSBV7HzPj7Efe5"
    "LIjil8HKs2nD1YWgyGckPVNhKXfZ/j7UPLp6D82t1fvCJ56Z6cOHfXjHYLhQYG0mFdBml4Z2pU9QdM8b"
    "x9qhzYWYYWcUrFSlxycHZLNROlNiT7frsMP6PhNFOLAMK5IU2YHJflP4u0aOUpagMXAzCKaYfBxuqQod"
    "0tu4xXNGPa/zF82RQ1edfsNZ0+RkZDskG7v5oeUfdd1YZjKbKBIcw/LAwJNnyUbJE1Zb3QUgqsdBFiEv"
    "XlY+BLAjLKryqBGaLEjWlfPLjOm5v7R8DQ+AC/QB0M207w+tW/jDC/J4cCYGepB6jvgu5KnrJHNsE1Al"
    "a9+h6ecYHih0HpXLxRPyLhXde5OBW6v7TdArpSuwjGoT39aMPUf5/Sm/4BFqz7mTvnbQQrkqJ4zN300k"
    "P0hfjgmHScS6JZ6Mq7YZUj+SrgnQP1lIHtYFar6Meaq+5xnmNyNAKSLSu3bXIvAGW/MRekxWELmg68T7"
    "3cwwuHVk4krCXqT3SmbhVm95k40Y38Nzd8JBHRueFp29+YGeCnbMwdo9LZAwiTIWfb7TFkXw0BUmrsYR"
    "ZeWvmmvfe1HblCdhqSSsyrC+LVYoKE0ieW6AkCXm77WK0cHfGA8OFW7gPPZ9JC/u55fAsUVdxkzFGO5s"
    "kmTVShjwPEKAekVCvyLZKhj0l1Cs1xMUsv7L7GUxGIqIj2nf9HQqLmQECy4vGXDVJIgb9Lr2VLWrp3Hb"
    "cDw0dSoCpEqbIwO2FHcjRkCKKt4nMNo0O8AlfdM9oyZoBo0jaFTLJ1rzXSguNToW105n1anqxrtTlWw+"
    "NoaH9IaSl1FPSBY2IOl7fIZmonNRy5rNKB7yz/bAP2D70W8SGBPo+K/Xbf37//wnPGx5/4+HE+zKfDsU"
    "C+Q4UoBMc+BlN9J1WYzm2jgR/bwq5wS5mqS8pirhwlHnPryIS6zMmmNpt0SU2I4hCxVYfi/fVvmbY8be"
    "pyTBkASuMT+WRpWzwUbjVqSwRpLoMKhoSK0GnSJFomRl5KLy86wQHhNgEew7CG+LmGKq6A/cT+9JKLo0"
    "N29V80ejM/OhLi34HjR+p7egwvmGmM1ICs8GQvcIhUs70fny46gFV5K0wkl43kxtV3YtI0FQXliaSguQ"
    "O0C6fL4o9iNMipOERKj1uiOgwgh1+7c7sQ4mvhF/vcmJ2QZtYgZOq6b/OPBFyhZqCk91kUXx8qRbVozR"
    "bzcdvU+jwInTU3NHywlvyTjvi/4s17FgRRjv2cylDl4OZ285kjmFeqvU34TKZSLBw4U0Kv+0avEUujlN"
    "YL4ae+HtZz53DqovCidJqT2q86zM7eRd6U04TzvkRnE+U4eOG4Yru5eHmIUdAX0T47IV4GsBacbthhYv"
    "dLG4rd3i6eTaZb7ADuo2f0tVV/U2OWczxUL360RXldz/IvaXME8l6DpjxEP7EVW53jmVNxHbrlcFliIx"
    "ObL06Id23P4WXZc28dIlcQSvyUNZ42fZYRD96U8whThNYFvV9O3yTEKE8TlBu9R7nHu9WFSS3MPsEQG7"
    "PHTr/PypsLuiDXZ5+DtgRdIQhIsqNurIc0q8R/81RYfnO6wYV0Kx/FfwVzILF4l9Iv3tv2Ti9fh63CYQ"
    "gjmgbqnNQRM7iiOM4BH6taQgcy40M92K/gaH+RR+cMAvckHzwsmRXwU2nvq32dwyynMSFOyfXuEO3vmY"
    "6u3pUGALq2/KBaJWVB4OP+Rb8jFHML8XA7lbaxziyG8n/wXB9+33K2CNG8wNiHZ5SJVPlEE2XxjPMBet"
    "t4EpHl7pSzGboYHZF45PPVjoPOvxjSy/Pn3fuHR89q7P86DKP/l9aPF5ixzmDVUYpD8UrJyny4/HHehY"
    "rvYXDIYzbKVY7KtSCY3wvE5ye0vExWMZQOeMU+M4Lw3WhIXzvIifn4/yjJQOowKES4Pco/w7tqu+A/Ur"
    "Uz8dBrw1tCrXBmLWYYWGUVb2qdZ82+2IobEhxtJICdRXGD1BgyIMKlk/StsaA8yFucDsy7aJ31dSgJ6C"
    "g8f8MeDNU0Ogeoj1gXAlO0+bF8R4WRT7V/oQhFIhTPp67wmV1afmedrS8NP2E/5GvxeVahpOV6S4l2tD"
    "2qVKc5d3W0n6xYEaiftVdvDsewy+e43grnwE5IaFRRgZT7Nl/77QAW/T8mJKCToEbDrd47irE6yXDlb8"
    "E1h7RZXKU06daduFvS2dduybD+Q+48xAU0j21/X+ikMOzbFEk+/5331Vkg/BsjarWNmEH2D/sMbbLwd5"
    "ka1OgS86dWc3qClBYCT7ofXIwxDM4c4ePMTcNV04Zf826NuLq6noKn3QDt8AzWyeRZEdk39jCGWKGLGl"
    "SlarKmbrzdDoRGNNEvDlTgl+PVFUrJsb6qSUBZK/jCxdL3bFIp+wz63Ls/HA112rJHDrQD6TH5K25aGK"
    "Ll/Brax5mgVio0fzjr7Dc4gQ6ydjvxH/TY7fIt7LezH7LEbVPsICkCysRNVYjFobEcqQHOa71FeUFkUP"
    "e5/BfGHvvn7f+dMJRv38pozfy8/jPexHPitj+yDuUIif/CzwJzXonmnVhBr94P7ZrslkzNc/v4EZtlcA"
    "rCjE6G5Jkb9mqw5YcslteDRuDgoiOO9SvX5WphHrN0r7N4heEojQ6vSq0H6TWYLUBYtsSkFQtv+tEYnj"
    "gOKnjcbEGtyX/w0B+gNZZwx6s9/HOgvWnr8f+qxU4vYcLBZh8lcpv5cqW6TocyH+fe5Gfo5ixxiVJJJV"
    "8D8MhpZeb9weNTJxD/3eeG+oU6jToe7h3+8OLMpl8YxK1UmHWcuyfgY3Tj0swOUkJX0gRTlMIsSVrU5J"
    "RPW3ZN8xdp2cXJZC+5jccGaWEqcGx7F1/OmjZ4xQse+Gh+kjTmyX1QRxmObGj4zgnTAdX+dbuqlgZQND"
    "5PGdOsnF3L/tw8hHXw8chpzDUwKTWvKl3WsQnN5xGo3loXDghOUu+83R1m+nkrVs9mwE8ssayZK18S9N"
    "fszfDhyjbDPfiaXfmuXx0/UDTpdeoEllT0TRp2X/KXcCp+DzPOGNHsZAqIFwCbzK5nmxxEoBoTEoi3Rg"
    "/JLhzQqJ9lF3zHeSnuVqQywoajlR/dW7Y12KCWCnethPQVzhE2jT1Rw0RM0/c/eNwsp+9pWsyIZ+Jl3m"
    "oZC/JaPxS5giJpmOBPjQI6nQWAJTgRD3MRcIK52dTRc6dEEn1ucbGEXqQ9tm/Xykybk5SUYKxObwsvQT"
    "H3obYZ2U8zSVe5K1D9SqnC4l8HtqFT5Z37ZAkbfA0zV2ud4Vt5BmLvAUFq6gCn+VM2pdHIe1OGvNcKg2"
    "ktgWGMJS2ZM+uaBSsKct+o3+OPzyYl1UTCcCd2erxi+AU4oiueWSZIol/74leEcx3AIQavocROI93OQg"
    "MAHmbyMKPlGsCZ8glw96fJjIMJ7VvTk0eqKYJclV37gy3mVQqCdzP3v9+y3mx5wAUdK6n003o7QaX0UK"
    "IAiupX1SJvFhaWLu+B9JwDaYFvZmel/O6Gc/HahjfvK3irBZifyu50CNlslSAgy5PQyjKlFm6ePRDj/Q"
    "ZJe/Wl2ZS3+a0vOVC2uIfvkW6FgkgU12Uh2pNxMffRPYfe1gp7OCCLmM20AwCcJwnZHf6m8IFuVs9sk6"
    "gTG3Qq4tmNGlpDyivYQEtDm1sGmdNBf0VBG4Ux8GO5ZF/lkp97kaQV87xCyKPiiXBxatMpHTs3Tqi3E0"
    "ci0w9bn29fLQAwRbVgfpD+B0EB36+0o357981/w//skZCOx/HlI9+X9s7cN2CMAbSQ6iXlAI2wtfQeiI"
    "F4wZ12I8l7dSBhm7SDmCeoO7Su+JyMRqfXuraIqPOSLXMC0ryrWk9Cz0BCcvyeS7AuNPSLkVNcat9VJ+"
    "Fa/MeeB5OnKhvYI+sec8SuIuOhh+/ytANjoB0CN5O1zGD/1vIvmv88av4aiIkd3Gz4ug74GQIK3l4EjZ"
    "p2TZPMszJRs+8onHx4PhO3amm8ZF5EgtmXTVtKDcmz8DinjT5iGyq/KC/UPTFi2WKzhQAK4yV4VT5thR"
    "N6gCJrbVfX358+TOmWDWZVVfkMcBrSm64P2sBnCwJ5UvIpZw5kxh33QfPsI1E0PzwYRhORNGUxNpYfUq"
    "HgWp5l8dYgWJY+bWVHQfE9szqAWI3FA2GkI9JH+ISaZVTweLe37ZEUzNeaZM0IDVfE+MJB0p3N4ef+6S"
    "LIsuUdXreJDqVkvU1uKkUbYcN3UThR/w0uL/9gxW6AuMYRNkZoc1GJz5wN+J8de70JN+OX5hkehwPG/B"
    "Gj2iEXRVbwiRBD8auCQ2D/ELmzBBo/9sRz0YDYiJgW2XrosAgDJmV3ot2m73ghEdRP/8bTAT5agqyIsX"
    "tqKgLqdMOYVUfuCm4+Faub9bhIfRui2qmXYmUxxCbD+YpQPuMwjL6x0hehDA0Qh4uu7qOAnOucMvGAfe"
    "tarJBacSARK6wwU2+6voEjeE2G8c2QBEfPEeBatPZopVHXo5KtaQSGI4mybh39tM0R3kmdEdqGq2pr9q"
    "BCv8ppR7hirPshRFjwoWT4BEJVz5BDeNwnQR33Sq4Z7tV1b9RjQfoIsQPrs0i+YsOQtAfCLjbT26+nvR"
    "JjE/A8vY8ZOHpccQoXNCZq7FOPz86uZ56Krrym9fMkHpQmIVGMwLd4gbYT8H7yWGMMi103WJYLfjW3Jn"
    "/WEem48bY2b8VL2k3cCU6mVU7Mvt3gBv0F5vkSCc3HcQPcmaGKGCzR3U2u8XjZH0be3b411tn24mCsaP"
    "WGPuCl9NcXCjYPJCx20PWvF8zQtVtlDzJClOLshlx9wM4322uAzThBXcfpPepDHJ9lrizfg9O1R1FWw4"
    "Ci7lL0yaeeUmzFR7R1hcyrC/ZPRizzXD1JLGFfqMZszJPNy8tfGX64i94DiVCQh2FFG1nK/WC4OB6zQv"
    "SlIu5P7OOhYDhAMuEl3NtOTNmonfKuKOUlW2n1p0dwPpeLYVSnT7/mLem7pyT+Vnwsr+Q6upHjqC0V2f"
    "RimJlf81i8ftvIWR4BkdOMohJoOKIE0wT0PxjqCU/K1g7JoEWwszBj8wwZMvDHd6R8UotmQ53upGOZZe"
    "m3udEkYLwQVeVA6iSJxmIva98dTDkqGiYl2QfTLttOgJ8KNSFWGr3S+Zl4NYXwlJ90vU89byJml9/PDY"
    "BMGsqn+Xc1ySAHP3Y0E4hI69KEAYr/UbzPK6Rx6DqN1AYTlQYGaZ83sdvD2wa6AlLkLP1/S35PCnK4Sx"
    "VblQyyKJnGezwF105ljkx4/H7KfGwMcPSZp3XPI1nok+JLqqgsqXIS3+GnkBJOEjpaUKZ9j+aiKupbuk"
    "oCa7MZLIdwwrvsBbK5eU7ovn9v1pVuPN6Wnf2hy6KBZ/SU0oRrtjMmSpy3WHUHRDkx/gGYdPduyMChtY"
    "8ypgQZY0OQGgc0WV4nMtb7fCVIMC3nAADoxVgKIZIICtxLTo9zS1a41bZmClVNRFnPo920u3IDtYgFEG"
    "LzRYfl1643ZKLiJtcQr3FBvxGmJSN0uWksSb7gEDGVAUvzyufh/c5SajsyTDYEfPEU9Ww9jy9mFqn78T"
    "sKo145UVKn9HW3K8chCon8yJrOYMJcsJ+pZgjp/t96fNyw9h0JitrTo5akRT6+julXCkhdTxVoe+7sqa"
    "Ku3Fn97iHFd3tQb3UI8tbDCj1VTWO7ZOx6b6IXWg2/7uIdpyKnnHJw8XqiPY8cDpliqyU55TKtElzg++"
    "HDZlKgoZ0Fp44VsCKGFDoQd1H9wppvUV3bcMScKP4RFO0hyR0aRSqMEGOwqAE91PT34My1y0D86eo5Ia"
    "De/zdPNtquK3T+uXzos81oPwJ0ZEzVQdhPRMkzBr+enBD0VKfSzdk/TYLXmm9PkwjFs7vuRyTCHpIBcz"
    "EjTQgtYtesKHdm9pCbtJ7MLtkoRVC2pBn/uM+BE9ppkWmupEmld2cW75rUzhY6zLmZ1+fu8sB1Z4+LL4"
    "lA7JsdzZR0o3gDR4SCAcj0OeJvcj9XFQ7PpUKKqRNda0lzSysTOf6kp6N8N1NUX6ZaY0gYiWarhoO7GF"
    "+QA2AQKrKE1FBxMKMI0DJJSOpiuz8aN6eVFGfLbISycnKNJhqLq01ncYp/LMCOIzP77glrrInneObg7b"
    "kQkcbQfyeQ3+sNuDXrKXcjAvbokFMx5ZTxl7kMzxO4uDjg4RwN5T1z7RJAdxW3CfNxPc8bE/xEm9Rf0W"
    "J70h6HzHY3DhKwy1HYwyulZdbCYFZpX9RZ700ww/ZU9C7hxDI7BpRNfzradgNfDSTISffGOVPUB5fgVy"
    "T3oRk5OvnV/8YcLjAqTaYbICQ8r95CtuiY503beFVxFMz483nMlNxClClGCO+EEJ8dRsX4LfLqS4C7+F"
    "wqelVaOZ0VY2WExdPKsv62J8vJyclfL1zlmNaR8TpND0XVwK32hO6k5ys4zAnq5410KrYyxwEYXfjGP3"
    "3+3+Ldg0dHzY+G5JS+J6kljjRh8w3SeLujfrmtVgv6k0QRNGmrGxekcmNK4+Hnz8xEk6L3a8QmgI40uK"
    "Zbkr8U+LxE0dlacJWGHVkjECZFwGyiQhvpObMLWNmKI4+ROmIh3RTrCWeP0Adk1YDlaNi43+Jt4jv+eL"
    "1xsA0exBhmADrRYskHGJcGMss7FFfm176UZa6Xaz6G3QRMNuGKi3tKGqulSOhNbr4rQPkmnJy1vJcEFt"
    "iKFZuh8pwS17gG2E3wfO+QsMIAkbPJvcv1iMUArpae+3DoOVNCWDiJ9wV8VHpRpt6eKu7cprti56FfKi"
    "KExHBJ4CpplcWSjCIY4nz9I3It9bk4jHP6ZEdQjRy8VLzTZAz6ciVQgURpwncNGkACTJS3TeXQr8MlP9"
    "BNeuo/YJKp4uHzZdnTIXPN90SXI8uZLp+a/94r//k3f3Mv8v3t1f9EOiVq6+z2ltoPWZ/SARoCngRkss"
    "x+jqDpvTXg61qFZhEk0rvnfzE/mbyZqTY0errXjjqmRWkvVJgHkl8RMo/CXW0HvQpqKmQaZ9eBxGuG7m"
    "a+GZObczdwy4+EQxAcIocFwhspFPxytVpB6kcUGvftNZTYJfbPtmJ4p9fhs6gD5oWFnm1Wcw+daspOzG"
    "XTmyhR6UBXP9RTIH+jleCnaRGi38x0K/VEFKqLyKVf1S9tZg10ZcmPpKDGWKbMesWDt2X+NjJHiWd9he"
    "L7dwQ80RYnkIBRSiBZpRCvHGQUKOkM9w7yS4od8W4M8S76n3OuT2ifKBU3LzFwxAQM24Wn7H1IMArk/m"
    "JBJG4c3F3z9fm34X2vuOcn+O2cnKv82EMxp0CBjGKDFqXKauOQXjA3NA8fIwbyAvXC+0q/xXz69VudqV"
    "eVd6WRr5afrSPp/9yz/SPjb41UHAIBkUyERmmE90AgJ7I0vmMzUfiqdnqnOIJEdx9ceLfRxUxPySND8Q"
    "NSEzlizZH0/7HJfv6t7X1VzWKmpd/5aChuCPkA0u3mPgLz0WHU4U1qXWwEamc6dKNUDtlu69gbwxkYG5"
    "ZLJFRpb5smLXn9lu1pdtHEu++I5bNDHERpsYhL+lqTCP5WOn0TGUIdt1qRFp5ETntcMRmv3Ug0ZMM2iH"
    "5Xw7877cThwPiR/ciEbW8TmHZ+p56eYjoRaym+KVVjmGti0lLWcGKMxBgBiC2uhA91ansxmujkkaFnJX"
    "YxauUN7YxF00DNM1pJ8YzaCsboPUuMXLqQO6yPq6xh/Jz3wizFyNhUPgi/S8zfRz2zeWb9i0R8Uo82OB"
    "K+SZ5a3jjKnEtC5DXyFweUlJ+DoTPC1mwJzmfZ+HOU+83Cn6pBoE5y9v3uqhMqzz5P0J4TcXlqH0fbVu"
    "eMuhBcgE9St/8M5/LcsPOKWOXnTjOm9vsVIj/mM5kjsnPyGS7ZnSUBKqIvAHEdwNsGnrRUsTaDlTiPeX"
    "0ammlZCuQY+dv7SrDit4cCth0dMXz/zMWbN0WJGiddvh83MYSdjcyJ6ZWy4EBVgH+zo3Ry4zz/TF4RSe"
    "7xNT7OnaZVR9qr2VqDj+6OdDLMxbSoSQpK1XWdtT/wJjvguVtPeWGgYMB1lTfMxizRBdur3EgGAhma6S"
    "0DZkldafewXEn16nAas2gOE/tvhDK8mgzz6ispg8R/GN4Pp6tjk0A3qlr5NS9hNkzTDajR2pdKVR4osp"
    "FQsYGGxgjGYlbJ4hiX40tum3Fv3DbM4bRQZbonMh4XDwrSFdNad21KNB/Pxp3qmkwdVqb3PN9EXML4Pc"
    "JVezktemURlBd774zlg/3dZBBJ6dd/rWid85Miz/7JCqdOd52k0xj58LLNNp7+gRf6uE8pNj7DFVtuvw"
    "OPK1a6qQyNLT8dLiHqYPbOlhtXCR/I4RWXQzQ/tQux9IkY6tWwT/TLXVCo9dJSXzrECVv51RRZgi3+fH"
    "CNS96kP1m1Km/3WILMyN7pOiKxoXnFTrr47eH7j/lKuRmirpna8fVCmdGtA0mqZ51IYxwowFuDIxfdHe"
    "6I2TI17rQolRdKoSUjxtCMDbFvtX2wQO1HPVO3HDNawK/Pi5YAqoqR2zK3QPWcBIw9b5h07TePp10kuS"
    "OItu7Y/yJrOb8R/Q9IeZc+uaYcDT3bU13Rh6gQ8wl+KiN+P8A1+simUfRigTCN025zXtFlzdj0CI+s0x"
    "PWPklbqIORl9XR3Vh+WyLBlZOUXYMspQdFqZkYY2VAUxQLvai3c07Pae310+YnagjbOfnvZrpqLKB7ak"
    "5SLDXyLaHyWDMIxv2zoV2IRHF6npn19ts/Woq4nM8c5O/SahsCCdi3Tfvonl87VSOh+lkuMgPSu2+/2r"
    "hGZTB3vzaWyKuMZVwxqPVIbZ22NuPJJAYsNx3sle1wFnzH3/fCDIe2pK94RTYBsKLtoxurnN1FjT/FcD"
    "tABWzvezoHMnQV6wVkNtpMXrllStvzVnNeFFphx9aQEuQxUzDYzHlqh2+eN5CyqeaNzxfN3skWs3uM2P"
    "d3/zN3t96rnw9LR3xV9jMwB1yziX6RYvM/0aa87hCS7+lh9No0m9BChzBj+kX4RojWXAJ/p+AiQ9W0Fa"
    "Gt0E/uiHSKhIT3Na85LyLfoBFe/SzcJUzOj+LUY6lzI/9/J1ZIzLTHDqe6+SL6qTIIo9OfIWfYBoeOGx"
    "Obt9zrMqEZozRD1GMuiJh5Dmbr+VWH7euftef2GwNU8Uxd93JE0vaSq7K2kGWnSaFPwWAPxG/QBxi8HT"
    "dUlQ4m+bLv1AjoDprba+pdocGx1+CHhxRBDkAAqgAYcwQnrrYzt3B8Cp+b+tNrAQUeuuCoNjm76L19rl"
    "bkxWlW2H+bGJvAs93e0K0y4LUMt/oOYGfCFYs8QC+Lfa7fghpd+Cz37/GEAmCI+Om5hQtWzpOP5vMuOn"
    "VvEtyYUM5aHWmlpiTnfPZ+AL8yx4XnqeYvPflwznJV+P9FwOE7lmauGUlKL89rEXau4C/ueB5i4ugZwP"
    "gza04LAKVsV9jAmCpd5l73TL21FSA1tGImi3mk/6Az7Agrrq0JFOtrqpqM4jfb2oDV9aI6g/IIWbbrAK"
    "8irkrXAbJtJb5cRkKGZqQTK0r9pihqbpzo/UCXJCyaP3SCDNCaH5iqXZnSQA4BQ6QDSZO4orbWYT4Qzb"
    "jbLPmhniHwEKPjj+GhCJ4hiKC4/g0gMjaFjU2Dh80AQ+PRNODiox9nlzK7j4CmP3+zzLqu5LCIgA55bg"
    "RV2tGC5+6+4S8vntlW9LD1OoBcUa3dfst/ylLuxfLKL+9//9T/Yp9qD/b5/i6PbgP2YGihzH+3iI4S5E"
    "2Kq7MVWtD4vpJDYkGajlmclPjovBtkKYRAGak2nae1Fu0XXVG34zA/UvdUI/u/5pVW2NG7CqP3upLVjv"
    "ZQ5ZvLr+297gi4W93ofvvzyHKNBUjXPV9t8vB9A+fobBpGgcfEAcfrBBKNypRRHqAG/g98gl2domKONl"
    "vUulToBxT34WeQ7kFBP1pDDfSgVgzyqapyiVQCsUDwL8SucN9KHvWxZur9B6kuMA+Z5+zLZstreK/H0T"
    "sCkWQe8EOOP022vROpc/8PV/H3PB9bxGsdcR7Pvazgnsx46G6TvkEOLeMPVBbYxS515KiE7xJBSsh1eo"
    "UDpGF4N6rK9lt842YPjI5MN8hj6EWcwPeXJgvq34d8/G1HiI7sWXPKeCBBRsc8OmWYXzbsmnAQH8xt0H"
    "COhkcHYmnF1o/PEdiL3/Tg9Zl9JPPiCI4Fsdfo8bpmYUBvKheH7qfv08/LsiLWdFj7AK1Yth8BJd7cZb"
    "hNn9vPTO5AmiteOr0/kLK38z2DPpvT847fQc9hjTDz0WBv7mPzkBMpEphrJJG6euzuNSxd8SJ0bzdlSe"
    "xzMR/ua7Q9OApwpjPEPVtaagH0BiCGGbHk6uevq12ODJXX0HQXMTrZXQCLpP+tOt3AYJS+VG1CL/hNXk"
    "Us0keXrlijWpAxwMxgkhSrdfSf5zOMJm+ReUOrP1+24isYdotsI/uYOwx6cSjaxqoArI7EvOGd4L0Wf+"
    "GnzUrhHyfbNiLqN5jxTb4IAQJHxG9VrZSPCn/vwUoUFaHNxWDJIW06Cg08AaQC/SI7lDp8f2AxVbsafD"
    "rV2wIjh8XAYMtjmhnYNtUk4oY3zwsa2hE8lfPxeESc+oXeehflfDEON4Goyx5HmPaSO9+WY/3XXIDK78"
    "vRUo4JcAl68dTMfGlS2iZ+gpgNSnjK8l78W1Qum18DEL6FPVtdD1SQQBMWPxO+eqd1Kz3ARvQfJL2SPQ"
    "j2Wa7ar7mclOGjSdYl2fvjGmQJ3fej1E+6TGCBa02urnO9vJcsn32EoXT2ZnCPjdfFG5wXyewGgFlJ64"
    "ImrloDs+C5HeW5cM5jyVkw4ZwMI05wTYOqu0g2IrWK3P5TEvMoRr8Gmc+gjHg2TqCmWXwt/WokvCiJNv"
    "2plcsuWT5awsUZZCeEwYToYQ4cKb7y7Q7WCdkvyFmSvZQROFi5oHMz0iHtN+a+YvGTRyjEvOo1sLY3Nx"
    "1CZSqaBwr9oGUdROYEOjvuf2KM3pDdftF4RN1mObH7Y08q6d2FW9RZpWUYD32mlMKm60lDozWfK57ZGo"
    "1vPHcb+Ik+aoTSshGKw6zf0NA6HqwHccxnIDv/qbXMCav4ShI+JiAcLOZEhI1OgLSLEg1q531K4xrVhS"
    "YP/19kP+LoUA8U8F6YL7oRqBY9RLbD4iH1MUivazkl8pCIlpvq/I92OecIOHu1jg4gc0tm59Iv9uGpeT"
    "AUz5HhLn/PwV04QHiz8cN3L9GFlsWV41Kyi2pYsnIuiGRf3NdbPbVItWvrRGZ+GgFVX9hsduWdjulHdW"
    "MiEauH8Q1g8lnPLjxAHOjsoB7fy5+tuhWBSBwc1P1rZ0V5WJnASlfHWPfgWzXRKvHkWrXt24gwmX8Lef"
    "I1JnJJv1+enrqIWvpQqj/hq5Ha5U7lyhDQWbwmIF6l1fsv0bWiCVK91KGu75l48p/oA0Y+1UY0ObzM0P"
    "wqeFUQBSSb+sLqyUnQ1MKedHatueNGLcOZFyb5c5KfN3z7E4BOS1l+u1p3tq46jqubGMMX4HjsXO7g7w"
    "biX60F9kMnj66gNbiqJESYPds6802PGZWfe9nJAPq8OR/d/XtMAK4G0KHMxzBG8xMZFfYwrAXraJ85vS"
    "eYPz2Sqdq3Rh/hMnMuvZdtprPN++aVWyPNx5ldp3MoOkmaKQ5gm4XVCLiFTWsWUH9lvxOiuvGzBDfnKP"
    "zkaC8mjK+jHDVOMuxDA+RuHsjqSHMzubni8Ut+dtmmKdbk3vc6RRvZoZVTWDoR34JuqVBn/UO2IE+DOf"
    "GC+s5nZQVg7twwjx9zVM+taNNsRWc4rhJDyhHSz3FkzTM84DdBM+L6+hi48DzfYLOPtvoh0GONocU8Z/"
    "nA+pJpOLRuTf8dPfIqsno4sl6od8MjBFtyFu3k8c0QVPpUz3rfnNxai27UtVXWOuPkFe13Ht+6EtmHMJ"
    "co8FhMdGgyH42pNAyunPefVve8oZ1NFNv9M8viqWFAVx+Qq8AvpCl8WWY2MdVG8Ks8yaoEyvGxEYKD2P"
    "Dx4gJiI/VXW2NMtocitFzbX9Z82HDHPMqd85UtHy8S1X7l0TjRuT88n6TMi3rFJdFafvQjPG5sXfT0EM"
    "RENQU2ZWyGagIW+xMBEBVGD0tGLGnoHLuHf/AmdBXiG61izrnqdrGzqvjwAGV6MLCTQF9o6cp3qe9mHI"
    "8Umf9X0PKWJ+k/Qbyd+EZNSmCI7lTQfJaxvGMI7qmomNu7dgYbir+dL8T6lO4FeAcMZTeDsf/b3C6z7D"
    "IgmCTDSDbkC1TXv4//Vc6P/2v/7JfI3hP9+nrkiYo+zLhqh4kPRD0qhursbdPBdmQQI3M6VEdYzEE65T"
    "ztJuJ84XamdZ4Grk4a0sfMd+oAt29ZSNxFRKF/+0mXkp+FPLNV//zTTgKvlzOnyF6NB+N8CzvHEMIjoS"
    "lbp5fZAi0VC9J7eLJJseRJ8XbAAQNagPuOuCKWqG+q2RZMmKpSLm+V4vba2vD6d/u1GJJ0fxHYlTAllq"
    "Ife3Bh8mQg/QNAxQ1HgVx9Nj6L/PhpAyl7p16n+vfPkt2c//2t6sBN3kbdyYcQlwTIQjSzwjNSKGvT83"
    "qwDUR/NY68uORnVetXpZyoO4p3J+bxS5Yd//OuOwTopgcdSVBlNwXmVcSzUdJI3/Dek41J+VSOY5stpK"
    "O7VNzcQ2asSTY07+fJlxkbTG4i0mvRKdHf21vkNN1TVbGQyOBm7mIkz74uxt8WsaupZlD3Pt8Yvj5AoV"
    "X/BBqOakksJk3/2cV/yPOMqysVrOxd6ZxLTt2PARznasE9USi7GVosRD0dejwpSt2wnpcmTY/i1MuN/n"
    "bpn1R3+bQYmdFCc+I1tp++unRrSZxfH2XdyQ6d/ZIygEnEx5P3K2f2uxdDAZg37QSWRFaAnf9yqYLHIQ"
    "e3DoN/gEYq6fmDfq9EZJzGr0DAWFWAHuGp/oYgsxLMPl1F6vUp/l6LhxnHpfwA86GPGsGIWb53aspR0D"
    "R6GqaABHMNJb6ExAIm1HkQyxOb6eG1WJJVAkkK2PDARqv+NZLd+9PwG5Pnv9IwOKPsHkl8D1oYxio+zJ"
    "6zuW8U3wIzezk5jLC9140FZGnyycabP3H2SiKqn6aa4Wfq+k7ZznydLyEdhoMiqkbNcdmPafbqrZ31Ii"
    "nvlETMt7RL5jeAOQ4N/B9DtG2f618Q0X39jzaY4Dkxr5ni8SlmDkm5uXKtCQhhXM3570+tC8WX2415HD"
    "QhbzoEm/raRJ8nmm4024O9/3bYWBtVoegSIeUuL1wx00s08bUoOmi+aXa8el70VHgRv0DPoVgSFdZiWG"
    "1Un6Kt/7w1hEMLfcxK5WWdCwany39S22G7wsOnTisMcHwpZQ77Gzv5EOtRFDPFo6n3K1r0aVibgaukJl"
    "HeVWmrpx38iIYzjkWhOIgySGdEWrJQEO1DsEUs5JkUnSJq80jPTLedv/UHfmJlb/J968ZgbAmTR4zgx5"
    "0X+Tfqx/wRGAnzJxZ9+2OE24pSpXqjGylfLjwXS2fY6K0n6H27nb6Xz5mP+JAL1t3+kuP20AiKZaHi/2"
    "qL+hpyFlA6VQUoFVnqTdRbtNNK282vXkc8ZgG0HvDcQ5r8X+c6/6tm3PLlSrXu0b7wTvECwYtkQonCbh"
    "JAOmaKE7D8lhHJdd6qd4m+qARYvkiHZokmePdGfI8Jqx/o0VkBu8lUky07tUCpihgZhD4yRzL3qXdJH+"
    "CMs6q8110eAhEfHX4qBI47m42HcGSs3BRU3kofBcODl5rTKsZdVXTOkrUOKINH9DpIkffNUidr3f7FRG"
    "uAK83NHpBseIfW3SlPnajT/w4/MWFviMiwsbjSilvpAlXvvAGEjY8oaP5O2XUfEB2616pFvIqARTuuQ9"
    "B1dL9EaZETkSLVji8Gf0t8GqK0RqlS1JNOAgBfTGcXaj+zDB19rX/BOJK5UqDwvC/PcH5DYSNGEr6QZu"
    "EHoKfh4R/F7c5406MPugfCOEJQlrOkN9/Gnew4j8RkeijojMNsM74nh9OAOYBHx4M5pesM02N9NPDc3I"
    "AwwKhWaabLVWKT79gIG6FjV/8/HMxxF8++U2nUwg4KPC15cYdbAcgZRxs8w2FbWh2IE+jTWOLzMCqmw/"
    "bEFmL8KjNUibJu1D/kl2bIt2aYihiRbq4eLBcgH0/FuaoNPiE9cwqGLu+HsVr2vMDwiXMc/Un/eXMRnm"
    "mGQvv7wEc6Z56LTbtbAEIiWMFBqJuVXd+UfvIYEdJuEMZ9VykWY2V2lXB6KqbZLcmXKkfQb25H5PHAm1"
    "ZVkNJuXh+wAKDLDXCrIMCZI8iN9b9XNvOP3YLHcPPM4NxcuByjw39OYk9fhGDb86J277ftD9Tcjaf4te"
    "5kmfjYUa2xA2CeXFh1/W8fow8KuBmbY10jzpCmphjVcjXzQ/MskKnfzP39nzOSLGrlSoumOl3CQca9H2"
    "nw+YUuivm4N5R75FV6CiX5VK21624kAHurMXYvc44JQ3ViHfF6HCCmuw5iKVLX6oN8I/daO/RS8LF9qH"
    "zuyNon1HyA+Kw4R24cUAhqVDsS9xnAcrnkcQyk8MDyuao5+r8ZbT5pFnpPiP+g5tNM0riIHYiEOORx+i"
    "XQbh2OesD3W+qMxem35Ngmyzt+3oWyB1Cvm2MGwkSaL6kbL9EoS9xsQdkqykzeF9CoaPSslqy5JvgJ4W"
    "NIb7Xvscgd9oCZSxNxrIVToFi44jsFCBgdTMHbNzEs9nTl+RX/v+RMhc6SbmY/xtiNSX3UB6VoyZLG6H"
    "ByHCbYmBStLPwUtaSX4goJsLssjyYup9CoBG8+5mzRuYVXAC2qmf9g/LHvM0b9RaHX6oIvj86+f5AdDA"
    "/amDgYPLLSWt840qLqnnfpy+UVM4wud3uzAi+BeF872v15gixV6P1GMihHm3BqaZ4ePH/JI8OWRJXhTr"
    "KjvSrhi18jbA31dJpZTJBP+VCLti2LZk+aDaHV5md6iNEAHCAVrq4mzMH0V3E24CjjQMEGGKGEygSBoh"
    "dvPbb35+L7QKUFlvms82WF1ciMxXQsfiVwA1FOXNnQ8qDab7B8ORbPG2DRXB8vaQrv0F7N8BH1sWrKfz"
    "gQmaFFFio0mvS2ibUWW6bPb+zUPH+8cYSssL5oyyD9BCNWSdRMyiIvSb9FBlitRzjfPiTCACTiVw0VKb"
    "57hTb4pjzPRnDLf15Fg0vtj2FWZytWdGfvtT0tCGsuoDBo/jZ4Nb6LSt5ogRblKrddYur5xde5V3bkV5"
    "b65SNL5SwWuhpPz08prGMolNyx8w9uM85XAssnauuaWigzvznZehVqZBT23x1Bb64ceJHvVvg9PA9C8U"
    "WxVtJYnLkerFPI5tBSFMLrWpfAPZcVECsz2YV2ETHha0NCrAIemZ0cCVndvQ2a8IS+1RVGH4E65eEgr1"
    "CNvqZTBrtdbNs/ahKpVcH7+9votiszgLnOuKrzW6q7dOqDr4z0BI6s3xI7+uDA5U7VYt0I/1yxn6VglG"
    "sIvF/mIbXVwmEVzmzh7NED9A/uWuV+/6X0WFJc8Icv9KBUjpqEXcoU6ACMCXb89FQoCn5r6/RCU0V2vz"
    "k+68jC/0aTsJ3fS6N/sWhPr13zcOS7jnb3j23RnIT5sBPloYqxf4BhVDXH5/jhZgk+a/OOvv3/6BJynW"
    "/32H7r9Zu349yQcestBiNV5j7u+7izPi2Cr2rbOsnbMex5JII2HemNrzW8biZbKOVWZLWN/+jm9yZQO7"
    "9wqWE4T3QRnHYxpLZrU3A0gcFzN0n3YrChYZclGdKbz48zlpEMAfcjD3nH797BkOJiS+SHAi4487PXWO"
    "j/h6oCB5uKx4IILChpM9Gbmk8hifaE6PT9ASMJQxhkqFAErvjhRr2u9no8MoNb/oiiwZBeRSz4gMJgqy"
    "4Y444pwMhkM2D+oenFwyMRV2JrULB2Hn1bt6MCZd0qXg8cvUxaLkLvBGngv6WuFnbQWfpC4XcpA7936a"
    "gWVY/vpsjbMAfFZ+qIU4golGAw1AIpkf4Tf1bimwHvpuHYBhePUDFiCoqvetOuwR5fw1Boa7v0SAdME5"
    "A2Eb8zU2jHfrA4ql8aUKwvAanyl2dhTYyc2VQUYdm0N/JloqJMRhYGrw7VfyTUDKovwG4NoyE8TyrDBt"
    "zBffj37A0nymg7iP+onBVDCmvuwJD9CfPCTVHhdlVKqLTy7jgFlLs9GvKSacIjMpk+LJMcz36erwthh0"
    "W+K3OJ3uEsJ8a+z3HRzT0wXxq7zgaZgoTsMDZVaScvj3XvafKpdqMdi5c8dx4wDGp9xVB8GgYujwsdxD"
    "W0mEack/VvSx6T0J6K3Z1zSuVRP4O16lvfmqavPPmX6QsUML99tf50ZiZyn/QK2+Iggn0ZzQXYh6810u"
    "nreYU0bEUOoW14hcAGj1W8CXMl4vGjD9obxoKgT9g44f6rDSZRtgNxOU/bGjL2MA1PBksw/zV4HmLnZj"
    "9T5gjADk3BA1Hfi63q+7OKy/jwsxvSpvlpgfcj/8Ozb5MBt78tKqbzfh+xRV9syiAENBpXmV00H5geIz"
    "SMeGIVb4ZYRI3E99yA4gHYivLqu7RaVfCmHUHz4/EGkFNpAcz4hl6cozhGiRlrtmwet2vHw7PcLs2YAF"
    "1BEmqhqQ0E0UHAu6hsauZhU66X6Yww8otM1WrNu1vdeuL1YOK8bLfKSmhvv/tPfeOBYDa5veghjQu5De"
    "e8+M3hx6ew6BAZQrEKAxWocSQZEWow3MFoYt6J+ZYG5yA0HBDTrqBvuQVfV+z1OnioXv+4O33xp4wSD+"
    "O6u1Inn2pab22xg0SjaonRQ4/mTIcMbeokCkCsMjutQfTOacDh/SF31xyheRikSONtCXh+iFVBasylrn"
    "jUvyAxlY1BiVyL4xUenGXv0GBthNKPgW1cJGqBlCL/OmEsnAkz064h+UV0V2BRhKz8NXQXfuVjNuI/5O"
    "VzwcQHxlxT7p+iMFrGzOkjXwzt7Oe9O1Qip5J4GYF0l3Z7588WQ18DkncrQKYP82GXbXV0h7Q/vT6TAA"
    "rFLc/Sypd8onWeAKHN4xjEsDXN9cN/B1lFe32GjnCjSGOsiwyYhDmjD8nYDTN7kzvonLd+B6PONTDL+m"
    "y4fzVGVbBK+K5X7stniH4HPGKoT0+kXezsH6fi76OvDmbce7ZIioveLftaXc7lIVpccexiGn2p1gIDPC"
    "GPjnAJ2HuzEd07kfLzGByZ2JxVgeW+47Y5AkpyGuu4TYjrfexuXtjgIt+tJNEwAkEhzhVy24R312PHqq"
    "HGANQlW1QYDPT2dVVTAgNUqATusER3KyHwY0RCZ7XvtVxROS+YBDQ/jqD7kv9FNPDxwswoywnfatG2ZQ"
    "MCLjr/T0cV2Rx6sr1IeeA8sgnH1JrVxA38xvE7Z/X7wNGsu55nc9qjVIBNYL32rAMBl9B143M32sOXwz"
    "WXb71097t15PVGD4ByQngw14x+Vu6xQN3wmarudwAGEUYfiY6iX4FXAEMwhSNrxF2GH7uZ2/aIFJr02A"
    "t8LQGFZNhPPV8993KT9iI7qhV4bBUmUZz3eFv4tvEZKGDF6JjQHUrWthyhFTJPYvKFIpsApiiW8o7rWv"
    "URmYW6GOnKAZuBh9Q91M1TjX0QYXF14KbAGj/MDr6uVWzP3UZZEYHbapL1tn0u+wBoZv5s4vV8fjT4JO"
    "uc6UXkGJLt5VJfAKdvKz1PX8MhqwQTejSIElKZqq86Z+nU3VYpGkXAQ0QU1hOMfYKpuHHjvjSZ/0S71Y"
    "hZpNs1ypJj/HDxutGqnqAajDr8HVqGdiJc+k9fTEPZBDX82bFnUyk3xC+8WtQe2OfXhFfBii6o37VhQo"
    "8XMofN+0aMU2cWUvDsMh5APX/fTuK96xVazEIqHpoH0554MppDE7LVa/hgo30LhD0WzB5zL1AzyPh5Eb"
    "+nonpur53pSNqNmXVoYG0NYlndwWL2Ngv3Lk0cHEqtPbpSYr7Q9dWpOGQpNfgD+v3mxsW1Dx206dMl38"
    "CpAMHE31x12DVvMq0GXSADL15be1+TnwGcm3XyGSnLFHHFcMIgZqoUWm22r9RSMto0KlsfCL2etXLhiJ"
    "EXtyjU0mVatZi0PYdA0GY2ZeQW5kjXu6GuOZVsIUK+XyoEvS2n9SwJuT1JnusEjB1GT8L+lXZFjmcc6D"
    "lnETnU0CfKTFPArEu1N6xWk4yyqaJmNmx1/SYn42WkhyRpPunZsFRolSPTbzCL5Q34Dxl/QfveliPCHu"
    "B8HjFiJy+sulD38Q6q9KlY8KPXL8O14hk3YB4n3cZu+vJDy+FMgTYDOqJnDTl3Ial/U6jXnzSeAIGcO+"
    "7HJTrkZt+ixtK8ZA5NWeyZSi+4GK1pLh/Q4TKQWesgVHbqqHmZvV5dYg5dVzum9lh13p3Vf5feTu12iC"
    "mkb+6AmA7sIHp3w/uykIDjt3HWck+Yr0C0TFfjOm4/NJu6IbQVQ0+BxLhM/PY9mG83XC5qAMW7tOlL6x"
    "b7CyMWXcTySh7PWWj8AzokpPDyYwwhP5waJ6rCOrXbF2a666s/FKWuJfe1/32+VBP3lLdV6nE0lxFI0h"
    "lmWt1wmx2QMAb4sCcdaQeRSSvcU+D76lXD4OWWWI3hvTU+26ERQbc1ZcSA2gmiYMa1l0oeLrpayi3MiR"
    "98WaAZdDyimvUtNcwof98pBz1NScAWqThLLrfGwzqkUG8wEX7gs++aUJ5lIPPwUwHLXrqfjYwnq0pvJR"
    "JJdf9eb3x9F1cP50V7Mws2E9IKTy2H2qH1eitgLhGyQ4S7unDauFVm3dHKy2W/rwgy/b7gnjZ9HcKGZW"
    "WxRNk1d6MY0IfvNJ41rMlcsAAizSSETXIC1+Hs0Gc1x+fRaPDN/GpmbBGyloRGSqI2M8o+6xmCE66rsB"
    "CYR0uUAPsAM8npCgmiAgUKuP9tbW1WlVUZXzY93fPFU1cC3ksLTk4hDo6ApxaAdt4Yhvj5Fw2PrEk73W"
    "8mdJIACmJ22jBIhsPt329QVUt5Rk7zyVD/ZL9dasRx5OWr512QCZQD9hJjvA0xeDOMkUzYnt+rtVymEV"
    "6Kv2Xel3SkcmWT+W8SqoqCVLKPYYod6//cnDI6bH/l4ebXSMy3yiOoLNYjGHrEbMIyrqtWtf/HiS2TWR"
    "rba3U4lIYb40jkaL9eKVCi8M6bhykwbIXLcMYUakLugax3WVDSCj6DdrJhhXq/jeHZxGSR1mLwdxR7qe"
    "QkSu7RhaOFpkU/Q3iz2KQiyoADqwxlSjrZ5B4WNHFB7mkxXDPP6liu9Xf3Nnjp8jmnNwgMcjvCEDPxqS"
    "nDv8m0zE+bbvTfcv2Rf9FDv/YC3V//p//RMeyC//9i7NE4796Nrc1qENfHWn7pvvn3ZWkoNRzAlTvw1X"
    "V4cXLVpSm3wNWZgWJ25zNsDQaj/Cy03lVi+qN1kzc3eFZVZxGzQDLT0kl3aoIM97KRe8XMge12EIcg7u"
    "xv5ORSRwGsc2pqayG9yfcgLfT82P+Jm9RHNeBBgQ2eNkPtOxqjA1lUsiNFi4LCMFwckV6a9IE5zX8ZS3"
    "cUQyGIe9n0M8D/r9AWTS/uCvYvUrMa+cYvcLbfsQe7PEqcLCEmrfbIsy9CArtMOiDig5jnU0tnYJO+wi"
    "NoNg2wD53z5rd8+9z3E1+JjxBfeR7wI1eQ879ZPB+IZp+tEKfkj0Ek6A9bMltk78KfpRSJKufLPWft7B"
    "YRNwoG3faP0OrrYEb0M0rd2kf2/wqVALRNtQ0b5tO2+uLBvpyxvz/X0J88MQHOy2jHDqP+pryq6QKA3D"
    "Su3fGxC9eRwWL4KiDhaCxMH6VhQ/zsRTql2iJXw9FGld/Y1ZLNMtqaaIDGM5PC992YNNkGf3zoJJRZK4"
    "GqprRjSX3GsxiAmuNlSgQeg6tgypVzhaaUD3koF1FVDTOI2D2yUjkJsinbvbF9dbBmaWJXrP7UdSiWSu"
    "0EK83bb/tp0X7EuhX4X5pfYEhmc/Ab68PaNe+XszHn9v/m/peFCn+8PfopGOScccV+2KLu8gR3dvI3mC"
    "Q7e9Xcv2bXamPe4jvv/yM0gUEwprG3N4X8YBXOHCl51PvYM6j9XIbT6u42mShg5VjSvKr7EDpuE3lK34"
    "U+XzUs8IjTLxloFyixp8uM2pvPrtDN2PUfaB/CqMuRSoWJb3N5GNCvvbZm85tOQkaWuxOTcGys2NfaIB"
    "2cmPtgHzt5PT13yexDNIUcaCtT02HVNguLVgL6j7yL4R9FTEhEbTdQw/DWDPWVDM35YKWWPAqzjw7miC"
    "Qgg+8khRHEZIkC8lMQrWN5LgQ8kND0LXS1K9gSDA/hKage4FwG20pj20ZkHGpkrmtWDBkTL2KnHrR7qY"
    "9HZ67q2bClckOpMk4mAHhtrSZzFUv/1vi7TyvdjHIcQQflitKZCF+TGczhwgWiR+CBUsYpi1ukJmEVBM"
    "DIKYCZLY5YwzJ/HP0uwsKmQARLGR+CklB0VuF6WNuhW5miOGw2AOhHsvTBf8D9wdb+ZH1mAZT+/MEOn5"
    "44QNOUJzd6vzy30BZAj4xIBH6tkZ+eksChc14GDVgRgiBvABLjO6RhweYKSZYfZPmBVFKGERpeSPcgXy"
    "p0pjHUZEgCn5nNoovchvmPlH+7b+/T914KH0b+9c28M4ju4i/MbAsw1oOlU0AcYRkc+Y8RmL8IPuCJdL"
    "WXB40kotujeynzXdowVztI/+mYOQJhyTy8WEUjjHmfVfI7aYoyOhGRFupHpakHNaMQiMFwlrxghDebw+"
    "Cs/TAUg0mp4YbWtPXH6evbou+RMk2ZP+cPq5ajDHH9PgSY4R59tH+/l+1JBPqGuLNgDwkH6n+EbzfWK1"
    "U1liXIi3Dz2B+jq8qlF/UH+yPidh6IysLjDjcejXPgjfcZs4GUccL3F/22IpX18eqn4SAuj1oNjQfXxh"
    "mTzrGNHO7TIxGy3frt/P/jXeP26WPOMqBhge6Suz+pofuw9Euo5M7SIcunROAOONVTz8ADSQjCZUtPaC"
    "vXkntPGoCg3et0Qmb6OInPZkL4RZv7wF8A6pKBMJLFQiQRitWp6RSAws38Oila8utr6ITntM7wDlOqXd"
    "fpWcAAGHbZyGGW8WAJPKPkq6lvqkiL+fXtK6uHWnsWeUn0r/zdjAQNq3afH5ILKWnjCZdqz/SyV2i+Dt"
    "RKyvTYcyKgbWXYpGrZirpt2YKGsQ0nLmJbddBpRIqlteRGWV9yjNmbvcvqDA6IMmSfhZXnWkjkZHWXWv"
    "4Zi+rvSvBU2qINrJz74n3uTuHCe/SEroWRvRuHzJKpjQb8VKbQrJgxNCeIK7dGRfUw76K0lOlBJpsm6T"
    "t+tuHwWbs4Rwy8gE7l1yBBZc87tCeFEMUSXLEzlKgoLq5KFuV3DGXfsZmmaqv7aWE3Cb1EdtnRBiwlef"
    "NolfC7KmNXNFweVXvsNethzuazpM4dY+ghdjOsAUDgDHRfq0c3UC83FuP63QuniLN6RnI1E8G06AnP7d"
    "b4h8NNGQUnqTzwMEGK0JXtoKOa5iGcrKLfPzO/uPiS+dXiI1Z35TiNa9JvqSZEGbn9qeacodxNrc+kqd"
    "PjdjnvBcT62zCnOPomQJhNhVncrm3gpTM6zJ6/6DEOrqN/4jPbLgiIlQ5yAxO3jkYB/vw4bAPKch9UqM"
    "XCP5YZEy/WCip1AqOZhM81IA1B8GMnyGOj7mu7L5QeVtyxmJj7lvxuOKL60KmlQ1+Zb6URv9zaPLUxgq"
    "qz+hjRAqwzdeE1tmx0Fer/jNTpqe8U+FTsbyoaZbVthCXxHlpzwUlo0VVYoeToq+SDjnZn6SjgoJnfm8"
    "newQuoiJGLd7xO7mTohf3ZlzVqCvG7jisUoN6vIk8I7ysGqgteLmPa7OOYeN1MiyefYu7/6IFwjmbU3V"
    "mxqqlxeoKBtSSSzvSkeYGSsUn2/AN66syV/Ag4eTlNuYhaCeDRvBqX9Jbtsk1i8M+JIUARZMIwv1l9g6"
    "zrkXz7krv/XSWpQADQ9MsJ4PhCR7mtzVi16x6bcQF6+qLy5NtnxZdCmANSG2CxjS9Yn8/NfZatTVXl7k"
    "QmmtIz5gF7W9Pejl9N4pYv3zw6b0OD3Hxpwsckou+s4lroJEcPeq/N1HeAlExnnsJmocrhLjbqT3Pb55"
    "i7vFDvqywd4xmMFz+v1IGLMIIePKl8E9IJDtyjX+ACraOiVMxrc4Wz4HBL9BqtsBhTDlrZh44AjofTam"
    "YhR9GX7dz/6bL/xll84PIBmFjMPOTRmvhbdIZXyPga/UftOzutTNLpMES3peYThJ+ntNeyJzK0izmvXl"
    "0BWWH1y1Hq63AakvIeWNmZEQ1EZhK55xOInxfV+abMubSm+t2ZsRXpg+W546goJOlI0JHcFrYqZEF3P5"
    "HHJnPi8sdDL7YT1OEeSmEmboi+rmswN8xzFhL9zMkwyx3c/f5uy7arLssNJJtlQnzfgSH62fu0imvIJ3"
    "D5BWolMV/tbpjjPrXFb2UxhpF7Gk030arTl3pd3F4gdKstiPs/Kt0IRWwU0b0Lxq6o8Cb8C/oWpDGBsI"
    "qmGFdyg0WBIBkO6BB/c2OdQMryHVvmOIfjLWwfjk8fFbvk01lUOXcJBzTV6YevKX4rLhyYmmFac+4Awm"
    "OuFcx6s1lRZvlVzRXxpwuYbkfNWtwwMPKrMmsqGmm0WmsZlO/13frfIM9uUS6+YETxOsTx1GoaTZ9EP3"
    "biRaTQmxvlzW5KJqyysKIrTJtcAnUDw7IOmL7j7sXI0pIFlTIT1zRTXKPrKK//D8g3//P/8T7CE4/7bG"
    "cUPiCGmL0PX+n0MEx3ofsnIdz7AzfV8Y3HpxdAlpP+fKbz9V6DCtEw05//z62fs+t+d1HLeRsJuyqxCN"
    "+sr0WXewXk5HkSceeoZ8l7FLTWMxDbW3J9IKefUteB9qUI2trR6SpDIQBYGrTHf7dqSW162PG7qBD33j"
    "AsisayfOEbR6NbPsZ/gEJh+jN9WvczN3u0RJA3jBaG6hukyjRunfSz4BdWB+gfF4CAyD3GoGa9NfCqxC"
    "yRuw+fRDXnV9vnUP8JWI2twZ9N8rkG8h5d5ySd6JySm/S4ZuHT8AjCihjKA3kkSAC+f/DtEG6kLbxP3L"
    "ZqvC6QtIkpkMdSO5A7fsVHzQGAY2QXsut/aBLoOinor9fWyTp+7gO9PiTIqIhF2oaNv9RCGRtxbvB4Ld"
    "3SYzL5/JEZWtJPuGGeUZvZOBF6o3C/WOITKIGFZ23Cc9ex2lCH3VZQ9V6VFbeuVlescZ2mMjKLkCHfHY"
    "DDz8jbG6tFOz9s7OaZsxCOcHWnf9KxCVIstnfR3OLSZTA/K6myl++wkHwO6tr1nXBxFSEttzuGwQ5Hyr"
    "DDrj8jfOZ0SBvxdqxwHxiteX6J0kqGsSlb72p9UHEOOIchV4aX2aD9cMwmAoitQEEmJT9Rinh4OBsozF"
    "RWrXVmk8SegVrmlR/HjHBNugHVwpQzLTwVqlI5IvZQJHCaOdmBZCqdQJAQ2bcJGPZJrtgbLEmniUH6zz"
    "440JOriU9TJ0f4pibXW1VOgodEUMpaHj2Ehu0YMlU+jUyzMzQyMzYe9TyXxngJhkYlncy3N/BCY0PIpl"
    "1hRGyaOl+x1++WqikRbQ3nPlaYl2drzwGu7FOmvq8NvjNGjFGQ3jyhILHmK0jbRdSdCy+2lzAV9+WXq+"
    "pPpjiu+Eqr5ayNS4w74PDkXyI7Kmm7AuRti5Yt2t1VnpIsRHfmm9mebcmT+Owr7CbyLF121anlFFKvmm"
    "tPHR9UL9KD0RP6nO6fncHUx7+ZaPUwDdbnwkaImw5tZKdKizIm7jpm9XrLbr4g9EWlvORppMKWSiPeK2"
    "SpXBhIRGU5uzkMhVSykbb7T1VxUmAa1DkPzaBE3d9ovno+omTcbeougDTcQR4oFoYsr/uBT59hrXBCnZ"
    "3pXbbmT4VXGQXlxpRc5Mh1DT+C74Ib1D2Ju0aDijAVfGW2BLW5SKZFwedkSbQlgwMvTD0aPKjrvyJkkA"
    "YQ64QGHWTDNQM4oVlLFybVEFbefWCUHb0E10SOlU3kyt7qC+W+QN3s463hed9ZMoY9QYZeI7xBTU+6us"
    "dEuV28GaEi+47gmDf3wSpWoIf7vFgrtBVYufcQKphpJRo71ifBqeGOHW1QrkXxX5+tUNumGlwM4GLJQY"
    "qq6LKVgWFdisY7uX5LQHJAacq75A39mWRXdkDj/51asfxAFWRcPkQ6Vdgat6s2JJuN30rJ8vdk2r3mbI"
    "ZM+fATJ5O5tAF7x5XiLVzZ9xqfhH83b/4Z95L6H0/PfrN5A7gL8BgFOkYe/p9kY6ANP9G0N7Ht0ZzyWg"
    "x6on93EXsfWcKiGazutGQdFmD+pd9QPhMe/97bX9rE7HahwKOU+oOgIWra3soh+PW4k7C0cudpKjDr4S"
    "TZYkWuHUTYOOdAqawuZWTZaof/UQONXH3zfJUsLwrikgnNaINHTaMUNl9JhWJaBHYBY+OjeX4hwCtXlc"
    "SB6iO/P3eQy36CZk5v7m2C+EKKtS9lKKHMQl2PFp5mQGIxHTfC1UcaqRhFG7JQkiQPkRzktI9z2RCUwu"
    "5R39N6kNz0xC8xmDR6DvRAK6XyS+iRMCJdjIRp8FtJ365mu5x0OBJvCWjL/Fxhq5LLsKMixO/80Yfiml"
    "jFw6WT7GWYoKYguCNox081gBy1yTHR2Ibg149HsJYzhdXxj9iFPX+W1HHmPQwS17r8rHG+qaLbqudKjt"
    "sW6l5NjHL2K7yahk4uK+vAJiI5jTABxycNCNUhMjJiI+QOzVHhHzHRa/fNcox0suh32VG1kJGCiB3aAI"
    "zRt3me5ANMTDdyERsFaF2lJ07DcYAjhg7oY57HhKqbsucw+WdGWA/cfDUWHz+t3B3Oga6DqEg7Hz4sXw"
    "fw4jpIzisIzwNKFbCPe2tTOfiRR3yzfT07e4rNs6RfX8BjtQg8TFbeZD/8q9PzJNREmoGkL4qNw1M5nc"
    "3EDkMpAqSL/Gl4GYlLndz7awWNwVm66bJhecEntXREadJYNduneYl5fmm1nJzEOVUUm+fxBueAr6cvgB"
    "35rTv45qMAITsGyTyVHUFmzzNU3HZCz+AZCJU9ofCnUnWNXU1Z8PVbWELq2WKhkJzokDYv3c3qj44o+m"
    "/MaNvEqpS9S7n2cmrfXtmKhtyfG8sUrfmxMOCWFGok7DCCymXoaFN7F4foQoGA2zw/dhDq26UN5rPf2Q"
    "qMxAvAa0/u0yVyayRy2xdOqYLSfi5ouKBm3dhUhQ0X5kabRJ8kYYwyVNq3QMFwmOT967CMV1qGNOF4RE"
    "MFC1Bo0/0L56irjiPpr0sih5Hpto/lvRSANtQrkTJRCIB+is+c+bL3P//D6Q40qucXuJg7ZzmWZUYYrz"
    "IFQR/DXiyyB8/0c11/gME5Lao0UiFIHXIfGaRfIAVc95RSt4QhfsZw4AlcyWJvGhR8rQ8o1wbDaQ7tmS"
    "PZfx9lPvhiMSMeAFhMVLBaXkP4fvPAiNQ8ARvXB00WEN6bThSzEBSByR41eJ05R5m4zQMJiv0ueYhRSN"
    "UZvYfc9S6bqpZ6HXzWEPedPb1PMKzDT6fh/DVEOE1fPfy6Qh6hR/YhSOWuY27wNkZIHB5CDnoQGjkHyn"
    "Rsre9AUDUkM/O09leu3tYh9KPqxyqCLTDM786VH4CssHTZZulauu9nWeMHGSFWCTWTAqC1nRrbKVJJ/P"
    "K/LP+Us8uQ8+nqusGnZASPq3lRiFZbo4a/oh/L8lhzDu2y7pwiXX2DAn8DcCgk+mUkAtW/tEOcHgQrmd"
    "jum0QEEX8Dckts6P3NQytiYriaK3G+Jbfl4UvoQ2XAl+vUcGZDr++ZF6z7Tknz4UTYFkh/kUU0qgYrbE"
    "f4fOSGxjct0RfkLRCxDB8y8tm8tJRq0ftNmwpEYv56Dn6XA1eIAShq7ZvIKTLks4GOvXQJz4L9qDxGEV"
    "8+kbg3eizJM46tK+rk+yn22q7RXP6zGM0ZkCBwV6fJaMc39hPgxjt9T7W8K2lDOtwumoIzOIj+hp1gpm"
    "YCF5B6gTOBLOPSr+nVIrAWI9/Hu/NwSChFXqCJX/rQ8lbKPEMKq7O1A4TbayaxI48QlnC7ifM47tFLUt"
    "uGZ/FCFNnZB4B5M+0DMA1tWxzSTckuVFSV2mdp2WfB6VJlfgZDsq7oDKutB2ur0c1N3Q3z9fmnOnXhIa"
    "g1lbyOnGiHs5NSWiLGWXPELp/SIPAt4AeHWXe3EhzMLTfYyvTzzgz6XpnfL9xlHFdApjdEyTMJ92NG6G"
    "oeUS3crXLepJGDgoqbcqDxVaRnV0HCsM50tAWZB6MrvEL0IkUI3ErH3eQYlDuGeJ91WmMql94TsVm9eW"
    "gCdBCu42djCrrfqnQz/oW6sk9rrMcYUjz5cyo93tC4yeh+ht0pzAzembu2Q8dy6G7ld8jtEmBE40dGYF"
    "YuWnmGUI1gmvx7GuK+bx6SK83JFJurVFUdoRRr60rVbKnSRPO+hbX5Prq26bfGD6Zb+09YabbCnubPWO"
    "xiS+mkNN5HOe1iYGAG4TRhDQ3hbqJZCvty+FnXVgvqM8tNCTH3yggXGVVlawgckB2q+eBJ5q1OPMm4b7"
    "Cqgj181HmWUnU4s+H8q6cpzSkBy4CerURHOqmJMqegSUwbfj8QBHS42adpXofIZ/sKfwf/8nWEs0/u07"
    "0j2Ks+gbhK4v10AFAG+4pZ9ZTAhZTMTbF3mP+bI96zLWHGT7+3RcTX35IxQGFoz0DjqcxMybxnDXPkhU"
    "tqsULxbe4rfykfdhNNfgs7Kbo3NsxfWxD92iKpt0mrzvBknAfxcOoyQAlMAD6m30Jvxa2frQ3ZiSJvrf"
    "LLhghmEuR8n84B/iHbvDfbZYN+Po1E3mSdYgCOBwtUeq8KqBBOYjZpeoir90glZX/Kql9nvV5fXOX7dl"
    "kPmABuNptb+Y5uLaG+iE8bdO6dmUZyc9ujsp/J6qLcZyakRqfYZxLp4y1nN7WaXdRiPFvmEbOqvnZT7b"
    "uKET+PdWBIvCaC9dh9romnKPE+c6pELRVJ0VNYxi2ikSjVm0kQ+ET04HJdSXyaE08TiG//lqOp03vNYn"
    "030+CEuFcFskn0X3Hks+kdV/gCmKxmH1J1baIxFAqrGo9O9g/i1KpB9LcuJDtMMUn5H6u/iYxm++vUC+"
    "djb7GLjbe52WGEV4GArBVsSdY47Jj9ITdn6RLbq6EyllmAaABoPWvqF4suRF9LH7ltiTE9hzUNsGXE/3"
    "W6QJ1u/lDyMUmDxx8AGVvXiCDQG8WseWawbqlBlUmU1+K2BFasMfvwIJtU/yG+mUhX5pUEYN/mpWRTZi"
    "EA7Z+bIPFXzEH6tInMb+2XllbBhPiE0cNEZKmzwnOC47u0EorsRGgHiOVNGHSQgO5clhEK/MD4seHlD9"
    "6ycHXklFL/6+RMtP060Sg72DlsgRYME99bVFCl5XIVZrSmNApGzgrdsithzvP3L2e4nF8htvffexKFry"
    "NA57u/DvN00s81NaZKBtx/PHibQyikhBg441xb3POhLkl4Fc1XzrnA3kKsCXyAHQvbv4zkmuMawifbyR"
    "03rudYLQSBziIwyU+WZ3j69cZxJtf+7LekhpJVM7SfT89FeqfGuehrXzAdhlQyk034WzNQVVsvuGYFSa"
    "y4OIoKGee5SVx946m+mS3aJGHFyX8yEAi+RSAm+BRwtzhmpikDQQD4UNrZe/f9+n1ph8+GfZuhdh2W/r"
    "9pDZcyc9xFVGE9p329QrxyqaCpFFt3jSKi+s3TanhEGiv0FGiTASbYkC+00lhjAoinM5i16lTOvEUdVK"
    "Gnw2HewT/fK/SP12zNeGLaZWd/mX0bMEddNnP3ZlGL/SsuPjd7vJM6ZJDq7rw3UFw8wRkxB5mBY8LBGj"
    "bRE5k8c4PlKE3e++mCO5d6c6YGSY0KXwAVOyPJ9Qbt4fcdVquy6yb8uq0TQTSAMi4M/6gpzZ6LYLzT1c"
    "MrZPca/YlS3ErTX1MOYCblTCiz+N6QQxDOJQRiVwn/VveCdRg6w0wicFNbCrtbvw0whi2bgdbzj5FNvA"
    "rUQpUzOL5OghGLQ83t4itTLMy16W0BJ5PruzQkfMwDPF726xg2FF/uhrFYmiZ4yfI/Q9iuqWfCSvezkQ"
    "AwAUM2S3b97N02ZeghsHqraW9UOQ0eR/nQNIrx4veuZhpdjP9ci3TixVcAMYNhALpKzQgieQyPMneffv"
    "hwlhPRcosX2JZzFpDSg9w37Lv1lAhMxrrFV7xQham4lHwngEJbINiHxcOEPvgbtbMP1hs59ZHI13G7kw"
    "7Sldzr/xWLOYy8qwsyUb0cRwKOMI49Z1XYaASA0o66/VCQ5OuyPXM7P0RbhVo0U2FA6mQ36Nk39XSRW5"
    "7GtNfKviL0iC+LiO57ZmvT1zph/Aises1koLv9TYJduW5fKUpIQO3WhiKGstbjOFVMqdukXiVcJ9w63K"
    "qWkopkrv7B1tJPO8bpv/iKnTGxuN/sN56//wH/+ZPSfMfz23N4rr6BfB6CS9dbR461NF0jWSfXdS7hOM"
    "TTJWZXnFXaVUSbxz1nD12BAIzVIJIrz5qdcwHWY/d9/KE43H8unDcAsz+lMheHNFazhmurgFjWtws8tI"
    "t5/sHsRYInvlkvQDYwqUrboGDJHmfsEKUzTgPv2ElhVJxmaF62SvKhmP0HZJegdaAD1KgyWOQDx9oQFU"
    "qkD0C/IDRX7Xo4LWcF1TKedFeEnstwPqQeY5XzXF/bPdNebkIFF4KhYW7aVrMZq/inuNIhPdMpi4nv/x"
    "MYXUSvqHrrXOwvF+TAaFmhpQi3Oxam2xL10K3bJzTUQv+3u8g8WlXQHydxzY9cVAytyZyzA3BuUjNpZy"
    "8zC/yd2Cy1nn7ubUVR/HsI7TAs5j/IwxIlmPqid9Vp5TRPdg157ak6RItoePpI90hLwK0relksmrgDeS"
    "fXIDHF1GwwQQTYir4tDwR5PVKZYlmPv7zYwqbsctRK4DBNRBTYdrdnxFVsgWN6ggLWseutyfaziDR+5t"
    "raIhfzXMU0efPW4bIGrnGiaB66R7x+B/QcF9LHg+XBu9MSIS47qu6ksncxopb7D7bH/nzrKgAf4qq3XU"
    "ehOVghAZvelvOzHCPtSsnzivSfDrw9VAuXjEJKOPkj2z4IuXbsL9misOkn1lT2j/BT6/WYIJAv6seIof"
    "PlpXZ0yeYF5ZI5D8TNUHC4p8a4r+Wcbh0Eo9ijj7ZpyctTjJNIsnG4VpZhb9hydI1Y3GoA9gYzpThuDV"
    "9+Pgp9rOsIyd25gnxsTeb08cq3P5TsM+4ctL7GRuIW8xJJNL/rzXMFU6K+SLaz2frXKuvHIuZD7PqgWC"
    "OJkinYK3YOT+Zv1SfEGf1ltaZ576zfkeVv7IrMzv1ZDWMchGhouxGzqQg76wv31S15U599wvhnFD8+so"
    "iD2ySx2m8nhbzco3wbeaVTKJmpKH9YKdr1e4Mqz2t+5qPEjPtFE9RVs840R2FvvMKBAxcmi7+Qat16oE"
    "NYyWaG5J4X2g3BvjgwnZL6Y0gIJxB2EW4ZloaIWl8pTb+NkmZ0SWHDAMP8xC4+tU65OjC2g1vlRaOMbK"
    "p5EsdGwzGkty5fOEY30qpvh5nw2t6UkyoL4Y2UoCcExPnaHyUTYfk1/EglIyoH2tzy0f6nZkGI4qIv+m"
    "JB35ZQr6euPYOHUAqIsPek4rcVD+VI8ZWI5+EqqLNjHNL9a+0em/tXmpvVIAI8TuUrUn6UodOOC3Ukgg"
    "UqFnDqKopal1lOF700A1qaI2NNuWWq3sN8VPRVBt9wc4ArpPoPkYYILJzsKs0SsA1lJ8cUV1RztjhBxW"
    "baz2cuqhRMspBOGoRgnhOq5PfP6cAEp9F7GMt5j+qj9BmvhVYXD3s+5fwcfgANkSCfWBALMAwa1kwyOU"
    "/c7iJ8uzngisxVMOeIsm2yZetD1eS9+2gXYLcv56vbmCoQDgn71uGUd1pvIpIIoAYuxV70yK0JlmbQsE"
    "RrAAZFwmBE2o9HEaNMfo3MgzlCwC8FXgwrh1FX3R/XEWiM0Vh5jWn85Z3m5kXD3orA2mW+uvLgM4XMiD"
    "Jd3PDvauyGpJhgwKXH+OPNlB4jd63mmjq9rTxifVz689Y9u57k3G56+SVxP1Eb/aLmt/r3xiDCqf5kHz"
    "4GRh1oSu00B2AeVyusv6puHdjNDcGluZZ1kftDUpdktck5aXLv23+kzsluGbSyIVthsAr36EE306bc6j"
    "5GPsyjNgvoTBDpQu3y0NpqYpaeCENdcRIOA3y92yPK6w9RJqmIzCepIYT/0R0JtNRqD/1NjHCihdiO63"
    "gEDwU6Tgi33qw0Wd5AuTurRfExYTgdPVxZEgXqkGnK2BXt4eV1vdC/Ch4KtCbVnQZ2ceKahWee0NYbFw"
    "BP+T9TZR2LrQ34IZHbLaBRiQ85UzQKwqFuzDeSffsnObgAZc01rGh/JSJ2NgBOd8GLwurcDNVQA5dccK"
    "KZ42rflsq5xERq063qsSclEypDd5LPyl5pYVeu2bs9VUUPqtxcn0SQoyJ8aF437iGgexAPmunyqRXu1d"
    "f8HatFEvarTD9RGfcr7M+DWbNLrXsz3M3blKXyRNhXrECq/glc8Cq9cZ9uc4e0MIbxvudhYc6FXZjIQJ"
    "+tAPZe+9mJ9i41R1naKtCTML1Suy9vOIL9sTN3lXNKNTkx175wJ5cwzkX3LERePZ+LZKJdEtgG3QdwJ9"
    "SP0w6FeuqfyGVoHyw0HXlBmRLTSCWlZk5oqihh/5la3+A1D7M1XlE5U+BYAqMOL2leHwHnDFrdIU3ai5"
    "TQIBJSmPAIA0Dxu+AX1tmJiiW2/WrYic4IHYFqs3UMfff9+mFEj6bv2Feh8kgdY/vSIEZePTZZUUF5V3"
    "jLZtua7p0ipQMYsM1B/K5E2nIioUE5L5qkktKT9/Wzi7b1Sco+ggCDrUA1BRBU5+YoVYW/WDUQOfzF09"
    "6V/6Ws63bDlYOVXWtttc9lNCUF3C0QnxhwDuH0fpcX0VPjD73jMPw+Qgh0BAncfAFFbFusJYdyJFwvRT"
    "Uup3F2VWAW14gP60RRQytyHc7U1Z1FSVZlY5A9bnUz5BKBvarZQUKQHyiKeRpZnwr2g8X3ZTW8wUOG1/"
    "Us+/Cm3m2C1dsvL9oYuKmMvsCeZiu4tYgw8F2J1zbvJj19m24gRxefHDQh9PhalyBGMkPfZ59H7HkrQD"
    "h2gEgmiaFJyNnLTOViSC3Dmr6+cDJGzPjiWjFbGYxbpOIX+5SpMS7DCFoyuC4pdZKI3ftNW/NxFhW2NX"
    "ewyRNRgbBoGAEC1CpSQAhDprCXjKIrKNaJogXr80S4d9/FEwKiYzxPmXWpAq7GLaTgkbttzUvrb5G9mi"
    "07jXSYKfiLUzt1DmncfDTdnMaYhvGDeSg78MBHwOP8AjGCk1l955Kp4uyfgelF7YvlhHJxVNVuW6fr/4"
    "l95YyQeuzJkNMffT4h8GK6qKNWtr7QA2VHHpLgnk6icH5TcaAy276wbjGL81d5tlscES4cRV9APKZ6sg"
    "4AUtj4pAjkKBzQDsLYaeV4OmgBaZw/811gB5HfSIY02gwch2a8eF4g6pqY2UfJTBKS7xtrfywJeu+28O"
    "oAsJlkSMTmI9uvmL7TC4S97VwZu3vSXk61PlHD4KInxsjAjstfeJ9ZkCuMg6cl5LR+S6rxppxj6K9Alo"
    "nKoe6mDEvLrcUAGU0XOTCAmx5wZSU5Kzd+bZAJ1C24mbdYVO4QQ2KWG0sBadW4xMHD+52km8+TMzXQBh"
    "meu34vN5Wcv1xTHxUo3HCXuWbsrgKwTMIvP3ZFzw5Lku4Xh+Xj//wn3kgp/7yRF0sWHjQ9S36zKCkDSi"
    "01x+5zNZ9FW/AKRP11bjiC5OTD3eGF8O/lknTDRP/MmR3beukVb82IscZR+koTOtgPyPG1ptoXwFnK3I"
    "+ZBt8mUjnoRvFeNwkrExMIErPJd8srwQHbnGuqQmkPWC6SsnEK340/9o3vP//t/+p//8f/4v/8zuEB36"
    "bzOfD7KXfzOf9stNIzrgq58kr8TlIcsKsThsWSp7xKrpovlVjx8h6LtXdrLXsn55wgpEAl8w4c511d+I"
    "kbF97w6Vc7LAyxloFFZTpX7JkwMYrZ/YJ3S+o3pSw+Vz+unbxduLgAesquJHBg7aYM7NGwIr7nRjVhIO"
    "NhXXCkZ8MZqjEKbg6SvU4+JD18A82ZeMWMJPpgoF91kiwxqm6tRosxraV8ROjO6f6DIxyByvtu0PsOxy"
    "Zcxo0/3wV/srMrXu6Pzc3czez3hhZccGvgegmZxcjquTzwd+DTZoRcft16ouaBxWxFTZeEQlnqIB8VV2"
    "5txnZN547/brZGzGvTllYFinGIlipy3hkFD9ARJrdHju1EENAqKyhX+R3qhpSjAStZ9ECOh8Zn07n5hf"
    "YyIDy2uAkQU85GuCcPRtXQiJfo70Y+ttIyV3mDvemJWZPnqf+TKKWjvRzK1Z6pWwwDwR06d4a22hhvlL"
    "DrFydrxVBhfBimNGa0NxWrpFvcF2h8WbWlVvgkdfkAaYB+cGC/iQoIfiAJhHcO5txsyiX8W8hAaovi6R"
    "trrGCOJ+4PAx5GH8Pre2CQjK6SdCsePPp814RXgmV/bUhp0mRl2w7po6C3gL9S/+DvzWBbqHIOLhoMj2"
    "YbfPToFs3gJx1Vq3OIzx3dcr+8HZvdy9xfNDkOGXr1Z4OPGrIqzJrdb8TMVqse9424wH4iPGL4jDWOc+"
    "0i5Ft2JKpKobhkGJWkRCdnzL2ckt4A7nzBhuQ79cTXZK7SNA6gn7IQVWXrY3mwirXKyQHStgfmI5BTYX"
    "iqVjvmuv/wcW5a1lNryFljmauGP7jwlcyWv/jX9S7fB5cTtBU1M5Ll6mu5WCc9mWuX5+ahvTYZy5wF3R"
    "Jb6sEySUrNvZvudNIOwhxPUgxz6ibDlYcMu6T0FKQwbuPRIjfFs/lTDp9Ateys/mltJWKoUgyg5kLBjp"
    "U3Z7507KOzoKYKWjFyDPFLjoLeKqHzKekaQJnKM45bJocGF9HMG/rz2d0nTKdUtQThYRTZAJd6b4pAjZ"
    "F9NGmPb2FaWqrtT30Y+ii1wJwgfAnoQfiaZrjCwKEZ3ARD7d64mUr9xZPure/8PVL28y/SuW/hVL/4ql"
    "f8XS/69i6T/9H/8kMMnBf59MR/H/JlNlPaAnySAE/7BwUJSTg7bQzQ83a/Yu46YTdCnhDsHA6QaxyCzu"
    "tNYxUatB01sn5trOG3+DG17uaXJSyCtIFuXjU37JHrseo4GTz/4Y3YPkiUfY5UNOFUqWLBG8gpoIDhu4"
    "TlVZBeixpPtVWr8NyIcdbjEeg9rQoO0Sc5gucNxqJkAUPR2gnlSSaZSzGMmBTbZmhhSDHYwMHcFtBAfT"
    "2dsifSUmD/B9HMXt2V6Kslk23mXIXIow7zyjf31NSZiiH1/IVSARU9dfVQXFB8samHn2isMaVAW0Brip"
    "HbwnevCV0FowrltVJZxn1hGTKVNyaRCi4+e5F+hsxwjkfhj+mGb2wcleRzdFiF1m0q5PMXJvTn7w5RCR"
    "nD4/Gsx/CqAxibxmz1ndw4BPGCrcRUx4CHLU00UeDvLgZLkJ6+b12lboRUaXGHrW6d+yfOcyi4iSEbHX"
    "uOfDeHNYW8piVGbkNh09BbWnbkjiQGscTDByI7lK0WNcqkDXGRdC8H/gdotez6jHvKdJQ1OndQkzXak8"
    "iEsHM0OAIs2SweSmAz6TWpcmT/iH7i9Yc9VJAVD9A+1ttFL4of3QriQddUYhFiE7owLSL0RwD4GJ5Lzo"
    "anl81eYI2LKRMRZMNIr+xt3vsT9gRDMnQwfwEHXnMSLjdXYMrExk/OaW3VF6nsK66BARaggxVjef9IwL"
    "9XUnlLVCxmp+hbv7Aoe2KYX3+UU12eDGKP30TdVkl9XDjSPSoJGixk3+LP0KmCLDQ22LGwE+oyu/mf0H"
    "PijQPpV7evRRBDD2k4dXsww20701/2DdgbyW9gG7bboFI5wEzfIgoqzE2TMvUuctABh40Aj8nXdsPuNP"
    "8xt/O4Zd4fQhTnPqPWvXjKswYYVTE+uT3PXocEcrwjWK7QFiL1vBybbVWdNtmvYvg9urvseGjnE4rA2o"
    "YCHeBQGUzOUA49rtHbuEJvYR8sE4CPa6bx+sbMeyHJGCg5qR3r3YdwQslRK8Y2H1+RizbAix5cICD6yO"
    "y+D5TUIB/R4jXDslWjIdsg7yMmL4arb4KBvw1nMpOeHId5sf9o8S6F/x86/4+Vf8/Ct+/j+Pn3/3XwC9"
    "/oj6"
)

# Кэш: emoji -> путь к временному PNG файлу
_EMOJI_PNG_CACHE = {}
_EMOJI_PNG_DIR   = None
_EMOJI_MAP       = None   # заполняется лениво

def _get_emoji_map():
    global _EMOJI_MAP, _EMOJI_PNG_DIR
    if _EMOJI_MAP is not None:
        return _EMOJI_MAP
    try:
        raw = _zlib.decompress(_b64.b64decode(_EMOJI_PNG_DATA))
        _EMOJI_MAP = _ejson.loads(raw.decode("utf-8"))
        # Определяем папку для PNG файлов
        if PLATFORM == "android":
            try:
                from android.storage import app_storage_path
                _base = app_storage_path()
            except Exception:
                _base = _eos.path.dirname(_eos.path.abspath(__file__))
        else:
            _base = _eos.path.dirname(_eos.path.abspath(__file__))
        _EMOJI_PNG_DIR = _eos.path.join(_base, ".emoji_cache")
        _eos.makedirs(_EMOJI_PNG_DIR, exist_ok=True)
    except Exception as ex:
        _EMOJI_MAP = {}
        _EMOJI_PNG_DIR = tempfile.gettempdir()
    return _EMOJI_MAP

def get_emoji_png(emoji_char):
    """Возвращает путь к PNG файлу для emoji. Создаёт файл если нужно."""
    if not emoji_char:
        return None
    # Нормализуем — убираем variation selector
    em_plain = emoji_char.replace('\ufe0f', '').strip()

    # Проверяем кэш
    if emoji_char in _EMOJI_PNG_CACHE:
        return _EMOJI_PNG_CACHE[emoji_char]
    if em_plain in _EMOJI_PNG_CACHE:
        return _EMOJI_PNG_CACHE[emoji_char]

    emap = _get_emoji_map()
    # Ищем с variation selector и без
    b64data = emap.get(emoji_char) or emap.get(em_plain)
    if not b64data:
        return None

    if _EMOJI_PNG_DIR is None:
        _get_emoji_map()  # инициализируем директорию

    try:
        # Безопасное имя файла
        safe = "_".join(f"{ord(c):05X}" for c in em_plain if c.strip())
        if not safe:
            safe = f"{abs(hash(emoji_char)):08X}"
        path = _eos.path.join(_EMOJI_PNG_DIR or tempfile.gettempdir(), f"{safe}.png")

        if not _eos.path.exists(path):
            png_bytes = _b64.b64decode(b64data)
            with open(path, "wb") as f:
                f.write(png_bytes)

        if _eos.path.exists(path) and _eos.path.getsize(path) > 0:
            _EMOJI_PNG_CACHE[emoji_char] = path
            _EMOJI_PNG_CACHE[em_plain] = path
            return path
    except Exception:
        pass
    return None


def _has_emoji(text):
    """True если строка содержит emoji символы."""
    import re
    return bool(re.search(
        "[\U0001F000-\U0001FFFF\U00002600-\U000027FF"
        "\U00002300-\U000023FF\U00002B00-\U00002BFF"
        "\U0001F900-\U0001F9FF]", text))

# ── EmojiLabel: BoxLayout с Image(png) + MDLabel(текст) ─────────────────────
_ALL_EMOJI_WIDGETS = []   # weakref список для будущих обновлений

def EmojiLabel(text="", font_style="Body1", **kwargs):
    """
    Надёжный виджет для текста с emoji.
    - Только emoji → Image (PNG)
    - Текст + emoji → горизонтальный BoxLayout: [Image|Image...] + MDLabel
    - Только текст  → обычный MDLabel
    Гарантирует горизонтальный текст на всех платформах.
    """
    emap     = _get_emoji_map()
    box_h    = kwargs.pop("height",    S(32))
    sh_y     = kwargs.pop("size_hint_y", None)
    halign   = kwargs.pop("halign",    "left")
    valign   = kwargs.pop("valign",    "middle")
    bold_kw  = kwargs.pop("bold",      False)
    tc_kw    = kwargs.pop("theme_text_color", "Primary")
    txtc_kw  = kwargs.pop("text_color", None)

    EMOJI_RE = _re_compile_emoji()

    emoji_matches = list(EMOJI_RE.finditer(text))
    stripped = text.strip()

    # ── Только emoji (один символ) → просто Image ────────────────────────────
    if stripped in emap and len(emoji_matches) == 1 and \
            emoji_matches[0].group() == stripped:
        path = get_emoji_png(stripped)
        if path:
            img = KivyImage(source=path,
                            size_hint=(None, None),
                            size=(box_h, box_h),
                            allow_stretch=True, keep_ratio=True)
            img._emoji_text = text
            _ALL_EMOJI_WIDGETS.append(_weakref.ref(img))
            return img

    # ── Нет emoji → чистый MDLabel ───────────────────────────────────────────
    if not emoji_matches:
        lbl = MDLabel(text=text, font_style=font_style,
                      size_hint_y=sh_y, height=box_h,
                      halign=halign, valign=valign,
                      bold=bold_kw,
                      theme_text_color=tc_kw,
                      **({} if txtc_kw is None else {"text_color": txtc_kw}),
                      **kwargs)
        lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        lbl._emoji_text = text
        return lbl

    # ── Смешанный текст + emoji → горизонтальный BoxLayout ───────────────────
    box = MDBoxLayout(orientation="horizontal",
                      size_hint_y=sh_y, height=box_h,
                      spacing=S(3))
    box._emoji_text = text

    tokens = []
    last = 0
    for m in emoji_matches:
        if m.start() > last:
            tokens.append(("text", text[last:m.start()]))
        tokens.append(("emoji", m.group()))
        last = m.end()
    if last < len(text):
        tokens.append(("text", text[last:]))

    em_sz = int(box_h * 0.85)

    for ttype, tval in tokens:
        if ttype == "emoji":
            # Каждый emoji-символ рендерим отдельно
            for ch in _split_emoji(tval):
                path = get_emoji_png(ch)
                if path:
                    img = KivyImage(source=path,
                                    size_hint=(None, None),
                                    size=(em_sz, em_sz),
                                    allow_stretch=True, keep_ratio=True,
                                    pos_hint={"center_y": 0.5})
                    box.add_widget(img)
                # emoji не в базе — просто пропускаем (не рисуем □)
        else:
            tval_clean = tval.strip()
            if not tval_clean:
                continue
            lbl_kwargs = dict(
                text=tval_clean,
                font_style=font_style,
                size_hint_x=1,
                size_hint_y=1,
                halign=halign,
                valign=valign,
                bold=bold_kw,
                theme_text_color=tc_kw,
            )
            if txtc_kw is not None:
                lbl_kwargs["text_color"] = txtc_kw
            lbl = MDLabel(**lbl_kwargs)
            # КРИТИЧНО: text_size задаём через bind чтобы текст был горизонтальным
            lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
            box.add_widget(lbl)

    _ALL_EMOJI_WIDGETS.append(_weakref.ref(box))
    return box


def _re_compile_emoji():
    """Возвращает скомпилированный RE для поиска emoji."""
    import re
    return re.compile(
        "[\U0001F000-\U0001FFFF"
        "\U00002600-\U000027FF"
        "\U00002300-\U000023FF"
        "\U00002B00-\U00002BFF"
        "\U0001F900-\U0001F9FF"
        "\u2702-\u27b0"
        "\u2500-\u25FF"
        "\ufe0f"          # variation selector
        "\u200d"          # ZWJ
        "]+",
        re.UNICODE
    )


def _split_emoji(emoji_str):
    """Разбивает строку emoji на отдельные символы (учитывая ZWJ последовательности)."""
    result = []
    i = 0
    while i < len(emoji_str):
        # Собираем ZWJ-последовательность (семья, флаги и т.д.)
        seq = emoji_str[i]
        j = i + 1
        while j < len(emoji_str) and emoji_str[j] in ('\u200d', '\ufe0f'):
            seq += emoji_str[j]
            if j + 1 < len(emoji_str):
                seq += emoji_str[j + 1]
                j += 2
            else:
                j += 1
        result.append(seq)
        i = j if j > i + 1 else i + 1
    return result


def update_emoji_label(widget, new_text):
    """Обновляет текст/изображение EmojiLabel виджета."""
    if widget is None:
        return
    widget._emoji_text = new_text
    if isinstance(widget, KivyImage):
        path = get_emoji_png(new_text.strip())
        if path:
            widget.source = path
        return
    if isinstance(widget, MDLabel):
        widget.text = new_text
        return
    if isinstance(widget, MDBoxLayout):
        # Обновляем первый MDLabel в боксе
        for child in reversed(widget.children):
            if isinstance(child, MDLabel):
                child.text = new_text.strip()
                return
        # Если нет Label — обновляем первый Image
        for child in reversed(widget.children):
            if isinstance(child, KivyImage):
                path = get_emoji_png(new_text.strip())
                if path:
                    child.source = path
                return



# ═══════════════════════════════════════════════════════════════════════════
#  Голосовой помощник
# ═══════════════════════════════════════════════════════════════════════════
class CalendarWidget(MDBoxLayout):
    MONTH_NAMES = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                   "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    DAY_NAMES   = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]

    def __init__(self, on_select=None, task_dates=None, **kw):
        super().__init__(**kw)
        self.on_select  = on_select
        self.task_dates = task_dates or set()
        self.orientation = "vertical"
        self.spacing    = S(2)
        self.size_hint_y = None
        self.height     = S(340)
        now = datetime.now()
        self.yr = now.year; self.mo = now.month
        self.sel = date.today()
        self._draw()

    def _draw(self):
        self.clear_widgets()
        # ── Заголовок месяца ──
        hdr = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(44))
        pb = MDIconButton(icon="chevron-left", size_hint_x=None, width=S(40),
                          theme_text_color="Custom", text_color=C["text2"])
        nb = MDIconButton(icon="chevron-right", size_hint_x=None, width=S(40),
                          theme_text_color="Custom", text_color=C["text2"])
        pb.bind(on_release=self._prev); nb.bind(on_release=self._next)
        mo_lbl = MDLabel(text=f"{self.MONTH_NAMES[self.mo-1]} {self.yr}",
                         font_style="Subtitle1", bold=True, halign="center",
                         valign="middle", theme_text_color="Custom", text_color=C["text"])
        mo_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        hdr.add_widget(pb); hdr.add_widget(mo_lbl); hdr.add_widget(nb)
        self.add_widget(hdr)

        # ── Строка дней недели ──
        d_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(28))
        for d in self.DAY_NAMES:
            dl = MDLabel(text=d, font_style="Caption", halign="center", valign="middle",
                         theme_text_color="Custom", text_color=C["text2"])
            dl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            d_row.add_widget(dl)
        self.add_widget(d_row)

        # ── Сетка дней ──
        CELL = S(38)
        grid = GridLayout(cols=7, size_hint_y=None, spacing=S(1),
                          row_force_default=True, row_default_height=CELL)
        grid.bind(minimum_height=grid.setter("height"))

        first  = date(self.yr, self.mo, 1)
        offset = first.weekday()          # 0=Пн
        n_days = cal_module.monthrange(self.yr, self.mo)[1]
        today  = date.today()
        # Принудительно задаём высоту через число строк
        n_rows = (offset + n_days + 6) // 7
        grid.height = CELL * n_rows + S(1) * (n_rows - 1)

        for _ in range(offset):
            grid.add_widget(Widget(size_hint_y=None, height=CELL))

        for d in range(1, n_days+1):
            cur      = date(self.yr, self.mo, d)
            is_today = (cur == today)
            is_sel   = (cur == self.sel)
            ds       = cur.strftime("%d.%m.%Y")
            has      = ds in self.task_dates

            from kivy.uix.label import Label as _KLabel
            from kivy.metrics import sp as _sp
            from kivy.uix.floatlayout import FloatLayout as _FL

            bg_col  = C["accent"] if is_today else (C["acc_s"] if is_sel else (0,0,0,0))
            txt_col = C["surf"]   if is_today else (C["accent"] if is_sel else C["text"])
            day_str = str(d)

            cell_fl = _FL(size_hint_y=None, height=CELL)

            def _draw_fl_bg(w, *_, _bg=bg_col, _has=has,
                            _is_today=is_today, _is_sel=is_sel):
                w.canvas.before.clear()
                cx = w.x + w.width / 2
                cy = w.y + w.height / 2
                r  = S(16)
                with w.canvas.before:
                    Color(*_bg)
                    Ellipse(pos=(cx - r, cy - r), size=(r*2, r*2))
                    if _has and not _is_today and not _is_sel:
                        Color(*C["accent"])
                        dr = S(2.5)
                        Ellipse(pos=(cx - dr, w.y + S(3)), size=(dr*2, dr*2))

            cell_fl.bind(pos=_draw_fl_bg, size=_draw_fl_bg)

            num_lbl = _KLabel(
                text=day_str,
                halign="center", valign="middle",
                color=txt_col,
                size_hint=(1, 1),
                pos_hint={"x": 0, "y": 0},
                font_size=_sp(11))
            num_lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], s[1])))
            cell_fl.add_widget(num_lbl)
            cell = cell_fl

            def _tap(w, t, dt=cur):
                if w.collide_point(*t.pos): self._pick(dt); return True
            cell.bind(on_touch_up=_tap)
            grid.add_widget(cell)

        self.add_widget(grid)
        # Обновляем высоту виджета сразу и через bind
        total_h = hdr.height + d_row.height + grid.height + S(8)
        self.height = total_h
        def _upd_h(*_):
            self.height = hdr.height + d_row.height + grid.height + S(8)
        grid.bind(height=lambda *_: _upd_h())
        Clock.schedule_once(lambda *_: _upd_h(), 0)
        Clock.schedule_once(lambda *_: _upd_h(), 0.3)

    def _prev(self,*_):
        self.mo-=1
        if self.mo<1: self.mo=12; self.yr-=1
        self._draw()

    def _next(self,*_):
        self.mo+=1
        if self.mo>12: self.mo=1; self.yr+=1
        self._draw()

    def _pick(self,d):
        self.sel=d
        if self.on_select: self.on_select(d)
        self._draw()

    def refresh_dates(self, task_dates):
        self.task_dates=task_dates; self._draw()


# ═══════════════════════════════════════════════════════════════════════════
#  Карточка задачи со свайпом
# ═══════════════════════════════════════════════════════════════════════════
class TaskCard(MDCard):
    SWIPE_THRESHOLD = 60   # пикселей для срабатывания свайпа

    def __init__(self, task_id, title, task_date, priority="Средний",
                 done=False, category="", comment="", subtasks=None,
                 original_date="", show_cat=False, time_str="", **kw):
        super().__init__(**kw)
        self.app           = MDApp.get_running_app()
        self.task_id       = task_id
        self.title         = title
        self.task_date     = task_date
        self.priority      = priority
        self.done          = done
        self.category      = category
        self.comment       = comment
        self.subtasks      = subtasks or []
        self.original_date = original_date
        self.show_cat      = show_cat
        self.time_str      = time_str
        self.orientation   = "vertical"
        self.spacing       = S(4)
        self.size_hint_y   = None
        self._touch_start_x = None
        self._swiping      = False

        is_fem = self._fem()
        if is_fem:
            self.radius=[S(18)]; self.elevation=1; self.md_bg_color=C["surf"]
            self.padding=[S(14),S(12),S(12),S(10)]
        else:
            self.radius=[S(10)]; self.elevation=0; self.md_bg_color=C["surf"]
            self.padding=[S(12),S(10),S(10),S(8)]

        self._build(); self._calc_h()

    def _fem(self): return THEMES.get(MDApp.get_running_app().theme_name,{}).get("gender")=="female"

    def _build(self):
        is_fem = self._fem()
        # ── Полоска приоритета слева ─────────────────────────────────────
        _prio_colors = {
            "Высокий": C.get("red",   (0.9, 0.3, 0.3, 1)),
            "Средний":  C.get("accent",(1.0, 0.6, 0.0, 1)),
            "Низкий":   C.get("green", (0.3, 0.8, 0.4, 1)),
        }
        _sc = _prio_colors.get(self.priority, C.get("surf2", (0.2, 0.2, 0.2, 1)))
        from kivy.graphics import Color as _KCS, Rectangle as _KRECT
        with self.canvas.before:
            _KCS(*_sc)
            self._stripe_rect = _KRECT(pos=(self.x, self.y), size=(S(4), self.height))
        def _upd_stripe(*_):
            self._stripe_rect.pos  = (self.x, self.y)
            self._stripe_rect.size = (S(4), self.height)
        self.bind(pos=_upd_stripe, size=_upd_stripe)

        row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                          height=S(44), spacing=S(8), padding=[S(6),0,0,0])
        # чекбокс
        ico = "check-circle" if self.done else ("radiobox-blank" if is_fem else "checkbox-blank-outline")
        col = C["green"] if self.done else C["text2"]
        cb = MDIconButton(icon=ico, size_hint_x=None, width=S(34),
                          theme_text_color="Custom", text_color=col)
        cb.bind(on_release=self._toggle); row.add_widget(cb)
        self._cb_icon = cb

        # текст
        txt_col = C["text2"] if self.done else C["text"]
        ti = MDBoxLayout(orientation="vertical", spacing=S(1))
        title_lbl = MDLabel(text=self.title, font_style="Body1",
                            theme_text_color="Custom", text_color=txt_col,
                            halign="left", valign="middle",
                            shorten=True, shorten_from="right")
        self._title_lbl = title_lbl
        title_lbl.bind(size=lambda w,s: setattr(w, "text_size", (s[0], None)))
        ti.add_widget(title_lbl)
        sub_parts = []
        if self.task_date: sub_parts.append(self.task_date)
        if self.time_str:  sub_parts.append(self.time_str)
        if self.show_cat and self.category: sub_parts.append(self.category)
        if sub_parts:
            sub_lbl = MDLabel(text="  ".join(sub_parts),
                              font_style="Caption", theme_text_color="Secondary",
                              halign="left", valign="middle")
            sub_lbl.bind(size=lambda w,s: setattr(w, "text_size", (s[0], None)))
            ti.add_widget(sub_lbl)
        row.add_widget(ti)

        # подзадачи — прогресс-бар + кнопка просмотра
        if self.subtasks:
            dn = sum(1 for s in self.subtasks if s.get("done"))
            tot = len(self.subtasks)
            pct_sub = dn/tot if tot else 0
            sub_col = MDBoxLayout(orientation="vertical", size_hint_x=None,
                                   width=S(54), spacing=S(2))
            cnt_row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                  height=S(20), spacing=S(2))
            cnt_lbl = MDLabel(text=f"{dn}/{tot}", font_style="Caption",
                              halign="center", theme_text_color="Custom",
                              text_color=C["accent"], size_hint_x=1)
            cnt_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            cnt_row.add_widget(cnt_lbl)
            # Кнопка просмотра подзадач
            sub_btn = MDIconButton(icon="format-list-checks",
                                   size_hint=(None,None), size=(S(22),S(20)),
                                   theme_text_color="Custom", text_color=C["accent"])
            def _show_subs(*_, subs=self.subtasks, app=self.app):
                from kivy.uix.modalview import ModalView
                mv = ModalView(background_color=(0,0,0,0.5), auto_dismiss=False,
                               size_hint=(0.9, None))
                card = MDCard(orientation="vertical", size_hint_y=None,
                              radius=[S(14)], elevation=6,
                              md_bg_color=C["surf"], padding=[S(14),S(12)])
                card.bind(minimum_height=card.setter("height"))
                # Заголовок
                hdr = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                  height=S(36), spacing=S(6))
                dn2 = sum(1 for s in subs if s.get("done"))
                h_lbl = MDLabel(text=f"Подзадачи {dn2}/{len(subs)}",
                                font_style="Subtitle2", bold=True,
                                theme_text_color="Primary", halign="left", valign="middle")
                h_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
                hdr.add_widget(h_lbl)
                # Кнопка озвучить всё
                spk = Widget(size_hint_x=None, width=S(4))
                hdr.add_widget(Widget())
                card.add_widget(hdr)
                # Список подзадач
                for sub in subs:
                    srow = MDBoxLayout(orientation="horizontal",
                                       size_hint_y=None, height=S(40), spacing=S(8))
                    ico = "checkbox-marked" if sub.get("done") else "checkbox-blank-outline"
                    scb = MDIconButton(icon=ico, size_hint_x=None, width=S(32),
                                       theme_text_color="Custom",
                                       text_color=C["accent"] if sub.get("done") else C["text2"])
                    def _tog(w, s=sub):
                        s["done"] = not s.get("done", False)
                        w.icon = "checkbox-marked" if s["done"] else "checkbox-blank-outline"
                        w.text_color = C["accent"] if s["done"] else C["text2"]
                        app.save_tasks()
                        # Обновить счётчик
                        dn3 = sum(1 for x in subs if x.get("done"))
                        h_lbl.text = f"Подзадачи {dn3}/{len(subs)}"
                        cnt_lbl.text = f"{dn3}/{len(subs)}"
                    scb.bind(on_release=_tog)
                    srow.add_widget(scb)
                    # Кнопка озвучить одну подзадачу
                    spk1 = Widget()
                    # tts removed
                    s_lbl = MDLabel(text=sub.get("title",""), font_style="Body2",
                                    theme_text_color="Custom",
                                    text_color=C["text2"] if sub.get("done") else C["text"],
                                    halign="left", valign="middle")
                    s_lbl.bind(size=lambda w,s2: setattr(w,"text_size",(s2[0],None)))
                    srow.add_widget(s_lbl)
                    card.add_widget(srow)
                # Кнопка закрыть
                close_btn = MDRaisedButton(text="Закрыть", md_bg_color=C["surf2"],
                                            size_hint_y=None, height=S(40),
                                            on_release=lambda *_: mv.dismiss())
                card.add_widget(Widget(size_hint_y=None, height=S(6)))
                card.add_widget(close_btn)
                mv.add_widget(card); mv.open()
            sub_btn.bind(on_release=_show_subs)
            cnt_row.add_widget(sub_btn)
            sub_col.add_widget(cnt_row)
            prog_w = Widget(size_hint_y=None, height=S(4))
            _pf = [pct_sub]
            def _dp(w,*_):
                w.canvas.clear()
                with w.canvas:
                    Color(*C["acc_s"])
                    RoundedRectangle(pos=w.pos, size=w.size, radius=[S(2)])
                    if _pf[0] > 0:
                        Color(*C["accent"])
                        RoundedRectangle(pos=w.pos, size=(max(w.width*_pf[0],S(2)),w.height),
                                         radius=[S(2)])
            prog_w.bind(pos=_dp, size=_dp); sub_col.add_widget(prog_w)
            row.add_widget(sub_col)

        # три точки
        menu_btn = MDIconButton(icon="dots-vertical", size_hint_x=None, width=S(28),
                                theme_text_color="Custom", text_color=C["text2"])
        menu_btn.bind(on_release=self._show_menu); row.add_widget(menu_btn)
        self.add_widget(row)

        # приоритет (женский)
        if is_fem and not self.done:
            PMAP={"Высокий":("Срочно",C["red"],(1.0,0.90,0.90,1)),
                  "Средний":("Важно",C["accent"],C["acc_s"]),
                  "Низкий":("Легкое",C["green"],(0.88,0.96,0.92,1))}
            ICONS={"Высокий":"fire","Средний":"star","Низкий":"heart"}
            ptxt,pcol,pbg=PMAP.get(self.priority,("",C["text2"],C["surf2"]))
            if ptxt:
                tag_row=MDBoxLayout(size_hint_y=None,height=S(28),padding=[S(44),0,0,0])
                tag=MDCard(size_hint=(None,None),size=(S(96),S(24)),
                           radius=[S(12)],elevation=0,md_bg_color=pbg)
                tr=MDBoxLayout(orientation="horizontal",spacing=S(4),padding=[S(8),0])
                tr.add_widget(MDIconButton(icon=ICONS[self.priority],size_hint_x=None,
                                            width=S(18),theme_text_color="Custom",text_color=pcol))
                _lbl_tmp=MDLabel(text=ptxt,font_style="Caption",
                                       theme_text_color="Custom",text_color=pcol,
                                       halign="left", valign="middle")
                _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
                tag.add_widget(tr); tag_row.add_widget(tag); self.add_widget(tag_row)
                tr.add_widget(_lbl_tmp)

        # ── Строка тегов ─────────────────────────────────────────────────
        task = self.app.tasks.get(self.task_id, {})
        _tags = task.get("tags", [])
        if _tags:
            tags_row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                    height=S(26), spacing=S(4),
                                    padding=[S(44), 0, S(4), 0])
            for tag in _tags[:4]:
                tag_pill = MDCard(size_hint=(None, None),
                                   size=(S(len(tag)*7+18), S(20)),
                                   radius=[S(10)], elevation=0,
                                   md_bg_color=(*C["accent"][:3], 0.15))
                tag_lbl = MDLabel(text=f"#{tag}", font_style="Caption",
                                   theme_text_color="Custom",
                                   text_color=C["accent"],
                                   halign="center", valign="middle",
                                   size_hint=(1,1))
                tag_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
                tag_pill.add_widget(tag_lbl)
                tags_row.add_widget(tag_pill)
            self.add_widget(tags_row)
            self._has_tags = True
        else:
            self._has_tags = False

    def _calc_h(self):
        is_fem=self._fem()
        h=S(44)+S(20)
        if is_fem and not self.done: h+=S(28)
        if self.subtasks: h+=S(4)
        if getattr(self, "_has_tags", False): h+=S(26)
        self.height=h

    # ── Свайп ────────────────────────────────────────────────────────────────
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start_x = touch.x
            self._swiping = False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._touch_start_x is not None and self.collide_point(*touch.pos):
            dx = touch.x - self._touch_start_x
            if abs(dx) > S(20):
                self._swiping = True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._touch_start_x is not None:
            dx = touch.x - self._touch_start_x
            if self._swiping and abs(dx) > S(self.SWIPE_THRESHOLD):
                if dx > 0:   # вправо = выполнено
                    Clock.schedule_once(lambda *_: self._toggle(), 0.05)
                else:        # влево = удалить
                    Clock.schedule_once(lambda *_: self._delete_confirm(), 0.05)
                self._touch_start_x = None
                self._swiping = False
                return True
        self._touch_start_x = None; self._swiping = False
        return super().on_touch_up(touch)

    def _toggle(self, *_):
        self.done = not self.done
        if self.task_id in self.app.tasks:
            self.app.tasks[self.task_id]["done"] = self.done
        self.app.save_tasks()
        if self.done:
            self._animate_done()
        self.app.refresh_task_list()
        if self.done:
            done_today = sum(1 for t in self.app.tasks.values()
                             if t.get("done") and
                             t.get("date","") == date.today().strftime("%d.%m.%Y"))
            if done_today > 0 and done_today % 3 == 0:
                Clock.schedule_once(lambda *_: self.app._show_motivation_popup(), 0.6)
            # уведомление
            self.app._send_notification(f"Задача выполнена: {self.title}")

    def _delete_confirm(self):
        from kivy.uix.modalview import ModalView
        mv = ModalView(background_color=(0,0,0,0.5), auto_dismiss=True,
                       size_hint=(0.88,None))
        card = MDCard(orientation="vertical", size_hint_y=None, height=S(160),
                      radius=[S(16)], elevation=6, md_bg_color=C["surf"],
                      padding=[S(20),S(16)])
        ci = MDBoxLayout(orientation="vertical", spacing=S(12))
        ci.add_widget(MDLabel(text="Удалить задачу?",
                               font_style="H6", bold=True,
                               theme_text_color="Custom", text_color=C["text"],
                               halign="center", size_hint_y=None, height=S(36)))
        _lbl_tmp=MDLabel(text=self.title, font_style="Body2",
                               theme_text_color="Secondary", halign="center",
                               size_hint_y=None, height=S(28))
        ci.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        br = MDBoxLayout(orientation="horizontal", spacing=S(12), size_hint_y=None, height=S(44))
        cancel = MDRaisedButton(text="Отмена", size_hint_x=0.5,
                                 elevation=0, md_bg_color=C["surf2"])
        cancel.bind(on_release=lambda *_: mv.dismiss())
        delete = MDRaisedButton(text="Удалить", size_hint_x=0.5,
                                 elevation=0, md_bg_color=C["red"])
        def _do_del(*_):
            mv.dismiss()
            Clock.schedule_once(lambda *_: self._delete(), 0.1)
        delete.bind(on_release=_do_del)
        br.add_widget(cancel); br.add_widget(delete)
        ci.add_widget(br); card.add_widget(ci); mv.add_widget(card); mv.open()

    def _start_pomodoro_for_task(self):
        app = self.app
        if hasattr(app, '_pg_pomodoro'):
            app._nav_switch("pomodoro")
            Clock.schedule_once(lambda *_: (
                setattr(app._pg_pomodoro, '_task_id', self.task_id) or
                setattr(app._pg_pomodoro._task_lbl, 'text', self.title[:40])
            ), 0.1)
            app._show_toast("Фокус на: " + self.title[:25])

    def _show_menu(self, inst):
        from kivy.uix.modalview import ModalView
        W=S(188); IH=S(48)
        mv=ModalView(background_color=(0,0,0,0), auto_dismiss=True,
                     size_hint=(None,None), size=(W,IH*5+S(12)))
        card=MDCard(orientation="vertical", size_hint=(1,1),
                    radius=[S(12)], elevation=4, md_bg_color=C["surf"], padding=[S(4)])
        for ico,txt,col,cb in [
            ("eye-outline","Детали",C["text"],
             lambda: self.app.open_task_detail(self.task_id)),
            ("pencil-outline","Редактировать",C["accent"],
             lambda: self.app.open_task_form(self.task_id)),
            ("clock-play","Pomodoro",C["accent"],
             lambda: self._start_pomodoro_for_task()),
            ("share-variant","Поделиться",C["accent"],
             lambda: self.app.share_task(self.task_id)),
            ("trash-can-outline","Удалить",C["red"],self._delete)]:
            row=MDBoxLayout(orientation="horizontal", spacing=S(6),
                            size_hint_y=None, height=IH)
            row.add_widget(MDIconButton(icon=ico, size_hint_x=None, width=S(34),
                                         theme_text_color="Custom", text_color=col))
            _lbl_tmp=MDLabel(text=txt, font_style="Body2",
                                   theme_text_color="Custom", text_color=col,
                          halign="left", valign="middle")
            row.add_widget(_lbl_tmp)
            _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            def _up(w,t,_cb=cb,_row=row):
                if _row.collide_point(*t.pos):
                    mv.dismiss(); Clock.schedule_once(lambda *_: _cb(), 0.12); return True
            row.bind(on_touch_up=_up); card.add_widget(row)
        mv.add_widget(card)
        bx,by=inst.to_window(inst.x,inst.y)
        mv.pos=(max(S(4),bx-W-S(4)),
                max(S(4),min(by,Window.height-mv.height-S(4))))
        mv.open()

    # ── Свайп-жесты ──────────────────────────────────────────────────────────
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.x_orig = self.x  # обновляем при каждом касании
            touch.ud[f"swipe_{id(self)}"] = {
                "sx": touch.x, "sy": touch.y,
                "dx": 0, "moved": False, "owner": True
            }
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        key = f"swipe_{id(self)}"
        if key in touch.ud and touch.ud[key].get("owner"):
            dx = touch.x - touch.ud[key]["sx"]
            dy = touch.y - touch.ud[key]["sy"]
            touch.ud[key]["dx"] = dx
            if abs(dx) > 8:
                touch.ud[key]["moved"] = True
            # Визуальный сдвиг только по горизонтали
            if abs(dx) > abs(dy):
                self.x = self.x_orig + dx * 0.45
                # Окраска подсказки
                if dx > 30:
                    self.md_bg_color = (*C.get("green",(0.3,0.8,0.4,1))[:3], 0.3)
                elif dx < -30:
                    self.md_bg_color = (*C.get("red",(0.9,0.3,0.3,1))[:3], 0.3)
                else:
                    self.md_bg_color = C["surf"]
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        key = f"swipe_{id(self)}"
        if key in touch.ud and touch.ud[key].get("owner"):
            dx = touch.ud[key]["dx"]
            dy = touch.y - touch.ud[key]["sy"]
            moved = touch.ud[key].get("moved", False)
            # Сброс цвета и позиции
            self.md_bg_color = C["surf"]
            anim = Animation(x=self.x_orig, duration=0.12, t="out_quad")
            anim.start(self)
            if moved and abs(dx) > abs(dy) * 0.7:
                if dx > self.SWIPE_THRESHOLD:
                    Clock.schedule_once(lambda *_: self._toggle_done_swipe(), 0.12)
                    return True
                elif dx < -self.SWIPE_THRESHOLD:
                    Clock.schedule_once(lambda *_: self._confirm_delete_swipe(), 0.12)
                    return True
        return super().on_touch_up(touch)

    def on_pos(self, *_):
        if not hasattr(self, "x_orig"):
            self.x_orig = self.x

    def _toggle_done_swipe(self):
        task = self.app.tasks.get(self.task_id)
        if not task: return
        # Свайп вправо = переключить выполнено / не выполнено
        new_done = not task.get("done", False)
        task["done"] = new_done
        self.done = new_done
        self.app.save_tasks()
        self._update_checkbox_visual()
        if new_done:
            self._animate_done()
            self.app._show_toast("Выполнено!")
        else:
            self.app._show_toast("Отмечено как невыполненное")
        Clock.schedule_once(lambda *_: self.app.refresh_task_list(), 0.45)

    def _update_checkbox_visual(self):
        """Мгновенно обновляет иконку чекбокса и стиль заголовка."""
        is_fem = self._fem()
        if hasattr(self, "_cb_icon"):
            self._cb_icon.icon = ("check-circle" if self.done
                                   else ("radiobox-blank" if is_fem else "checkbox-blank-outline"))
            self._cb_icon.text_color = C["green"] if self.done else C["text2"]
        if hasattr(self, "_title_lbl"):
            self._title_lbl.text_color = C["text2"] if self.done else C["text"]
            self._title_lbl.font_style = "Body1"
            try:
                self._title_lbl.text = (f"[s]{self.title}[/s]" if self.done else self.title)
                self._title_lbl.markup = True
            except Exception:
                pass

    def _animate_done(self):
        """Анимация выполнения — мигание зелёным."""
        orig_color = list(self.md_bg_color)
        anim = (Animation(md_bg_color=[0.2,0.8,0.4,1], duration=0.15) +
                Animation(md_bg_color=orig_color, duration=0.2))
        anim.start(self)

    def _confirm_delete_swipe(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        def _do_del(*_): 
            dlg.dismiss()
            self._delete()
        dlg = MDDialog(
            title="Удалить задачу?",
            text=f'"{self.title}"',
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                MDRaisedButton(text="Удалить", md_bg_color=(0.8,0.2,0.2,1),
                               on_release=_do_del),
            ])
        dlg.open()

    def _delete(self):
        self.app.tasks.pop(self.task_id, None)
        self.app.save_tasks(); self.app.refresh_task_list()


# ═══════════════════════════════════════════════════════════════════════════
#  Форма задачи
# ═══════════════════════════════════════════════════════════════════════════
class TaskFormScreen(MDScreen):
    def __init__(self, app, task_id=None, on_save=None, on_cancel=None, **kw):
        super().__init__(**kw)
        self._app=app; self._task_id=task_id
        self._on_save=on_save; self._on_cancel=on_cancel
        td=app.tasks.get(task_id,{}) if task_id else {}
        self._subtasks=list(td.get("subtasks",[]))
        self._time_val=td.get("time","")
        self._remind_val=td.get("reminder","")
        self._repeat_val=td.get("repeat","Не повторять")
        self._date_val=td.get("date",datetime.now().strftime("%d.%m.%Y"))
        self._build(td)

    def _build(self, td):
        is_fem=self._app._is_fem()
        root=MDBoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*C["bg"]); _bg=Rectangle(size=Window.size, pos=(0,0))
        root.bind(size=lambda w,s: setattr(_bg,"size",s))
        hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(56), md_bg_color=C["surf"],
                        padding=[S(16),S(8)])
        hdr.bind(on_touch_down=lambda w,t: bool(w.collide_point(*t.pos)))
        title_hdr=MDLabel(text="Новая задача" if not self._task_id else "Редактировать",
                          font_style="H6", bold=True, theme_text_color="Primary",
                          halign="center", valign="middle")
        title_hdr.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        hdr.add_widget(title_hdr)
        root.add_widget(hdr)
        sv=ScrollView(do_scroll_x=False, do_scroll_y=True,
                     bar_width=S(3), scroll_type=['bars','content'])
        inn=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(0), padding=[S(16),S(14),S(16),S(30)])
        # ── Заголовок + автоподсказки из истории задач ──────────────────────
        self.tf_title = MDTextField(hint_text="Что нужно сделать?",
                                    text=td.get("title",""),
                                    size_hint_x=1, size_hint_y=None, height=S(54))
        inn.add_widget(Widget(size_hint_y=None, height=S(4)))
        inn.add_widget(self.tf_title)

        # Контейнер для подсказок (заполняется динамически при вводе)
        self._suggest_box = MDBoxLayout(orientation="vertical", size_hint_y=None,
                                         height=0, spacing=S(2))
        inn.add_widget(self._suggest_box)

        # Список уникальных названий ранее созданных задач (без текущей)
        _hist_titles = []
        _seen_lower = set()
        for t in self._app.tasks.values():
            tt = t.get("title","").strip()
            if tt and t.get("id") != td.get("id") and tt.lower() not in _seen_lower:
                _seen_lower.add(tt.lower())
                _hist_titles.append(tt)

        def _update_suggestions(instance, value):
            self._suggest_box.clear_widgets()
            q = value.strip().lower()
            if not q or len(q) < 2:
                self._suggest_box.height = 0
                return
            matches = [t for t in _hist_titles
                       if q in t.lower() and t.lower() != q][:4]
            if not matches:
                self._suggest_box.height = 0
                return
            for m in matches:
                row = MDCard(size_hint_y=None, height=S(34), radius=[S(8)],
                             elevation=0, md_bg_color=C["surf2"],
                             padding=[S(10),S(4)])
                lbl = MDLabel(text=m, font_style="Body2",
                              theme_text_color="Secondary",
                              halign="left", valign="middle",
                              shorten=True, shorten_from="right")
                lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
                row.add_widget(lbl)
                def _pick(w, touch, title=m):
                    if w.collide_point(*touch.pos):
                        self.tf_title.text = title
                        self._suggest_box.clear_widgets()
                        self._suggest_box.height = 0
                        return True
                row.bind(on_touch_up=_pick)
                self._suggest_box.add_widget(row)
            self._suggest_box.height = S(36) * len(matches) + S(2) * (len(matches)-1)

        self.tf_title.bind(text=_update_suggestions)
        inn.add_widget(Widget(size_hint_y=None, height=S(8)))

        # ── Теги (необязательно) ──────────────────────────────────────────
        inn.add_widget(self._lbl("Теги (необязательно)"))
        self._tf_tags = MDTextField(
            hint_text="#работа #срочно #важно",
            text=" ".join(["#"+t for t in td.get("tags", [])]),
            size_hint_x=1, size_hint_y=None, height=S(48))
        inn.add_widget(self._tf_tags)

        # Популярные теги — быстрый выбор
        _all_tags = set()
        for t in self._app.tasks.values():
            _all_tags.update(t.get("tags", []))
        if _all_tags:
            tags_sv = ScrollView(size_hint_y=None, height=S(36), do_scroll_y=False)
            tags_quick = MDBoxLayout(orientation="horizontal", size_hint_x=None,
                                     spacing=S(6), padding=[0, S(2)])
            tags_quick.bind(minimum_width=tags_quick.setter("width"))
            for tag in sorted(_all_tags)[:8]:
                tb = MDRaisedButton(text="#"+tag, elevation=0, size_hint_x=None,
                                    width=S(len(tag)*8+32), size_hint_y=None,
                                    height=S(26), md_bg_color=C["surf2"])
                def _add_tag(_, t=tag):
                    cur = self._tf_tags.text.strip()
                    htag = "#" + t
                    if htag not in cur:
                        self._tf_tags.text = (cur + " " + htag).strip()
                tb.bind(on_release=_add_tag)
                tags_quick.add_widget(tb)
            tags_sv.add_widget(tags_quick)
            inn.add_widget(tags_sv)

        inn.add_widget(Widget(size_hint_y=None, height=S(4)))
        # Категория
        inn.add_widget(self._lbl("Категория"))
        cats=self._app.categories
        self._sel_cat=td.get("category", cats[0] if cats else "Работа")
        cat_sv=ScrollView(size_hint_y=None, height=S(88), do_scroll_y=False)
        cat_row=MDBoxLayout(orientation="horizontal", size_hint_x=None, spacing=S(10))
        cat_row.bind(minimum_width=cat_row.setter("width"))
        self._cat_btns={}
        for c in cats:
            btn=self._cat_card(c, c==self._sel_cat)
            self._cat_btns[c]=btn; cat_row.add_widget(btn)
        cat_sv.add_widget(cat_row); inn.add_widget(cat_sv)
        inn.add_widget(Widget(size_hint_y=None, height=S(8)))
        # Приоритет
        inn.add_widget(self._lbl("Приоритет"))
        self._sel_prio=td.get("priority","Средний")
        p_row=MDBoxLayout(orientation="horizontal", spacing=S(8),
                          size_hint_y=None, height=S(42))
        self._prio_btns={}
        prios=(([("fire","Срочно","Высокий"),("star","Важно","Средний"),("heart","Легкое","Низкий")])
               if is_fem else
               [("arrow-down","Низкий","Низкий"),("minus","Средний","Средний"),("arrow-up","Высокий","Высокий")])
        for ico_p,lbl_t,val in prios:
            sel=(val==self._sel_prio)
            bg=C["acc_s"] if (is_fem and sel) else (C["accent"] if (not is_fem and sel) else C["surf2"])
            tc=C["accent"] if (is_fem and sel) else ((1,1,1,1) if (not is_fem and sel) else C["text2"])
            btn=MDCard(size_hint_x=0.33, size_hint_y=None, height=S(40),
                       radius=[S(20)] if is_fem else [S(10)], elevation=0, md_bg_color=bg)
            br2=MDBoxLayout(orientation="horizontal", spacing=S(4), padding=[S(6),0], size_hint=(1,1))
            br2.add_widget(MDIconButton(icon=ico_p, size_hint_x=None, width=S(24),
                                         theme_text_color="Custom", text_color=tc))
            _lbl_tmp=MDLabel(text=lbl_t, font_style="Caption",
                                   theme_text_color="Custom", text_color=tc,
                                   halign="left", valign="middle",
                                   shorten=True, shorten_from="right")
            br2.add_widget(_lbl_tmp)
            _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            btn.add_widget(br2)
            def _tp(w,t,v=val):
                if w.collide_point(*t.pos): self._pick_prio(v); return True
            btn.bind(on_touch_up=_tp); self._prio_btns[val]=btn; p_row.add_widget(btn)
        inn.add_widget(p_row)
        inn.add_widget(Widget(size_hint_y=None, height=S(10)))
        # Параметры
        params=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(6),S(4)])
        params.bind(minimum_height=params.setter("height"))
        p_inn=MDBoxLayout(orientation="vertical", adaptive_height=True)
        date_disp=self._date_val+(f"  {self._time_val}" if self._time_val else "")
        r_dt,self._date_lbl=self._param_row(
            "calendar-outline","Дата",self._date_val or "Не выбрано",self._open_date_picker)
        p_inn.add_widget(r_dt); self._sep(p_inn)
        r_tm,self._time_lbl=self._param_row(
            "clock-outline","Время",self._time_val or "Не выбрано",self._open_time_picker)
        p_inn.add_widget(r_tm); self._sep(p_inn)
        r_rem,self._remind_lbl=self._param_row(
            "bell-outline","Напоминание",self._remind_val or "Не выбрано",self._pick_reminder)
        p_inn.add_widget(r_rem); self._sep(p_inn)
        r_rep,self._repeat_lbl=self._param_row(
            "repeat","Повтор",self._repeat_val,self._pick_repeat)
        p_inn.add_widget(r_rep)
        params.add_widget(p_inn); inn.add_widget(params)
        inn.add_widget(Widget(size_hint_y=None, height=S(10)))
        # Заметка — открывается в отдельном окне, чтобы клавиатура не перекрывала
        self._note_text = td.get("comment","")
        note_c=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(16),S(12)])
        note_c.bind(minimum_height=note_c.setter("height"))
        ni=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
        note_hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(28))
        _lbl_tmp=MDLabel(text="Заметка", font_style="Subtitle2",
                              theme_text_color="Custom", text_color=C["text"],
                      halign="left", valign="middle")
        note_hdr.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        note_hdr.add_widget(MDIconButton(icon="pencil-outline", size_hint_x=None,
                              width=S(32), theme_text_color="Custom", text_color=C["accent"]))
        ni.add_widget(note_hdr)
        self._note_preview = MDLabel(
            text=self._note_text if self._note_text else "Нажмите, чтобы добавить заметку...",
            font_style="Body2",
            theme_text_color="Custom",
            text_color=C["text"] if self._note_text else C["text2"],
            size_hint_y=None, height=S(36))
        self._note_preview.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        ni.add_widget(self._note_preview)
        note_c.add_widget(ni); inn.add_widget(note_c)
        self._note_mv = None
        def _open_note(*_):
            # Защита от двойного открытия
            if self._note_mv is not None:
                return
            from kivy.uix.modalview import ModalView
            mv_note=ModalView(background_color=(0,0,0,0.6), auto_dismiss=True,
                               size_hint=(0.95,None), height=S(310),
                               pos_hint={"center_x":0.5,"top":0.93})
            def _on_dismiss(*_):
                self._note_mv = None
            mv_note.bind(on_dismiss=_on_dismiss)
            self._note_mv = mv_note
            card=MDCard(orientation="vertical", size_hint=(1,1),
                        radius=[S(16)], elevation=8,
                        md_bg_color=C["surf"], padding=[S(16),S(14)])
            hdr_n=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(30))
            _lbl_tmp=MDLabel(text="Заметка", font_style="Subtitle1", bold=True,
                                     theme_text_color="Custom", text_color=C["text"],
                          halign="left", valign="middle")
            hdr_n.add_widget(_lbl_tmp)
            _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            x_btn=MDIconButton(icon="close", size_hint_x=None, width=S(30),
                               theme_text_color="Custom", text_color=C["text2"])
            x_btn.bind(on_release=lambda *_: mv_note.dismiss())
            hdr_n.add_widget(x_btn); card.add_widget(hdr_n)
            nf=MDTextField(hint_text="Введите заметку...",
                           text=self._note_text,
                           multiline=True, size_hint_y=None, height=S(160), mode="fill")
            card.add_widget(nf)
            br=MDBoxLayout(orientation="horizontal", spacing=S(10),
                           size_hint_y=None, height=S(48), padding=[0,S(4)])
            cancel=MDFlatButton(text="Отмена", size_hint_x=0.38,
                                theme_text_color="Custom", text_color=C["text2"])
            cancel.bind(on_release=lambda *_: mv_note.dismiss())
            ok=MDRaisedButton(text="Сохранить", size_hint_x=0.62,
                              md_bg_color=C["accent"], elevation=0)
            def _ok(btn_inst):
                self._note_text = nf.text.strip()
                preview_text = self._note_text if self._note_text else "Нажмите, чтобы добавить заметку..."
                self._note_preview.text = preview_text
                self._note_preview.text_color = C["text"] if self._note_text else C["text2"]
                mv_note.dismiss()
            ok.bind(on_release=_ok)
            br.add_widget(cancel); br.add_widget(ok); card.add_widget(br)
            mv_note.add_widget(card); mv_note.open()
            Clock.schedule_once(lambda *_: setattr(nf,"focus",True), 0.3)
        def _note_tap(w,t):
            if note_c.collide_point(*t.pos): _open_note(); return True
        note_c.bind(on_touch_up=_note_tap)
        # stub tf_note чтобы _save() не сломался
        class _NoteProxy:
            pass
        _np = _NoteProxy()
        _np.__class__ = type("_NP", (), {"text": property(lambda s: self._note_text)})
        self.tf_note = _np
        inn.add_widget(Widget(size_hint_y=None, height=S(10)))
        # Подзадачи
        sub_c=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                     md_bg_color=C["surf"], padding=[S(16),S(12)])
        sub_c.bind(minimum_height=sub_c.setter("height"))
        s_inn=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
        s_hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(32))
        _lbl_tmp=MDLabel(text="Подзадачи", font_style="Subtitle2",
                                  theme_text_color="Custom", text_color=C["text"],
                      halign="left", valign="middle")
        s_hdr.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        add_s=MDIconButton(icon="plus-circle-outline", size_hint_x=None, width=S(36),
                            theme_text_color="Custom", text_color=C["accent"])
        add_s.bind(on_release=lambda *_: self._add_sub_dialog())
        s_hdr.add_widget(add_s); s_inn.add_widget(s_hdr)
        self._sub_rows=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(2))
        for sub in self._subtasks:
            self._add_sub_widget(sub.get("title",""), sub.get("done",False))
        s_inn.add_widget(self._sub_rows); sub_c.add_widget(s_inn); inn.add_widget(sub_c)
        inn.add_widget(Widget(size_hint_y=None, height=S(16)))
        sv.add_widget(inn); root.add_widget(sv)
        # Нижний footer — всегда виден, кнопки работают через on_touch_up
        footer=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                           height=S(60), md_bg_color=C["surf"],
                           padding=[S(12),S(8),S(12),S(8)], spacing=S(10))
        back2=MDCard(size_hint_x=0.4, size_hint_y=None, height=S(44),
                     radius=[S(8)], elevation=0, md_bg_color=C["surf2"])
        back2_lbl=MDLabel(text="< Назад", halign="center", valign="middle",
                          theme_text_color="Custom", text_color=C["text"],
                          size_hint=(1,1))
        back2_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        back2.add_widget(back2_lbl)
        def _back_tap(w,t):
            if back2.collide_point(*t.pos): self._cancel(); return True
        back2.bind(on_touch_up=_back_tap)
        save2=MDCard(size_hint_x=0.6, size_hint_y=None, height=S(44),
                     radius=[S(8)], elevation=0, md_bg_color=C["accent"])
        save2_lbl=MDLabel(text="Сохранить", halign="center", valign="middle",
                          theme_text_color="Custom", text_color=(1,1,1,1),
                          size_hint=(1,1))
        save2_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        save2.add_widget(save2_lbl)
        def _save_tap(w,t):
            if save2.collide_point(*t.pos): self._save(); return True
        save2.bind(on_touch_up=_save_tap)
        footer.add_widget(back2); footer.add_widget(save2)
        root.add_widget(footer); self.add_widget(root)

    def _lbl(self, text):
        lbl = MDLabel(text=text, font_style="Caption",
                      theme_text_color="Custom", text_color=C["text2"],
                       size_hint_y=None, height=S(24),
                      halign="left", valign="middle")
        lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        return lbl

    def _cat_card(self, name, selected):
        is_fem=self._app._is_fem()
        bg=(C["acc_s"] if is_fem else C["accent"]) if selected else C["surf2"]
        tc=(C["accent"] if is_fem else (1,1,1,1)) if selected else C["text2"]
        card=MDCard(size_hint=(None,None), size=(S(70),S(78)),
                    radius=[S(14)], elevation=0, md_bg_color=bg)
        ci=MDBoxLayout(orientation="vertical", spacing=S(2), padding=[S(4),S(8)])
        ci.add_widget(MDIconButton(icon=CAT_ICONS.get(name,"dots-horizontal-circle-outline"),
                                    size_hint_y=None, height=S(30),
                                    theme_text_color="Custom",
                                    text_color=C["accent"] if selected else C["text2"]))
        cat_lbl=MDLabel(text=name, font_style="Caption",
                         theme_text_color="Custom", text_color=tc,
                         halign="center", valign="middle",
                         size_hint_y=None, height=S(22))
        cat_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        ci.add_widget(cat_lbl)
        card.add_widget(ci)
        def _tap(w,t,n=name):
            if w.collide_point(*t.pos): self._pick_cat(n); return True
        card.bind(on_touch_up=_tap)
        return card

    def _pick_cat(self, c):
        self._sel_cat=c; is_fem=self._app._is_fem()
        for k,b in self._cat_btns.items():
            sel=(k==c)
            b.md_bg_color=(C["acc_s"] if is_fem else C["accent"]) if sel else C["surf2"]
            ci=b.children[0]
            if len(ci.children)>=2:
                lbl=ci.children[0]; ico=ci.children[1]
                lbl.text_color=(C["accent"] if is_fem else (1,1,1,1)) if sel else C["text2"]
                ico.text_color=C["accent"] if sel else C["text2"]

    def _pick_prio(self, v):
        self._sel_prio=v; is_fem=self._app._is_fem()
        for k,b in self._prio_btns.items():
            sel=(k==v)
            b.md_bg_color=(C["acc_s"] if is_fem else C["accent"]) if sel else C["surf2"]
            br2=b.children[0]
            tc=(C["accent"] if is_fem else (1,1,1,1)) if sel else C["text2"]
            for w in br2.children:
                if hasattr(w,"text_color"): w.text_color=tc

    def _param_row(self, icon, label, value, on_tap):
        row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(52), spacing=S(8), padding=[S(8),0])
        row.add_widget(MDIconButton(icon=icon, size_hint_x=None, width=S(34),
                                    theme_text_color="Custom", text_color=C["text2"]))
        lbl_w=MDLabel(text=label, font_style="Body1", theme_text_color="Primary",
                      halign="left", valign="middle",
                      shorten=True, shorten_from="right")
        lbl_w.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        row.add_widget(lbl_w)
        val_lbl=MDLabel(text=value, font_style="Body2",
                        theme_text_color="Secondary", halign="right",
                        valign="middle", size_hint_x=None, width=S(128))
        val_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],s[1])))
        row.add_widget(val_lbl)
        row.add_widget(MDIconButton(icon="chevron-right", size_hint_x=None, width=S(24),
                                    theme_text_color="Custom", text_color=C["text2"]))
        def _tap(w,t):
            if row.collide_point(*t.pos): on_tap(); return True
        row.bind(on_touch_up=_tap)
        return row, val_lbl

    def _sep(self, parent):
        s=Widget(size_hint_y=None, height=S(1))
        def _dr(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(*C["div"]); Rectangle(pos=(w.x+S(44),w.y), size=(w.width-S(44),S(1)))
        s.bind(pos=_dr, size=_dr); parent.add_widget(s)

    def _open_date_picker(self):
        dates={t.get("date","") for t in self._app.tasks.values()}
        box=MDBoxLayout(orientation="vertical", adaptive_height=True, padding=[S(4)])
        cal=CalendarWidget(task_dates=dates)
        try: cal.sel=datetime.strptime(self._date_val,"%d.%m.%Y").date()
        except Exception: pass
        box.add_widget(cal)
        dlg=MDDialog(title="Выберите дату", type="custom", content_cls=box,
                     buttons=[
                         MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                         MDRaisedButton(text="Выбрать", md_bg_color=C["accent"],
                                        on_release=lambda *_: self._apply_date(cal.sel, dlg))])
        dlg.open()

    def _apply_date(self, d, dlg):
        self._date_val=d.strftime("%d.%m.%Y")
        self._date_lbl.text=self._date_val; dlg.dismiss()

    def _open_time_picker(self):
        """Диалог выбора времени — кнопки +/- без ScrollView."""
        from kivy.uix.modalview import ModalView
        try:
            cur_h = int(self._time_val.split(":")[0])
            cur_m = int(self._time_val.split(":")[1])
        except Exception:
            cur_h = 9; cur_m = 0

        # Изменяемые значения (не через sel[idx] — ловушка замыкания)
        h_val = [cur_h]
        m_val = [cur_m]

        mv = ModalView(background_color=(0,0,0,0.5), auto_dismiss=False,
                       size_hint=(0.82, None))
        card = MDCard(orientation="vertical", size_hint_y=None, height=S(260),
                      radius=[S(16)], elevation=6, md_bg_color=C["surf"],
                      padding=[S(16), S(12)])

        title = MDLabel(text="Выберите время", font_style="H6", bold=True,
                        theme_text_color="Primary", halign="center",
                        size_hint_y=None, height=S(36))
        title.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(title)

        row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                          height=S(150), spacing=S(12), padding=[S(4),S(4)])

        def _make_col(get_fn, set_fn, max_val):
            col = MDBoxLayout(orientation="vertical", spacing=S(4))
            up = MDRaisedButton(text="+", size_hint_y=None, height=S(44),
                                 md_bg_color=C["surf2"], elevation=0,
                                 font_size=S(22))
            lbl = MDLabel(text=f"{get_fn():02d}", font_style="H4", bold=True,
                           halign="center", valign="middle",
                           theme_text_color="Primary",
                           size_hint_y=None, height=S(52))
            lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            dn = MDRaisedButton(text="-", size_hint_y=None, height=S(44),
                                 md_bg_color=C["surf2"], elevation=0,
                                 font_size=S(22))
            def _up(*_):
                set_fn((get_fn()+1) % max_val)
                lbl.text = f"{get_fn():02d}"
            def _dn(*_):
                set_fn((get_fn()-1) % max_val)
                lbl.text = f"{get_fn():02d}"
            up.bind(on_release=_up)
            dn.bind(on_release=_dn)
            col.add_widget(up); col.add_widget(lbl); col.add_widget(dn)
            return col

        h_col = _make_col(lambda: h_val[0], lambda v: h_val.__setitem__(0,v), 24)
        sep = MDLabel(text=":", font_style="H4", bold=True,
                      theme_text_color="Primary", halign="center",
                      size_hint_x=None, width=S(20),
                      size_hint_y=None, height=S(48))
        sep.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        m_col = _make_col(lambda: m_val[0], lambda v: m_val.__setitem__(0,v), 60)
        row.add_widget(h_col); row.add_widget(sep); row.add_widget(m_col)
        card.add_widget(row)

        btn_row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                              height=S(44), spacing=S(8))
        def _clear(*_):
            self._time_val = ""
            self._time_lbl.text = "Не выбрано"; mv.dismiss()
        def _apply(*_):
            self._time_val = f"{h_val[0]:02d}:{m_val[0]:02d}"
            self._time_lbl.text = self._time_val; mv.dismiss()
        btn_row.add_widget(MDFlatButton(text="Очистить", on_release=_clear))
        btn_row.add_widget(Widget())
        btn_row.add_widget(MDRaisedButton(text="Выбрать",
                            md_bg_color=C["accent"], on_release=_apply))
        card.add_widget(btn_row)
        mv.add_widget(card); mv.open()

    def _show_picker(self, title, opts, cur, lbl, setter):
        from kivy.uix.modalview import ModalView
        mv=ModalView(background_color=(0,0,0,0.5), auto_dismiss=True, size_hint=(0.88,None))
        card=MDCard(orientation="vertical", size_hint_y=None,
                    height=S(len(opts)*52+20), radius=[S(16)], elevation=6,
                    md_bg_color=C["surf"], padding=[S(6),S(8)])
        for opt in opts:
            row=MDBoxLayout(size_hint_y=None, height=S(50), padding=[S(16),0])
            opt_lbl=MDLabel(text=opt, font_style="Body1",
                                theme_text_color="Custom",
                                text_color=C["accent"] if opt==cur else C["text"],
                                halign="left", valign="middle")
            opt_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            row.add_widget(opt_lbl)
            def _sel(w,t,o=opt,r=row):
                if r.collide_point(*t.pos):
                    setter(o); lbl.text=o; mv.dismiss(); return True
            row.bind(on_touch_up=_sel); card.add_widget(row)
        mv.add_widget(card); mv.open()

    def _pick_reminder(self):
        self._show_picker("Напоминание", REMIND_OPTIONS, self._remind_val,
                          self._remind_lbl, lambda v: setattr(self,"_remind_val",v))

    def _pick_repeat(self):
        self._show_picker("Повтор", REPEAT_OPTIONS, self._repeat_val,
                          self._repeat_lbl, lambda v: setattr(self,"_repeat_val",v))

    def _add_sub_widget(self, title, done=False):
        row=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(38), spacing=S(6))
        ico="checkbox-marked-outline" if done else "checkbox-blank-outline"
        cb=MDIconButton(icon=ico, size_hint_x=None, width=S(32),
                        theme_text_color="Custom",
                        text_color=C["accent"] if done else C["text2"])
        def _tog(w):
            d=(w.icon=="checkbox-blank-outline")
            w.icon="checkbox-marked-outline" if d else "checkbox-blank-outline"
            w.text_color=C["accent"] if d else C["text2"]
        cb.bind(on_release=lambda w: _tog(w)); row.add_widget(cb)
        _lbl_tmp=MDLabel(text=title, font_style="Body2",
                               theme_text_color="Custom", text_color=C["text"],
                      halign="left", valign="middle")
        row.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        self._sub_rows.add_widget(row)

    def _add_sub_dialog(self):
        box=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(8), padding=[S(4)])
        nf=MDTextField(hint_text="Название подзадачи", size_hint_y=None, height=S(52))
        box.add_widget(nf)
        dlg=MDDialog(title="Добавить подзадачу", type="custom", content_cls=box,
                     buttons=[
                         MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                         MDRaisedButton(text="Добавить", md_bg_color=C["accent"],
                                        on_release=lambda *_: self._do_add_sub(nf.text.strip(),dlg))])
        dlg.open()

    def _do_add_sub(self, title, dlg):
        import time
        if title:
            self._subtasks.append({"id":str(time.time()),"title":title,"done":False})
            self._add_sub_widget(title)
        dlg.dismiss()

    def _cancel(self):
        if self._on_cancel: self._on_cancel()

    def _save(self):
        if getattr(self, "_save_locked", False): return
        self._save_locked = True
        title=self.tf_title.text.strip()
        if not title: self.tf_title.hint_text="Введите название!"; self._save_locked=False; return
        # Parse tags from text field
        _raw_tags = getattr(self, "_tf_tags", None)
        _tags = []
        if _raw_tags:
            _tags = [w.strip("#") for w in _raw_tags.text.split() if w.startswith("#")]
        data={"title":title,"comment":getattr(self,"_note_text","").strip(),
              "category":self._sel_cat,"priority":self._sel_prio,
              "date":self._date_val,"time":self._time_val,
              "reminder":self._remind_val,"repeat":self._repeat_val,
              "subtasks":self._subtasks,"tags":_tags}
        if self._task_id:
            self._app.tasks[self._task_id].update(data)
        else:
            tid=str(datetime.now().timestamp())
            self._app.tasks[tid]={"id":tid,**data,
                                   "original_date":data["date"],"done":False,"result":""}
        self._app.save_tasks()
        if self._on_save: self._on_save()


# ═══════════════════════════════════════════════════════════════════════════
#  Детали задачи
# ═══════════════════════════════════════════════════════════════════════════
class TaskDetailScreen(MDScreen):
    def __init__(self, app, task_id, on_back=None, **kw):
        super().__init__(**kw)
        self._app=app; self._task_id=task_id; self._on_back=on_back
        self._build()

    def _build(self):
        td=self._app.tasks.get(self._task_id,{})
        root=MDBoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*C["bg"]); _bg=Rectangle(size=Window.size, pos=(0,0))
        root.bind(size=lambda w,s: setattr(_bg,"size",s))
        hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(56), md_bg_color=C["surf"], padding=[S(4),S(8)])
        back=MDIconButton(icon="chevron-left", size_hint_x=None, width=S(44),
                          theme_text_color="Custom", text_color=C["text2"])
        back.bind(on_release=lambda *_: self._on_back() if self._on_back else None)
        hdr.add_widget(back)
        _lbl_tmp=MDLabel(text="Задача", font_style="H6", bold=True,
                               theme_text_color="Primary", halign="center")
        hdr.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        hdr.add_widget(MDIconButton(icon="dots-horizontal", size_hint_x=None, width=S(44),
                                    theme_text_color="Custom", text_color=C["text2"]))
        root.add_widget(hdr)
        sv=ScrollView()
        inn=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(10), padding=[S(14),S(14),S(14),S(30)])
        tc=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                  md_bg_color=C["surf"], padding=[S(16),S(14)])
        tc.bind(minimum_height=tc.setter("height"))
        ti=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(6))
        sr=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(28))
        sr.add_widget(MDIconButton(
            icon="check-circle" if td.get("done") else "checkbox-blank-circle-outline",
            size_hint_x=None, width=S(30), theme_text_color="Custom",
            text_color=C["green"] if td.get("done") else C["text2"]))
        sr.add_widget(Widget())
        sr.add_widget(MDIconButton(icon="star-outline", size_hint_x=None, width=S(34),
                                   theme_text_color="Custom", text_color=C["text2"]))
        ti.add_widget(sr)
        _lbl_tmp=MDLabel(text=td.get("title",""), font_style="H6", bold=True,
                              theme_text_color="Custom", text_color=C["text"],
                              size_hint_y=None, height=S(34),
                      halign="left", valign="middle")
        ti.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        cat=td.get("category","")
        if cat:
            _cat_lbl = EmojiLabel(text=f"  {CAT_EMOJI.get(cat,'')} {cat}",
                                   font_style="Caption",
                                   theme_text_color="Custom", text_color=C["accent"],
                                   size_hint_y=None, height=S(22))
            ti.add_widget(_cat_lbl)
        tc.add_widget(ti); inn.add_widget(tc)
        pc=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                  md_bg_color=C["surf"], padding=[S(6),S(4)])
        pc.bind(minimum_height=pc.setter("height"))
        pi=MDBoxLayout(orientation="vertical", adaptive_height=True)
        today_s=date.today().strftime("%d.%m.%Y")
        d_str=td.get("date","")
        d_disp=d_str+(" (сегодня)" if d_str==today_s else "")
        t_str=td.get("time","") or "В течение дня"
        self._det_row(pi,"calendar-outline",d_disp,t_str); self._sep(pi)
        self._det_row(pi,"bell-outline","Напоминание",td.get("reminder","") or "Не выбрано")
        self._sep(pi)
        prio=td.get("priority","Средний")
        pcol={"Высокий":C["red"],"Средний":C["orange"],"Низкий":C["green"]}.get(prio,C["text2"])
        pr_row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                           height=S(52), spacing=S(8), padding=[S(8),0])
        pr_row.add_widget(MDIconButton(icon="fire", size_hint_x=None, width=S(34),
                                        theme_text_color="Custom", text_color=C["text2"]))
        _lbl_tmp=MDLabel(text="Приоритет", font_style="Body1",
                                   theme_text_color="Primary",
                      halign="left", valign="middle")
        pr_row.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        pb=MDCard(size_hint=(None,None), size=(S(80),S(26)), radius=[S(13)], elevation=0,
                  md_bg_color=(*pcol[:3],0.15))
        _lbl_tmp=MDLabel(text=prio, font_style="Caption", halign="center",
                               valign="middle", theme_text_color="Custom", text_color=pcol)
        pb.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        pr_row.add_widget(pb); pi.add_widget(pr_row); self._sep(pi)
        self._det_row(pi,"repeat","Повтор",td.get("repeat","") or "Не повторять")
        pc.add_widget(pi); inn.add_widget(pc)
        note=td.get("comment","")
        if note:
            nc=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(16),S(12)])
            nc.bind(minimum_height=nc.setter("height"))
            ni=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
            _lbl_tmp=MDLabel(text="Заметка", font_style="Subtitle2",
                                   theme_text_color="Custom", text_color=C["text"],
                                   size_hint_y=None, height=S(22),
                          halign="left", valign="middle")
            ni.add_widget(_lbl_tmp)
            _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            _lbl_tmp=MDLabel(text=note, font_style="Body2",
                                   theme_text_color="Custom", text_color=C["text2"],
                                   size_hint_y=None,
                                   height=S(max(40,len(note)//36*22+22)),
                          halign="left", valign="middle")
            ni.add_widget(_lbl_tmp)
            _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            nc.add_widget(ni); inn.add_widget(nc)
        subs=td.get("subtasks",[])
        if subs:
            sc=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(16),S(12)])
            sc.bind(minimum_height=sc.setter("height"))
            si=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
            dn_c=sum(1 for s in subs if s.get("done"))
            hdr_row=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(32))
            hdr_row.add_widget(MDLabel(text=f"Подзадачи  {dn_c}/{len(subs)}",
                                       font_style="Subtitle2",
                                       theme_text_color="Custom", text_color=C["text"]))
            # Кнопка озвучки подзадач
            speak_btn=MDIconButton(icon="volume-high", size_hint_x=None, width=S(36),
                                   theme_text_color="Custom", text_color=C["accent"])
            def _speak_subs(*_):
                all_text = ". ".join(s.get("title","") for s in subs)
                pass  # tts removed
            speak_btn.bind(on_release=_speak_subs)
            hdr_row.add_widget(speak_btn)
            si.add_widget(hdr_row)
            for sub in subs:
                srow=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                 height=S(38), spacing=S(8))
                sico="checkbox-marked" if sub.get("done") else "checkbox-blank-outline"
                scb=MDIconButton(icon=sico, size_hint_x=None, width=S(32),
                                 theme_text_color="Custom",
                                 text_color=C["accent"] if sub.get("done") else C["text2"])
                def _tog(w,s=sub):
                    s["done"]=not s.get("done",False)
                    w.icon="checkbox-marked" if s["done"] else "checkbox-blank-outline"
                    w.text_color=C["accent"] if s["done"] else C["text2"]
                    self._app.save_tasks()
                scb.bind(on_release=_tog); srow.add_widget(scb)
                _lbl_tmp=MDLabel(text=sub.get("title",""), font_style="Body2",
                                        theme_text_color="Custom",
                                        text_color=C["text2"] if sub.get("done") else C["text"],
                              halign="left", valign="middle")
                srow.add_widget(_lbl_tmp)
                _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
                si.add_widget(srow)
            sc.add_widget(si); inn.add_widget(sc)
        sv.add_widget(inn); root.add_widget(sv)
        br=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                       height=S(66), md_bg_color=C["surf"], padding=[S(16),S(8)], spacing=S(12))
        edit=MDRaisedButton(text="Редактировать", size_hint_x=1,
                             size_hint_y=None, height=S(48), elevation=0, md_bg_color=C["accent"])
        edit.bind(on_release=lambda *_: self._app.open_task_form(self._task_id))
        del_b=MDIconButton(icon="trash-can-outline", size_hint_x=None,
                            width=S(50), size_hint_y=None, height=S(48),
                            theme_text_color="Custom", text_color=C["red"])
        def _del(*_):
            self._app.tasks.pop(self._task_id, None)
            self._app.save_tasks()
            if self._on_back: self._on_back()
        del_b.bind(on_release=_del)
        br.add_widget(edit); br.add_widget(del_b)
        root.add_widget(br); self.add_widget(root)

    def _det_row(self, parent, icon, label, value):
        row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(52), spacing=S(8), padding=[S(8),0])
        row.add_widget(MDIconButton(icon=icon, size_hint_x=None, width=S(34),
                                    theme_text_color="Custom", text_color=C["text2"]))
        lbl=MDLabel(text=label, font_style="Body1", theme_text_color="Primary",
                    halign="left", valign="middle",
                    size_hint_x=None, width=S(110),
                    shorten=True, shorten_from="right")
        lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        row.add_widget(lbl)
        val=MDLabel(text=value, font_style="Body2",
                    theme_text_color="Secondary",
                    halign="right", valign="middle",
                    shorten=True, shorten_from="right")
        val.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        row.add_widget(val)
        parent.add_widget(row)

    def _sep(self, parent):
        s=Widget(size_hint_y=None, height=S(1))
        def _dr(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(*C["div"]); Rectangle(pos=(w.x+S(44),w.y), size=(w.width-S(44),S(1)))
        s.bind(pos=_dr, size=_dr); parent.add_widget(s)


# ═══════════════════════════════════════════════════════════════════════════
#  ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
#  Pomodoro таймер
# ═══════════════════════════════════════════════════════════════════════════
class PomodoroScreen(MDScreen):
    """Экран фокус-таймера Pomodoro — 25 мин работы / 5 мин отдых."""

    WORK_SEC  = 25 * 60
    SHORT_SEC =  5 * 60
    LONG_SEC  = 15 * 60

    def __init__(self, app_ref, **kw):
        super().__init__(**kw)
        self._app   = app_ref
        self._secs  = self.WORK_SEC
        self._running   = False
        self._mode      = "work"   # "work" | "short" | "long"
        self._sessions  = 0
        self._task_id   = None
        self._clock_ev  = None
        self._build()

    def _build(self):
        from kivy.uix.widget import Widget
        root = MDBoxLayout(orientation="vertical",
                           md_bg_color=C["bg"], padding=[S(20), S(24)])
        # ── Шапка ────────────────────────────────────────────────────────
        top = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(48))
        back = MDRaisedButton(text="< Назад", size_hint_x=None, width=S(100),
                              elevation=0, md_bg_color=C["surf2"])
        back.bind(on_release=lambda *_: self._app._nav_switch("tasks"))
        self._mode_lbl = MDLabel(text="ФОКУС", font_style="Caption", bold=True,
                                  theme_text_color="Custom", text_color=C["accent"],
                                  halign="center", valign="middle")
        self._mode_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        top.add_widget(back); top.add_widget(self._mode_lbl)
        top.add_widget(Widget(size_hint_x=None, width=S(100)))
        root.add_widget(top)

        # ── Сессии ───────────────────────────────────────────────────────
        root.add_widget(Widget(size_hint_y=None, height=S(16)))
        self._sess_box = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                     height=S(20), spacing=S(6),
                                     padding=[S(16),0])
        root.add_widget(self._sess_box)
        self._update_session_dots()

        root.add_widget(Widget(size_hint_y=None, height=S(8)))

        # ── Кольцо таймера ───────────────────────────────────────────────
        from kivy.uix.widget import Widget as KWidget
        from kivy.graphics import Line as KGLine, Color as KGColor, InstructionGroup
        class RingWidget(KWidget):
            def __init__(self, timer_screen, **kw):
                super().__init__(**kw)
                self._ts = timer_screen
                # Создаём инструкции один раз
                self._bg_col  = KGColor(*C["surf2"])
                self._bg_ring = KGLine(width=S(12))
                self._fg_col  = KGColor(*C["accent"])
                self._fg_ring = KGLine(width=S(12), cap="round")
                self.canvas.add(self._bg_col)
                self.canvas.add(self._bg_ring)
                self.canvas.add(self._fg_col)
                self.canvas.add(self._fg_ring)
                self.bind(size=self._draw, pos=self._draw)
            def _draw(self, *_):
                if self.width <= 0 or self.height <= 0:
                    return
                cx, cy = self.center
                r = max(S(8), min(self.width, self.height) / 2 - S(10))
                total = (self._ts.WORK_SEC if self._ts._mode == "work"
                         else self._ts.SHORT_SEC if self._ts._mode == "short"
                         else self._ts.LONG_SEC)
                pct = self._ts._secs / max(1, total)
                angle = pct * 360
                self._bg_col.rgba  = C["surf2"]
                self._bg_ring.circle = (cx, cy, r)
                self._fg_col.rgba  = C["accent"]
                self._fg_ring.circle = (cx, cy, r, 90, 90 + angle)
        # Текст поверх кольца — FloatLayout содержит и кольцо и таймер
        fl = MDFloatLayout(size_hint_y=None, height=S(240))
        self._ring = RingWidget(self, size_hint=(1,1),
                                pos_hint={"center_x":0.5,"center_y":0.5})
        self._timer_lbl = MDLabel(
            text=self._fmt(self._secs), font_style="H3", bold=True,
            theme_text_color="Custom", text_color=C["text"],
            halign="center", valign="middle",
            size_hint=(1,1), pos_hint={"center_x":0.5,"center_y":0.5})
        fl.add_widget(self._ring)
        fl.add_widget(self._timer_lbl)
        root.add_widget(fl)

        root.add_widget(Widget(size_hint_y=None, height=S(16)))

        # ── Активная задача ───────────────────────────────────────────────
        self._task_lbl = MDLabel(text="Задача не выбрана", font_style="Body2",
                                  theme_text_color="Secondary",
                                  halign="center", size_hint_y=None, height=S(24))
        self._task_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        root.add_widget(self._task_lbl)

        pick_btn = MDRaisedButton(text="Выбрать задачу", elevation=0,
                                   md_bg_color=C["surf2"],
                                   size_hint_y=None, height=S(38))
        pick_btn.bind(on_release=self._pick_task)
        root.add_widget(pick_btn)

        root.add_widget(Widget(size_hint_y=None, height=S(24)))

        # ── Кнопки управления ─────────────────────────────────────────────
        btn_row = MDBoxLayout(orientation="horizontal", spacing=S(12),
                               size_hint_y=None, height=S(52))
        self._main_btn = MDRaisedButton(
            text="Старт", md_bg_color=C["accent"],
            size_hint_x=1, elevation=0)
        self._main_btn.bind(on_release=self._toggle)
        reset_btn = MDRaisedButton(
            text="Сброс", md_bg_color=C["surf2"],
            size_hint_x=None, width=S(90), elevation=0)
        reset_btn.bind(on_release=self._reset)
        skip_btn = MDRaisedButton(
            text="Пропустить", md_bg_color=C["surf2"],
            size_hint_x=None, width=S(120), elevation=0)
        skip_btn.bind(on_release=self._skip)
        btn_row.add_widget(reset_btn)
        btn_row.add_widget(self._main_btn)
        btn_row.add_widget(skip_btn)
        root.add_widget(btn_row)

        root.add_widget(Widget(size_hint_y=None, height=S(20)))

        # ── Режимы ───────────────────────────────────────────────────────
        mode_row = MDBoxLayout(orientation="horizontal", spacing=S(8),
                                size_hint_y=None, height=S(38))
        for label, mode in [("25 мин", "work"), ("5 мин", "short"), ("15 мин", "long")]:
            mb = MDRaisedButton(text=label, elevation=0, size_hint_x=1,
                                 md_bg_color=C["accent"] if mode==self._mode else C["surf2"])
            mb.bind(on_release=lambda *_, m=mode, b=mb: self._set_mode(m))
            mode_row.add_widget(mb)
            setattr(self, f"_mode_btn_{mode}", mb)
        root.add_widget(mode_row)

        self.add_widget(root)

    def _set_mode(self, mode):
        self._mode = mode
        secs_map = {"work": self.WORK_SEC, "short": self.SHORT_SEC, "long": self.LONG_SEC}
        labels = {"work": "ФОКУС", "short": "КОРОТКИЙ ОТДЫХ", "long": "ДЛИННЫЙ ОТДЫХ"}
        self._secs = secs_map[mode]
        self._running = False
        if self._clock_ev:
            self._clock_ev.cancel(); self._clock_ev = None
        self._main_btn.text = "Старт"
        self._mode_lbl.text = labels[mode]
        for m in ("work", "short", "long"):
            btn = getattr(self, f"_mode_btn_{m}", None)
            if btn: btn.md_bg_color = C["accent"] if m == mode else C["surf2"]
        self._timer_lbl.text = self._fmt(self._secs)
        if hasattr(self, "_ring"): self._ring._draw()

    def _toggle(self, *_):
        if self._running:
            self._running = False
            if self._clock_ev: self._clock_ev.cancel(); self._clock_ev = None
            self._main_btn.text = "Продолжить"
        else:
            self._running = True
            self._main_btn.text = "Пауза"
            self._clock_ev = Clock.schedule_interval(self._tick, 1)

    def _tick(self, dt):
        if self._secs > 0:
            self._secs -= 1
            self._timer_lbl.text = self._fmt(self._secs)
            if hasattr(self, "_ring"): self._ring._draw()
        else:
            self._running = False
            if self._clock_ev: self._clock_ev.cancel(); self._clock_ev = None
            self._on_complete()

    def _on_complete(self):
        self._main_btn.text = "Старт"
        if self._mode == "work":
            self._sessions += 1
            self._update_session_dots()
            # Отметить задачу как выполненную если выбрана
            if self._task_id and self._task_id in self._app.tasks:
                task = self._app.tasks[self._task_id]
                msg = f"Pomodoro завершён! Задача: {task['title'][:30]}"
            else:
                msg = f"Pomodoro #{self._sessions} завершён! Отдохните."
            self._app._show_toast(msg)
            self._app._send_notification(msg, "Flow·Do Pomodoro")
            # Авто-переключение на отдых
            if self._sessions % 4 == 0:
                self._set_mode("long")
            else:
                self._set_mode("short")
        else:
            self._app._show_toast("Отдых закончен — время работать!")
            self._set_mode("work")

    def _reset(self, *_):
        self._running = False
        if self._clock_ev: self._clock_ev.cancel(); self._clock_ev = None
        secs_map = {"work": self.WORK_SEC, "short": self.SHORT_SEC, "long": self.LONG_SEC}
        self._secs = secs_map[self._mode]
        self._timer_lbl.text = self._fmt(self._secs)
        self._main_btn.text = "Старт"
        if hasattr(self, "_ring"): self._ring._draw()

    def _skip(self, *_):
        self._running = False
        if self._clock_ev: self._clock_ev.cancel(); self._clock_ev = None
        self._secs = 0
        self._on_complete()

    def _update_session_dots(self):
        self._sess_box.clear_widgets()
        from kivy.graphics import Color as _DC, RoundedRectangle as _DR
        for i in range(4):
            dot_w = Widget(size_hint_x=None, width=S(16), size_hint_y=None, height=S(16))
            _active = i < (self._sessions % 4)
            _dcol = C["accent"] if _active else C["surf2"]
            with dot_w.canvas:
                _DC(*_dcol)
                _dr = _DR(pos=dot_w.pos, size=dot_w.size, radius=[S(8)])
            def _upd(w, *_, r=_dr):
                r.pos = (w.x, w.y); r.size = (w.width, w.height)
            dot_w.bind(pos=_upd, size=_upd)
            self._sess_box.add_widget(dot_w)

    def _pick_task(self, *_):
        """Показывает список задач для выбора."""
        from kivy.uix.modalview import ModalView
        from kivy.uix.scrollview import ScrollView
        tasks = [t for t in self._app.tasks.values() if not t.get("done")]
        if not tasks:
            self._app._show_toast("Нет активных задач")
            return
        mv = ModalView(background_color=(0,0,0,0.6), auto_dismiss=True,
                       size_hint=(0.9, 0.7),
                       pos_hint={"center_x":0.5,"center_y":0.5})
        card = MDCard(orientation="vertical", size_hint=(1,1),
                      radius=[S(16)], elevation=8,
                      md_bg_color=C["surf"], padding=[S(12),S(12)])
        hdr = MDLabel(text="Выберите задачу", font_style="H6", bold=True,
                      theme_text_color="Custom", text_color=C["text"],
                      halign="center", size_hint_y=None, height=S(40))
        hdr.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(hdr)
        sv = ScrollView()
        lst = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
        for t in tasks[:20]:
            row = MDCard(size_hint_y=None, height=S(52), radius=[S(8)],
                         elevation=0, md_bg_color=C["surf2"],
                         padding=[S(12),S(8)])
            lbl = MDLabel(text=t["title"][:55], font_style="Body2",
                          theme_text_color="Primary",
                          halign="left", valign="middle")
            lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            row.add_widget(lbl)
            def _sel(w, touch, tid=t["id"], tname=t["title"]):
                if w.collide_point(*touch.pos):
                    self._task_id = tid
                    self._task_lbl.text = tname[:40]
                    mv.dismiss()
                    return True
            row.bind(on_touch_up=_sel)
            lst.add_widget(row)
        sv.add_widget(lst); card.add_widget(sv)
        cancel = MDRaisedButton(text="Отмена", elevation=0,
                                 md_bg_color=C["surf2"],
                                 size_hint_y=None, height=S(40))
        cancel.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(cancel)
        mv.add_widget(card); mv.open()

    @staticmethod
    def _fmt(secs):
        return f"{secs // 60:02d}:{secs % 60:02d}"

class DailyTodoApp(MDApp):

    def build(self):
        self.theme_cls.theme_style     = "Light"
        self.theme_cls.primary_palette = "Pink"

        # Загружаем шрифт с эмодзи если доступен (Android / Linux)
        _emoji_paths = [
            "/system/fonts/NotoColorEmoji.ttf",
            "/system/fonts/NotoEmoji-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        ]
        from kivy.core.text import LabelBase
        for _ep in _emoji_paths:
            if os.path.exists(_ep):
                try:
                    LabelBase.register("emoji", _ep)
                except Exception:
                    pass
                break
        self.store      = JsonStore("tasks.json")
        self.cfg_store  = JsonStore("config.json")
        self.tasks      = {}
        self.categories = ["Работа","Дом","Личное","Покупки","Тренировки"]
        self.cur_cat    = "Все"
        self.sel_date   = datetime.now().strftime("%d.%m.%Y")
        self.filter_date = False
        self.show_done   = True
        self.cur_tab     = "tasks"
        self._cal_sel    = date.today()
        self.user_name   = ""
        self.user_emoji  = "😊"   # эмодзи настроения пользователя
        self.theme_name  = "Роза"
        self._save_ev    = None
        self._ref_ev     = None
        self._ring_pct   = 0.0
        self.weekly_goal = 80       # цель на неделю %
        self.mood_history = {}      # {"DD.MM.YYYY": 1-5}
        self._anthropic_api_key = ""
        self._cal_view_mode = "month"   # "month" | "day"
        self._search_query  = ""        # строка поиска задач

        self._load_config()
        self._apply_md_style()
        self.sm = MDScreenManager()
        if not self.user_name:
            self._build_welcome()
        else:
            self._build_main()
        # планировщик повторяющихся задач
        Clock.schedule_interval(self._check_repeating_tasks, 3600)
        Clock.schedule_once(self._check_repeating_tasks, 5)
        return self.sm

    def _apply_md_style(self):
        self.theme_cls.theme_style = "Dark" if THEMES.get(self.theme_name,{}).get("dark") else "Light"

    def _is_fem(self):
        return THEMES.get(self.theme_name,{}).get("gender") == "female"

    # ── Уведомления ─────────────────────────────────────────────────────────
    def _send_notification(self, message, title="Flow·Do"):
        if PLYER_OK:
            try:
                _plyer_notif.notify(title=title, message=message,
                                    app_name="FlowDo", timeout=5)
            except Exception:
                pass

    # ── Тост (мини-уведомление внутри приложения) ───────────────────────────
    def _show_toast(self, text):
        from kivy.uix.modalview import ModalView
        mv=ModalView(background_color=(0,0,0,0), auto_dismiss=True,
                     size_hint=(0.85,None), height=S(54),
                     pos_hint={"center_x":0.5,"y":0.08})
        card=MDCard(orientation="vertical", size_hint=(1,1),
                    radius=[S(27)], elevation=4,
                    md_bg_color=(*C["accent"][:3],0.92), padding=[S(16),S(8)])
        _lbl_tmp=MDLabel(text=text, font_style="Body1",
                                 theme_text_color="Custom", text_color=(1,1,1,1),
                                halign="center", valign="middle")
        card.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        mv.add_widget(card); mv.open()
        Clock.schedule_once(lambda *_: mv.dismiss(), 2.5)

    # ── Повторяющиеся задачи ─────────────────────────────────────────────────
    def _show_swipe_tip(self, *_):
        """Показывает подсказку по свайпу при первом запуске."""
        if self.cfg_store.exists("swipe_tip_shown"):
            return
        self.cfg_store.put("swipe_tip_shown", v=True)
        from kivy.uix.modalview import ModalView
        mv = ModalView(background_color=(0,0,0,0.6), auto_dismiss=True,
                       size_hint=(0.85, None), height=S(220),
                       pos_hint={"center_x":0.5,"center_y":0.5})
        card = MDCard(orientation="vertical", size_hint=(1,1),
                      radius=[S(18)], elevation=10,
                      md_bg_color=C["surf"], padding=[S(22),S(18)], spacing=S(10))
        tips = [
            ("Свайп вправо >>", "Выполнено"),
            ("Свайп влево <<", "Удалить"),
            ("Долгий тап на +", "Быстрое добавление"),
            ("Меню '...'", "Детали / Pomodoro"),
        ]
        for title, desc in tips:
            row = MDBoxLayout(orientation="vertical", size_hint_y=None,
                              height=S(44), spacing=S(2),
                              padding=[0, S(4)])
            t_lbl = MDLabel(text=title + "  —  " + desc,
                            font_style="Body2",
                            theme_text_color="Custom", text_color=C["text"],
                            halign="left", size_hint_y=None, height=S(36))
            t_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            row.add_widget(t_lbl)
            card.add_widget(row)
        ok_btn = MDRaisedButton(text="Понятно!", md_bg_color=C["accent"],
                                 size_hint_y=None, height=S(40), elevation=0)
        ok_btn.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(ok_btn)
        mv.add_widget(card); mv.open()

    def _check_repeating_tasks(self, *_):
        today_s = date.today().strftime("%d.%m.%Y")
        to_add = []
        for t in list(self.tasks.values()):
            repeat = t.get("repeat","Не повторять")
            if repeat == "Не повторять" or not t.get("done"):
                continue
            orig_date_s = t.get("original_date", t.get("date",""))
            try:
                orig_date = datetime.strptime(orig_date_s, "%d.%m.%Y").date()
            except Exception:
                continue
            if repeat == "Каждый день":
                next_d = date.today()
            elif repeat == "Каждую неделю":
                next_d = date.today()
            elif repeat == "Каждый месяц":
                try:
                    next_d = orig_date.replace(month=date.today().month,
                                               year=date.today().year)
                except Exception:
                    continue
            else:
                continue
            next_s = next_d.strftime("%d.%m.%Y")
            # проверяем, нет ли уже такой задачи на эту дату
            exists = any(
                tt.get("title") == t["title"] and
                tt.get("date") == next_s and
                not tt.get("done")
                for tt in self.tasks.values()
            )
            if not exists and next_s >= today_s:
                to_add.append({**t, "id":str(datetime.now().timestamp()+random.random()),
                                "date":next_s, "done":False, "original_date":next_s})
        for task in to_add:
            self.tasks[task["id"]] = task
        if to_add:
            self.save_tasks()
            Clock.schedule_once(lambda *_: self.refresh_task_list(), 0.1)

    # ── Настроение ───────────────────────────────────────────────────────────
    def _save_mood(self, value):
        today_s = date.today().strftime("%d.%m.%Y")
        self.mood_history[today_s] = value
        self.cfg_store.put("mood_history", data=self.mood_history)

    def _load_mood_history(self):
        if self.cfg_store.exists("mood_history"):
            self.mood_history = self.cfg_store.get("mood_history").get("data", {})

    # ── Приветствие ─────────────────────────────────────────────────────────
    def _build_welcome(self):
        if self.sm.has_screen("welcome"): return
        sc=MDScreen(name="welcome")
        root=FloatLayout()
        with root.canvas.before:
            Color(*C["bg"]); self._wbg=Rectangle(size=Window.size, pos=(0,0))
        root.bind(size=lambda w,s: setattr(self._wbg,"size",s))
        card=MDCard(size_hint=(0.92,None),
                    height=min(S(480),Window.height*0.86),
                    pos_hint={"center_x":0.5,"center_y":0.5},
                    radius=[S(28)], elevation=4, md_bg_color=C["surf"], padding=[S(28),S(22)])
        sv=ScrollView(size_hint=(1,1))
        ci=MDBoxLayout(orientation="vertical", spacing=S(14), size_hint_y=None)
        ci.bind(minimum_height=ci.setter("height"))
        _lbl_tmp=MDLabel(text="Flow\u00b7Do", font_style="H4", bold=True,
                               theme_text_color="Custom", text_color=C["accent"],
                               halign="center", size_hint_y=None, height=S(52))
        ci.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        _init_mot_text = random.choice(MOTIVATIONS_F)
        self._w_quote=EmojiLabel(text=_init_mot_text,
                               font_style="Subtitle2",
                               halign="center", size_hint_y=None, height=S(42),
                               theme_text_color="Secondary")
        ci.add_widget(self._w_quote)
        _lbl_tmp=MDLabel(text="Выберите стиль:", font_style="Caption",
                               theme_text_color="Secondary", size_hint_y=None, height=S(20),
                      halign="left", valign="middle")
        ci.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        g_row=MDBoxLayout(orientation="horizontal", spacing=S(10),
                          size_hint_y=None, height=S(46))
        self._wg_fem=MDRaisedButton(text="Женский", size_hint_x=0.5,
                                     md_bg_color=C["accent"], elevation=0)
        self._wg_mal=MDRaisedButton(text="Мужской", size_hint_x=0.5,
                                     md_bg_color=C["surf2"], elevation=0)
        self._wg_fem.bind(on_release=lambda *_: self._wel_gender("female"))
        self._wg_mal.bind(on_release=lambda *_: self._wel_gender("male"))
        g_row.add_widget(self._wg_fem); g_row.add_widget(self._wg_mal)
        ci.add_widget(g_row)
        _lbl_tmp=MDLabel(text="Ваше имя:", font_style="Caption",
                               theme_text_color="Secondary", size_hint_y=None, height=S(20),
                      halign="left", valign="middle")
        ci.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        self._wf_name=MDTextField(hint_text="Введите имя *", size_hint_y=None, height=S(52))
        ci.add_widget(self._wf_name)
        ci.add_widget(Widget(size_hint_y=None, height=S(10)))
        go=MDRaisedButton(text="Начать", md_bg_color=C["accent"],
                           size_hint=(1,None), height=S(52), elevation=2)
        go.bind(on_release=self._welcome_go); ci.add_widget(go)
        sv.add_widget(ci); card.add_widget(sv); root.add_widget(card)
        sc.add_widget(root); self.sm.add_widget(sc)
        self.sm.current="welcome"

    def _wel_gender(self, g):
        tn="Бронза" if g=="male" else "Роза"
        C.update(THEMES[tn]); self.theme_name=tn
        self._apply_md_style()
        # Пересоздаём welcome экран с новыми цветами
        saved_name = getattr(self._wf_name, "text", "") if hasattr(self, "_wf_name") else ""
        if self.sm.has_screen("welcome"):
            self.sm.remove_widget(self.sm.get_screen("welcome"))
        self._build_welcome()
        # Восстанавливаем введённое имя
        if saved_name and hasattr(self, "_wf_name"):
            self._wf_name.text = saved_name
        # Подсвечиваем активную кнопку
        try:
            self._wg_fem.md_bg_color = C["accent"] if g=="female" else C["surf2"]
            self._wg_mal.md_bg_color = C["accent"] if g=="male"   else C["surf2"]
            self._wg_fem.children[0].text_color = (1,1,1,1) if g=="female" else C["text"]
            self._wg_mal.children[0].text_color = (1,1,1,1) if g=="male"   else C["text"]
        except Exception:
            pass
        if hasattr(self, "_w_quote"):
            update_emoji_label(self._w_quote, random.choice(MOTIVATIONS_M if g=="male" else MOTIVATIONS_F))

    def _welcome_go(self, *_):
        name=self._wf_name.text.strip()
        if not name: self._wf_name.hint_text="Введите имя!"; return
        self.user_name=name
        self._apply_md_style(); self._save_config()
        self._build_main(); self.sm.current="main"

    # ── Главный экран ────────────────────────────────────────────────────────
    def _build_main(self):
        if self.sm.has_screen("main"):
            self.sm.remove_widget(self.sm.get_screen("main"))
        sc=MDScreen(name="main")
        root=FloatLayout()
        with root.canvas.before:
            Color(*C["bg"]); self._mbg=Rectangle(size=Window.size, pos=(0,0))
        root.bind(size=lambda w,s: setattr(self._mbg,"size",s))
        ui=MDBoxLayout(orientation="vertical", md_bg_color=(0,0,0,0))
        ui.add_widget(self._make_topbar())
        self.pages=MDBoxLayout(orientation="vertical")
        ui.add_widget(self.pages)
        ui.add_widget(self._make_nav())
        root.add_widget(ui)

        # FAB — добавить задачу
        self._fab=MDCard(size_hint=(None,None), size=(S(56),S(56)),
                          radius=[S(28)], elevation=8, md_bg_color=C["accent"],
                          pos_hint={"right":0.94,"y":0.10})
        _lbl_tmp=MDLabel(text="+", font_style="H5", bold=True,
                                      halign="center", valign="middle",
                                      theme_text_color="Custom", text_color=(1,1,1,1))
        self._fab.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        _fab_press_time = [0]
        def _ft_down(w, t):
            if w.opacity < 0.5: return False
            if self._fab.collide_point(*t.pos):
                import time as _time
                _fab_press_time[0] = _time.time()
            return False
        def _ft(w, t):
            if w.opacity < 0.5: return False
            if self._fab.collide_point(*t.pos):
                if getattr(self, "_fab_locked", False): return True
                self._fab_locked = True
                Clock.schedule_once(lambda *_: setattr(self, "_fab_locked", False), 0.8)
                import time as _time
                held = _time.time() - _fab_press_time[0]
                if held > 0.5:
                    # Долгое нажатие — быстрое добавление
                    self._quick_add_sheet()
                else:
                    # Обычное нажатие — полная форма
                    self.open_task_form()
                return True
        self._fab.bind(on_touch_down=_ft_down, on_touch_up=_ft)
        root.add_widget(self._fab)


        sc.add_widget(root); self.sm.add_widget(sc)
        self._pg_tasks    = self._mk_tasks_page()
        self._pg_calendar = self._mk_calendar_page()
        self._pg_pomodoro = PomodoroScreen(app_ref=self, name="pg_pomodoro")
        self._pg_stats    = self._mk_stats_page()
        self._pg_settings = self._mk_settings_page()
        self.pages.add_widget(self._pg_tasks)
        self.cur_tab="tasks"; self._nav_update("tasks")
        Clock.schedule_once(self.load_tasks, 0.2)
        Clock.schedule_once(self._show_swipe_tip, 1.5)
        Clock.schedule_once(self._check_shared_intent, 0.5)

    def _check_shared_intent(self, *_):
        """Проверяет, не было ли приложение открыто через 'Открыть с помощью' (.json файл)."""
        if PLATFORM != "android":
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            intent = activity.getIntent()
            if intent is None:
                return
            action = intent.getAction()
            Intent = autoclass("android.content.Intent")
            if action == Intent.ACTION_VIEW or action == Intent.ACTION_SEND:
                uri = intent.getData()
                if uri is not None:
                    self.handle_shared_file(uri.toString())
        except Exception:
            pass

    # ── Топбар ──────────────────────────────────────────────────────────────
    def _make_topbar(self):
        is_fem=self._is_fem()
        now=datetime.now(); h=now.hour
        greet="Доброе утро," if h<12 else ("Добрый день," if h<18 else "Добрый вечер,")

        if is_fem:
            # Женская тема: приветствие + имя + дата
            # Высоты: padding_top=10, r1=26, name_row=40, date=20, padding_bot=6 → ~102
            tb=MDBoxLayout(orientation="vertical", size_hint_y=None, height=S(102),
                           md_bg_color=C["surf"],
                           padding=[S(18),S(10),S(14),S(6)], spacing=S(0))
            r1=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(26))
            greet_lbl=MDLabel(text=greet, font_style="Caption",
                              theme_text_color="Custom", text_color=C["text2"],
                              halign="left", valign="middle")
            greet_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            r1.add_widget(greet_lbl)
            av=MDIconButton(icon="account-circle-outline", size_hint=(None,None),
                            size=(S(36),S(36)), theme_text_color="Custom",
                            text_color=C["accent"])
            av.bind(on_release=lambda *_: self._nav_switch("settings"))
            r1.add_widget(av); tb.add_widget(r1)

            # Строка имени: эмодзи (если есть) + имя
            name_row=MDBoxLayout(orientation="horizontal", spacing=S(6),
                                  size_hint_y=None, height=S(40))
            _u_em_path=get_emoji_png(self.user_emoji.strip()) if self.user_emoji else None
            if _u_em_path:
                _u_em_img=KivyImage(source=_u_em_path, size_hint=(None,None),
                                     size=(S(30),S(30)), allow_stretch=True, keep_ratio=True)
                name_row.add_widget(_u_em_img)
            _u_name_lbl=MDLabel(text=self.user_name or "Имя", font_style="H5", bold=True,
                                 theme_text_color="Custom", text_color=C["accent"],
                                 halign="left", valign="middle")
            _u_name_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            name_row.add_widget(_u_name_lbl)
            self._tb_name=name_row; self._tb_name_lbl=_u_name_lbl
            tb.add_widget(name_row)

            self._tb_date=MDLabel(text=self._fmt_date(now), font_style="Caption",
                                   theme_text_color="Custom", text_color=C["text2"],
                                   halign="left", valign="middle",
                                   size_hint_y=None, height=S(20))
            self._tb_date.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            tb.add_widget(self._tb_date)

        else:
            # Мужская тема: иконки справа + СЕГОДНЯ + дата
            # Высоты: padding_top=10, r1=30, name=30, date=20, padding_bot=6 → ~96
            tb=MDBoxLayout(orientation="vertical", size_hint_y=None, height=S(96),
                           md_bg_color=C["surf"],
                           padding=[S(18),S(10),S(14),S(6)], spacing=S(0))
            r1=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(30))
            r1.add_widget(MDIconButton(icon="menu", size_hint_x=None, width=S(36),
                                        theme_text_color="Custom", text_color=C["text2"]))
            r1.add_widget(Widget())
            # Аватар пользователя — KivyImage если есть PNG, иначе иконка колокольчика
            _u_em_path_m=get_emoji_png(self.user_emoji.strip()) if self.user_emoji else None
            if _u_em_path_m:
                em_btn=MDCard(size_hint=(None,None), size=(S(34),S(34)),
                              radius=[S(8)], elevation=0, md_bg_color=C["surf2"])
                em_img=KivyImage(source=_u_em_path_m, size_hint=(1,1),
                                  allow_stretch=True, keep_ratio=True)
                em_btn.add_widget(em_img)
                em_btn.bind(on_touch_up=lambda w,t:
                    self._nav_switch("settings") if w.collide_point(*t.pos) else None)
                r1.add_widget(em_btn)
            r1.add_widget(Widget(size_hint_x=None, width=S(4)))
            r1.add_widget(MDIconButton(icon="bell-outline", size_hint_x=None, width=S(36),
                                       theme_text_color="Custom", text_color=C["text2"]))
            tb.add_widget(r1)

            self._tb_name=MDLabel(text="СЕГОДНЯ", font_style="H6", bold=True,
                                   theme_text_color="Primary",
                                   halign="left", valign="middle",
                                   size_hint_y=None, height=S(30))
            self._tb_name.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            tb.add_widget(self._tb_name)

            self._tb_date=MDLabel(text=self._fmt_date(now), font_style="Caption",
                                   theme_text_color="Secondary",
                                   halign="left", valign="middle",
                                   size_hint_y=None, height=S(20))
            self._tb_date.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            tb.add_widget(self._tb_date)

        return tb

    def _fmt_date(self, now):
        DAYS=["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        MONTHS=["января","февраля","марта","апреля","мая","июня",
                "июля","августа","сентября","октября","ноября","декабря"]
        return f"{now.day} {MONTHS[now.month-1]}, {DAYS[now.weekday()].lower()}"

    # ── Навигация ────────────────────────────────────────────────────────────
    def _make_nav(self):
        # Навбар: только иконки, без подписей. Активная — pill-подсветка.
        NAV_H = S(62)
        nav = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                          height=NAV_H, md_bg_color=C["nav"],
                          padding=[S(6), S(6), S(6), S(6)])
        self._nav_btns = {}
        TABS = [
            ("tasks",    "home-variant",        ),
            ("calendar", "calendar-month",      ),
            ("pomodoro", "clock-play",           ),
            ("stats",    "chart-bar",            ),
            ("settings", "cog",                  ),
        ]
        for tab, ico in TABS:
            # контейнер одной кнопки
            col = FloatLayout(size_hint_x=1, size_hint_y=1)

            # pill-фон (виден только для активной вкладки)
            pill = Widget(size_hint=(None, None),
                          size=(S(48), S(32)),
                          pos_hint={"center_x": 0.5, "center_y": 0.5})
            def _draw_pill(w, *_, c=C):
                w.canvas.clear()
                with w.canvas:
                    Color(*c["acc_s"])
                    RoundedRectangle(pos=w.pos, size=w.size, radius=[S(16)])
            pill.bind(pos=_draw_pill, size=_draw_pill)
            pill.opacity = 0   # скрыт по умолчанию
            col.add_widget(pill)

            # иконка
            btn = MDIconButton(
                icon=ico,
                size_hint=(None, None), size=(S(44), S(44)),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                theme_text_color="Custom", text_color=C["text2"])
            btn.bind(on_release=lambda _, t=tab: self._nav_switch(t))
            col.add_widget(btn)

            self._nav_btns[tab] = (btn, pill)
            nav.add_widget(col)
        return nav

    def _nav_update(self, tab):
        for t, (b, pill) in self._nav_btns.items():
            active = (t == tab)
            b.text_color = C["accent"] if active else C["text2"]
            pill.opacity = 1 if active else 0

    def _nav_switch(self, tab):
        if self.cur_tab==tab: return
        # сбрасываем поиск при уходе с вкладки задач
        if self.cur_tab == "tasks" and hasattr(self, "_search_field"):
            try:
                self._search_field.text = ""
                self._search_query = ""
                if hasattr(self, "_search_clear_btn"):
                    self._search_clear_btn.opacity = 0
            except Exception:
                pass
        self.cur_tab=tab; self._nav_update(tab)
        self.pages.clear_widgets()
        pg={"tasks":self._pg_tasks,"calendar":self._pg_calendar,
            "pomodoro":self._pg_pomodoro,
            "stats":self._pg_stats,"settings":self._pg_settings}[tab]
        self.pages.add_widget(pg)
        self._fab.opacity = 1 if tab == "tasks" else 0
        if tab=="stats":
            def _stats_open(*_):
                self._refresh_stats()
                Clock.schedule_once(lambda *_: (
                    setattr(self._stats_sv, 'scroll_y', 1.0)
                    if hasattr(self, '_stats_sv') else None
                ), 0.3)
            Clock.schedule_once(_stats_open, 0.05)
        if tab=="calendar":Clock.schedule_once(lambda *_: self._refresh_cal(), 0.05)
        if tab=="settings":Clock.schedule_once(lambda *_: self._rebuild_cats_list(), 0.05)
        # скрыть/показать FAB и голос — ТОЛЬКО на вкладке задач
        fab_vis = (tab == "tasks")
        self._fab.opacity       = 1 if fab_vis else 0
        # Полностью отключаем touch-события когда скрыты
        self._fab.disabled       = not fab_vis

    # ════════════════════════════════════════════════════════════════════════
    #  СТРАНИЦА: ЗАДАЧИ
    # ════════════════════════════════════════════════════════════════════════
    def _mk_tasks_page(self):
        is_fem=self._is_fem()

        pg = MDBoxLayout(orientation="vertical")

        # ScrollView — весь контент прокручивается
        sv = ScrollView(size_hint=(1,1))
        inn = MDBoxLayout(orientation="vertical", adaptive_height=True,
                          spacing=S(8), padding=[S(12),S(8),S(12),S(80)])
        sv.add_widget(inn)

        # ── Задача дня ───────────────────────────────────────────────────
        day_c = MDCard(size_hint_y=None, height=S(96),
                       radius=[S(18)] if is_fem else [S(10)],
                       elevation=2 if is_fem else 0,
                       md_bg_color=C["surf"], padding=[S(16),S(14)])
        dc = MDBoxLayout(orientation="horizontal", spacing=S(12))
        di = MDBoxLayout(orientation="vertical", spacing=S(4))

        hdr_path = get_emoji_png("⭐")
        if hdr_path:
            hdr_row = MDBoxLayout(orientation="horizontal",
                                  size_hint_y=None, height=S(18), spacing=S(4))
            hdr_img = KivyImage(source=hdr_path, size_hint=(None,None),
                                size=(S(16),S(16)), allow_stretch=True, keep_ratio=True)
            hdr_row.add_widget(hdr_img)
            hdr_lbl = MDLabel(text="Задача дня", font_style="Caption",
                              theme_text_color="Custom", text_color=C["text2"],
                              halign="left", valign="middle")
            hdr_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            hdr_row.add_widget(hdr_lbl)
            di.add_widget(hdr_row)
        else:
            hdr_lbl = MDLabel(text="Задача дня", font_style="Caption",
                              theme_text_color="Custom", text_color=C["text2"],
                              size_hint_y=None, height=S(18),
                              halign="left", valign="middle")
            hdr_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            di.add_widget(hdr_lbl)

        self._day_task_lbl = MDLabel(text="Список пуст", font_style="Subtitle1",
                                     bold=True, theme_text_color="Custom",
                                     text_color=C["text"], size_hint_y=None, height=S(30),
                                     halign="left", valign="middle",
                                     shorten=True, shorten_from="right")
        self._day_task_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        di.add_widget(self._day_task_lbl)

        self._day_task_sub = MDLabel(text="", font_style="Caption",
                                     theme_text_color="Custom", text_color=C["text2"],
                                     size_hint_y=None, height=S(20),
                                     halign="left", valign="middle")
        self._day_task_sub.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        di.add_widget(self._day_task_sub)
        dc.add_widget(di)

        prog_box = MDBoxLayout(orientation="vertical", size_hint_x=None,
                               width=S(56), spacing=S(4))
        self._day_pct_lbl = MDLabel(text="0%", font_style="Subtitle2", bold=True,
                                    halign="center", theme_text_color="Custom",
                                    text_color=C["accent"], size_hint_y=None, height=S(24))
        prog_box.add_widget(self._day_pct_lbl)
        self._prog_bg = Widget(size_hint=(1,1))
        self._prog_fill = 0.0
        def _draw_prog(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(*C["acc_s"])
                RoundedRectangle(pos=w.pos, size=w.size, radius=[S(5)])
                if self._prog_fill > 0:
                    Color(*C["accent"])
                    RoundedRectangle(pos=w.pos,
                                     size=(w.width, max(w.height*self._prog_fill, S(4))),
                                     radius=[S(5)])
        self._prog_bg.bind(pos=_draw_prog, size=_draw_prog)
        self._draw_prog = _draw_prog
        prog_box.add_widget(self._prog_bg)
        self._pct_lbl = MDLabel(text="0%", font_style="Caption",
                                halign="center", theme_text_color="Secondary",
                                size_hint_y=None, height=S(16))
        prog_box.add_widget(self._pct_lbl)
        dc.add_widget(prog_box)
        day_c.add_widget(dc)
        inn.add_widget(day_c)

        # ── Категории ────────────────────────────────────────────────────
        cat_sv = ScrollView(size_hint_y=None, height=S(42), do_scroll_y=False)
        self.cat_bar = MDBoxLayout(orientation="horizontal", size_hint_x=None,
                                   spacing=S(8), padding=[S(14),S(4),S(14),S(4)])
        self.cat_bar.bind(minimum_width=self.cat_bar.setter("width"))
        self._cat_btns = {}
        b_all = self._mk_cat_btn("Все"); self._cat_btns["Все"]=b_all
        self.cat_bar.add_widget(b_all)
        for cat in self.categories:
            b = self._mk_cat_btn(cat); self._cat_btns[cat]=b; self.cat_bar.add_widget(b)
        cat_sv.add_widget(self.cat_bar)
        inn.add_widget(cat_sv)

        # ── Фильтры ──────────────────────────────────────────────────────
        flt_sv = ScrollView(size_hint_y=None, height=S(38), do_scroll_y=False)
        flt_r = MDBoxLayout(orientation="horizontal", size_hint_x=None,
                            spacing=S(6), padding=[0,S(2)])
        flt_r.bind(minimum_width=flt_r.setter("width"))
        def _mk_flt(text, cb):
            card = MDCard(size_hint_x=None, width=S(6*len(text)+24),
                          size_hint_y=None, height=S(30),
                          radius=[S(15)] if is_fem else [S(6)],
                          elevation=0, md_bg_color=C["surf2"])
            lbl = MDLabel(text=text, font_style="Caption",
                          halign="center", valign="middle",
                          theme_text_color="Custom", text_color=C["text"], size_hint=(1,1))
            lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            card._lbl=lbl; card.add_widget(lbl)
            def _tap(w,t):
                if card.collide_point(*t.pos): cb(); return True
            card.bind(on_touch_up=_tap)
            return card
        self.f_date  = _mk_flt("Все даты",    self._tog_date)
        self.f_done  = _mk_flt("Скрыть вып.", self._tog_done)
        self.f_carry = _mk_flt("Перенести",   self._carry)
        for b in (self.f_date, self.f_done, self.f_carry):
            flt_r.add_widget(b)
        flt_sv.add_widget(flt_r); inn.add_widget(flt_sv)

        # ── Поиск ────────────────────────────────────────────────────────
        search_box = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                 height=S(44), spacing=S(8), padding=[0,S(2),0,S(2)])
        search_ico = MDIconButton(icon="magnify", size_hint=(None,None),
                                  size=(S(36),S(36)),
                                  theme_text_color="Custom", text_color=C["text2"])
        self._search_field = MDTextField(
            hint_text="Поиск задач, подзадач, комментариев...",
            size_hint=(1,None), height=S(40), mode="fill")
        clear_btn = MDIconButton(icon="close-circle-outline",
                                 size_hint=(None,None), size=(S(36),S(36)),
                                 theme_text_color="Custom", text_color=C["text2"],
                                 opacity=0)
        self._search_clear_btn = clear_btn
        def _on_search_text(field, text):
            self._search_query = text.strip().lower()
            clear_btn.opacity = 1 if text.strip() else 0
            self.refresh_task_list()
        def _on_clear_search(*_):
            self._search_field.text = ""
            self._search_query = ""
            clear_btn.opacity = 0
            self.refresh_task_list()
        self._search_field.bind(text=_on_search_text)
        clear_btn.bind(on_release=_on_clear_search)
        search_box.add_widget(search_ico)
        search_box.add_widget(self._search_field)
        search_box.add_widget(clear_btn)
        inn.add_widget(search_box)

        self._search_result_lbl = MDLabel(
            text="", font_style="Caption",
            theme_text_color="Custom", text_color=C["text2"],
            size_hint_y=None, height=S(18), halign="left")
        self._search_result_lbl.bind(
            size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        inn.add_widget(self._search_result_lbl)

        # ── Список задач ──────────────────────────────────────────────────
        self.task_list = MDBoxLayout(orientation="vertical", adaptive_height=True,
                                     spacing=S(10) if is_fem else S(6))
        inn.add_widget(self.task_list)

        pg.add_widget(sv)
        return pg

    def _mk_cat_btn(self, cat):
        is_fem=self._is_fem(); sel=(cat==self.cur_cat)
        # Для "Все" — специальная иконка ✨
        if cat == "Все":
            em = "\u2728"  # ✨ есть в базе
        else:
            em=CAT_EMOJI.get(cat,"")
        rad=S(16) if is_fem else S(8)
        bg=C["accent"] if sel else C["surf2"]
        tc=(1,1,1,1) if sel else C["text"]
        w=max(S(80), S(7)*len(cat)+S(52))
        card=MDCard(size_hint_x=None, width=w, size_hint_y=None, height=S(36),
                    radius=[rad], elevation=0, md_bg_color=bg)
        inner=MDBoxLayout(orientation="horizontal", spacing=S(4),
                          padding=[S(8),0], size_hint=(1,1))
        if em:
            em_path=get_emoji_png(em.strip())
            if em_path:
                em_img=KivyImage(source=em_path, size_hint=(None,None),
                                  size=(S(20),S(20)), allow_stretch=True, keep_ratio=True)
                inner.add_widget(em_img)
        txt_lbl=MDLabel(text=cat, font_style="Caption", bold=sel,
                        halign="center", valign="middle",
                        theme_text_color="Custom", text_color=tc,
                        size_hint_x=1)
        txt_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        inner.add_widget(txt_lbl)
        card._lbl=txt_lbl; card.add_widget(inner)
        def _tap(w,t):
            if card.collide_point(*t.pos): self._switch_cat(cat); return True
        card.bind(on_touch_up=_tap)
        return card

    def _update_cat_colors(self):
        is_fem=self._is_fem()
        for c,b in self._cat_btns.items():
            sel=(c==self.cur_cat)
            b.md_bg_color=C["accent"] if sel else C["surf2"]
            # Обновляем цвет текстовой метки (_lbl)
            if hasattr(b,"_lbl"):
                b._lbl.text_color=(1,1,1,1) if sel else C["text"]
                b._lbl.bold=sel

    def _switch_cat(self, c):
        self.cur_cat=c; self._update_cat_colors()
        self.refresh_task_list()
        self._save_config()

    # ════════════════════════════════════════════════════════════════════════
    #  СТРАНИЦА: КАЛЕНДАРЬ (с почасовым видом)
    # ════════════════════════════════════════════════════════════════════════
    def _mk_calendar_page(self):
        is_fem=self._is_fem()
        pg=MDBoxLayout(orientation="vertical")
        hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(54), md_bg_color=C["surf"], padding=[S(16),S(10)])
        self._cal_month_lbl=MDLabel(text=self._cal_month_str(), font_style="H6",
                                     bold=True, theme_text_color="Primary")
        hdr.add_widget(self._cal_month_lbl); hdr.add_widget(Widget())
        # переключатель вид месяц/день
        view_toggle=MDCard(size_hint=(None,None), size=(S(80),S(30)),
                           radius=[S(15)], elevation=0, md_bg_color=C["surf2"])
        self._cal_view_lbl=MDLabel(text="Месяц", font_style="Caption",
                                    halign="center", valign="middle",
                                    theme_text_color="Custom", text_color=C["text"],
                                    size_hint=(1,1))
        view_toggle.add_widget(self._cal_view_lbl)
        def _tog_view(w,t):
            if view_toggle.collide_point(*t.pos):
                self._cal_view_mode = "day" if self._cal_view_mode=="month" else "month"
                self._cal_view_lbl.text = "День" if self._cal_view_mode=="day" else "Месяц"
                Clock.schedule_once(lambda *_: self._refresh_cal(), 0.05)
                return True
        view_toggle.bind(on_touch_up=_tog_view)
        hdr.add_widget(view_toggle)
        pg.add_widget(hdr)

        sv=ScrollView()
        inn=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(10), padding=[S(12),S(8),S(12),S(20)])
        sv.add_widget(inn)
        task_dates={t.get("date","") for t in self.tasks.values()}
        self.cal_w=CalendarWidget(on_select=self._on_cal_select, task_dates=task_dates)
        # Обёртка с фиксированной высотой для корректного отображения в ScrollView
        cal_holder=MDBoxLayout(orientation="vertical", size_hint_y=None)
        cal_holder.bind(minimum_height=cal_holder.setter("height"))
        cal_holder.add_widget(self.cal_w)
        self.cal_w.bind(height=lambda w,h: setattr(cal_holder,"height",h))
        cal_holder.height=self.cal_w.height
        inn.add_widget(cal_holder)
        self._cal_day_lbl=MDLabel(text="Сегодня", font_style="Subtitle1", bold=True,
                                   theme_text_color="Primary",
                                   size_hint_y=None, height=S(34))
        inn.add_widget(self._cal_day_lbl)
        self.cal_task_list=MDBoxLayout(orientation="vertical",
                                        adaptive_height=True, spacing=S(4))
        inn.add_widget(self.cal_task_list)
        add_btn=MDRaisedButton(text="  Добавить задачу",
                                size_hint_y=None, height=S(50),
                                md_bg_color=C["accent"], elevation=0)
        add_btn.bind(on_release=lambda *_: self.open_task_form())
        inn.add_widget(add_btn)
        pg.add_widget(sv)
        return pg

    def _cal_month_str(self):
        MONTHS=["Январь","Февраль","Март","Апрель","Май","Июнь",
                "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
        return MONTHS[self._cal_sel.month-1]

    def _on_cal_select(self, d):
        self._cal_sel=d
        if hasattr(self,"_cal_month_lbl"):
            self._cal_month_lbl.text=self._cal_month_str()
        self._refresh_cal()

    def _refresh_cal(self):
        if not hasattr(self,"cal_task_list"): return
        self.cal_task_list.clear_widgets()
        ds=self._cal_sel.strftime("%d.%m.%Y")
        DAYS=["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        MONTHS=["января","февраля","марта","апреля","мая","июня",
                "июля","августа","сентября","октября","ноября","декабря"]
        today=date.today(); sfx=" (сегодня)" if self._cal_sel==today else ""
        self._cal_day_lbl.text=(f"{DAYS[self._cal_sel.weekday()]}, "
                                 f"{self._cal_sel.day} {MONTHS[self._cal_sel.month-1]}{sfx}")

        tasks=sorted([t for t in self.tasks.values() if t.get("date")==ds],
                     key=lambda t:(t.get("done",False), t.get("time","23:59") or "23:59"))

        if not tasks:
            self.cal_task_list.add_widget(
                MDLabel(text="Нет задач на этот день", halign="center",
                        theme_text_color="Secondary", size_hint_y=None, height=S(44)))
            if hasattr(self,"cal_w"):
                self.cal_w.refresh_dates({t.get("date","") for t in self.tasks.values()})
            return

        is_fem=self._is_fem()

        if self._cal_view_mode=="day":
            # ── Почасовой вид ────────────────────────────────────────────
            HOURS=["09:00","10:00","11:00","12:00","13:00","14:00",
                   "15:00","16:00","17:00","18:00","19:00","20:00"]
            for h in HOURS:
                slot=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                 height=S(52), spacing=S(8), padding=[0,S(4)])
                _lbl_tmp=MDLabel(text=h, font_style="Caption",
                                        theme_text_color="Custom", text_color=C["text2"],
                                        size_hint_x=None, width=S(44),
                                        halign="right", valign="middle")
                slot.add_widget(_lbl_tmp)
                _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
                # линия
                line_w=Widget(size_hint=(None,None), size=(S(1),S(44)),
                              pos_hint={"center_y":0.5})
                def _dl(w,*_):
                    w.canvas.clear()
                    with w.canvas:
                        Color(*C["div"]); Rectangle(pos=w.pos, size=w.size)
                line_w.bind(pos=_dl, size=_dl); slot.add_widget(line_w)
                # задача на этот час
                h_tasks=[t for t in tasks if t.get("time","").startswith(h[:2])]
                if h_tasks:
                    t=h_tasks[0]
                    tc2=MDCard(size_hint_y=None, height=S(44),
                               radius=[S(12)] if is_fem else [S(8)],
                               elevation=0,
                               md_bg_color=(*C["accent"][:3], 0.15) if not t.get("done") else C["surf2"],
                               padding=[S(12),S(8)])
                    row2=MDBoxLayout(orientation="horizontal")
                    _lbl_tmp=MDLabel(text=t.get("title",""), font_style="Body2",
                                            theme_text_color="Custom",
                                            text_color=C["text2"] if t.get("done") else C["text"],
                                  halign="left", valign="middle")
                    row2.add_widget(_lbl_tmp)
                    _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
                    if t.get("done"):
                        row2.add_widget(MDIconButton(icon="check", size_hint_x=None, width=S(28),
                                                      theme_text_color="Custom", text_color=C["green"]))
                    tc2.add_widget(row2)
                    def _tap2(w,touch,tid=t["id"]):
                        if w.collide_point(*touch.pos): self.open_task_detail(tid); return True
                    tc2.bind(on_touch_up=_tap2); slot.add_widget(tc2)
                else:
                    slot.add_widget(Widget())
                self.cal_task_list.add_widget(slot)
        else:
            # ── Список ───────────────────────────────────────────────────
            for t in tasks:
                if t.get("time"):
                    slot=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                     height=S(52), spacing=S(8), padding=[0,S(4)])
                    _lbl_tmp=MDLabel(text=t["time"], font_style="Caption",
                                            theme_text_color="Custom", text_color=C["text2"],
                                            size_hint_x=None, width=S(44),
                                            halign="right", valign="middle")
                    slot.add_widget(_lbl_tmp)
                    _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
                    dot=Widget(size_hint=(None,None), size=(S(8),S(8)),
                               pos_hint={"center_y":0.5})
                    def _dd(w,*_,done=t.get("done",False)):
                        w.canvas.clear()
                        with w.canvas:
                            Color(*(C["green"] if done else C["accent"]))
                            Ellipse(pos=w.pos, size=w.size)
                    dot.bind(pos=_dd, size=_dd); slot.add_widget(dot)
                    tc2=MDCard(size_hint_y=None, height=S(44),
                               radius=[S(12)] if is_fem else [S(8)],
                               elevation=0, md_bg_color=C["surf"], padding=[S(12),S(8)])
                    _lbl_tmp=MDLabel(text=t.get("title",""), font_style="Body2",
                                           theme_text_color="Custom",
                                           text_color=C["text2"] if t.get("done") else C["text"],
                                  halign="left", valign="middle")
                    tc2.add_widget(_lbl_tmp)
                    _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
                    def _tap(w,touch,tid=t["id"]):
                        if w.collide_point(*touch.pos): self.open_task_detail(tid); return True
                    tc2.bind(on_touch_up=_tap); slot.add_widget(tc2)
                    self.cal_task_list.add_widget(slot)
                else:
                    self.cal_task_list.add_widget(
                        TaskCard(task_id=t["id"], title=t["title"], task_date=t["date"],
                                 done=t.get("done",False), priority=t.get("priority","Средний"),
                                 category=t.get("category",""), comment=t.get("comment",""),
                                 original_date=t.get("original_date",t["date"]),
                                 subtasks=t.get("subtasks",[]), show_cat=True))

        if hasattr(self,"cal_w"):
            self.cal_w.refresh_dates({t.get("date","") for t in self.tasks.values()})

    # ════════════════════════════════════════════════════════════════════════
    #  СТРАНИЦА: СТАТИСТИКА
    # ════════════════════════════════════════════════════════════════════════
    def _mk_stats_page(self):
        is_fem=self._is_fem()
        pg=MDBoxLayout(orientation="vertical")

        # ── Заголовок ────────────────────────────────────────────────────────
        hdr=MDBoxLayout(orientation="vertical", size_hint_y=None, height=S(84),
                        md_bg_color=C["surf"], padding=[S(16),S(8),S(16),S(6)])
        title_row=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(36))
        t_lbl=MDLabel(text="Статистика", font_style="H6", bold=True,
                      theme_text_color="Primary", halign="left", valign="middle")
        t_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        title_row.add_widget(t_lbl); hdr.add_widget(title_row)

        self._stat_period="week"; self._sp_btns={}
        pr=MDBoxLayout(orientation="horizontal", spacing=S(4),
                       size_hint_y=None, height=S(30))
        for txt,val in [("Неделя","week"),("Месяц","month"),("Всё","all")]:
            sel=(val=="week")
            btn=MDCard(size_hint_y=None, height=S(28), size_hint_x=None, width=S(70),
                       radius=[S(14)], elevation=0,
                       md_bg_color=C["accent"] if sel else C["surf2"])
            sp_lbl=MDLabel(text=txt, font_style="Caption",
                           halign="center", valign="middle",
                           theme_text_color="Custom",
                           text_color=(1,1,1,1) if sel else C["text"])
            sp_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            btn._lbl=sp_lbl; btn.add_widget(sp_lbl)
            def _sp(w,t,v=val):
                if w.collide_point(*t.pos):
                    self._stat_period=v
                    for kk,bb in self._sp_btns.items():
                        s2=(kk==v); bb.md_bg_color=C["accent"] if s2 else C["surf2"]
                        if hasattr(bb,"_lbl"): bb._lbl.text_color=(1,1,1,1) if s2 else C["text"]
                    self._refresh_stats(); return True
            btn.bind(on_touch_up=_sp); self._sp_btns[val]=btn; pr.add_widget(btn)
        hdr.add_widget(pr); pg.add_widget(hdr)

        # ── ScrollView ───────────────────────────────────────────────────────
        sv=ScrollView(size_hint=(1,1), do_scroll_x=False)
        self._stats_sv=sv
        inn=MDBoxLayout(orientation="vertical", size_hint_y=None,
                        spacing=S(12), padding=[S(14),S(12),S(14),S(80)])
        inn.bind(minimum_height=inn.setter("height"))
        self._stats_inn=inn
        sv.add_widget(inn)

        RAD = [S(18)] if is_fem else [S(12)]

        # ── Мотивация ────────────────────────────────────────────────────────
        MOT_H = S(76) if is_fem else S(110)
        mot_box=MDBoxLayout(orientation="vertical", size_hint_y=None, height=MOT_H,
                             spacing=S(4), padding=[S(16),S(10)])
        with mot_box.canvas.before:
            from kivy.graphics import Color as KColor, RoundedRectangle as KRR
            KColor(*C["surf"])
            mot_box._bg_rect=KRR(pos=mot_box.pos, size=mot_box.size, radius=RAD)
        mot_box.bind(pos=lambda w,v: setattr(w._bg_rect,'pos',v),
                     size=lambda w,v: setattr(w._bg_rect,'size',v))
        if is_fem:
            _init_mot = _pick_motivation(True, 0, 0, 0)
            self._motiv_lbl=EmojiLabel(text=_init_mot,
                                       font_style="Subtitle2", bold=True,
                                       theme_text_color="Primary",
                                       size_hint_y=None, height=S(28),
                                       halign="left", valign="middle")
            self._motiv_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            self._motiv_sub=MDLabel(text="Загрузка...", font_style="Caption",
                                    theme_text_color="Secondary",
                                    size_hint_y=None, height=S(20),
                                    halign="left", valign="middle")
            self._motiv_sub.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            mot_box.add_widget(self._motiv_lbl); mot_box.add_widget(self._motiv_sub)
        else:
            self._motiv_lbl=MDLabel(text="ДИСЦИПЛИНА СЕГОДНЯ —",
                                    font_style="H6", bold=True,
                                    theme_text_color="Primary",
                                    size_hint_y=None, height=S(30),
                                    halign="left", valign="middle")
            self._motiv_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            mot_box.add_widget(self._motiv_lbl)
            res_lbl=MDLabel(text="РЕЗУЛЬТАТ ЗАВТРА", font_style="H6", bold=True,
                            theme_text_color="Custom", text_color=C["accent"],
                            size_hint_y=None, height=S(30), halign="left", valign="middle")
            res_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            mot_box.add_widget(res_lbl)
            _init_mot_m = _pick_motivation(False, 0, 0, 0)
            self._motiv_sub=MDLabel(text=_init_mot_m, font_style="Caption",
                                    theme_text_color="Secondary",
                                    size_hint_y=None, height=S(20),
                                    halign="left", valign="middle")
            self._motiv_sub.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            mot_box.add_widget(self._motiv_sub)
        inn.add_widget(mot_box)

        # ── Статистика: цифры + столбики по дням (без кольца) ───────────────
        # padding_v=28 + stats_row=60 + lbl=20 + spacing=8*2 + bars=70 = 194
        STAT_CARD_H = S(28)+S(60)+S(8)+S(20)+S(8)+S(70)
        ring_box=MDBoxLayout(orientation="vertical", size_hint_y=None,
                             height=STAT_CARD_H, spacing=S(8),
                             padding=[S(16),S(14)])
        with ring_box.canvas.before:
            KColor(*C["surf"])
            ring_box._bg_rect=KRR(pos=ring_box.pos, size=ring_box.size, radius=RAD)
        ring_box.bind(pos=lambda w,v: setattr(w._bg_rect,'pos',v),
                      size=lambda w,v: setattr(w._bg_rect,'size',v))

        # Строка с цифрами (без кольца — занимает всю ширину)
        stats_row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                              height=S(60), spacing=S(16))
        self._sd_lbl=MDLabel(text="0", font_style="H4", bold=True,
                              theme_text_color="Custom", text_color=C["accent"],
                              size_hint_y=None, height=S(60),
                              halign="left", valign="middle")
        self._sd_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        self._sf_lbl=MDLabel(text="выполнено из 0", font_style="Caption",
                              theme_text_color="Secondary", size_hint_y=None, height=S(60),
                              halign="left", valign="middle")
        self._sf_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        self._sp_badge=MDLabel(text="0%", font_style="H5", bold=True,
                                theme_text_color="Custom", text_color=C["accent"],
                                size_hint_x=None, width=S(60), size_hint_y=None, height=S(60),
                                halign="right", valign="middle")
        self._sp_badge.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        # Заглушки для совместимости с _refresh_stats
        self._ring_pct_lbl=self._sp_badge
        stats_row.add_widget(self._sd_lbl)
        stats_row.add_widget(self._sf_lbl)
        stats_row.add_widget(self._sp_badge)
        ring_box.add_widget(stats_row)

        prod_lbl=MDLabel(text="Продуктивность по дням", font_style="Caption",
                         theme_text_color="Secondary", size_hint_y=None, height=S(20),
                         halign="left", valign="middle")
        prod_lbl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        ring_box.add_widget(prod_lbl)

        self._bars_box=MDBoxLayout(orientation="horizontal", spacing=S(5),
                                    size_hint_y=None, height=S(70))
        ring_box.add_widget(self._bars_box)
        inn.add_widget(ring_box)

        # ── Мини-карточки ────────────────────────────────────────────────────
        mini_r=MDBoxLayout(orientation="horizontal", spacing=S(12),
                            size_hint_y=None, height=S(96))
        def _mini(ico_txt, title, sub, attr):
            box=MDBoxLayout(orientation="vertical", spacing=S(4), padding=[S(14),S(10)])
            with box.canvas.before:
                KColor(*C["surf"])
                box._bg=KRR(pos=box.pos, size=box.size,
                             radius=[S(14)] if is_fem else [S(10)])
            box.bind(pos=lambda w,v: setattr(w._bg,'pos',v),
                     size=lambda w,v: setattr(w._bg,'size',v))
            ico_row = MDBoxLayout(orientation="horizontal",
                                  size_hint_y=None, height=S(32))
            # Напрямую через get_emoji_png чтобы гарантировать отображение
            em_path = get_emoji_png(ico_txt.strip())
            if em_path:
                ico = KivyImage(source=em_path, size_hint=(None,None),
                                size=(S(28),S(28)), allow_stretch=True, keep_ratio=True)
            else:
                ico = MDLabel(text=ico_txt, font_style="H6", halign="center",
                              valign="middle", size_hint_x=None, width=S(28),
                              size_hint_y=None, height=S(28),
                              theme_text_color="Primary")
                ico.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            ico_row.add_widget(ico)
            ico_row.add_widget(Widget())
            box.add_widget(ico_row)
            t_l=MDLabel(text=title, font_style="Caption",
                        theme_text_color="Secondary", size_hint_y=None, height=S(18),
                        halign="left", valign="middle")
            t_l.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            box.add_widget(t_l)
            val_l=MDLabel(text="0", font_style="H5", bold=True,
                          theme_text_color="Primary", size_hint_y=None, height=S(30),
                          halign="left", valign="middle")
            val_l.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            setattr(self, attr, val_l); box.add_widget(val_l)
            return box
        mini_r.add_widget(_mini("\U0001f525","Серия","_s_streak","_s_streak"))
        mini_r.add_widget(_mini("\U0001f4cc","Всего задач","_s_total","_s_total"))
        inn.add_widget(mini_r)

        # ── Цель на неделю ───────────────────────────────────────────────────
        gc_box=MDBoxLayout(orientation="vertical", size_hint_y=None, height=S(96),
                           spacing=S(6), padding=[S(16),S(12)])
        with gc_box.canvas.before:
            KColor(*C["surf"])
            gc_box._bg_rect=KRR(pos=gc_box.pos, size=gc_box.size, radius=RAD)
        gc_box.bind(pos=lambda w,v: setattr(w._bg_rect,'pos',v),
                    size=lambda w,v: setattr(w._bg_rect,'size',v))
        gh=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(24))
        gl=MDLabel(text="ЦЕЛЬ НА НЕДЕЛЮ", font_style="Caption",
                   theme_text_color="Custom", text_color=C["text2"],
                   halign="left", valign="middle")
        gl.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        gh.add_widget(gl); gh.add_widget(Widget())
        self._goal_pct_lbl=MDLabel(text=f"{self.weekly_goal}%", font_style="Caption",
                                    theme_text_color="Custom", text_color=C["accent"],
                                    size_hint_x=None, width=S(36), halign="right")
        gh.add_widget(self._goal_pct_lbl)
        minus_b=MDIconButton(icon="minus", size_hint_x=None, width=S(30),
                             theme_text_color="Custom", text_color=C["text2"])
        plus_b=MDIconButton(icon="plus", size_hint_x=None, width=S(30),
                            theme_text_color="Custom", text_color=C["text2"])
        def _chg_goal(delta):
            self.weekly_goal=max(10,min(100,self.weekly_goal+delta))
            if hasattr(self,"_goal_pct_lbl"): self._goal_pct_lbl.text=f"{self.weekly_goal}%"
            self._refresh_stats()
        minus_b.bind(on_release=lambda *_: _chg_goal(-5))
        plus_b.bind(on_release=lambda *_: _chg_goal(5))
        gh.add_widget(minus_b); gh.add_widget(plus_b)
        gc_box.add_widget(gh)
        sub_lbl=MDLabel(text=f"Выполнить {self.weekly_goal}% задач", font_style="Caption",
                        theme_text_color="Secondary", size_hint_y=None, height=S(16))
        gc_box.add_widget(sub_lbl)
        self._goal_prog=Widget(size_hint_y=None, height=S(10))
        self._goal_fill=0.0
        def _dgp(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(*C["surf2"]); RoundedRectangle(pos=(w.x,w.y),size=(w.width,w.height),radius=[S(5)])
                if self._goal_fill>0:
                    fill=min(1.0,self._goal_fill/(self.weekly_goal/100))
                    Color(*C["accent"]); RoundedRectangle(pos=(w.x,w.y),size=(max(w.width*fill,S(10)),w.height),radius=[S(5)])
        self._goal_prog.bind(pos=_dgp,size=_dgp)
        self._draw_goal=_dgp; gc_box.add_widget(self._goal_prog)
        inn.add_widget(gc_box)

        # ── Трекер настроения (оба пола) ─────────────────────────────────────
        mood_box=MDBoxLayout(orientation="vertical", size_hint_y=None, height=S(170),
                             spacing=S(6), padding=[S(16),S(12)])
        with mood_box.canvas.before:
            KColor(*C["surf"])
            mood_box._bg_rect=KRR(pos=mood_box.pos, size=mood_box.size, radius=[S(14)])
        mood_box.bind(pos=lambda w,v: setattr(w._bg_rect,'pos',v),
                      size=lambda w,v: setattr(w._bg_rect,'size',v))
        mood_title = "Как твоё настроение сегодня?" if is_fem else "Настроение сегодня"
        mood_box.add_widget(MDLabel(text=mood_title,
                                    font_style="Subtitle2", bold=True,
                                    theme_text_color="Primary",
                                    size_hint_y=None, height=S(26)))
        # Строка emoji-кнопок — используем GridLayout чтобы влезали все
        n_faces = len(MOOD_FACES)
        mood_r = MDBoxLayout(orientation="horizontal",
                             size_hint_y=None, height=S(52), spacing=S(4))
        today_s=date.today().strftime("%d.%m.%Y")
        cur_mood=self.mood_history.get(today_s,0)
        self._mood_btns=[]
        for i, face in enumerate(MOOD_FACES):
            # Каждую кнопку делаем как MDCard с Image внутри
            btn_card = MDCard(
                size_hint=(1, None), height=S(48),
                radius=[S(10)], elevation=0,
                md_bg_color=C["accent"] if i+1==cur_mood else C["surf2"])
            face_img = EmojiLabel(text=face, height=S(36),
                                  size_hint_y=None)
            # Центрируем img в карточке
            inner = MDBoxLayout(orientation="horizontal",
                                padding=[S(4),S(4)],
                                size_hint=(1,1))
            inner.add_widget(face_img)
            btn_card.add_widget(inner)
            btn_card._mv = i+1
            btn_card._face_img = face_img
            def _on_mood_touch(w, t, v=i+1, card=btn_card):
                if w.collide_point(*t.pos):
                    self._pick_mood_stat(v)
            btn_card.bind(on_touch_up=_on_mood_touch)
            self._mood_btns.append(btn_card)
            mood_r.add_widget(btn_card)
        mood_box.add_widget(mood_r)
        # История настроения — последние 7 дней
        hist_r=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                           height=S(32), spacing=S(4))
        for i in range(6,-1,-1):
            d2=date.today()-timedelta(days=i)
            mv=self.mood_history.get(d2.strftime("%d.%m.%Y"),0)
            col=MDBoxLayout(orientation="vertical", spacing=S(2))
            face_lbl=EmojiLabel(text=MOOD_FACES[mv-1] if mv else "·",
                                font_style="Caption", halign="center",
                                height=S(28), size_hint_y=None)
            col.add_widget(face_lbl); hist_r.add_widget(col)
        mood_box.add_widget(hist_r)
        inn.add_widget(mood_box)

        # ── Тепловая карта — последние 5 недель ─────────────────────────
        heat_box = MDBoxLayout(orientation="vertical", size_hint_y=None,
                               spacing=S(6), padding=[S(16), S(12)])
        heat_box.bind(minimum_height=heat_box.setter("height"))
        from kivy.graphics import Color as _HBGC, RoundedRectangle as _HBGRR
        with heat_box.canvas.before:
            _HBGC(*C["surf"])
            heat_bg = _HBGRR(pos=heat_box.pos, size=heat_box.size, radius=[S(8)])
        heat_box.bind(pos=lambda w,v: setattr(heat_bg,"pos",v),
                      size=lambda w,v: setattr(heat_bg,"size",v))
        ht_lbl = MDLabel(text="АКТИВНОСТЬ (5 недель)", font_style="Caption",
                         theme_text_color="Custom", text_color=C["text2"],
                         size_hint_y=None, height=S(18), halign="left", valign="middle")
        ht_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        heat_box.add_widget(ht_lbl)
        # Дни недели заголовок
        days_hdr = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(14),
                               spacing=S(3), padding=[S(22), 0, 0, 0])
        for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]:
            dl = MDLabel(text=d, font_style="Caption", theme_text_color="Secondary",
                         halign="center", size_hint_x=1, size_hint_y=None, height=S(14))
            dl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            days_hdr.add_widget(dl)
        heat_box.add_widget(days_hdr)
        # Сетка — 5 строк (недели) × 7 колонок (дни)
        from datetime import date as _date, timedelta as _td
        today_h = _date.today()
        # Выровняем к понедельнику
        start_day = today_h - _td(days=today_h.weekday() + 7*4)
        tasks_done_dates = set()
        tasks_all_dates  = {}
        for t in self.tasks.values():
            ds = t.get("date","")
            if ds:
                tasks_all_dates[ds] = tasks_all_dates.get(ds, 0) + 1
                if t.get("done"):
                    tasks_done_dates.add(ds)
        for week in range(5):
            week_row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                    height=S(22), spacing=S(3))
            # Номер недели
            wn = (start_day + _td(days=week*7))
            wlbl = MDLabel(text=f"W{wn.isocalendar()[1]}", font_style="Caption",
                           theme_text_color="Custom", text_color=C["text2"],
                           size_hint_x=None, width=S(20), halign="right")
            wlbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            week_row.add_widget(wlbl)
            for day in range(7):
                d = start_day + _td(days=week*7+day)
                ds = d.strftime("%d.%m.%Y")
                total_d = tasks_all_dates.get(ds, 0)
                done_d  = 1 if ds in tasks_done_dates else 0
                is_today = (d == today_h)
                is_future = (d > today_h)
                # Интенсивность цвета по количеству выполненных задач
                if is_future:
                    bg = C["surf2"]
                elif total_d == 0:
                    bg = C["surf2"]
                elif done_d >= total_d and total_d > 0:
                    bg = C["accent"]
                elif total_d > 0:
                    # частично выполнено
                    ratio = done_d / total_d if total_d else 0
                    r,g,b,a = C["accent"]
                    bg = (r,g,b, 0.3 + 0.7*ratio)
                else:
                    bg = C["surf2"]
                cell = Widget(size_hint_x=1, size_hint_y=None, height=S(18))
                from kivy.graphics import Color as _KC, RoundedRectangle as _HKRR
                with cell.canvas:
                    _KC(*bg)
                    _cell_rect = _HKRR(pos=cell.pos, size=cell.size, radius=[S(3)])
                def _upd_cell(w, *_, r=_cell_rect):
                    r.pos = w.pos; r.size = w.size
                cell.bind(pos=_upd_cell, size=_upd_cell)
                week_row.add_widget(cell)
            heat_box.add_widget(week_row)
        # Легенда
        legend_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(16),
                                  spacing=S(6), padding=[S(22), 0, 0, 0])
        for label, color in [("Нет", C["surf2"]), ("Частично", (*C["accent"][:3], 0.4)),
                              ("Все", C["accent"])]:
            dot = Widget(size_hint_x=None, width=S(12), size_hint_y=None, height=S(12))
            from kivy.graphics import Color as _KC2, RoundedRectangle as _KRR2
            with dot.canvas:
                _KC2(*color)
                _dot_rect = _KRR2(pos=dot.pos, size=dot.size, radius=[S(3)])
            def _upd_dot(w, *_, r=_dot_rect):
                r.pos = w.pos; r.size = w.size
            dot.bind(pos=_upd_dot, size=_upd_dot)
            leg_lbl = MDLabel(text=label, font_style="Caption",
                              theme_text_color="Secondary",
                              size_hint_x=None, width=S(55),
                              size_hint_y=None, height=S(14))
            leg_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            legend_row.add_widget(dot)
            legend_row.add_widget(leg_lbl)
        heat_box.add_widget(legend_row)
        inn.add_widget(heat_box)

        pg.add_widget(sv)
        return pg

    def _pick_mood_stat(self, v):
        self._save_mood(v)
        for b in getattr(self,"_mood_btns",[]):
            if hasattr(b,"_mv"):
                b.md_bg_color = C["accent"] if b._mv==v else C["surf2"]
        self._show_toast(f"Настроение: {MOOD_LABELS[v-1]}")

    def _refresh_stats(self):
        if not hasattr(self,"_sd_lbl"): return
        is_fem=self._is_fem()
        period=getattr(self,"_stat_period","week")
        today=date.today()
        all_t=list(self.tasks.values())
        today_s=today.strftime("%d.%m.%Y")
        if period=="week":    from_date=today-timedelta(days=today.weekday())
        elif period=="month": from_date=today.replace(day=1)
        else:                 from_date=date(2000,1,1)
        from_s=from_date.strftime("%d.%m.%Y")
        pt=[t for t in all_t if from_s<=t.get("date","")<=today_s]
        done=sum(1 for t in pt if t.get("done"))
        total=len(pt); pct=done/total if total else 0.0
        self._sd_lbl.text=str(done)
        self._sf_lbl.text=f"выполнено из {total}"
        self._sp_badge.text=f"{int(pct*100)}%"
        self._ring_pct=pct
        if hasattr(self,"_ring_pct_lbl"): self._ring_pct_lbl.text=f"{int(pct*100)}%"
        # Серия
        streak=0; d=today
        while True:
            ds=d.strftime("%d.%m.%Y")
            if any(t.get("done") and t.get("date","")==ds for t in all_t):
                streak+=1; d-=timedelta(days=1)
            else: break
        self._s_streak.text=str(streak)
        mon_s=today.replace(day=1).strftime("%d.%m.%Y")
        self._s_total.text=str(sum(1 for t in all_t
                                    if mon_s<=t.get("date","")<=today_s))
        # Мотивация — умный выбор на основе прогресса и настроения
        done_today=sum(1 for t in all_t if t.get("done") and t.get("date","")==today_s)
        total_today=sum(1 for t in all_t if t.get("date","")==today_s)
        mood_val=self.mood_history.get(today_s, 0)
        mot_msg = _pick_motivation(is_fem, done_today, total_today, mood_val)
        if hasattr(self,"_motiv_lbl"):
            if is_fem:
                update_emoji_label(self._motiv_lbl, mot_msg)
            # мужской — _motiv_lbl статичный ("ДИСЦИПЛИНА СЕГОДНЯ"), не трогаем
        if hasattr(self,"_motiv_sub"):
            if is_fem:
                sub_txt = f"Уже выполнено {done_today} из {total_today} дел"
                self._motiv_sub.text = sub_txt
            else:
                self._motiv_sub.text = mot_msg
        if hasattr(self,"_goal_pct_lbl"):
            self._goal_fill=pct; self._draw_goal(self._goal_prog)
        # Столбики
        self._bars_box.clear_widgets()
        DAY=["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
        data=[]
        for i in range(6,-1,-1):
            d2=today-timedelta(days=i); ds2=d2.strftime("%d.%m.%Y")
            cnt=sum(1 for t in all_t if t.get("done") and t.get("date","")==ds2)
            data.append((DAY[d2.weekday()],cnt,i==0))
        max_cnt=max((x[1] for x in data),default=1) or 1
        BAR_H=S(48)
        for day_n,cnt,is_td in data:
            col=MDBoxLayout(orientation="vertical", spacing=S(1), size_hint_x=1)
            col.add_widget(MDLabel(text=str(cnt) if cnt else "",
                                   font_style="Caption", halign="center",
                                   theme_text_color="Custom",
                                   text_color=C["accent"] if is_td else C["text2"],
                                   size_hint_y=None, height=S(14)))
            bh=max(S(4),BAR_H*cnt/max_cnt) if cnt else S(4)
            bb=MDBoxLayout(orientation="vertical", size_hint_y=None, height=BAR_H,
                            padding=[0,BAR_H-bh,0,0])
            bw=Widget(size_hint_y=None, height=bh)
            bc=C["accent"] if is_td else C["acc_s"]
            def _db(w,*_,c=bc):
                w.canvas.clear()
                with w.canvas:
                    Color(*c)
                    RoundedRectangle(pos=(w.x,w.y), size=(w.width,w.height),
                                     radius=[S(4),S(4),0,0])
            bw.bind(pos=_db, size=_db); bb.add_widget(bw); col.add_widget(bb)
            _lbl_tmp=MDLabel(text=day_n, font_style="Caption", halign="center",
                                   theme_text_color="Custom",
                                   text_color=C["accent"] if is_td else C["text2"],
                                   size_hint_y=None, height=S(16))
            col.add_widget(_lbl_tmp)
            _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            self._bars_box.add_widget(col)

    # ════════════════════════════════════════════════════════════════════════
    #  СТРАНИЦА: НАСТРОЙКИ
    # ════════════════════════════════════════════════════════════════════════
    def _mk_settings_page(self):
        is_fem=self._is_fem()
        pg=MDBoxLayout(orientation="vertical")
        hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(54), md_bg_color=C["surf"], padding=[S(16),S(10)])
        _lbl_tmp=MDLabel(text="Настройки", font_style="H6",
                                bold=True, theme_text_color="Primary",
                      halign="left", valign="middle")
        hdr.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        pg.add_widget(hdr)
        sv=ScrollView()
        inn=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(10), padding=[S(14),S(12),S(14),S(20)])
        sv.add_widget(inn)

        def _sec(txt):
            return MDLabel(text=txt, font_style="Caption",
                           theme_text_color="Custom", text_color=C["text2"],
                           size_hint_y=None, height=S(26))

        # Профиль
        p_card=MDCard(size_hint_y=None, height=S(72),
                      radius=[S(14)] if is_fem else [S(10)],
                      elevation=1 if is_fem else 0, md_bg_color=C["surf"], padding=[S(12),S(10)])
        pr=MDBoxLayout(orientation="horizontal", spacing=S(12))
        av=MDCard(size_hint=(None,None), size=(S(56),S(56)), radius=[S(28)],
                  elevation=0, md_bg_color=C["accent"])
        av_inner=FloatLayout(size_hint=(1,1))
        em_sz=S(40)
        _em_path=get_emoji_png(self.user_emoji.strip()) if self.user_emoji else None
        if _em_path:
            self._s_emoji_lbl=KivyImage(source=_em_path, size_hint=(None,None),
                                         size=(em_sz,em_sz), allow_stretch=True,
                                         keep_ratio=True,
                                         pos_hint={"center_x":0.5,"center_y":0.5})
        else:
            self._s_emoji_lbl=MDLabel(text=self.user_emoji or "😊", font_style="H5",
                                       halign="center", valign="middle",
                                       theme_text_color="Custom", text_color=(1,1,1,1),
                                       size_hint=(None,None), size=(em_sz,em_sz),
                                       pos_hint={"center_x":0.5,"center_y":0.5})
            self._s_emoji_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        av_inner.add_widget(self._s_emoji_lbl)
        av.add_widget(av_inner)
        pr.add_widget(av)
        pn=MDBoxLayout(orientation="vertical", spacing=S(2))
        self._s_name=MDLabel(text=self.user_name or "Имя", font_style="Subtitle1",
                              bold=True, theme_text_color="Primary",
                              size_hint_y=None, height=S(28))
        pn.add_widget(self._s_name)
        _lbl_tmp=MDLabel(text="Нажмите чтобы изменить", font_style="Caption",
                               theme_text_color="Secondary", size_hint_y=None, height=S(18),
                      halign="left", valign="middle")
        pn.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        pr.add_widget(pn); p_card.add_widget(pr)
        p_card.bind(on_release=lambda *_: self._edit_profile()); inn.add_widget(p_card)

        # Голосовой помощник — статус
        inn.add_widget(_sec("ТЕМА ПРИЛОЖЕНИЯ"))
        g_row=MDBoxLayout(orientation="horizontal", spacing=S(10),
                           size_hint_y=None, height=S(46))
        for glabel,gtheme,gactive in [("Женский","Роза",is_fem),
                                       ("Мужской","Бронза",not is_fem)]:
            gc=MDCard(size_hint_x=0.5, size_hint_y=None, height=S(44),
                      radius=[S(22)], elevation=0,
                      md_bg_color=C["accent"] if gactive else C["surf2"],
                      padding=[S(4),0])
            gl=MDLabel(text=glabel, font_style="Body2", bold=True,
                        halign="center", valign="middle", theme_text_color="Custom",
                        text_color=(1,1,1,1) if gactive else C["text2"])
            gl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            gc.add_widget(gl)
            gc.bind(on_release=lambda _,t=gtheme: self._apply_theme(t))
            g_row.add_widget(gc)
        inn.add_widget(g_row)
        _lbl_tmp=MDLabel(text="Выберите тему:", font_style="Caption",
                               theme_text_color="Custom", text_color=C["text2"],
                               size_hint_y=None, height=S(22),
                      halign="left", valign="middle")
        inn.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        themes_sv=ScrollView(size_hint_y=None, height=S(220), do_scroll_x=False)
        tgrid=GridLayout(cols=3, size_hint_y=None, size_hint_x=1,
                         spacing=S(8), padding=[0,S(4)])
        tgrid.bind(minimum_height=tgrid.setter("height"))
        for tn in THEMES: tgrid.add_widget(self._theme_card(tn))
        themes_sv.add_widget(tgrid); inn.add_widget(themes_sv)

        # Категории
        inn.add_widget(_sec("КАТЕГОРИИ"))
        cat_c=MDCard(size_hint_y=None, radius=[S(14)], elevation=0,
                     md_bg_color=C["surf"], padding=[S(4),S(4)])
        cat_c.bind(minimum_height=cat_c.setter("height"))
        cat_i=MDBoxLayout(orientation="vertical", adaptive_height=True)
        self._cats_box=MDBoxLayout(orientation="vertical", adaptive_height=True)
        self._rebuild_cats_list(); cat_i.add_widget(self._cats_box)
        add_r=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                          height=S(50), padding=[S(12),0])
        add_r.add_widget(MDIconButton(icon="plus", size_hint_x=None, width=S(34),
                                       theme_text_color="Custom", text_color=C["accent"]))
        _lbl_tmp=MDLabel(text="Добавить категорию", font_style="Body1",
                                  theme_text_color="Custom", text_color=C["accent"],
                      halign="left", valign="middle")
        add_r.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        def _tac(w,t):
            if add_r.collide_point(*t.pos): self._add_category(); return True
        add_r.bind(on_touch_up=_tac)
        cat_i.add_widget(add_r); cat_c.add_widget(cat_i); inn.add_widget(cat_c)

        # Уведомления
        inn.add_widget(_sec("УВЕДОМЛЕНИЯ"))
        notif_c=MDCard(size_hint_y=None, radius=[S(14)], elevation=0,
                       md_bg_color=C["surf"], padding=[S(4),S(4)])
        notif_c.bind(minimum_height=notif_c.setter("height"))
        ni=MDBoxLayout(orientation="vertical", adaptive_height=True)
        for ntxt,nstate in [("Напоминания",True),("Звук",True),("Вибрация",False)]:
            ni.add_widget(self._notif_row(ntxt, nstate))
        plyer_lbl=MDLabel(
            text="[OK] plyer активен" if PLYER_OK else "[!] pip install plyer",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=S(20), padding=[S(16),0])
        ni.add_widget(plyer_lbl); notif_c.add_widget(ni); inn.add_widget(notif_c)

        # Данные
        inn.add_widget(_sec("ДАННЫЕ"))
        data_c=MDCard(size_hint_y=None, radius=[S(14)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(4),S(4)])
        data_c.bind(minimum_height=data_c.setter("height"))
        di=MDBoxLayout(orientation="vertical", adaptive_height=True)
        for dtxt,dico,dcb in [
            ("Резервная копия","content-save-outline",self._backup_restore),
            ("Импорт из текста","clipboard-text-outline",self.import_from_text),
            ("О приложении","information-outline",self._show_about)]:
            di.add_widget(self._sett_row(dico,dtxt,dcb))
        data_c.add_widget(di); inn.add_widget(data_c)
        self._exp_lbl=MDLabel(text="", font_style="Caption",
                               theme_text_color="Secondary", size_hint_y=None, height=S(20))
        inn.add_widget(self._exp_lbl)
        rb=MDRaisedButton(text="Сбросить и начать заново",
                           size_hint_y=None, height=S(46),
                           md_bg_color=C["surf2"], elevation=0)
        rb.bind(on_release=self._reset); inn.add_widget(rb)
        pg.add_widget(sv)
        return pg

    def _notif_row(self, label, state):
        row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(52), padding=[S(16),0,S(16),0])
        _lbl_tmp=MDLabel(text=label, font_style="Body1", theme_text_color="Primary",
                      halign="left", valign="middle")
        row.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        tog_w=FloatLayout(size_hint=(None,None), size=(S(48),S(28)))
        tog_bg=Widget(size_hint=(1,1)); _st=[state]
        def _redraw_tog(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(*(C["accent"] if _st[0] else C["surf2"]))
                RoundedRectangle(pos=w.pos, size=w.size, radius=[S(14)])
        tog_bg.bind(pos=_redraw_tog, size=_redraw_tog)
        dot=Widget(size_hint=(None,None), size=(S(22),S(22)))
        def _redraw_dot(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(1,1,1,1); Ellipse(pos=w.pos, size=w.size)
        dot.bind(pos=_redraw_dot, size=_redraw_dot)
        def _pos_dot(*_):
            if _st[0]: dot.pos=(tog_w.x+tog_w.width-S(24), tog_w.y+S(3))
            else:      dot.pos=(tog_w.x+S(2), tog_w.y+S(3))
        tog_w.bind(pos=_pos_dot, size=_pos_dot)
        def _toggle(w,t):
            if tog_w.collide_point(*t.pos):
                _st[0]=not _st[0]; _redraw_tog(tog_bg); _pos_dot(); return True
        tog_w.bind(on_touch_up=_toggle)
        tog_w.add_widget(tog_bg); tog_w.add_widget(dot)
        row.add_widget(tog_w)
        return row

    def _sett_row(self, icon, label, on_tap):
        row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(52), spacing=S(8), padding=[S(10),0])
        row.add_widget(MDIconButton(icon=icon, size_hint_x=None, width=S(34),
                                    theme_text_color="Custom", text_color=C["text2"]))
        _lbl_tmp=MDLabel(text=label, font_style="Body1", theme_text_color="Primary",
                      halign="left", valign="middle")
        row.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        row.add_widget(MDIconButton(icon="chevron-right", size_hint_x=None, width=S(26),
                                    theme_text_color="Custom", text_color=C["text2"]))
        def _tap(w,t):
            if row.collide_point(*t.pos): on_tap(); return True
        row.bind(on_touch_up=_tap)
        return row

    def _sett_row_value(self, icon, label, value, on_tap):
        row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(52), spacing=S(8), padding=[S(10),0])
        row.add_widget(MDIconButton(icon=icon, size_hint_x=None, width=S(36),
                                    theme_text_color="Custom", text_color=C["text2"]))
        _lbl_tmp=MDLabel(text=label, font_style="Body1", theme_text_color="Primary",
                      halign="left", valign="middle")
        row.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        _lbl_tmp=MDLabel(text=value, font_style="Body2",
                               theme_text_color="Custom", text_color=C["text2"],
                               halign="right")
        row.add_widget(_lbl_tmp)
        _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        row.add_widget(MDIconButton(icon="chevron-right", size_hint_x=None, width=S(28),
                                    theme_text_color="Custom", text_color=C["text2"]))
        def _tap(w,t):
            if row.collide_point(*t.pos): on_tap(); return True
        row.bind(on_touch_up=_tap)
        sep=Widget(size_hint_y=None, height=S(1))
        def _dr(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(*C["div"]); Rectangle(pos=(w.x+S(46),w.y), size=(w.width-S(46),S(1)))
        sep.bind(pos=_dr, size=_dr)
        wrap=MDBoxLayout(orientation="vertical", adaptive_height=True)
        wrap.add_widget(row); wrap.add_widget(sep)
        return wrap

    def _rebuild_cats_list(self):
        if not hasattr(self,"_cats_box"): return
        self._cats_box.clear_widgets()
        for cat in self.categories:
            cnt=sum(1 for t in self.tasks.values() if t.get("category")==cat)
            em=CAT_EMOJI.get(cat,"")
            ico=CAT_ICONS.get(cat,"dots-horizontal-circle-outline")
            row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                            height=S(52), padding=[S(8),0], spacing=S(8))
            em_path=get_emoji_png(em.strip()) if em else None
            if em_path:
                em_w=KivyImage(source=em_path, size_hint=(None,None),
                                size=(S(28),S(28)), allow_stretch=True, keep_ratio=True)
                row.add_widget(em_w)
            else:
                row.add_widget(MDIconButton(icon=ico, size_hint_x=None, width=S(34),
                                             theme_text_color="Custom", text_color=C["accent"]))
            name_lbl=MDLabel(text=cat, font_style="Body1", theme_text_color="Primary",
                             halign="left", valign="middle")
            name_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            row.add_widget(name_lbl)
            cnt_lbl=MDLabel(text=str(cnt), font_style="Body2",
                            theme_text_color="Secondary",
                            halign="right", size_hint_x=None, width=S(36))
            cnt_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            row.add_widget(cnt_lbl)
            row.add_widget(MDIconButton(icon="chevron-right", size_hint_x=None, width=S(26),
                                         theme_text_color="Custom", text_color=C["text2"]))
            def _row_tap(w,t,c=cat):
                if w.collide_point(*t.pos): self._edit_cat_emoji(c); return True
            row.bind(on_touch_up=_row_tap)
            self._cats_box.add_widget(row)

    def _refresh_cat_bar(self):
        """Перестраивает cat_bar после изменения эмодзи категорий."""
        if hasattr(self,"cat_bar"):
            self.cat_bar.clear_widgets(); self._cat_btns={}
            b_all=self._mk_cat_btn("Все"); self._cat_btns["Все"]=b_all
            self.cat_bar.add_widget(b_all)
            for c in self.categories:
                b=self._mk_cat_btn(c); self._cat_btns[c]=b; self.cat_bar.add_widget(b)
            self._update_cat_colors()

    def _edit_cat_emoji(self, cat):
        """Диалог выбора эмодзи для существующей категории."""
        CAT_EMOJI_OPTS = [
            "🔥","⭐","🎯","💡","🏠","💼","💪","🎵","📚","🌿",
            "⚡","🌟","🚀","🎉","🏆","🌈","🦋","🔑","🎁","🧘",
            "🚴","🏊","⚽","🔖","📌","❤️","💰","✨","💥","🏋️",
            "📅","🌙","🌊","🌸","🌺","💛","💙","💜","🐶","🐱",
        ]
        cur_em=CAT_EMOJI.get(cat,"")
        sel_emoji=[cur_em]
        from kivy.uix.modalview import ModalView
        from kivy.uix.gridlayout import GridLayout as GL
        mv=ModalView(background_color=(0,0,0,0.5), auto_dismiss=False, size_hint=(0.9,None))
        card=MDCard(orientation="vertical", size_hint_y=None, height=S(400),
                    radius=[S(16)], elevation=6, md_bg_color=C["surf"],
                    padding=[S(14),S(12)])
        title_lbl=MDLabel(text=f"Эмодзи для «{cat}»", font_style="H6", bold=True,
                           theme_text_color="Primary", halign="center",
                           size_hint_y=None, height=S(36))
        title_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(title_lbl)
        # Preview строка: картинка + текст
        preview_row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                height=S(36), spacing=S(8))
        preview_img_box=MDBoxLayout(size_hint=(None,None), size=(S(32),S(32)))
        _ini_path=get_emoji_png(cur_em.strip()) if cur_em else None
        preview_img=KivyImage(source=_ini_path or "", size_hint=(1,1),
                              allow_stretch=True, keep_ratio=True,
                              opacity=1 if _ini_path else 0)
        preview_img_box.add_widget(preview_img)
        preview_row.add_widget(preview_img_box)
        preview_lbl=MDLabel(text="нет" if not cur_em else "выбрано",
                            font_style="Body2", theme_text_color="Secondary",
                            halign="left", valign="middle")
        preview_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        preview_row.add_widget(preview_lbl)
        card.add_widget(preview_row)
        # ScrollView чтобы сетка всегда влезала независимо от размера экрана
        em_sv=ScrollView(size_hint_y=None, height=S(220), do_scroll_x=False)
        grid=GL(cols=8, spacing=S(4), size_hint_y=None, size_hint_x=1,
                padding=[S(2),S(2)])
        grid.bind(minimum_height=grid.setter("height"))
        em_cards=[]
        def _pick(em):
            sel_emoji[0]=em
            em_path=get_emoji_png(em.strip())
            if em_path:
                preview_img.source=em_path; preview_img.opacity=1
            else:
                preview_img.opacity=0
            preview_lbl.text="выбрано"
            for ec in em_cards:
                ec.md_bg_color=C["accent"] if ec._em==em else C["surf2"]
        for em in CAT_EMOJI_OPTS:
            ec=MDCard(size_hint=(None,None), size=(S(38),S(38)),
                      radius=[S(8)], elevation=0,
                      md_bg_color=C["accent"] if em==cur_em else C["surf2"])
            ec._em=em
            em_path=get_emoji_png(em.strip())
            if em_path:
                img=KivyImage(source=em_path, size_hint=(1,1),
                              allow_stretch=True, keep_ratio=True)
                ec.add_widget(img)
            else:
                lbl=MDLabel(text=em, halign="center", valign="middle")
                lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
                ec.add_widget(lbl)
            ec.bind(on_release=lambda w,e=em: _pick(e))
            em_cards.append(ec)
            grid.add_widget(ec)
        em_sv.add_widget(grid)
        card.add_widget(em_sv)
        btn_row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                            height=S(44), spacing=S(6))
        def _cancel_em(*_): mv.dismiss()
        def _clear_em(*_):
            CAT_EMOJI.pop(cat,None)
            self._save_config()
            self._rebuild_cats_list(); self._refresh_cat_bar(); mv.dismiss()
        def _apply_em(*_):
            if sel_emoji[0]: CAT_EMOJI[cat]=sel_emoji[0]
            self._save_config()
            self._rebuild_cats_list(); self._refresh_cat_bar(); mv.dismiss()
        btn_row.add_widget(MDFlatButton(text="Отмена", on_release=_cancel_em))
        btn_row.add_widget(MDFlatButton(text="Убрать", on_release=_clear_em))
        btn_row.add_widget(Widget())
        btn_row.add_widget(MDRaisedButton(text="Сохранить",
                            md_bg_color=C["accent"], on_release=_apply_em))
        card.add_widget(btn_row)
        mv.add_widget(card); mv.open()

    def _theme_card(self, tn):
        td=THEMES[tn]; sel=(tn==self.theme_name)
        c=MDCard(size_hint_x=1, size_hint_y=None, height=S(90), radius=[S(12)],
                 elevation=3 if sel else 0,
                 md_bg_color=C["accent"] if sel else C["surf"],
                 padding=[S(8),S(8)])
        ci=MDBoxLayout(orientation="vertical", spacing=S(4))
        dots=MDBoxLayout(orientation="horizontal", spacing=S(4),
                         size_hint_y=None, height=S(22))
        for key in ("bg","accent","surf2"):
            dot=Widget(size_hint=(None,None), size=(S(18),S(18))); col_v=td[key]
            def _dd(w,*_,cv=col_v):
                w.canvas.clear()
                with w.canvas:
                    Color(*cv); RoundedRectangle(size=w.size, pos=w.pos, radius=[S(4)])
            dot.bind(pos=_dd, size=_dd); dots.add_widget(dot)
        dots.add_widget(Widget())
        ci.add_widget(dots)
        tc=(1,1,1,1) if sel else C["text"]
        name_lbl=MDLabel(text=tn, font_style="Caption", bold=sel,
                          theme_text_color="Custom", text_color=tc,
                          halign="left", valign="middle",
                          size_hint_y=None, height=S(20))
        name_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        ci.add_widget(name_lbl)
        kind="тёмная" if td.get("dark") else "светлая"
        tc2=(0.8,0.8,0.8,1) if sel else C["text2"]
        kind_lbl=MDLabel(text=kind, font_style="Caption",
                          theme_text_color="Custom", text_color=tc2,
                          halign="left", size_hint_y=None, height=S(16))
        kind_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        ci.add_widget(kind_lbl)
        if sel:
            check=MDLabel(text="✓ выбрана", font_style="Caption",
                           theme_text_color="Custom", text_color=(1,1,1,1),
                           halign="left", size_hint_y=None, height=S(14))
            check.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            ci.add_widget(check)
        c.add_widget(ci); c.bind(on_release=lambda _,t=tn: self._apply_theme(t))
        return c

    def _apply_theme(self, tn):
        td=THEMES.get(tn)
        if not td: return
        C.update(td); self.theme_name=tn
        self._apply_md_style(); self._save_config()
        Clock.schedule_once(self._rebuild, 0.1)

    def _set_gender(self, g):
        self._apply_theme("Бронза" if g=="male" else "Роза")

    def _add_category(self):
        from kivy.uix.gridlayout import GridLayout as GL
        CAT_EMOJI_OPTS = [
            "🔥","⭐","🎯","💡","🏠","💼","💪","🎵","📚","🌿",
            "⚡","🌟","🚀","🎉","🏆","🌈","🦋","🔑","🎁","🧘",
            "🚴","🏊","⚽","🔖","📌","❤️","💰","✨","💥","🏋️",
            "📅","🌙","🌊","🌸","🌺","💛","💙","💜","🐶","🐱",
        ]
        sel_emoji=[""]
        box=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(10), padding=[S(4)])
        nf=MDTextField(hint_text="Название категории", size_hint_y=None, height=S(52))
        box.add_widget(nf)
        # Preview строка
        em_prev_row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                height=S(36), spacing=S(8))
        em_prev_img_box=MDBoxLayout(size_hint=(None,None), size=(S(32),S(32)))
        em_prev_img=KivyImage(source="", size_hint=(1,1),
                              allow_stretch=True, keep_ratio=True, opacity=0)
        em_prev_img_box.add_widget(em_prev_img)
        em_prev_row.add_widget(em_prev_img_box)
        em_preview_lbl=MDLabel(text="Эмодзи: не выбран", font_style="Body2",
                                theme_text_color="Secondary", halign="left", valign="middle")
        em_preview_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        em_prev_row.add_widget(em_preview_lbl)
        box.add_widget(em_prev_row)
        em_sv=ScrollView(size_hint_y=None, height=S(180), do_scroll_x=False)
        grid=GL(cols=8, spacing=S(4), size_hint_y=None, size_hint_x=1,
                padding=[S(2),S(2)])
        grid.bind(minimum_height=grid.setter("height"))
        em_cards=[]
        def _pick_em(em):
            sel_emoji[0]=em
            em_path=get_emoji_png(em.strip())
            if em_path:
                em_prev_img.source=em_path; em_prev_img.opacity=1
            else:
                em_prev_img.opacity=0
            em_preview_lbl.text="выбрано"
            for ec in em_cards:
                ec.md_bg_color=C["accent"] if ec._em==em else C["surf2"]
        for em in CAT_EMOJI_OPTS:
            ec=MDCard(size_hint=(None,None), size=(S(42),S(42)),
                      radius=[S(8)], elevation=0, md_bg_color=C["surf2"])
            ec._em=em
            em_path=get_emoji_png(em.strip())
            if em_path:
                img=KivyImage(source=em_path, size_hint=(1,1),
                              allow_stretch=True, keep_ratio=True)
                ec.add_widget(img)
            else:
                lbl=MDLabel(text=em, halign="center", valign="middle")
                lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
                ec.add_widget(lbl)
            ec.bind(on_release=lambda w,e=em: _pick_em(e))
            em_cards.append(ec)
            grid.add_widget(ec)
        em_sv.add_widget(grid)
        box.add_widget(em_sv)
        dlg=MDDialog(title="Новая категория", type="custom", content_cls=box,
                     buttons=[
                         MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                         MDRaisedButton(text="Добавить", md_bg_color=C["accent"],
                                        on_release=lambda *_: self._do_add_cat(nf.text.strip(), dlg, sel_emoji[0]))])
        dlg.open()

    def _do_add_cat(self, name, dlg, emoji=""):
        if name and name not in self.categories:
            self.categories.append(name)
            if emoji: CAT_EMOJI[name]=emoji
            self._save_config()
            self._rebuild_cats_list()
            if hasattr(self,"cat_bar"):
                b=self._mk_cat_btn(name); self._cat_btns[name]=b
                self.cat_bar.add_widget(b,index=1); self._update_cat_colors()
        dlg.dismiss()

    def _edit_profile(self):
        from kivy.uix.gridlayout import GridLayout as _GL

        # Только эмодзи которые есть в PNG-базе, по группам
        EMOJI_GROUPS = {
            "😊": ["😊","😄","😁","😎","🤩","😍","🥰","😇","😌","🙂","😐","😔","😢","😭","😤","😡","🥳","🤗","😴","🤔","😏","🥺","😬","🤯","😺"],
            "💪": ["💪","🏃","🧘","🏋️","🚴","🏊","⚽","🎯","🔥","⚡","🌟","✨","🚀","💥","🎉","🏆","🔑","🎁","🎵","📚"],
            "🌿": ["🌸","🌺","🌻","🌹","🍀","🌿","🌊","🌈","☀️","🌙","⭐","❄️","🍁","🌴","🦋","🐾"],
            "❤️": ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","💖","💗","💓","💞","💝","💘","💕","🫀"],
            "🐱": ["😺","🐶","🐱","🐻","🐼","🦊","🐨","🦁","🐸","🐧","🦄","🐉","🦅","🦋","🐬"],
        }

        _selected = [self.user_emoji]
        _current_group = [list(EMOJI_GROUPS.keys())[0]]

        outer = MDBoxLayout(orientation="vertical", adaptive_height=True,
                            spacing=S(8), padding=[S(2),S(4)])

        # Поле имени
        nf = MDTextField(hint_text="Имя", text=self.user_name,
                         size_hint_y=None, height=S(52))
        outer.add_widget(nf)

        # Превью
        preview_row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                                  height=S(52), spacing=S(12))
        preview_card = MDCard(size_hint=(None,None), size=(S(48),S(48)),
                               radius=[S(24)], elevation=0, md_bg_color=C["surf2"])
        _ini_path = get_emoji_png(self.user_emoji.strip()) if self.user_emoji else None
        self._preview_emoji_img = KivyImage(
            source=_ini_path or "", size_hint=(1,1),
            allow_stretch=True, keep_ratio=True, opacity=1 if _ini_path else 0)
        preview_card.add_widget(self._preview_emoji_img)
        preview_row.add_widget(preview_card)
        _hint = MDLabel(text="Выберите эмодзи ниже",
                        font_style="Caption", theme_text_color="Secondary",
                        halign="left", valign="middle")
        _hint.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        preview_row.add_widget(_hint)
        outer.add_widget(preview_row)

        # Вкладки — горизонтальный ScrollView
        tab_sv = ScrollView(size_hint_y=None, height=S(44), do_scroll_y=False)
        tab_row = MDBoxLayout(orientation="horizontal", size_hint_x=None,
                               spacing=S(6), padding=[S(2),S(4)])
        tab_row.bind(minimum_width=tab_row.setter("width"))
        outer.add_widget(tab_sv)

        # Сетка эмодзи — вертикальный ScrollView
        grid_sv = ScrollView(size_hint_y=None, height=S(200), do_scroll_x=False)
        grid = _GL(cols=6, spacing=S(6), padding=S(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        grid_sv.add_widget(grid)
        outer.add_widget(grid_sv)

        _tab_btns = []
        _em_cards = []

        def _fill_grid(group_name):
            grid.clear_widgets(); _em_cards.clear()
            for em in EMOJI_GROUPS[group_name]:
                ec = MDCard(size_hint=(None,None), size=(S(44),S(44)),
                             radius=[S(8)], elevation=0,
                             md_bg_color=C["accent"] if em==_selected[0] else C["surf2"])
                ec._em = em
                em_path = get_emoji_png(em.strip())
                if em_path:
                    img = KivyImage(source=em_path, size_hint=(1,1),
                                    allow_stretch=True, keep_ratio=True)
                    ec.add_widget(img)
                else:
                    lbl = MDLabel(text=em, halign="center", valign="middle")
                    lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
                    ec.add_widget(lbl)
                def _pick(w, e=em):
                    _selected[0] = e
                    p = get_emoji_png(e.strip())
                    if p:
                        self._preview_emoji_img.source=p
                        self._preview_emoji_img.opacity=1
                    for c in _em_cards:
                        c.md_bg_color = C["accent"] if c._em==e else C["surf2"]
                ec.bind(on_release=_pick)
                _em_cards.append(ec)
                grid.add_widget(ec)

        def _make_tab(gname):
            em_path = get_emoji_png(gname.strip())
            btn = MDCard(size_hint=(None,None), size=(S(40),S(36)),
                          radius=[S(8)], elevation=0,
                          md_bg_color=C["accent"] if gname==_current_group[0] else C["surf2"])
            if em_path:
                img = KivyImage(source=em_path, size_hint=(1,1),
                                allow_stretch=True, keep_ratio=True)
                btn.add_widget(img)
            def _on_tab(w):
                _current_group[0] = gname
                for b in _tab_btns: b.md_bg_color = C["surf2"]
                btn.md_bg_color = C["accent"]
                _fill_grid(gname)
            btn.bind(on_release=lambda w: _on_tab(w))
            return btn

        for gname in EMOJI_GROUPS:
            tb2 = _make_tab(gname)
            _tab_btns.append(tb2)
            tab_row.add_widget(tb2)
        tab_sv.add_widget(tab_row)
        _fill_grid(_current_group[0])

        def _do_save(*_):
            self.user_emoji = _selected[0]
            self._save_profile(nf.text, dlg)
            if hasattr(self,"_tb_name_lbl"):
                self._tb_name_lbl.text = self.user_name or "Имя"
            if hasattr(self,"_s_emoji_lbl"):
                em_path = get_emoji_png(self.user_emoji.strip()) if self.user_emoji else None
                if em_path and hasattr(self._s_emoji_lbl,"source"):
                    self._s_emoji_lbl.source = em_path
                elif hasattr(self._s_emoji_lbl,"text"):
                    self._s_emoji_lbl.text = self.user_emoji or "😊"

        dlg = MDDialog(title="Профиль", type="custom", content_cls=outer,
                       buttons=[
                           MDFlatButton(text="Отмена",
                                        on_release=lambda *_: dlg.dismiss()),
                           MDRaisedButton(text="Сохранить",
                                          md_bg_color=C["accent"],
                                          on_release=_do_save)])
        dlg.open()


    def _save_profile(self, name, dlg):
        if name.strip():
            self.user_name=name.strip()
            if hasattr(self,"_tb_name_lbl"):
                self._tb_name_lbl.text=self.user_name
            if hasattr(self,"_s_name"): self._s_name.text=self.user_name
            self._save_config()
        dlg.dismiss()

    def _manage_cats(self, *_):
        box=MDBoxLayout(orientation="vertical", spacing=S(6),
                        adaptive_height=True, padding=[S(4)])
        fields=[]
        for cat in self.categories:
            row=MDBoxLayout(orientation="horizontal", spacing=S(6),
                            size_hint_y=None, height=S(50))
            f=MDTextField(text=cat, size_hint_y=None, height=S(50))
            fields.append(f); row.add_widget(f); box.add_widget(row)
        add_b=MDRaisedButton(text="+ Добавить", size_hint_y=None, height=S(38),
                              md_bg_color=C["surf2"], elevation=0)
        def _af(*_):
            row=MDBoxLayout(orientation="horizontal", spacing=S(6),
                            size_hint_y=None, height=S(50))
            f=MDTextField(hint_text="Название...", size_hint_y=None, height=S(50))
            fields.append(f); row.add_widget(f); box.add_widget(row,index=1)
        add_b.bind(on_release=_af); box.add_widget(add_b)
        sv=ScrollView(size_hint_y=None, height=S(320)); sv.add_widget(box)
        dlg=MDDialog(title="Категории", type="custom", content_cls=sv,
                     buttons=[
                         MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                         MDRaisedButton(text="Сохранить", md_bg_color=C["accent"],
                                        on_release=lambda *_: self._save_cats(fields,dlg))])
        dlg.open()

    def _save_cats(self, fields, dlg):
        new=[f.text.strip() for f in fields if f.text.strip()]
        if not new: return
        for old,n in zip(self.categories,new):
            if old!=n:
                for t in self.tasks.values():
                    if t.get("category")==old: t["category"]=n
        self.categories=new
        if self.cur_cat not in self.categories and self.cur_cat != "Все":
            self.cur_cat = "Все"
        if hasattr(self,"cat_bar"):
            self.cat_bar.clear_widgets(); self._cat_btns={}
            b_all=self._mk_cat_btn("Все"); self._cat_btns["Все"]=b_all
            self.cat_bar.add_widget(b_all)
            for c in self.categories:
                b=self._mk_cat_btn(c); self._cat_btns[c]=b; self.cat_bar.add_widget(b)
            self._update_cat_colors()
        self.save_tasks(); self._rebuild_cats_list(); dlg.dismiss()
        self.refresh_task_list()

    # ── Фильтры ─────────────────────────────────────────────────────────────
    def _tog_date(self,*_):
        self.filter_date=not self.filter_date
        self.f_date.text=self.sel_date if self.filter_date else "Все даты"
        self.f_date.md_bg_color=(*C["accent"][:3], 0.15) if self.filter_date else C["surf2"]
        self.refresh_task_list()

    def _tog_done(self,*_):
        self.show_done=not self.show_done
        self.f_done.text="Показать вып." if not self.show_done else "Скрыть вып."
        self.f_done.md_bg_color=(*C["accent"][:3], 0.15) if not self.show_done else C["surf2"]
        self.refresh_task_list()

    def _carry(self,*_):
        today=datetime.now().strftime("%d.%m.%Y")
        for t in self.tasks.values():
            if not t.get("done") and t.get("date","")<today: t["date"]=today
        self.save_tasks(); self.refresh_task_list()

    # ── Открыть форму / детали ───────────────────────────────────────────────
    def open_task_form(self, task_id=None):
        sn=f"tf_{task_id or 'new'}"
        if self.sm.has_screen(sn): self.sm.remove_widget(self.sm.get_screen(sn))
        def _sv():
            self.sm.current="main"
            if self.sm.has_screen(sn): self.sm.remove_widget(self.sm.get_screen(sn))
            self.refresh_task_list()
            if self.cur_tab=="calendar": Clock.schedule_once(lambda *_:self._refresh_cal(),0.1)
        def _cn():
            self.sm.current="main"
            if self.sm.has_screen(sn): self.sm.remove_widget(self.sm.get_screen(sn))
        sc=TaskFormScreen(app=self,task_id=task_id,on_save=_sv,on_cancel=_cn,name=sn)
        self.sm.add_widget(sc); self.sm.current=sn

    def open_task_detail(self, task_id):
        sn=f"td_{task_id}"
        if self.sm.has_screen(sn): self.sm.remove_widget(self.sm.get_screen(sn))
        def _bk():
            self.sm.current="main"
            if self.sm.has_screen(sn): self.sm.remove_widget(self.sm.get_screen(sn))
            self.refresh_task_list()
            if self.cur_tab=="calendar": Clock.schedule_once(lambda *_:self._refresh_cal(),0.1)
        sc=TaskDetailScreen(app=self,task_id=task_id,on_back=_bk,name=sn)
        self.sm.add_widget(sc); self.sm.current=sn

    # ── Мотивационный popup ──────────────────────────────────────────────────
    def _show_motivation_popup(self):
        from kivy.uix.modalview import ModalView
        is_fem=self._is_fem()
        done_today=sum(1 for t in self.tasks.values()
                       if t.get("done") and
                       t.get("date","")==date.today().strftime("%d.%m.%Y"))
        mv=ModalView(background_color=(0,0,0,0.5), auto_dismiss=False, size_hint=(0.9,None))
        card=MDCard(orientation="vertical", size_hint_y=None,
                    height=S(280 if is_fem else 220),
                    radius=[S(24)], elevation=6, md_bg_color=C["surf"],
                    padding=[S(24),S(20)])
        ci=MDBoxLayout(orientation="vertical", spacing=S(12))
        ci.add_widget(MDLabel(text="\U0001f389" if is_fem else "\u26a1",
                               font_style="H4", halign="center",
                               size_hint_y=None, height=S(54)))
        ci.add_widget(MDLabel(text="Ты сегодня молодец! \U0001f496" if is_fem else "Отличная работа!",
                               font_style="H5", bold=True,
                               theme_text_color="Custom", text_color=C["accent"],
                               halign="center", size_hint_y=None, height=S(36)))
        ci.add_widget(MDLabel(text=f"Выполнено {done_today} задач!\nПродолжай в том же духе!",
                               font_style="Body1", theme_text_color="Secondary",
                               halign="center", size_hint_y=None, height=S(50)))
        if is_fem:
            mr=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(40))
            for face in MOOD_FACES:
                _lbl_tmp=EmojiLabel(text=face, font_style="H5",
                                       halign="center", size_hint_x=0.2)
                mr.add_widget(_lbl_tmp)
                _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            _lbl_tmp=MDLabel(text="Как твоё настроение?", font_style="Caption",
                                   theme_text_color="Secondary", halign="center",
                                   size_hint_y=None, height=S(18))
            ci.add_widget(_lbl_tmp)
            _lbl_tmp.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
            ci.add_widget(mr)
        close=MDRaisedButton(text="Продолжать!", size_hint=(1,None), height=S(48),
                              elevation=0, md_bg_color=C["accent"])
        close.bind(on_release=lambda *_: mv.dismiss())
        ci.add_widget(close); card.add_widget(ci); mv.add_widget(card); mv.open()

    # ── Список задач ─────────────────────────────────────────────────────────
    def refresh_task_list(self):
        if hasattr(self,"_ref_ev") and self._ref_ev: self._ref_ev.cancel()
        self._ref_ev=Clock.schedule_once(self._do_refresh, 0.05)

    def _do_refresh(self, *_):
        self._ref_ev=None
        if not hasattr(self,"task_list"): return
        self.task_list.clear_widgets()
        if self.cur_cat == "Все":
            tasks = list(self.tasks.values())
        else:
            tasks=[t for t in self.tasks.values() if t.get("category")==self.cur_cat]
        if self.filter_date: tasks=[t for t in tasks if t.get("date")==self.sel_date]
        if not self.show_done: tasks=[t for t in tasks if not t.get("done",False)]

        # ── Поиск по всем полям ──────────────────────────────────────────────
        q = getattr(self, "_search_query", "").strip().lower()
        if q:
            def _task_matches(t):
                # заголовок
                if q in t.get("title","").lower(): return True
                # комментарий
                if q in t.get("comment","").lower(): return True
                # дата
                if q in t.get("date","").lower(): return True
                # категория
                if q in t.get("category","").lower(): return True
                # подзадачи — заголовок и комментарий каждой
                for st in t.get("subtasks",[]):
                    if q in st.get("title","").lower(): return True
                    if q in st.get("comment","").lower(): return True
                # теги
                for tag in t.get("tags", []):
                    if q in tag.lower(): return True
                # тег с решёткой
                if q.startswith("#") and any(q[1:] in tag.lower() for tag in t.get("tags",[])):
                    return True
                return False
            tasks = [t for t in tasks if _task_matches(t)]
            # при поиске ищем ВО ВСЕХ категориях
            all_tasks = [t for t in self.tasks.values()]
            if self.filter_date:
                all_tasks = [t for t in all_tasks if t.get("date")==self.sel_date]
            if not self.show_done:
                all_tasks = [t for t in all_tasks if not t.get("done",False)]
            tasks = [t for t in all_tasks if _task_matches(t)]
            if hasattr(self,"_search_result_lbl"):
                c_done = sum(1 for t in tasks if t.get("done"))
                c_undone = len(tasks) - c_done
                self._search_result_lbl.text = (
                    f'Найдено: {len(tasks)}  |  \u2705 {c_done}  \u23f3 {c_undone}'
                    if tasks else "Ничего не найдено")
        else:
            if hasattr(self,"_search_result_lbl"):
                self._search_result_lbl.text = ""
        PRIO={"Высокий":0,"Средний":1,"Низкий":2}
        tasks.sort(key=lambda t:(t.get("done",False),
                                  PRIO.get(t.get("priority","Средний"),1),
                                  t.get("date","")))
        for t in tasks:
            card = TaskCard(
                task_id=t["id"],title=t["title"],task_date=t["date"],
                comment=t.get("comment",""),done=t.get("done",False),
                priority=t.get("priority","Средний"),
                category=t.get("category",""),
                original_date=t.get("original_date",t["date"]),
                subtasks=t.get("subtasks",[]),
                time_str=t.get("time",""))
            # Запоминаем исходную x позицию для свайпа
            def _init_x(w, pos):
                if not hasattr(w, "x_orig"):
                    w.x_orig = pos[0]
            card.bind(pos=_init_x)
            self.task_list.add_widget(card)

        # ── Пустой экран ─────────────────────────────────────────────────
        if not tasks:
            q = getattr(self, "_search_query", "").strip()
            empty_box = MDBoxLayout(orientation="vertical", spacing=S(12),
                                     size_hint_y=None, height=S(200),
                                     padding=[S(24), S(40)])
            if q:
                msg = f'Ничего не найдено по запросу "{q}"'
                hint = "Попробуйте другой запрос или измените фильтры"
            elif not self.show_done:
                msg = "Все задачи выполнены!"
                hint = "Отличная работа! Добавьте новые задачи нажав +"
            else:
                msg = "Нет задач"
                hint = "Нажмите + чтобы добавить первую задачу"
            em_title = MDLabel(text=msg, font_style="H6", bold=True,
                               theme_text_color="Custom", text_color=C["text"],
                               halign="center", size_hint_y=None, height=S(60))
            em_title.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            em_hint = MDLabel(text=hint, font_style="Body2",
                              theme_text_color="Secondary",
                              halign="center", size_hint_y=None, height=S(40))
            em_hint.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            empty_box.add_widget(em_title)
            empty_box.add_widget(em_hint)
            if not q:
                add_btn = MDRaisedButton(text="+ Добавить задачу",
                                          md_bg_color=C["accent"], elevation=0,
                                          size_hint_x=None, width=S(200),
                                          pos_hint={"center_x":0.5})
                add_btn.bind(on_release=lambda *_: self.open_task_form())
                empty_box.add_widget(add_btn)
            self.task_list.add_widget(empty_box)

        total=len(tasks); done=sum(1 for t in tasks if t.get("done"))
        pct=done/total if total else 0.0
        cat_label = "Все категории" if self.cur_cat=="Все" else self.cur_cat
        self.stat_lbl.text=f"{cat_label}: {total} задач  {done} выполнено" \
            if hasattr(self,"stat_lbl") else ""
        if hasattr(self,"_pct_lbl"): self._pct_lbl.text=f"{int(pct*100)}%"
        self._prog_fill=pct
        if hasattr(self,"_draw_prog"): self._draw_prog(self._prog_bg)
        if hasattr(self,"_day_pct_lbl"): self._day_pct_lbl.text=f"{int(pct*100)}%"

        is_fem=self._is_fem(); today_s=date.today().strftime("%d.%m.%Y")
        undone=[t for t in self.tasks.values()
                if not t.get("done") and t.get("date","")<=today_s]
        high=[t for t in undone if t.get("priority")=="Высокий"]
        pick=high or undone
        if hasattr(self,"_day_task_lbl"):
            if pick:
                self._day_task_lbl.text=pick[0]["title"][:42]
                tv=pick[0].get("time","")
                sub_txt=(tv if tv else
                    ("Поставь цель на сегодня \U0001f496" if is_fem else "до конца дня"))
                self._day_task_sub.text = sub_txt
            else:
                done_txt=("Всё выполнено! \U0001f389" if done else
                    ("Добавь первую задачу" if is_fem else "Список пуст"))
                self._day_task_lbl.text=done_txt
                sub2=f"Выполнено {done} дел \U0001f49e" if (done and is_fem) else ""
                self._day_task_sub.text = sub2
        if self.cur_tab=="calendar":
            Clock.schedule_once(lambda *_: self._refresh_cal(), 0.05)

    # ── Экспорт ──────────────────────────────────────────────────────────────

    def _quick_add_sheet(self):
        """Быстрое добавление задачи — всплывающий лист снизу."""
        from kivy.uix.modalview import ModalView
        from kivy.core.window import Window
        # Поднимаем контент при появлении клавиатуры
        _orig_softinput = Window.softinput_mode
        Window.softinput_mode = "below_target"
        from kivy.core.window import Window as _Win
        def _calc_height():
            return max(S(260), S(300))

        mv = ModalView(background_color=(0,0,0,0.5), auto_dismiss=True,
                       size_hint=(1, None), height=_calc_height(),
                       pos_hint={"x":0, "y":0})

        def _on_keyboard_height(win, kb_h):
            # Сдвигаем модальное окно вверх на высоту клавиатуры
            if kb_h > 0:
                mv.pos_hint = {"x":0, "y": kb_h / _Win.height}
                mv.height = _calc_height()
            else:
                mv.pos_hint = {"x":0, "y":0}
        _Win.bind(keyboard_height=_on_keyboard_height)

        def _on_dismiss(*_):
            Window.softinput_mode = _orig_softinput
            _Win.unbind(keyboard_height=_on_keyboard_height)
        mv.bind(on_dismiss=_on_dismiss)
        card = MDCard(orientation="vertical", size_hint=(1,1),
                      radius=[S(20),S(20),0,0], elevation=12,
                      md_bg_color=C["surf"], padding=[S(20),S(16)])
        # Заголовок
        hdr = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(32))
        ttl = MDLabel(text="Быстрое добавление", font_style="H6", bold=True,
                      theme_text_color="Custom", text_color=C["text"],
                      size_hint_x=1)
        ttl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        close_btn = MDIconButton(icon="close", size_hint_x=None, width=S(36),
                                  theme_text_color="Custom", text_color=C["text2"])
        close_btn.bind(on_release=lambda *_: mv.dismiss())
        hdr.add_widget(ttl); hdr.add_widget(close_btn)
        card.add_widget(hdr)
        # Поле ввода
        tf = MDTextField(hint_text="Что нужно сделать?",
                         size_hint_y=None, height=S(48),
                         mode="rectangle")
        card.add_widget(tf)
        # Строка категорий
        cat_row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                               height=S(36), spacing=S(6), padding=[0,S(4)])
        _qs_cat = [self.cur_cat if self.cur_cat != "Все" else self.categories[0]]
        for cat in self.categories[:4]:
            cb = MDRaisedButton(text=cat, elevation=0, size_hint_x=None,
                                 width=S(len(cat)*8+20), size_hint_y=None, height=S(28),
                                 md_bg_color=C["accent"] if cat==_qs_cat[0] else C["surf2"])
            def _sel_cat(_, c=cat, b=cb):
                _qs_cat[0] = c
                for ch in cat_row.children:
                    ch.md_bg_color = C["accent"] if ch.text == c else C["surf2"]
            cb.bind(on_release=_sel_cat)
            cat_row.add_widget(cb)
        card.add_widget(cat_row)
        # Кнопка сохранить
        save_btn = MDRaisedButton(
            text="Сохранить", md_bg_color=C["accent"],
            size_hint_y=None, height=S(42), elevation=0)
        def _quick_save(*_):
            title = tf.text.strip()
            if not title:
                tf.hint_text = "Введите название!"; return
            import uuid
            from datetime import date
            tid = str(uuid.uuid4())[:8]
            self.tasks[tid] = {
                "id": tid, "title": title,
                "date": date.today().strftime("%d.%m.%Y"),
                "category": _qs_cat[0],
                "priority": "Средний", "done": False,
                "comment": "", "tags": [], "subtasks": [],
                "time": "", "reminder": "", "repeat": "Не повторять"
            }
            self.save_tasks()
            self.refresh_task_list()
            mv.dismiss()
            self._show_toast(f"Добавлено: {title[:30]}")
        save_btn.bind(on_release=_quick_save)
        card.add_widget(save_btn)
        mv.add_widget(card)
        mv.open()
        # Фокус на поле ввода
        Clock.schedule_once(lambda *_: setattr(tf, "focus", True), 0.2)

    # ── Резервное копирование / Импорт / Поделиться ────────────────────────
    # ── Резервное копирование / Импорт / Поделиться ────────────────────────
    #  Используем системный SAF (Storage Access Framework):
    #  - Сохранение: ACTION_CREATE_DOCUMENT -> пользователь выбирает место
    #    (по умолчанию открывается папка "Download"), файл остаётся ПОСЛЕ
    #    удаления приложения.
    #  - Импорт: ACTION_OPEN_DOCUMENT -> пользователь выбирает файл бэкапа.
    #  - "Поделиться задачей": передаём JSON как ТЕКСТ через ACTION_SEND
    #    (без FileProvider — работает без доп. настройки в любом Android).

    def _backup_restore(self, *_):
        """Резервная копия — диалог сохранения и загрузки."""
        from kivy.uix.modalview import ModalView
        mv = ModalView(background_color=(0,0,0,0.6), auto_dismiss=True,
                       size_hint=(0.9, None), height=S(300),
                       pos_hint={"center_x":0.5,"center_y":0.5})
        card = MDCard(orientation="vertical", size_hint=(1,1),
                      radius=[S(16)], elevation=8,
                      md_bg_color=C["surf"], padding=[S(20),S(16)], spacing=S(10))
        title_lbl = MDLabel(text="Резервная копия", font_style="H6", bold=True,
                            theme_text_color="Custom", text_color=C["text"],
                            halign="center", size_hint_y=None, height=S(32))
        title_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(title_lbl)
        info_lbl = MDLabel(
            text="Сохраните файл в удобное место (например в Загрузки).\n"
                 "Этот файл можно загрузить позже, даже после переустановки.",
            font_style="Caption", theme_text_color="Secondary",
            halign="center", size_hint_y=None, height=S(56))
        info_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(info_lbl)
        save_btn = MDRaisedButton(text="Сохранить бэкап...",
                                   md_bg_color=C["accent"], elevation=0,
                                   size_hint_y=None, height=S(44))
        save_btn.bind(on_release=lambda *_: (mv.dismiss(), self._export()))
        card.add_widget(save_btn)
        load_btn = MDRaisedButton(text="Загрузить бэкап из файла...",
                                   md_bg_color=C["surf2"], elevation=0,
                                   size_hint_y=None, height=S(44))
        load_btn.bind(on_release=lambda *_: (mv.dismiss(), self._pick_import_file()))
        card.add_widget(load_btn)
        close_btn = MDRaisedButton(text="Закрыть", elevation=0,
                                    md_bg_color=C["surf2"],
                                    size_hint_y=None, height=S(36))
        close_btn.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(close_btn)
        mv.add_widget(card); mv.open()

    def _export(self, *_):
        """Открывает системный диалог 'Сохранить как' и пишет туда бэкап JSON."""
        data = {"tasks": list(self.tasks.values()),
                "categories": self.categories,
                "profile": {"name": self.user_name},
                "mood_history": self.mood_history}
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        fname = f"flowdo_backup_{ts}.json"
        text = json.dumps(data, ensure_ascii=False, indent=2)

        if PLATFORM == "android":
            try:
                from android import activity as _android_activity
                from jnius import autoclass, cast
                Intent = autoclass("android.content.Intent")
                String = autoclass("java.lang.String")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")

                intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("application/json")
                intent.putExtra(Intent.EXTRA_TITLE,
                                cast("java.lang.CharSequence", String(fname)))

                REQ_CODE = 7422
                def _on_result(request_code, result_code, intent_data):
                    if request_code != REQ_CODE: return
                    RESULT_OK = -1
                    if result_code != RESULT_OK or intent_data is None:
                        Clock.schedule_once(
                            lambda *_: self._show_toast("Сохранение отменено"), 0)
                        _android_activity.unbind(on_activity_result=_on_result)
                        return
                    uri = intent_data.getData()
                    try:
                        ctx = PythonActivity.mActivity
                        resolver = ctx.getContentResolver()
                        stream = resolver.openOutputStream(uri)
                        OutputStreamWriter = autoclass("java.io.OutputStreamWriter")
                        writer = OutputStreamWriter(stream, "UTF-8")
                        writer.write(text)
                        writer.flush()
                        writer.close()
                        Clock.schedule_once(
                            lambda *_: self._show_toast("Бэкап сохранён!"), 0)
                    except Exception as e:
                        Clock.schedule_once(
                            lambda *_: self._show_toast(f"Ошибка сохранения: {e}"), 0)
                    finally:
                        _android_activity.unbind(on_activity_result=_on_result)

                _android_activity.bind(on_activity_result=_on_result)
                PythonActivity.mActivity.startActivityForResult(intent, REQ_CODE)
            except Exception as e:
                self._show_toast(f"Не удалось открыть диалог сохранения: {e}")
        else:
            # Desktop: сохраняем в домашнюю папку
            path = os.path.join(os.path.expanduser("~"), fname)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self._show_toast(f"Сохранено: {path}")
                return path
            except Exception as e:
                self._show_toast(f"Ошибка: {e}")
                return None

    def _pick_import_file(self):
        """Открывает системный выбор файла для импорта бэкапа/задачи."""
        if PLATFORM == "android":
            try:
                from android import activity as _android_activity
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")

                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("*/*")  # некоторые файл-менеджеры неверно отдают mime для .json
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

                REQ_CODE = 7421
                def _on_result(request_code, result_code, intent_data):
                    if request_code != REQ_CODE: return
                    RESULT_OK = -1
                    if result_code != RESULT_OK or intent_data is None:
                        _android_activity.unbind(on_activity_result=_on_result)
                        return
                    uri = intent_data.getData()
                    if uri is None:
                        _android_activity.unbind(on_activity_result=_on_result)
                        return
                    try:
                        ctx = PythonActivity.mActivity
                        resolver = ctx.getContentResolver()
                        stream = resolver.openInputStream(uri)
                        BufferedReader = autoclass("java.io.BufferedReader")
                        InputStreamReader = autoclass("java.io.InputStreamReader")
                        reader = BufferedReader(InputStreamReader(stream))
                        sb = []
                        line = reader.readLine()
                        while line is not None:
                            sb.append(line)
                            line = reader.readLine()
                        reader.close()
                        text = "\n".join(sb)
                        data = json.loads(text)
                        Clock.schedule_once(lambda *_: self._apply_imported_data(data), 0)
                    except Exception as e:
                        Clock.schedule_once(
                            lambda *_: self._show_toast(f"Ошибка чтения файла: {e}"), 0)
                    finally:
                        _android_activity.unbind(on_activity_result=_on_result)

                _android_activity.bind(on_activity_result=_on_result)
                PythonActivity.mActivity.startActivityForResult(intent, REQ_CODE)
            except Exception as e:
                self._show_toast(f"Не удалось открыть выбор файла: {e}")
        else:
            from tkinter import filedialog, Tk
            try:
                root = Tk(); root.withdraw()
                path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
                root.destroy()
                if path:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._apply_imported_data(data)
            except Exception as e:
                self._show_toast(f"Ошибка: {e}")

    def _apply_imported_data(self, data):
        """Применяет данные из импортированного JSON (полный бэкап или одна задача)."""
        try:
            # Если это одна задача (поделились через share_task)
            if "task" in data and "tasks" not in data:
                t = data["task"]
                import uuid
                t["id"] = str(uuid.uuid4())[:8]  # новый id чтобы не конфликтовать
                self.tasks[t["id"]] = t
                self.save_tasks()
                self.refresh_task_list()
                self._show_toast(f"Задача добавлена: {t.get('title','')[:30]}")
                return
            # Полный бэкап
            if "tasks" in data:
                restored = {}
                for t in data["tasks"]:
                    if "id" in t:
                        restored[t["id"]] = t
                self.tasks = restored
                self.save_tasks()
            if "categories" in data:
                self.categories = data["categories"]
            if "profile" in data:
                self.user_name = data["profile"].get("name", self.user_name)
            self._save_config()
            self.refresh_task_list()
            self._show_toast(f"Загружено {len(self.tasks)} задач!")
        except Exception as e:
            self._show_toast(f"Ошибка импорта: {e}")

    def share_task(self, task_id):
        """Делится задачей как текстом (JSON) через системное меню — без FileProvider."""
        task = self.tasks.get(task_id)
        if not task:
            self._show_toast("Задача не найдена")
            return
        payload = json.dumps({"flowdo_share": True, "task": task},
                              ensure_ascii=False)
        share_text = (f"[FlowDo задача] {task.get('title','')}\n"
                       f"Вставьте этот текст в Flow·Do -> Настройки -> "
                       f"Резервная копия -> Импорт из текста, чтобы добавить задачу.\n\n"
                       f"{payload}")

        if PLATFORM == "android":
            try:
                from jnius import autoclass, cast
                Intent = autoclass("android.content.Intent")
                String = autoclass("java.lang.String")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                ctx = PythonActivity.mActivity

                intent = Intent(Intent.ACTION_SEND)
                intent.setType("text/plain")
                intent.putExtra(Intent.EXTRA_SUBJECT,
                                cast("java.lang.CharSequence", String("Задача из Flow\u00b7Do")))
                intent.putExtra(Intent.EXTRA_TEXT,
                                cast("java.lang.CharSequence", String(share_text)))
                title_cs = cast("java.lang.CharSequence", String("Поделиться задачей"))
                chooser = Intent.createChooser(intent, title_cs)
                ctx.startActivity(chooser)
            except Exception as e:
                self._show_toast(f"Не удалось открыть меню \"Поделиться\": {e}")
        else:
            try:
                import pyperclip
                pyperclip.copy(share_text)
                self._show_toast("Скопировано в буфер обмена!")
            except Exception:
                self._show_toast("Поделиться доступно только на Android")

    def import_from_text(self, *_):
        """Диалог ручного ввода/вставки JSON задачи для импорта."""
        from kivy.uix.modalview import ModalView
        mv = ModalView(background_color=(0,0,0,0.6), auto_dismiss=True,
                       size_hint=(0.9, None), height=S(320),
                       pos_hint={"center_x":0.5,"center_y":0.5})
        card = MDCard(orientation="vertical", size_hint=(1,1),
                      radius=[S(16)], elevation=8,
                      md_bg_color=C["surf"], padding=[S(20),S(16)], spacing=S(10))
        title_lbl = MDLabel(text="Импорт задачи из текста", font_style="H6", bold=True,
                            theme_text_color="Custom", text_color=C["text"],
                            halign="center", size_hint_y=None, height=S(32))
        title_lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(title_lbl)
        hint = MDLabel(text="Вставьте текст, полученный через 'Поделиться задачей'",
                       font_style="Caption", theme_text_color="Secondary",
                       halign="center", size_hint_y=None, height=S(36))
        hint.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(hint)
        tf = MDTextField(hint_text="Вставьте текст здесь...",
                         multiline=True, size_hint_y=None, height=S(120))
        card.add_widget(tf)
        import_btn = MDRaisedButton(text="Импортировать",
                                     md_bg_color=C["accent"], elevation=0,
                                     size_hint_y=None, height=S(44))
        def _do_import(*_):
            raw = tf.text.strip()
            # Извлекаем JSON — ищем первую { и последнюю }
            try:
                start = raw.index("{")
                end = raw.rindex("}") + 1
                data = json.loads(raw[start:end])
                self._apply_imported_data(data)
                mv.dismiss()
            except Exception as e:
                self._show_toast(f"Не удалось разобрать текст: {e}")
        import_btn.bind(on_release=_do_import)
        card.add_widget(import_btn)
        close_btn = MDRaisedButton(text="Отмена", elevation=0,
                                    md_bg_color=C["surf2"],
                                    size_hint_y=None, height=S(36))
        close_btn.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(close_btn)
        mv.add_widget(card); mv.open()

    def handle_shared_file(self, uri_or_path):
        """Вызывается когда приложение открыто через 'Открыть с помощью' для .json файла."""
        try:
            if PLATFORM == "android" and str(uri_or_path).startswith("content://"):
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                ctx = PythonActivity.mActivity
                resolver = ctx.getContentResolver()
                Uri = autoclass("android.net.Uri")
                uri = Uri.parse(str(uri_or_path))
                stream = resolver.openInputStream(uri)
                BufferedReader = autoclass("java.io.BufferedReader")
                InputStreamReader = autoclass("java.io.InputStreamReader")
                reader = BufferedReader(InputStreamReader(stream))
                sb = []
                line = reader.readLine()
                while line is not None:
                    sb.append(line)
                    line = reader.readLine()
                reader.close()
                text = "\n".join(sb)
                data = json.loads(text)
            else:
                with open(uri_or_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            self._apply_imported_data(data)
        except Exception as e:
            self._show_toast(f"Ошибка открытия файла: {e}")

    def _show_about(self, *_):
        from kivy.uix.modalview import ModalView
        mv = ModalView(background_color=(0,0,0,0.7), auto_dismiss=True,
                       size_hint=(0.9, None), height=S(320),
                       pos_hint={"center_x":0.5,"center_y":0.5})
        card = MDCard(orientation="vertical", size_hint=(1,1),
                      radius=[S(20)], elevation=8,
                      md_bg_color=C["surf"], padding=[S(24), S(20)], spacing=S(12))
        title = MDLabel(text="Flow·Do", font_style="H5", bold=True,
                        theme_text_color="Custom", text_color=C["accent"],
                        halign="center", size_hint_y=None, height=S(40))
        title.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
        card.add_widget(title)
        for line in ["Версия: 4.0", "Менеджер задач с голосовым помощником",
                     "Платформа: " + PLATFORM.title(),
                     "Задач: " + str(len(self.tasks)),
                     "Категорий: " + str(len(self.categories))]:
            lbl = MDLabel(text=line, font_style="Body2",
                          theme_text_color="Primary",
                          halign="center", size_hint_y=None, height=S(28))
            lbl.bind(size=lambda w,s: setattr(w,"text_size",(s[0],None)))
            card.add_widget(lbl)
        close_btn = MDRaisedButton(text="Закрыть", md_bg_color=C["accent"],
                                   size_hint=(1,None), height=S(44), elevation=0)
        close_btn.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(close_btn)
        mv.add_widget(card); mv.open()

    def _export(self,*_):
        """Сохраняет полный бэкап в общедоступную папку Download/FlowDo.
        Возвращает путь к файлу при успехе, иначе None."""
        self._request_storage_permission()
        folder = self._get_export_dir()
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"flowdo_backup_{ts}.json")
        try:
            with open(path,"w",encoding="utf-8") as f:
                json.dump({"tasks":list(self.tasks.values()),
                           "categories":self.categories,
                           "profile":{"name":self.user_name},
                           "mood_history":self.mood_history},
                          f, ensure_ascii=False, indent=2)
            if hasattr(self,"_exp_lbl"): self._exp_lbl.text=f"Сохранено: {path}"
            return path
        except Exception as e:
            if hasattr(self,"_exp_lbl"): self._exp_lbl.text=f"Ошибка: {e}"
            return None

    # ── Rebuild после смены темы ──────────────────────────────────────────────
    def _rebuild(self,*_):
        for attr in ("_pg_tasks","_pg_calendar","_pg_stats","_pg_settings",
                     "task_list","cat_bar","_cat_btns","stat_lbl","_pct_lbl",
                     "_prog_bg","_day_task_lbl","_day_task_sub","_day_pct_lbl",
                     "_ring_pct_lbl","_bars_box","_s_streak","_s_total",
                     "_motiv_lbl","_motiv_sub","_mood_btns","_sd_lbl","_sf_lbl",
                     "_sp_badge","_s_name","_s_emoji_lbl","_g_fem","_g_mal","_exp_lbl",
                     "_cats_box","_cal_month_lbl","_sp_btns",
                     "_goal_pct_lbl","_goal_prog","_draw_goal",
                     "_tasks_header","_nav_btns",
                     "_search_field","_search_result_lbl","_search_clear_btn"):
            if hasattr(self,attr):
                try: delattr(self,attr)
                except: pass
        self._ring_pct=0.0
        self._build_main(); self.sm.current="main"
        Clock.schedule_once(self.load_tasks, 0.2)

    def _reset(self,*_):
        self.user_name=""; self._save_config()
        if self.sm.has_screen("main"):
            self.sm.remove_widget(self.sm.get_screen("main"))
        self._build_welcome(); self.sm.current="welcome"

    # ── Загрузка / сохранение ────────────────────────────────────────────────
    def load_tasks(self, dt=None):
        self._load_mood_history()
        if self.cfg_store.exists("weekly_goal"):
            self.weekly_goal=self.cfg_store.get("weekly_goal").get("value",80)
        if self.store.exists("tasks"):
            for t in self.store.get("tasks")["items"]:
                t.setdefault("id",       str(datetime.now().timestamp()))
                t.setdefault("category", self.categories[0])
                t.setdefault("comment",  "")
                t.setdefault("done",     False)
                t.setdefault("priority", "Средний")
                t.setdefault("original_date", t.get("date",self.sel_date))
                t.setdefault("subtasks", [])
                t.setdefault("time",     "")
                t.setdefault("reminder", "")
                t.setdefault("repeat",   "Не повторять")
                self.tasks[t["id"]]=t
        self.refresh_task_list()

    def save_tasks(self):
        if hasattr(self,"_save_ev") and self._save_ev: self._save_ev.cancel()
        self._save_ev=Clock.schedule_once(self._do_save, 0.4)

    def _do_save(self,*_):
        self._save_ev=None
        self.store.put("tasks", items=list(self.tasks.values()))

    def _load_config(self):
        if self.cfg_store.exists("profile"):
            self.user_name  = self.cfg_store.get("profile").get("name","")
            self.user_emoji = self.cfg_store.get("profile").get("emoji","😊")
        if self.cfg_store.exists("theme"):
            tn=self.cfg_store.get("theme").get("name","Роза")
            if tn in THEMES: self.theme_name=tn; C.update(THEMES[tn])
        if self.cfg_store.exists("categories"):
            cats=self.cfg_store.get("categories").get("list",[])
            if cats: self.categories=cats
        if self.cfg_store.exists("weekly_goal"):
            self.weekly_goal=self.cfg_store.get("weekly_goal").get("value",80)
        if self.cfg_store.exists("cat_emoji"):
            saved=self.cfg_store.get("cat_emoji").get("map",{})
            CAT_EMOJI.update(saved)
        if self.cfg_store.exists("cur_cat"):
            saved_cat=self.cfg_store.get("cur_cat").get("name","Все")
            # "Все" всегда валидна; пользовательские — проверяем
            if saved_cat == "Все" or saved_cat in self.categories:
                self.cur_cat = saved_cat
        # Загружаем API ключ
        if self.cfg_store.exists("api_key"):
            self._anthropic_api_key = self.cfg_store.get("api_key").get("value","")
        else:
            self._anthropic_api_key = ""

    def _save_config(self):
        self.cfg_store.put("profile",    name=self.user_name, emoji=self.user_emoji)
        self.cfg_store.put("theme",      name=self.theme_name)
        self.cfg_store.put("categories", list=self.categories)
        self.cfg_store.put("weekly_goal",value=self.weekly_goal)
        self.cfg_store.put("cat_emoji",  map=dict(CAT_EMOJI))
        self.cfg_store.put("cur_cat",    name=self.cur_cat)
        self.cfg_store.put("api_key",    value=getattr(self,"_anthropic_api_key",""))

    # stat_lbl placeholder
    @property
    def stat_lbl(self):
        return getattr(self, "_stat_lbl_obj", None) or type("_",(),{"text":""})()


if __name__ == "__main__":
    DailyTodoApp().run()
