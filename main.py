# ═══════════════════════════════════════════════════════════════════════════
#  FLOW·DO  ·  KivyMD  ·  v4.0
#  Новое в v4.0:
#    ★ Голосовой помощник (vosk офлайн + pyttsx3 TTS)
#    ★ Свайп-жест на задачах (влево = удалить, вправо = выполнено)
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

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from datetime import datetime, date, timedelta
import calendar as cal_module
import json, os, random, math, threading

# ───────────────────────────────────────────────────────────────────────────
#  Голосовой модуль (мягкий импорт — работает и без vosk/pyttsx3)
# ───────────────────────────────────────────────────────────────────────────
try:
    import vosk, pyaudio, queue as _queue
    VOSK_OK = True
except ImportError:
    VOSK_OK = False

try:
    import pyttsx3 as _pyttsx3
    _tts_engine = _pyttsx3.init()
    _tts_engine.setProperty("rate", 160)
    TTS_OK = True
except Exception:
    TTS_OK = False

try:
    from plyer import notification as _plyer_notif
    PLYER_OK = True
except ImportError:
    PLYER_OK = False

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
    "Работа":"\U0001f4bc","Дом":"\U0001f3e0",
    "Личное":"\U0001f496","Покупки":"\U0001f6cd",
    "Тренировки":"\U0001f4aa","Семья":"\U0001f46a",
    "Учёба":"\U0001f4da","Финансы":"\U0001f4b0",
    "Прочее":"\U0001f4cc",
}

MOTIVATIONS_F = [
    "\U0001f338 Ты сегодня молодец!","\u2728 Всё получится!",
    "\U0001f338 Ты справляешься!","\U0001f31f Продолжай в том же духе!",
    "\U0001f495 Ты лучшая!",
]
MOTIVATIONS_M = [
    "Отличная работа!","Держи темп!","Фокус — результат!",
    "Дисциплина — ключ к успеху.","Контролируй день — контролируй жизнь.",
]

REPEAT_OPTIONS  = ["Не повторять","Каждый день","Каждую неделю","Каждый месяц"]
REMIND_OPTIONS  = ["Не выбрано","За 10 минут","За 30 минут","За 1 час","За 1 день"]
MOOD_FACES      = ["\U0001f61e","\U0001f610","\U0001f642","\U0001f60a","\U0001f604"]
MOOD_LABELS     = ["Плохо","Нейтрально","Нормально","Хорошо","Отлично"]


# ═══════════════════════════════════════════════════════════════════════════
#  Голосовой помощник
# ═══════════════════════════════════════════════════════════════════════════
class VoiceAssistant:
    """
    Распознаёт речь (vosk офлайн) и выполняет команды в приложении.
    При отсутствии vosk — fallback на диалог ввода текста.
    """
    VOSK_MODEL_PATH = "vosk-model-small-ru"   # скачать с alphacephei.com/vosk/models

    def __init__(self, app):
        self.app = app
        self._listening = False
        self._model = None
        self._audio_thread = None
        self._q = None
        if VOSK_OK and os.path.exists(self.VOSK_MODEL_PATH):
            try:
                import vosk
                self._model = vosk.Model(self.VOSK_MODEL_PATH)
            except Exception:
                self._model = None

    # ── TTS ─────────────────────────────────────────────────────────────────
    def speak(self, text):
        if TTS_OK:
            def _run():
                try:
                    _tts_engine.say(text)
                    _tts_engine.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=_run, daemon=True).start()
        # показываем тост
        Clock.schedule_once(lambda *_: self.app._show_toast(text), 0)

    # ── Запуск/остановка прослушивания ──────────────────────────────────────
    def start_listening(self, on_result):
        if self._model is None:
            # fallback — диалог текстового ввода
            self._text_fallback(on_result)
            return
        if self._listening:
            return
        self._listening = True
        import queue, pyaudio, vosk, json
        self._q = queue.Queue()

        def _audio():
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000,
                             input=True, frames_per_buffer=8000)
            rec = vosk.KaldiRecognizer(self._model, 16000)
            while self._listening:
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    txt = res.get("text","").strip()
                    if txt:
                        Clock.schedule_once(lambda *_, t=txt: on_result(t), 0)
                        break
            stream.stop_stream(); stream.close(); pa.terminate()
            self._listening = False

        self._audio_thread = threading.Thread(target=_audio, daemon=True)
        self._audio_thread.start()

    def stop_listening(self):
        self._listening = False

    def _text_fallback(self, on_result):
        """Показываем компактный оверлей ввода команды (без лишнего диалога)."""
        from kivy.uix.modalview import ModalView
        mv = ModalView(background_color=(0,0,0,0.55), auto_dismiss=True,
                       size_hint=(0.92, None), height=S(180),
                       pos_hint={"center_x": 0.5, "center_y": 0.5})
        card = MDCard(orientation="vertical", size_hint=(1,1),
                      radius=[S(20)], elevation=8,
                      md_bg_color=C["surf"], padding=[S(18), S(16)])
        hdr = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(36))
        hdr.add_widget(MDLabel(text="\U0001f3a4  Введите команду",
                               font_style="Subtitle1", bold=True,
                               theme_text_color="Custom", text_color=C["text"]))
        close_btn = MDIconButton(icon="close", size_hint_x=None, width=S(36),
                                 theme_text_color="Custom", text_color=C["text2"])
        close_btn.bind(on_release=lambda *_: mv.dismiss())
        hdr.add_widget(close_btn); card.add_widget(hdr)

        nf = MDTextField(hint_text="добавь задачу ... / что на сегодня?",
                         size_hint_y=None, height=S(52))
        card.add_widget(nf)

        btn_row = MDBoxLayout(orientation="horizontal", spacing=S(10),
                              size_hint_y=None, height=S(46))
        cancel = MDFlatButton(text="Отмена", size_hint_x=0.4)
        cancel.bind(on_release=lambda *_: mv.dismiss())
        go = MDRaisedButton(text="Выполнить", size_hint_x=0.6,
                            md_bg_color=C["accent"], elevation=0)
        go.bind(on_release=lambda *_: self._fb_ok(nf.text, mv, on_result))
        btn_row.add_widget(cancel); btn_row.add_widget(go)
        card.add_widget(btn_row)
        mv.add_widget(card); mv.open()
        # фокус на поле ввода
        Clock.schedule_once(lambda *_: setattr(nf, "focus", True), 0.3)

    def _fb_ok(self, text, mv, on_result):
        mv.dismiss()
        if text.strip():
            Clock.schedule_once(lambda *_: on_result(text.strip()), 0.1)

    # ── Парсинг команд ───────────────────────────────────────────────────────
    def process_command(self, text):
        t = text.lower().strip()
        app = self.app

        # ── Добавить задачу ──────────────────────────────────────────────────
        for kw in ["добавь задачу","добавить задачу","создай задачу","новая задача"]:
            if kw in t:
                title = t.split(kw,1)[-1].strip()
                # определяем дату
                target_date = date.today().strftime("%d.%m.%Y")
                for wrd, delta in [("завтра",1),("послезавтра",2)]:
                    if wrd in title:
                        target_date = (date.today()+timedelta(days=delta)).strftime("%d.%m.%Y")
                        title = title.replace(wrd,"").strip()
                # определяем категорию
                cat = app.cur_cat
                for c in app.categories:
                    if c.lower() in title:
                        cat = c; title = title.replace(c.lower(),"").strip(); break
                if title:
                    tid = str(datetime.now().timestamp())
                    app.tasks[tid] = {
                        "id":tid,"title":title.capitalize(),"comment":"",
                        "category":cat,"priority":"Средний","date":target_date,
                        "time":"","reminder":"","repeat":"Не повторять",
                        "subtasks":[],"original_date":target_date,"done":False
                    }
                    app.save_tasks(); app.refresh_task_list()
                    self.speak(f"Задача добавлена: {title}")
                else:
                    self.speak("Скажите название задачи")
                return

        # ── Отметить выполненной ─────────────────────────────────────────────
        for kw in ["отметь выполненной","завершить задачу","выполнена задача",
                   "сделал","сделала","готово"]:
            if kw in t:
                query = t.split(kw,1)[-1].strip()
                found = self._find_task(query)
                if found:
                    found["done"] = True
                    app.save_tasks(); app.refresh_task_list()
                    self.speak(f"Выполнено: {found['title']}")
                else:
                    self.speak("Задача не найдена")
                return

        # ── Удалить задачу ───────────────────────────────────────────────────
        for kw in ["удали задачу","удалить задачу","убери задачу"]:
            if kw in t:
                query = t.split(kw,1)[-1].strip()
                found = self._find_task(query)
                if found:
                    app.tasks.pop(found["id"], None)
                    app.save_tasks(); app.refresh_task_list()
                    self.speak(f"Удалено: {found['title']}")
                else:
                    self.speak("Задача не найдена")
                return

        # ── Найти / поиск ────────────────────────────────────────────────────
        for kw in ["найди","поиск","найти"]:
            if kw in t:
                query = t.split(kw,1)[-1].strip()
                results = [task for task in app.tasks.values()
                           if query in task.get("title","").lower()]
                if results:
                    names = ", ".join(r["title"] for r in results[:3])
                    self.speak(f"Найдено {len(results)}: {names}")
                else:
                    self.speak("Ничего не найдено")
                return

        # ── Что на сегодня ───────────────────────────────────────────────────
        for kw in ["что на сегодня","задачи на сегодня","список задач","план на день"]:
            if kw in t:
                today_s = date.today().strftime("%d.%m.%Y")
                tasks_today = [task for task in app.tasks.values()
                               if task.get("date") == today_s and not task.get("done")]
                if tasks_today:
                    count = len(tasks_today)
                    first = tasks_today[0]["title"]
                    self.speak(f"На сегодня {count} задач. Первая: {first}")
                else:
                    self.speak("На сегодня задач нет. Отличный день!")
                return

        # ── Статистика ───────────────────────────────────────────────────────
        for kw in ["статистика","сколько выполнено","прогресс"]:
            if kw in t:
                today_s = date.today().strftime("%d.%m.%Y")
                mon_s   = date.today().replace(day=1).strftime("%d.%m.%Y")
                done_m  = sum(1 for task in app.tasks.values()
                              if task.get("done") and mon_s <= task.get("date","") <= today_s)
                total_m = sum(1 for task in app.tasks.values()
                              if mon_s <= task.get("date","") <= today_s)
                pct = int(done_m/total_m*100) if total_m else 0
                self.speak(f"В этом месяце выполнено {done_m} из {total_m} задач — {pct}%")
                return

        # ── Настроение ───────────────────────────────────────────────────────
        for i, lbl in enumerate(MOOD_LABELS):
            if lbl.lower() in t:
                app._save_mood(i+1)
                self.speak(f"Настроение сохранено: {lbl}")
                return

        # ── Открыть страницу ─────────────────────────────────────────────────
        if "календарь" in t or "расписание" in t:
            app._nav_switch("calendar"); self.speak("Открываю календарь"); return
        if "настройки" in t:
            app._nav_switch("settings"); self.speak("Открываю настройки"); return

        self.speak("Команда не распознана. Попробуйте ещё раз")

    def _find_task(self, query):
        if not query:
            return None
        # точное совпадение
        for task in self.app.tasks.values():
            if query in task.get("title","").lower():
                return task
        # нечёткое (первые слова)
        words = query.split()
        for task in self.app.tasks.values():
            title_w = task.get("title","").lower().split()
            if any(w in title_w for w in words):
                return task
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  Кольцо прогресса
# ═══════════════════════════════════════════════════════════════════════════
def make_ring_widget(size_dp=90, get_pct=None, thick_dp=7):
    fl   = FloatLayout(size_hint=(None,None), size=(S(size_dp),S(size_dp)))
    ring = Widget(size_hint=(1,1))
    lbl  = MDLabel(text="0%", font_style="Subtitle1", bold=True,
                   theme_text_color="Custom", text_color=C["accent"],
                   size_hint=(1,1), halign="center", valign="middle")
    N = 60
    def _redraw(w,*_):
        w.canvas.clear()
        pct = get_pct() if get_pct else 0.0
        cx  = w.x+w.width/2; cy = w.y+w.height/2
        R   = min(w.width,w.height)/2*0.78
        r   = S(thick_dp)/2
        n_fg = max(0, int(round(N*pct)))
        with w.canvas:
            for i in range(N):
                ang = math.radians(90-360*i/N)
                ex  = cx+R*math.cos(ang)-r
                ey  = cy+R*math.sin(ang)-r
                Color(*(C["accent"] if i<n_fg else C["acc_s"]))
                Ellipse(pos=(ex,ey), size=(r*2,r*2))
    ring.bind(pos=_redraw, size=_redraw)
    ring._redraw = _redraw
    fl.add_widget(ring); fl.add_widget(lbl)
    return fl, lbl, ring


# ═══════════════════════════════════════════════════════════════════════════
#  Мини-календарь
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
        self.height     = S(296)
        now = datetime.now()
        self.yr = now.year; self.mo = now.month
        self.sel = date.today()
        self._draw()

    def _draw(self):
        self.clear_widgets()
        hdr = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(42))
        pb = MDIconButton(icon="chevron-left", size_hint_x=None, width=S(38),
                          theme_text_color="Custom", text_color=C["text2"])
        nb = MDIconButton(icon="chevron-right", size_hint_x=None, width=S(38),
                          theme_text_color="Custom", text_color=C["text2"])
        pb.bind(on_release=self._prev); nb.bind(on_release=self._next)
        hdr.add_widget(pb)
        hdr.add_widget(MDLabel(text=f"{self.MONTH_NAMES[self.mo-1]} {self.yr}",
                               font_style="Subtitle1", bold=True, halign="center",
                               theme_text_color="Custom", text_color=C["text"]))
        hdr.add_widget(nb)
        self.add_widget(hdr)
        d_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(24))
        for d in self.DAY_NAMES:
            d_row.add_widget(MDLabel(text=d, font_style="Caption", halign="center",
                                     theme_text_color="Custom", text_color=C["text2"]))
        self.add_widget(d_row)
        grid = GridLayout(cols=7, size_hint_y=None, spacing=S(2))
        grid.bind(minimum_height=grid.setter("height"))
        first  = date(self.yr,self.mo,1)
        offset = first.weekday()
        n_days = cal_module.monthrange(self.yr,self.mo)[1]
        today  = date.today()
        for _ in range(offset):
            grid.add_widget(Widget(size_hint_y=None, height=S(32)))
        for d in range(1, n_days+1):
            cur      = date(self.yr,self.mo,d)
            is_today = (cur==today); is_sel = (cur==self.sel)
            ds       = cur.strftime("%d.%m.%Y"); has = ds in self.task_dates
            cell = FloatLayout(size_hint_y=None, height=S(32))
            bg_w = Widget(size_hint=(None,None), size=(S(28),S(28)),
                          pos_hint={"center_x":0.5,"center_y":0.5})
            bg_col = C["accent"] if is_today else (C["acc_s"] if is_sel else (0,0,0,0))
            def _draw_bg(w,*_,col=bg_col):
                w.canvas.clear()
                with w.canvas:
                    Color(*col); Ellipse(pos=w.pos, size=w.size)
            bg_w.bind(pos=_draw_bg, size=_draw_bg); cell.add_widget(bg_w)
            txt_col = C["surf"] if is_today else (C["accent"] if is_sel else C["text"])
            cell.add_widget(MDLabel(text=str(d), font_style="Caption",
                                     halign="center", valign="middle",
                                     theme_text_color="Custom", text_color=txt_col,
                                     size_hint=(1,1)))
            if has and not is_today and not is_sel:
                dot = Widget(size_hint=(None,None), size=(S(4),S(4)),
                             pos_hint={"center_x":0.5,"y":0.04})
                def _dd(w,*_):
                    w.canvas.clear()
                    with w.canvas:
                        Color(*C["accent"]); Ellipse(pos=w.pos, size=w.size)
                dot.bind(pos=_dd, size=_dd); cell.add_widget(dot)
            def _tap(w,t,dt=cur):
                if w.collide_point(*t.pos): self._pick(dt); return True
            cell.bind(on_touch_up=_tap); grid.add_widget(cell)
        self.add_widget(grid)

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
        row = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                          height=S(44), spacing=S(8))
        # чекбокс
        ico = "check-circle" if self.done else ("radiobox-blank" if is_fem else "checkbox-blank-outline")
        col = C["green"] if self.done else C["text2"]
        cb = MDIconButton(icon=ico, size_hint_x=None, width=S(34),
                          theme_text_color="Custom", text_color=col)
        cb.bind(on_release=self._toggle); row.add_widget(cb)

        # текст
        txt_col = C["text2"] if self.done else C["text"]
        ti = MDBoxLayout(orientation="vertical", spacing=S(1))
        title_lbl = MDLabel(text=self.title, font_style="Body1",
                            theme_text_color="Custom", text_color=txt_col)
        ti.add_widget(title_lbl)
        sub_parts = []
        if self.task_date: sub_parts.append(self.task_date)
        if self.time_str:  sub_parts.append(self.time_str)
        if self.show_cat and self.category: sub_parts.append(self.category)
        if sub_parts:
            ti.add_widget(MDLabel(text="  ".join(sub_parts),
                                   font_style="Caption", theme_text_color="Secondary"))
        row.add_widget(ti)

        # подзадачи — прогресс-бар справа
        if self.subtasks:
            dn = sum(1 for s in self.subtasks if s.get("done"))
            tot = len(self.subtasks)
            pct_sub = dn/tot if tot else 0
            sub_col = MDBoxLayout(orientation="vertical", size_hint_x=None,
                                   width=S(46), spacing=S(2))
            sub_col.add_widget(MDLabel(text=f"{dn}/{tot}", font_style="Caption",
                                        halign="center", theme_text_color="Custom",
                                        text_color=C["accent"]))
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
                tr.add_widget(MDLabel(text=ptxt,font_style="Caption",
                                       theme_text_color="Custom",text_color=pcol,valign="middle"))
                tag.add_widget(tr); tag_row.add_widget(tag); self.add_widget(tag_row)

    def _calc_h(self):
        is_fem=self._fem()
        h=S(44)+S(20)
        if is_fem and not self.done: h+=S(28)
        if self.subtasks: h+=S(4)
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
        self.app.save_tasks(); self.app.refresh_task_list()
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
        ci.add_widget(MDLabel(text=self.title, font_style="Body2",
                               theme_text_color="Secondary", halign="center",
                               size_hint_y=None, height=S(28)))
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

    def _show_menu(self, inst):
        from kivy.uix.modalview import ModalView
        W=S(188); IH=S(48)
        mv=ModalView(background_color=(0,0,0,0), auto_dismiss=True,
                     size_hint=(None,None), size=(W,IH*3+S(12)))
        card=MDCard(orientation="vertical", size_hint=(1,1),
                    radius=[S(12)], elevation=4, md_bg_color=C["surf"], padding=[S(4)])
        for ico,txt,col,cb in [
            ("eye-outline","Детали",C["text"],
             lambda: self.app.open_task_detail(self.task_id)),
            ("pencil-outline","Редактировать",C["accent"],
             lambda: self.app.open_task_form(self.task_id)),
            ("trash-can-outline","Удалить",C["red"],self._delete)]:
            row=MDBoxLayout(orientation="horizontal", spacing=S(6),
                            size_hint_y=None, height=IH)
            row.add_widget(MDIconButton(icon=ico, size_hint_x=None, width=S(34),
                                         theme_text_color="Custom", text_color=col))
            row.add_widget(MDLabel(text=txt, font_style="Body2",
                                   theme_text_color="Custom", text_color=col))
            def _up(w,t,_cb=cb):
                if row.collide_point(*t.pos):
                    mv.dismiss(); Clock.schedule_once(lambda *_: _cb(), 0.12); return True
            row.bind(on_touch_up=_up); card.add_widget(row)
        mv.add_widget(card)
        bx,by=inst.to_window(inst.x,inst.y)
        mv.pos=(max(S(4),bx-W-S(4)),
                max(S(4),min(by,Window.height-mv.height-S(4))))
        mv.open()

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
                        padding=[S(4),S(8),S(16),S(8)])
        back=MDIconButton(icon="chevron-left", size_hint_x=None, width=S(44),
                          theme_text_color="Custom", text_color=C["text2"])
        back.bind(on_release=lambda *_: self._cancel()); hdr.add_widget(back)
        hdr.add_widget(MDLabel(text="Новая задача" if not self._task_id else "Редактировать",
                               font_style="H6", bold=True, theme_text_color="Primary",
                               halign="center"))
        save_lbl=MDLabel(text="Сохранить", font_style="Body1",
                          theme_text_color="Custom", text_color=C["accent"],
                          halign="right", size_hint_x=None, width=S(90))
        def _ts(w,t):
            if save_lbl.collide_point(*t.pos): self._save(); return True
        save_lbl.bind(on_touch_up=_ts); hdr.add_widget(save_lbl)
        root.add_widget(hdr)
        sv=ScrollView()
        inn=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(0), padding=[S(16),S(14),S(16),S(30)])
        # Заголовок
        self.tf_title=MDTextField(hint_text="Что нужно сделать?",
                                   text=td.get("title",""),
                                   size_hint_y=None, height=S(54))
        inn.add_widget(self.tf_title)
        inn.add_widget(Widget(size_hint_y=None, height=S(12)))
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
            br2.add_widget(MDLabel(text=lbl_t, font_style="Caption",
                                   theme_text_color="Custom", text_color=tc, valign="middle"))
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
            "calendar-outline","Дата и время",date_disp or "Не выбрано",self._open_date_picker)
        p_inn.add_widget(r_dt); self._sep(p_inn)
        r_rem,self._remind_lbl=self._param_row(
            "bell-outline","Напоминание",self._remind_val or "Не выбрано",self._pick_reminder)
        p_inn.add_widget(r_rem); self._sep(p_inn)
        r_rep,self._repeat_lbl=self._param_row(
            "repeat","Повтор",self._repeat_val,self._pick_repeat)
        p_inn.add_widget(r_rep)
        params.add_widget(p_inn); inn.add_widget(params)
        inn.add_widget(Widget(size_hint_y=None, height=S(10)))
        # Заметка
        note_c=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(16),S(12)])
        note_c.bind(minimum_height=note_c.setter("height"))
        ni=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
        ni.add_widget(MDLabel(text="Заметка", font_style="Subtitle2",
                              theme_text_color="Custom", text_color=C["text"],
                              size_hint_y=None, height=S(22)))
        self.tf_note=MDTextField(hint_text="Добавить заметку...", text=td.get("comment",""),
                                  multiline=True, size_hint_y=None, height=S(72), mode="fill")
        ni.add_widget(self.tf_note); note_c.add_widget(ni); inn.add_widget(note_c)
        inn.add_widget(Widget(size_hint_y=None, height=S(10)))
        # Подзадачи
        sub_c=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                     md_bg_color=C["surf"], padding=[S(16),S(12)])
        sub_c.bind(minimum_height=sub_c.setter("height"))
        s_inn=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
        s_hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(32))
        s_hdr.add_widget(MDLabel(text="Подзадачи", font_style="Subtitle2",
                                  theme_text_color="Custom", text_color=C["text"]))
        add_s=MDIconButton(icon="plus-circle-outline", size_hint_x=None, width=S(36),
                            theme_text_color="Custom", text_color=C["accent"])
        add_s.bind(on_release=lambda *_: self._add_sub_dialog())
        s_hdr.add_widget(add_s); s_inn.add_widget(s_hdr)
        self._sub_rows=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(2))
        for sub in self._subtasks:
            self._add_sub_widget(sub.get("title",""), sub.get("done",False))
        s_inn.add_widget(self._sub_rows); sub_c.add_widget(s_inn); inn.add_widget(sub_c)
        inn.add_widget(Widget(size_hint_y=None, height=S(16)))
        save_btn=MDRaisedButton(text="Сохранить задачу", size_hint_y=None, height=S(52),
                                 elevation=0, md_bg_color=C["accent"])
        save_btn.bind(on_release=lambda *_: self._save()); inn.add_widget(save_btn)
        sv.add_widget(inn); root.add_widget(sv); self.add_widget(root)

    def _lbl(self, text):
        return MDLabel(text=text, font_style="Caption",
                       theme_text_color="Custom", text_color=C["text2"],
                       size_hint_y=None, height=S(24))

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
        ci.add_widget(MDLabel(text=name, font_style="Caption",
                              theme_text_color="Custom", text_color=tc,
                              halign="center", size_hint_y=None, height=S(22)))
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
        row.add_widget(MDLabel(text=label, font_style="Body1", theme_text_color="Primary"))
        val_lbl=MDLabel(text=value, font_style="Body2",
                        theme_text_color="Secondary", halign="right",
                        size_hint_x=None, width=S(128))
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

    def _show_picker(self, title, opts, cur, lbl, setter):
        from kivy.uix.modalview import ModalView
        mv=ModalView(background_color=(0,0,0,0.5), auto_dismiss=True, size_hint=(0.88,None))
        card=MDCard(orientation="vertical", size_hint_y=None,
                    height=S(len(opts)*52+20), radius=[S(16)], elevation=6,
                    md_bg_color=C["surf"], padding=[S(6),S(8)])
        for opt in opts:
            row=MDBoxLayout(size_hint_y=None, height=S(50), padding=[S(16),0])
            row.add_widget(MDLabel(text=opt, font_style="Body1",
                                   theme_text_color="Custom",
                                   text_color=C["accent"] if opt==cur else C["text"]))
            def _sel(w,t,o=opt):
                if row.collide_point(*t.pos):
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
        row.add_widget(MDLabel(text=title, font_style="Body2",
                               theme_text_color="Custom", text_color=C["text"]))
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
        title=self.tf_title.text.strip()
        if not title: self.tf_title.hint_text="Введите название!"; return
        data={"title":title,"comment":self.tf_note.text.strip(),
              "category":self._sel_cat,"priority":self._sel_prio,
              "date":self._date_val,"time":self._time_val,
              "reminder":self._remind_val,"repeat":self._repeat_val,
              "subtasks":self._subtasks}
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
        hdr.add_widget(MDLabel(text="Задача", font_style="H6", bold=True,
                               theme_text_color="Primary", halign="center"))
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
        ti.add_widget(MDLabel(text=td.get("title",""), font_style="H6", bold=True,
                              theme_text_color="Custom", text_color=C["text"],
                              size_hint_y=None, height=S(34)))
        cat=td.get("category","")
        if cat:
            ti.add_widget(MDLabel(text=f"  {CAT_EMOJI.get(cat,'')} {cat}",
                                   font_style="Caption",
                                   theme_text_color="Custom", text_color=C["accent"],
                                   size_hint_y=None, height=S(22)))
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
        pr_row.add_widget(MDLabel(text="Приоритет", font_style="Body1",
                                   theme_text_color="Primary"))
        pb=MDCard(size_hint=(None,None), size=(S(80),S(26)), radius=[S(13)], elevation=0,
                  md_bg_color=(*pcol[:3],0.15))
        pb.add_widget(MDLabel(text=prio, font_style="Caption", halign="center",
                               valign="middle", theme_text_color="Custom", text_color=pcol))
        pr_row.add_widget(pb); pi.add_widget(pr_row); self._sep(pi)
        self._det_row(pi,"repeat","Повтор",td.get("repeat","") or "Не повторять")
        pc.add_widget(pi); inn.add_widget(pc)
        note=td.get("comment","")
        if note:
            nc=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(16),S(12)])
            nc.bind(minimum_height=nc.setter("height"))
            ni=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
            ni.add_widget(MDLabel(text="Заметка", font_style="Subtitle2",
                                   theme_text_color="Custom", text_color=C["text"],
                                   size_hint_y=None, height=S(22)))
            ni.add_widget(MDLabel(text=note, font_style="Body2",
                                   theme_text_color="Custom", text_color=C["text2"],
                                   size_hint_y=None,
                                   height=S(max(40,len(note)//36*22+22))))
            nc.add_widget(ni); inn.add_widget(nc)
        subs=td.get("subtasks",[])
        if subs:
            sc=MDCard(size_hint_y=None, radius=[S(16)], elevation=0,
                      md_bg_color=C["surf"], padding=[S(16),S(12)])
            sc.bind(minimum_height=sc.setter("height"))
            si=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(4))
            dn_c=sum(1 for s in subs if s.get("done"))
            si.add_widget(MDLabel(text=f"Подзадачи  {dn_c}/{len(subs)}",
                                   font_style="Subtitle2",
                                   theme_text_color="Custom", text_color=C["text"],
                                   size_hint_y=None, height=S(28)))
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
                srow.add_widget(MDLabel(text=sub.get("title",""), font_style="Body2",
                                        theme_text_color="Custom",
                                        text_color=C["text2"] if sub.get("done") else C["text"]))
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
        row.add_widget(MDLabel(text=label, font_style="Body1", theme_text_color="Primary"))
        row.add_widget(MDLabel(text=value, font_style="Body2",
                               theme_text_color="Secondary",
                               halign="right", size_hint_x=None, width=S(140)))
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
class DailyTodoApp(MDApp):

    def build(self):
        self.theme_cls.theme_style     = "Light"
        self.theme_cls.primary_palette = "Pink"
        self.store      = JsonStore("tasks.json")
        self.cfg_store  = JsonStore("config.json")
        self.tasks      = {}
        self.categories = ["Работа","Дом","Личное","Покупки","Тренировки"]
        self.cur_cat    = "Работа"
        self.sel_date   = datetime.now().strftime("%d.%m.%Y")
        self.filter_date = False
        self.show_done   = True
        self.cur_tab     = "tasks"
        self._cal_sel    = date.today()
        self.user_name   = ""
        self.theme_name  = "Роза"
        self._save_ev    = None
        self._ref_ev     = None
        self._ring_pct   = 0.0
        self.weekly_goal = 80       # цель на неделю %
        self.mood_history = {}      # {"DD.MM.YYYY": 1-5}
        self._voice      = VoiceAssistant(self)
        self._cal_view_mode = "month"   # "month" | "day"

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
        card.add_widget(MDLabel(text=text, font_style="Body1",
                                theme_text_color="Custom", text_color=(1,1,1,1),
                                halign="center", valign="middle"))
        mv.add_widget(card); mv.open()
        Clock.schedule_once(lambda *_: mv.dismiss(), 2.5)

    # ── Голосовой помощник — кнопка ─────────────────────────────────────────
    def _start_voice(self, *_):
        self._show_toast("\U0001f3a4 Слушаю...")
        self._voice.start_listening(self._on_voice_result)

    def _on_voice_result(self, text):
        self._voice.process_command(text)

    # ── Повторяющиеся задачи ─────────────────────────────────────────────────
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
        ci.add_widget(MDLabel(text="Flow\u00b7Do", font_style="H4", bold=True,
                               theme_text_color="Custom", text_color=C["accent"],
                               halign="center", size_hint_y=None, height=S(52)))
        self._w_quote=MDLabel(text=random.choice(MOTIVATIONS_F),
                               font_style="Subtitle2", theme_text_color="Secondary",
                               halign="center", size_hint_y=None, height=S(42))
        ci.add_widget(self._w_quote)
        ci.add_widget(MDLabel(text="Выберите стиль:", font_style="Caption",
                               theme_text_color="Secondary", size_hint_y=None, height=S(20)))
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
        ci.add_widget(MDLabel(text="Ваше имя:", font_style="Caption",
                               theme_text_color="Secondary", size_hint_y=None, height=S(20)))
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
        # кнопки: активная — accent, неактивная — surf2
        self._wg_fem.md_bg_color = C["accent"] if g=="female" else C["surf2"]
        self._wg_mal.md_bg_color = C["accent"] if g=="male"   else C["surf2"]
        # текст кнопок
        try:
            self._wg_fem.children[0].text_color = (1,1,1,1) if g=="female" else C["text"]
            self._wg_mal.children[0].text_color = (1,1,1,1) if g=="male"   else C["text"]
        except Exception:
            pass
        self._w_quote.text = random.choice(MOTIVATIONS_M if g=="male" else MOTIVATIONS_F)

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
        self._fab.add_widget(MDLabel(text="+", font_style="H5", bold=True,
                                      halign="center", valign="middle",
                                      theme_text_color="Custom", text_color=(1,1,1,1)))
        def _ft(w,t):
            if self._fab.collide_point(*t.pos): self.open_task_form(); return True
        self._fab.bind(on_touch_up=_ft); root.add_widget(self._fab)

        # Кнопка голосового помощника — левый нижний угол
        self._voice_btn=MDCard(size_hint=(None,None), size=(S(48),S(48)),
                                radius=[S(24)], elevation=6,
                                md_bg_color=C["surf2"],
                                pos_hint={"x":0.04,"y":0.10})
        self._voice_btn.add_widget(MDIconButton(
            icon="microphone", size_hint=(1,1),
            theme_text_color="Custom", text_color=C["accent"]))
        def _vt(w,t):
            if self._voice_btn.collide_point(*t.pos): self._start_voice(); return True
        self._voice_btn.bind(on_touch_up=_vt); root.add_widget(self._voice_btn)

        sc.add_widget(root); self.sm.add_widget(sc)
        self._pg_tasks    = self._mk_tasks_page()
        self._pg_calendar = self._mk_calendar_page()
        self._pg_stats    = self._mk_stats_page()
        self._pg_settings = self._mk_settings_page()
        self.pages.add_widget(self._pg_tasks)
        self.cur_tab="tasks"; self._nav_update("tasks")
        Clock.schedule_once(self.load_tasks, 0.2)

    # ── Топбар ──────────────────────────────────────────────────────────────
    def _make_topbar(self):
        is_fem=self._is_fem()
        now=datetime.now(); h=now.hour
        greet="Доброе утро," if h<12 else ("Добрый день," if h<18 else "Добрый вечер,")
        tb=MDBoxLayout(orientation="vertical", size_hint_y=None,
                       md_bg_color=C["surf"],
                       height=S(104) if is_fem else S(88),
                       padding=[S(18),S(10),S(14),S(6)])
        if is_fem:
            r1=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(26))
            r1.add_widget(MDLabel(text=greet, font_style="Caption",
                                   theme_text_color="Custom", text_color=C["text2"]))
            av=MDIconButton(icon="account-circle-outline", size_hint=(None,None),
                            size=(S(36),S(36)), theme_text_color="Custom", text_color=C["accent"])
            av.bind(on_release=lambda *_: self._nav_switch("settings"))
            r1.add_widget(av); tb.add_widget(r1)
            self._tb_name=MDLabel(text=f"{self.user_name} \U0001f495",
                                   font_style="H5", bold=True,
                                   theme_text_color="Custom", text_color=C["accent"],
                                   size_hint_y=None, height=S(44))
            tb.add_widget(self._tb_name)
            self._tb_date=MDLabel(text=self._fmt_date(now), font_style="Caption",
                                   theme_text_color="Custom", text_color=C["text2"],
                                   size_hint_y=None, height=S(20))
            tb.add_widget(self._tb_date)
        else:
            r1=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(30))
            r1.add_widget(MDIconButton(icon="menu", size_hint_x=None, width=S(36),
                                        theme_text_color="Custom", text_color=C["text2"]))
            r1.add_widget(Widget())
            bell=MDIconButton(icon="bell-outline", size_hint_x=None, width=S(36),
                              theme_text_color="Custom", text_color=C["text2"])
            r1.add_widget(bell); tb.add_widget(r1)
            self._tb_name=MDLabel(text="СЕГОДНЯ", font_style="H6", bold=True,
                                   theme_text_color="Primary",
                                   size_hint_y=None, height=S(34))
            tb.add_widget(self._tb_name)
            self._tb_date=MDLabel(text=self._fmt_date(now), font_style="Caption",
                                   theme_text_color="Secondary",
                                   size_hint_y=None, height=S(20))
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
        self.cur_tab=tab; self._nav_update(tab)
        self.pages.clear_widgets()
        pg={"tasks":self._pg_tasks,"calendar":self._pg_calendar,
            "stats":self._pg_stats,"settings":self._pg_settings}[tab]
        self.pages.add_widget(pg)
        if tab=="stats":   Clock.schedule_once(lambda *_: self._refresh_stats(), 0.05)
        if tab=="calendar":Clock.schedule_once(lambda *_: self._refresh_cal(), 0.05)
        if tab=="settings":Clock.schedule_once(lambda *_: self._rebuild_cats_list(), 0.05)
        # скрыть/показать FAB и голос
        fab_vis = (tab=="tasks" or tab=="calendar")
        self._fab.opacity    = 1 if fab_vis else 0
        self._voice_btn.opacity = 1

    # ════════════════════════════════════════════════════════════════════════
    #  СТРАНИЦА: ЗАДАЧИ
    # ════════════════════════════════════════════════════════════════════════
    def _mk_tasks_page(self):
        """
        Архитектура:
          FloatLayout
            ├─ ScrollView (size_hint 1,1)  ← весь контент, включая шапку
            │    └─ inn (adaptive_height)
            │         ├─ _scroll_header  (задача дня + категории)  [скроллится]
            │         ├─ фильтры
            │         └─ task_list
            └─ _sticky_header  (копия шапки, position top, hidden по умолчанию)
                               ← появляется при прокрутке ВНИЗ, исчезает при возврате

        При прокрутке вверх sticky мгновенно прячется — и видна оригинальная шапка.
        При прокрутке вниз (шапка ушла вверх за экран) sticky плавно появляется.
        """
        is_fem=self._is_fem()
        HEADER_H = S(138)   # высота шапки (задача дня S(96) + категории S(42))

        fl = FloatLayout()

        # ════════════════════════════════════════════════════════════════
        # 1. Один ScrollView — ВСЁ прокручивается
        # ════════════════════════════════════════════════════════════════
        sv = ScrollView(size_hint=(1,1))
        inn = MDBoxLayout(orientation="vertical", adaptive_height=True,
                          spacing=S(8), padding=[S(12),S(8),S(12),S(80)])
        sv.add_widget(inn)

        # ── Шапка внутри скролла ─────────────────────────────────────
        self._scroll_header = MDBoxLayout(orientation="vertical",
                                          size_hint_y=None, height=HEADER_H)

        # — Задача дня —
        day_c = MDCard(size_hint_y=None, height=S(96),
                       radius=[S(18)] if is_fem else [S(10)],
                       elevation=2 if is_fem else 0,
                       md_bg_color=C["surf"], padding=[S(16),S(14)])
        dc = MDBoxLayout(orientation="horizontal", spacing=S(12))
        di = MDBoxLayout(orientation="vertical", spacing=S(4))
        di.add_widget(MDLabel(text="\u2b50 Задача дня", font_style="Caption",
                               theme_text_color="Custom", text_color=C["text2"],
                               size_hint_y=None, height=S(18)))
        self._day_task_lbl = MDLabel(text="Загрузка...", font_style="Subtitle1",
                                     bold=True, theme_text_color="Custom",
                                     text_color=C["text"], size_hint_y=None, height=S(30))
        di.add_widget(self._day_task_lbl)
        self._day_task_sub = MDLabel(text="", font_style="Caption",
                                     theme_text_color="Custom", text_color=C["text2"],
                                     size_hint_y=None, height=S(20))
        di.add_widget(self._day_task_sub); dc.add_widget(di)

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
        prog_box.add_widget(self._pct_lbl); dc.add_widget(prog_box)
        day_c.add_widget(dc)
        self._scroll_header.add_widget(day_c)

        # — Категории —
        cat_sv = ScrollView(size_hint_y=None, height=S(42), do_scroll_y=False)
        self.cat_bar = MDBoxLayout(orientation="horizontal", size_hint_x=None,
                                   spacing=S(8), padding=[S(14),S(4),S(14),S(4)])
        self.cat_bar.bind(minimum_width=self.cat_bar.setter("width"))
        self._cat_btns = {}
        for cat in self.categories:
            b = self._mk_cat_btn(cat); self._cat_btns[cat]=b; self.cat_bar.add_widget(b)
        gear = MDRaisedButton(text="", size_hint_x=None, width=S(36),
                              size_hint_y=None, height=S(32), elevation=0,
                              md_bg_color=C["surf2"])
        gear.add_widget(MDIconButton(icon="cog-outline", size_hint=(1,1),
                                     theme_text_color="Custom", text_color=C["text2"]))
        gear.bind(on_release=self._manage_cats)
        self.cat_bar.add_widget(gear)
        cat_sv.add_widget(self.cat_bar)
        self._scroll_header.add_widget(cat_sv)
        inn.add_widget(self._scroll_header)

        # ── Фильтры ──────────────────────────────────────────────────
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

        # ── Список задач ──────────────────────────────────────────────
        self.task_list = MDBoxLayout(orientation="vertical", adaptive_height=True,
                                     spacing=S(10) if is_fem else S(6))
        inn.add_widget(self.task_list)
        fl.add_widget(sv)

        # ════════════════════════════════════════════════════════════════
        # 2. Sticky-шапка — Float поверх, появляется при прокрутке вниз
        # ════════════════════════════════════════════════════════════════
        self._tasks_header = MDBoxLayout(
            orientation="vertical", size_hint=(1, None), height=HEADER_H,
            pos_hint={"top": 1}, opacity=0)
        with self._tasks_header.canvas.before:
            Color(*C["bg"]); _hbg = Rectangle(size=(Window.width, HEADER_H), pos=(0,0))
        def _upd_hbg(w,*_):
            _hbg.size=(w.width, HEADER_H); _hbg.pos=(w.x, w.y)
        self._tasks_header.bind(pos=_upd_hbg, size=_upd_hbg)

        # — Задача дня (sticky-копия меток, не дублируем виджеты — просто рамка) —
        sticky_day = MDCard(size_hint_y=None, height=S(96),
                            radius=[S(18)] if is_fem else [S(10)],
                            elevation=4, md_bg_color=C["surf"],
                            padding=[S(16),S(14)])
        sticky_dc = MDBoxLayout(orientation="horizontal", spacing=S(12))
        sticky_di = MDBoxLayout(orientation="vertical", spacing=S(4))
        sticky_di.add_widget(MDLabel(text="\u2b50 Задача дня", font_style="Caption",
                                      theme_text_color="Custom", text_color=C["text2"],
                                      size_hint_y=None, height=S(18)))
        self._sticky_task_lbl = MDLabel(text="", font_style="Subtitle1", bold=True,
                                         theme_text_color="Custom", text_color=C["text"],
                                         size_hint_y=None, height=S(30))
        sticky_di.add_widget(self._sticky_task_lbl)
        self._sticky_task_sub = MDLabel(text="", font_style="Caption",
                                         theme_text_color="Custom", text_color=C["text2"],
                                         size_hint_y=None, height=S(20))
        sticky_di.add_widget(self._sticky_task_sub)
        sticky_dc.add_widget(sticky_di)
        # правая часть — просто процент
        self._sticky_pct = MDLabel(text="0%", font_style="Subtitle2", bold=True,
                                    halign="center", theme_text_color="Custom",
                                    text_color=C["accent"],
                                    size_hint_x=None, width=S(56))
        sticky_dc.add_widget(self._sticky_pct)
        sticky_day.add_widget(sticky_dc)
        self._tasks_header.add_widget(sticky_day)

        # — Категории (sticky-полоска, та же cat_bar через proxy) —
        sticky_cat_sv = ScrollView(size_hint_y=None, height=S(42), do_scroll_y=False)
        self._sticky_cat_bar = MDBoxLayout(orientation="horizontal", size_hint_x=None,
                                            spacing=S(8), padding=[S(14),S(4),S(14),S(4)])
        self._sticky_cat_bar.bind(minimum_width=self._sticky_cat_bar.setter("width"))
        # Клоны кнопок категорий — нажатие работает через оригинальный _switch_cat
        for cat in self.categories:
            b = self._mk_cat_btn(cat)
            self._sticky_cat_bar.add_widget(b)
        sticky_cat_sv.add_widget(self._sticky_cat_bar)
        self._tasks_header.add_widget(sticky_cat_sv)
        fl.add_widget(self._tasks_header)

        # ════════════════════════════════════════════════════════════════
        # 3. Логика показа/скрытия sticky по скроллу
        # ════════════════════════════════════════════════════════════════
        self._last_scroll_y = 1.0

        def _on_scroll(sv_inst, scroll_y):
            # scroll_y: 1.0 = самый верх, 0.0 = самый низ
            going_up   = scroll_y > self._last_scroll_y
            going_down = scroll_y < self._last_scroll_y
            self._last_scroll_y = scroll_y

            # Считаем, ушла ли оригинальная шапка за край экрана.
            # Высота контента и вьюпорта:
            content_h  = inn.height
            viewport_h = sv_inst.height
            scrollable = max(content_h - viewport_h, 1)
            # pixels прокручено от верха:
            scrolled_px = (1.0 - scroll_y) * scrollable

            header_gone = scrolled_px > HEADER_H  # шапка ушла с экрана

            if going_up:
                # Прокрутка ВВЕРХ — немедленно прячем sticky
                from kivy.animation import Animation
                Animation.cancel_all(self._tasks_header, "opacity")
                self._tasks_header.opacity = 0
            elif going_down and header_gone:
                # Прокрутка ВНИЗ и шапка за экраном — плавно показываем sticky
                from kivy.animation import Animation
                if self._tasks_header.opacity < 1:
                    Animation(opacity=1, d=0.18, t="out_quad").start(self._tasks_header)
            # Синхронизируем тексты sticky с оригиналом
            if hasattr(self, "_sticky_task_lbl"):
                self._sticky_task_lbl.text = self._day_task_lbl.text
                self._sticky_task_sub.text = self._day_task_sub.text
                self._sticky_pct.text      = self._day_pct_lbl.text

        sv.bind(scroll_y=_on_scroll)

        # Обёртка страницы
        pg = MDBoxLayout(orientation="vertical")
        pg.add_widget(fl)
        return pg

    def _mk_cat_btn(self, cat):
        is_fem=self._is_fem(); sel=(cat==self.cur_cat)
        em=CAT_EMOJI.get(cat,"")
        txt=f"{em} {cat}" if (is_fem and em) else cat
        w=max(S(80), S(7)*len(txt)+S(36))
        bg=C["accent"] if sel else C["surf2"]
        tc=(1,1,1,1) if sel else C["text"]
        rad=S(16) if is_fem else S(8)
        card=MDCard(size_hint_x=None, width=w, size_hint_y=None, height=S(32),
                    radius=[rad], elevation=0, md_bg_color=bg)
        lbl=MDLabel(text=txt, font_style="Caption", bold=sel,
                    halign="center", valign="middle",
                    theme_text_color="Custom", text_color=tc, size_hint=(1,1))
        card._lbl=lbl; card.add_widget(lbl)
        def _tap(w,t):
            if card.collide_point(*t.pos): self._switch_cat(cat); return True
        card.bind(on_touch_up=_tap)
        return card

    def _update_cat_colors(self):
        for c,b in self._cat_btns.items():
            sel=(c==self.cur_cat)
            b.md_bg_color=C["accent"] if sel else C["surf2"]
            if hasattr(b,"_lbl"):
                b._lbl.text_color=(1,1,1,1) if sel else C["text"]
                b._lbl.bold=sel

    def _switch_cat(self, c):
        self.cur_cat=c; self._update_cat_colors(); self.refresh_task_list()

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
        cal_card=MDCard(size_hint_y=None, height=S(294),
                        radius=[S(14)] if is_fem else [S(8)],
                        elevation=1 if is_fem else 0,
                        md_bg_color=C["surf"], padding=[S(8),S(6)])
        task_dates={t.get("date","") for t in self.tasks.values()}
        self.cal_w=CalendarWidget(on_select=self._on_cal_select, task_dates=task_dates)
        cal_card.add_widget(self.cal_w); inn.add_widget(cal_card)
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
                slot.add_widget(MDLabel(text=h, font_style="Caption",
                                        theme_text_color="Custom", text_color=C["text2"],
                                        size_hint_x=None, width=S(44),
                                        halign="right", valign="middle"))
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
                               md_bg_color=C["acc_s"] if not t.get("done") else C["surf2"],
                               padding=[S(12),S(8)])
                    row2=MDBoxLayout(orientation="horizontal")
                    row2.add_widget(MDLabel(text=t.get("title",""), font_style="Body2",
                                            theme_text_color="Custom",
                                            text_color=C["text2"] if t.get("done") else C["text"]))
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
                    slot.add_widget(MDLabel(text=t["time"], font_style="Caption",
                                            theme_text_color="Custom", text_color=C["text2"],
                                            size_hint_x=None, width=S(44),
                                            halign="right", valign="middle"))
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
                    tc2.add_widget(MDLabel(text=t.get("title",""), font_style="Body2",
                                           theme_text_color="Custom",
                                           text_color=C["text2"] if t.get("done") else C["text"]))
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
        hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(54), md_bg_color=C["surf"], padding=[S(16),S(10)])
        hdr.add_widget(MDLabel(text="Статистика", font_style="H6",
                                bold=True, theme_text_color="Primary"))
        hdr.add_widget(Widget())
        self._stat_period="week"; self._sp_btns={}
        pr=MDBoxLayout(orientation="horizontal", spacing=S(4),
                       size_hint_x=None, width=S(216))
        for txt,val in [("Неделя","week"),("Месяц","month"),("Всё","all")]:
            sel=(val=="week")
            btn=MDCard(size_hint_y=None, height=S(28), size_hint_x=None, width=S(70),
                       radius=[S(14)], elevation=0,
                       md_bg_color=C["accent"] if sel else C["surf2"])
            sp_lbl=MDLabel(text=txt, font_style="Caption",
                           halign="center", valign="middle",
                           theme_text_color="Custom",
                           text_color=(1,1,1,1) if sel else C["text"])
            btn._lbl=sp_lbl; btn.add_widget(sp_lbl)
            def _sp(w,t,v=val):
                if w.collide_point(*t.pos):
                    self._stat_period=v
                    for kk,bb in self._sp_btns.items():
                        s2=(kk==v)
                        bb.md_bg_color=C["accent"] if s2 else C["surf2"]
                        if hasattr(bb,"_lbl"):
                            bb._lbl.text_color=(1,1,1,1) if s2 else C["text"]
                    self._refresh_stats(); return True
            btn.bind(on_touch_up=_sp); self._sp_btns[val]=btn; pr.add_widget(btn)
        hdr.add_widget(pr); pg.add_widget(hdr)

        sv=ScrollView()
        inn=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(12), padding=[S(14),S(12),S(14),S(20)])
        sv.add_widget(inn)

        # Главная карточка
        mc=MDCard(size_hint_y=None, height=S(196),
                  radius=[S(18)] if is_fem else [S(12)],
                  elevation=2 if is_fem else 0, md_bg_color=C["surf"], padding=[S(16),S(14)])
        mc_in=MDBoxLayout(orientation="vertical", spacing=S(8))
        top=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(94))
        lc=MDBoxLayout(orientation="vertical", spacing=S(4))
        self._sd_lbl=MDLabel(text="0", font_style="H3", bold=True,
                              theme_text_color="Primary", size_hint_y=None, height=S(50))
        self._sf_lbl=MDLabel(text="выполнено из 0", font_style="Caption",
                              theme_text_color="Secondary", size_hint_y=None, height=S(20))
        self._sp_badge=MDLabel(text="0%", font_style="Caption", bold=True,
                                theme_text_color="Custom", text_color=C["accent"],
                                size_hint_y=None, height=S(18))
        lc.add_widget(self._sd_lbl); lc.add_widget(self._sf_lbl)
        lc.add_widget(self._sp_badge); top.add_widget(lc)
        ring_fl,self._ring_pct_lbl,self._ring_w=make_ring_widget(
            size_dp=92, get_pct=lambda: self._ring_pct, thick_dp=7)
        top.add_widget(ring_fl); mc_in.add_widget(top)
        mc_in.add_widget(MDLabel(text="Продуктивность", font_style="Caption",
                                  theme_text_color="Secondary", size_hint_y=None, height=S(18)))
        self._bars_box=MDBoxLayout(orientation="horizontal", spacing=S(5),
                                    size_hint_y=None, height=S(66))
        mc_in.add_widget(self._bars_box); mc.add_widget(mc_in); inn.add_widget(mc)

        # Мини-карточки
        mini_r=MDBoxLayout(orientation="horizontal", spacing=S(12),
                            size_hint_y=None, height=S(96))
        def _mini(ico_txt, title, sub, attr):
            c=MDCard(radius=[S(14)] if is_fem else [S(10)],
                     elevation=1 if is_fem else 0,
                     md_bg_color=C["surf"], padding=[S(14),S(10)])
            ci=MDBoxLayout(orientation="vertical", spacing=S(2))
            ci.add_widget(MDLabel(text=ico_txt, font_style="H5", size_hint_y=None, height=S(34)))
            ci.add_widget(MDLabel(text=title, font_style="Caption",
                                   theme_text_color="Secondary", size_hint_y=None, height=S(18)))
            lbl=MDLabel(text="0", font_style="H5", bold=True,
                        theme_text_color="Primary", size_hint_y=None, height=S(30))
            setattr(self,attr,lbl); ci.add_widget(lbl)
            ci.add_widget(MDLabel(text=sub, font_style="Caption",
                                   theme_text_color="Secondary", size_hint_y=None, height=S(14)))
            c.add_widget(ci); return c
        mini_r.add_widget(_mini("\U0001f525","Серия","дней","_s_streak"))
        mini_r.add_widget(_mini("\u2705","Всего задач","в месяце","_s_total"))
        inn.add_widget(mini_r)

        # Цель на неделю
        gc=MDCard(size_hint_y=None, height=S(96),
                  radius=[S(18)] if is_fem else [S(12)],
                  elevation=1 if is_fem else 0,
                  md_bg_color=C["surf"], padding=[S(16),S(12)])
        gi=MDBoxLayout(orientation="vertical", spacing=S(6))
        gh=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(24))
        gh.add_widget(MDLabel(text="ЦЕЛЬ НА НЕДЕЛЮ", font_style="Caption",
                               theme_text_color="Custom", text_color=C["text2"]))
        gh.add_widget(Widget())
        self._goal_pct_lbl=MDLabel(text=f"{self.weekly_goal}%", font_style="Caption",
                                    theme_text_color="Custom", text_color=C["accent"],
                                    size_hint_x=None, width=S(36), halign="right")
        gh.add_widget(self._goal_pct_lbl)
        # кнопки изменения цели
        minus_b=MDIconButton(icon="minus", size_hint_x=None, width=S(30),
                             theme_text_color="Custom", text_color=C["text2"])
        plus_b =MDIconButton(icon="plus",  size_hint_x=None, width=S(30),
                             theme_text_color="Custom", text_color=C["text2"])
        def _chg_goal(delta):
            self.weekly_goal=max(10,min(100,self.weekly_goal+delta))
            if hasattr(self,"_goal_pct_lbl"):
                self._goal_pct_lbl.text=f"{self.weekly_goal}%"
            self._refresh_stats()
        minus_b.bind(on_release=lambda *_: _chg_goal(-5))
        plus_b.bind(on_release=lambda *_: _chg_goal(5))
        gh.add_widget(minus_b); gh.add_widget(plus_b)
        gi.add_widget(gh)
        gi.add_widget(MDLabel(text=f"Выполнить {self.weekly_goal}% задач",
                               font_style="Caption", theme_text_color="Secondary",
                               size_hint_y=None, height=S(16)))
        self._goal_prog=Widget(size_hint_y=None, height=S(10))
        self._goal_fill=0.0
        def _dgp(w,*_):
            w.canvas.clear()
            with w.canvas:
                Color(*C["surf2"])
                RoundedRectangle(pos=(w.x,w.y), size=(w.width,w.height), radius=[S(5)])
                if self._goal_fill>0:
                    fill=min(1.0,self._goal_fill/(self.weekly_goal/100))
                    Color(*C["accent"])
                    RoundedRectangle(pos=(w.x,w.y),
                                     size=(max(w.width*fill,S(10)),w.height),
                                     radius=[S(5)])
        self._goal_prog.bind(pos=_dgp, size=_dgp)
        self._draw_goal=_dgp; gi.add_widget(self._goal_prog)
        gc.add_widget(gi); inn.add_widget(gc)

        # Трекер настроения
        if is_fem:
            mood_c=MDCard(size_hint_y=None, radius=[S(14)], elevation=1,
                          md_bg_color=C["surf"], padding=[S(16),S(12)])
            mood_c.bind(minimum_height=mood_c.setter("height"))
            mood_in=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(6))
            mood_in.add_widget(MDLabel(text="Как твоё настроение сегодня?",
                                        font_style="Subtitle2", bold=True,
                                        theme_text_color="Primary",
                                        size_hint_y=None, height=S(26)))
            mood_r=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(44))
            today_s=date.today().strftime("%d.%m.%Y")
            cur_mood=self.mood_history.get(today_s,0)
            self._mood_btns=[]
            for i,face in enumerate(MOOD_FACES):
                lbl2=MDLabel(text=face, font_style="H5",
                             halign="center", valign="middle", size_hint_x=0.2)
                lbl2._mv=i+1
                if i+1==cur_mood: lbl2.theme_text_color="Custom"; lbl2.text_color=C["accent"]
                lbl2.bind(on_touch_up=lambda w,t,v=i+1:
                          self._pick_mood_stat(v) if w.collide_point(*t.pos) else None)
                self._mood_btns.append(lbl2); mood_r.add_widget(lbl2)
            mood_in.add_widget(mood_r)
            # история настроения — мини-график последних 7 дней
            hist_r=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(32),
                               spacing=S(4))
            for i in range(6,-1,-1):
                d2=date.today()-timedelta(days=i)
                ds2=d2.strftime("%d.%m.%Y")
                mv=self.mood_history.get(ds2,0)
                col=MDBoxLayout(orientation="vertical", spacing=S(2))
                face_lbl=MDLabel(text=MOOD_FACES[mv-1] if mv else "·",
                                  font_style="Caption", halign="center")
                col.add_widget(face_lbl); hist_r.add_widget(col)
            mood_in.add_widget(hist_r)
            mood_c.add_widget(mood_in); inn.add_widget(mood_c)
        else:
            self._mood_btns=[]

        # Мотивация
        mot=MDCard(size_hint_y=None, height=S(78) if not is_fem else S(56),
                   radius=[S(12)], elevation=0,
                   md_bg_color=C["surf"], padding=[S(16),S(12)])
        mi=MDBoxLayout(orientation="vertical", spacing=S(4))
        if is_fem:
            self._motiv_lbl=MDLabel(text="Ты сегодня молодец! \U0001f496",
                                     font_style="Subtitle2", bold=True,
                                     theme_text_color="Primary", size_hint_y=None, height=S(26))
            self._motiv_sub=MDLabel(text="Уже выполнено 0 дел",
                                     font_style="Caption", theme_text_color="Secondary",
                                     size_hint_y=None, height=S(18))
            mi.add_widget(self._motiv_lbl); mi.add_widget(self._motiv_sub)
        else:
            self._motiv_lbl=MDLabel(text="ДИСЦИПЛИНА СЕГОДНЯ \u2014",
                                     font_style="H6", bold=True,
                                     theme_text_color="Primary", size_hint_y=None, height=S(30))
            mi.add_widget(self._motiv_lbl)
            mi.add_widget(MDLabel(text="РЕЗУЛЬТАТ ЗАВТРА", font_style="H6", bold=True,
                                   theme_text_color="Custom", text_color=C["accent"],
                                   size_hint_y=None, height=S(30)))
            self._motiv_sub=MDLabel(text="", size_hint_y=None, height=S(1))
        mot.add_widget(mi); inn.add_widget(mot)
        pg.add_widget(sv)
        return pg

    def _pick_mood_stat(self, v):
        self._save_mood(v)
        for b in getattr(self,"_mood_btns",[]):
            if hasattr(b,"_mv"):
                b.theme_text_color="Custom"
                b.text_color=C["accent"] if b._mv==v else C["text2"]
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
        self._ring_pct=pct; self._ring_pct_lbl.text=f"{int(pct*100)}%"
        self._ring_w._redraw(self._ring_w)
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
        msgs=MOTIVATIONS_F if is_fem else MOTIVATIONS_M
        if hasattr(self,"_motiv_lbl") and is_fem:
            self._motiv_lbl.text=msgs[done%len(msgs)]
        if hasattr(self,"_motiv_sub") and is_fem:
            self._motiv_sub.text=f"Уже выполнено {done} дел"
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
            col.add_widget(MDLabel(text=day_n, font_style="Caption", halign="center",
                                   theme_text_color="Custom",
                                   text_color=C["accent"] if is_td else C["text2"],
                                   size_hint_y=None, height=S(16)))
            self._bars_box.add_widget(col)

    # ════════════════════════════════════════════════════════════════════════
    #  СТРАНИЦА: НАСТРОЙКИ
    # ════════════════════════════════════════════════════════════════════════
    def _mk_settings_page(self):
        is_fem=self._is_fem()
        pg=MDBoxLayout(orientation="vertical")
        hdr=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                        height=S(54), md_bg_color=C["surf"], padding=[S(16),S(10)])
        hdr.add_widget(MDLabel(text="Настройки", font_style="H6",
                                bold=True, theme_text_color="Primary"))
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
        av=MDCard(size_hint=(None,None), size=(S(46),S(46)), radius=[S(23)],
                  elevation=0, md_bg_color=C["accent"])
        av.add_widget(MDIconButton(
            icon="account-heart-outline" if is_fem else "account-outline",
            theme_text_color="Custom", text_color=(1,1,1,1), size_hint=(1,1)))
        pr.add_widget(av)
        pn=MDBoxLayout(orientation="vertical", spacing=S(2))
        self._s_name=MDLabel(text=self.user_name or "Имя", font_style="Subtitle1",
                              bold=True, theme_text_color="Primary",
                              size_hint_y=None, height=S(28))
        pn.add_widget(self._s_name)
        pn.add_widget(MDLabel(text="Нажмите чтобы изменить", font_style="Caption",
                               theme_text_color="Secondary", size_hint_y=None, height=S(18)))
        pr.add_widget(pn); p_card.add_widget(pr)
        p_card.bind(on_release=lambda *_: self._edit_profile()); inn.add_widget(p_card)

        # Голосовой помощник — статус
        inn.add_widget(_sec("ГОЛОСОВОЙ ПОМОЩНИК"))
        va_c=MDCard(size_hint_y=None, radius=[S(14)], elevation=0,
                    md_bg_color=C["surf"], padding=[S(16),S(12)])
        va_c.bind(minimum_height=va_c.setter("height"))
        va_in=MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=S(6))
        vosk_status="\u2705 Vosk установлен (офлайн)" if VOSK_OK else "\u26a0 Vosk не установлен"
        tts_status ="\u2705 TTS (pyttsx3) активен"   if TTS_OK  else "\u26a0 TTS недоступен"
        va_in.add_widget(MDLabel(text=vosk_status, font_style="Body2",
                                  theme_text_color="Primary", size_hint_y=None, height=S(24)))
        va_in.add_widget(MDLabel(text=tts_status, font_style="Body2",
                                  theme_text_color="Primary", size_hint_y=None, height=S(24)))
        install_hint=MDLabel(
            text="pip install vosk pyaudio pyttsx3\nЗагрузите модель: alphacephei.com/vosk/models",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=S(36))
        va_in.add_widget(install_hint)
        test_btn=MDRaisedButton(text="\U0001f3a4 Тест голосового помощника",
                                 size_hint_y=None, height=S(42), elevation=0,
                                 md_bg_color=C["accent"])
        test_btn.bind(on_release=lambda *_: self._start_voice())
        va_in.add_widget(test_btn); va_c.add_widget(va_in); inn.add_widget(va_c)

        # Тема
        inn.add_widget(_sec("ТЕМА ПРИЛОЖЕНИЯ"))
        g_row=MDBoxLayout(orientation="horizontal", spacing=S(10),
                          size_hint_y=None, height=S(46))
        for glabel,gtheme,gactive in [("\U0001f338 Женский","Роза",is_fem),
                                       ("\u26a1 Мужской","Бронза",not is_fem)]:
            gc=MDCard(size_hint_x=0.5, size_hint_y=None, height=S(44),
                      radius=[S(22)], elevation=0,
                      md_bg_color=C["accent"] if gactive else C["surf2"])
            gc.add_widget(MDLabel(text=glabel, font_style="Body2", bold=True,
                                   halign="center", theme_text_color="Custom",
                                   text_color=(1,1,1,1) if gactive else C["text2"]))
            gc.bind(on_release=lambda _,t=gtheme: self._apply_theme(t))
            g_row.add_widget(gc)
        inn.add_widget(g_row)
        inn.add_widget(MDLabel(text="Выберите тему:", font_style="Caption",
                               theme_text_color="Custom", text_color=C["text2"],
                               size_hint_y=None, height=S(22)))
        tgrid=GridLayout(cols=3, size_hint_y=None, spacing=S(8))
        tgrid.bind(minimum_height=tgrid.setter("height"))
        for tn in THEMES: tgrid.add_widget(self._theme_card(tn))
        inn.add_widget(tgrid)

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
        add_r.add_widget(MDLabel(text="Добавить категорию", font_style="Body1",
                                  theme_text_color="Custom", text_color=C["accent"]))
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
            text="\u2705 plyer активен" if PLYER_OK else "\u26a0 pip install plyer",
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
            ("Резервная копия","content-save-outline",self._export),
            ("Экспорт задач","upload-outline",self._export),
            ("О приложении","information-outline",lambda:None)]:
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
        row.add_widget(MDLabel(text=label, font_style="Body1", theme_text_color="Primary"))
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
        row.add_widget(MDLabel(text=label, font_style="Body1", theme_text_color="Primary"))
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
        row.add_widget(MDLabel(text=label, font_style="Body1", theme_text_color="Primary"))
        row.add_widget(MDLabel(text=value, font_style="Body2",
                               theme_text_color="Custom", text_color=C["text2"],
                               halign="right"))
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
            ico=CAT_ICONS.get(cat,"dots-horizontal-circle-outline")
            row=MDBoxLayout(orientation="horizontal", size_hint_y=None,
                            height=S(52), padding=[S(8),0], spacing=S(8))
            row.add_widget(MDIconButton(icon=ico, size_hint_x=None, width=S(34),
                                         theme_text_color="Custom", text_color=C["accent"]))
            row.add_widget(MDLabel(text=cat, font_style="Body1", theme_text_color="Primary"))
            row.add_widget(MDLabel(text=str(cnt), font_style="Body2",
                                   theme_text_color="Secondary",
                                   halign="right", size_hint_x=None, width=S(36)))
            row.add_widget(MDIconButton(icon="chevron-right", size_hint_x=None, width=S(26),
                                         theme_text_color="Custom", text_color=C["text2"]))
            self._cats_box.add_widget(row)

    def _theme_card(self, tn):
        td=THEMES[tn]; sel=(tn==self.theme_name)
        c=MDCard(size_hint_y=None, height=S(88), radius=[S(14)],
                 elevation=3 if sel else 0,
                 md_bg_color=C["accent"] if sel else C["surf"])
        ci=MDBoxLayout(orientation="vertical", padding=[S(10),S(8)], spacing=S(4))
        dots=MDBoxLayout(orientation="horizontal", spacing=S(5),
                         size_hint_y=None, height=S(26))
        for key in ("bg","accent","surf2"):
            dot=Widget(size_hint=(None,None), size=(S(22),S(22))); col_v=td[key]
            def _dd(w,*_,cv=col_v):
                w.canvas.clear()
                with w.canvas:
                    Color(*cv); RoundedRectangle(size=w.size, pos=w.pos, radius=[S(5)])
            dot.bind(pos=_dd, size=_dd); dots.add_widget(dot)
        ci.add_widget(dots)
        nr=MDBoxLayout(orientation="horizontal", size_hint_y=None, height=S(22))
        tc=(1,1,1,1) if sel else C["text"]
        nr.add_widget(MDLabel(text=tn, font_style="Caption",
                               theme_text_color="Custom", text_color=tc))
        if sel:
            nr.add_widget(MDLabel(text="\u2713", font_style="Body1",
                                   theme_text_color="Custom", text_color=(1,1,1,1),
                                   size_hint_x=None, width=S(20), halign="right"))
        ci.add_widget(nr)
        kind="тёмная" if td.get("dark") else "светлая"
        tc2=(0.8,0.8,0.8,1) if sel else C["text2"]
        ci.add_widget(MDLabel(text=kind, font_style="Caption",
                               theme_text_color="Custom", text_color=tc2,
                               size_hint_y=None, height=S(14)))
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
        box=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(8), padding=[S(4)])
        nf=MDTextField(hint_text="Название категории", size_hint_y=None, height=S(52))
        box.add_widget(nf)
        dlg=MDDialog(title="Новая категория", type="custom", content_cls=box,
                     buttons=[
                         MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                         MDRaisedButton(text="Добавить", md_bg_color=C["accent"],
                                        on_release=lambda *_: self._do_add_cat(nf.text.strip(),dlg))])
        dlg.open()

    def _do_add_cat(self, name, dlg):
        if name and name not in self.categories:
            self.categories.append(name); self._save_config()
            self._rebuild_cats_list()
            if hasattr(self,"cat_bar"):
                b=self._mk_cat_btn(name); self._cat_btns[name]=b
                self.cat_bar.add_widget(b,index=1); self._update_cat_colors()
        dlg.dismiss()

    def _edit_profile(self):
        box=MDBoxLayout(orientation="vertical", adaptive_height=True,
                        spacing=S(8), padding=[S(4)])
        nf=MDTextField(hint_text="Имя", text=self.user_name,
                       size_hint_y=None, height=S(52))
        box.add_widget(nf)
        dlg=MDDialog(title="Редактировать профиль", type="custom", content_cls=box,
                     buttons=[
                         MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                         MDRaisedButton(text="Сохранить", md_bg_color=C["accent"],
                                        on_release=lambda *_: self._save_profile(nf.text,dlg))])
        dlg.open()

    def _save_profile(self, name, dlg):
        if name.strip():
            self.user_name=name.strip()
            if hasattr(self,"_tb_name"):
                self._tb_name.text=(f"{self.user_name} \U0001f495" if self._is_fem() else "СЕГОДНЯ")
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
        if self.cur_cat not in self.categories: self.cur_cat=self.categories[0]
        if hasattr(self,"cat_bar"):
            self.cat_bar.clear_widgets(); self._cat_btns={}
            for c in self.categories:
                b=self._mk_cat_btn(c); self._cat_btns[c]=b; self.cat_bar.add_widget(b)
            gear=MDRaisedButton(text="", size_hint_x=None, width=S(36),
                                 size_hint_y=None, height=S(32), elevation=0,
                                 md_bg_color=C["surf2"])
            gear.add_widget(MDIconButton(icon="cog-outline", size_hint=(1,1),
                                          theme_text_color="Custom", text_color=C["text2"]))
            gear.bind(on_release=self._manage_cats); self.cat_bar.add_widget(gear)
            self._update_cat_colors()
        self.save_tasks(); self._rebuild_cats_list(); dlg.dismiss()
        self.refresh_task_list()

    # ── Фильтры ─────────────────────────────────────────────────────────────
    def _tog_date(self,*_):
        self.filter_date=not self.filter_date
        self.f_date.text=self.sel_date if self.filter_date else "Все даты"
        self.f_date.md_bg_color=C["acc_s"] if self.filter_date else C["surf2"]
        self.refresh_task_list()

    def _tog_done(self,*_):
        self.show_done=not self.show_done
        self.f_done.text="Показать вып." if not self.show_done else "Скрыть вып."
        self.f_done.md_bg_color=C["acc_s"] if not self.show_done else C["surf2"]
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
        mv=ModalView(background_color=(0,0,0,0.5), auto_dismiss=True, size_hint=(0.9,None))
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
                mr.add_widget(MDLabel(text=face, font_style="H5",
                                       halign="center", size_hint_x=0.2))
            ci.add_widget(MDLabel(text="Как твоё настроение?", font_style="Caption",
                                   theme_text_color="Secondary", halign="center",
                                   size_hint_y=None, height=S(18)))
            ci.add_widget(mr)
        close=MDRaisedButton(text="Продолжать!", size_hint=(1,None), height=S(48),
                              elevation=0, md_bg_color=C["accent"])
        close.bind(on_release=lambda *_: mv.dismiss())
        ci.add_widget(close); card.add_widget(ci); mv.add_widget(card); mv.open()
        # TTS мотивация
        msgs=MOTIVATIONS_F if is_fem else MOTIVATIONS_M
        self._voice.speak(msgs[done_today % len(msgs)])

    # ── Список задач ─────────────────────────────────────────────────────────
    def refresh_task_list(self):
        if hasattr(self,"_ref_ev") and self._ref_ev: self._ref_ev.cancel()
        self._ref_ev=Clock.schedule_once(self._do_refresh, 0.05)

    def _do_refresh(self, *_):
        self._ref_ev=None
        if not hasattr(self,"task_list"): return
        self.task_list.clear_widgets()
        tasks=[t for t in self.tasks.values() if t.get("category")==self.cur_cat]
        if self.filter_date: tasks=[t for t in tasks if t.get("date")==self.sel_date]
        if not self.show_done: tasks=[t for t in tasks if not t.get("done",False)]
        PRIO={"Высокий":0,"Средний":1,"Низкий":2}
        tasks.sort(key=lambda t:(t.get("done",False),
                                  PRIO.get(t.get("priority","Средний"),1),
                                  t.get("date","")))
        for t in tasks:
            self.task_list.add_widget(TaskCard(
                task_id=t["id"],title=t["title"],task_date=t["date"],
                comment=t.get("comment",""),done=t.get("done",False),
                priority=t.get("priority","Средний"),
                category=t.get("category",""),
                original_date=t.get("original_date",t["date"]),
                subtasks=t.get("subtasks",[]),
                time_str=t.get("time","")))

        total=len(tasks); done=sum(1 for t in tasks if t.get("done"))
        pct=done/total if total else 0.0
        self.stat_lbl.text=f"{self.cur_cat}: {total} задач  {done} выполнено" \
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
                self._day_task_sub.text=(tv if tv else
                    ("Поставь цель на сегодня \U0001f496" if is_fem else "до конца дня"))
            else:
                self._day_task_lbl.text=("Всё выполнено! \U0001f389" if done else
                    ("Добавь первую задачу" if is_fem else "Список пуст"))
                self._day_task_sub.text=f"Выполнено {done} дел \U0001f49e" if (done and is_fem) else ""
        if self.cur_tab=="calendar":
            Clock.schedule_once(lambda *_: self._refresh_cal(), 0.05)

    # ── Экспорт ──────────────────────────────────────────────────────────────
    def _export(self,*_):
        path=os.path.join(os.path.expanduser("~"),"flowdo_backup.json")
        try:
            with open(path,"w",encoding="utf-8") as f:
                json.dump({"tasks":list(self.tasks.values()),
                           "categories":self.categories,
                           "profile":{"name":self.user_name},
                           "mood_history":self.mood_history},
                          f, ensure_ascii=False, indent=2)
            if hasattr(self,"_exp_lbl"): self._exp_lbl.text=f"Сохранено: {path}"
        except Exception as e:
            if hasattr(self,"_exp_lbl"): self._exp_lbl.text=f"Ошибка: {e}"

    # ── Rebuild после смены темы ──────────────────────────────────────────────
    def _rebuild(self,*_):
        for attr in ("_pg_tasks","_pg_calendar","_pg_stats","_pg_settings",
                     "task_list","cat_bar","_cat_btns","stat_lbl","_pct_lbl",
                     "_prog_bg","_day_task_lbl","_day_task_sub","_day_pct_lbl",
                     "_ring_w","_ring_pct_lbl","_bars_box","_s_streak","_s_total",
                     "_motiv_lbl","_motiv_sub","_mood_btns","_sd_lbl","_sf_lbl",
                     "_sp_badge","_s_name","_g_fem","_g_mal","_exp_lbl",
                     "_cats_box","_cal_month_lbl","_sp_btns",
                     "_goal_pct_lbl","_goal_prog","_draw_goal",
                     "_tasks_header","_nav_btns"):
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
            self.user_name=self.cfg_store.get("profile").get("name","")
        if self.cfg_store.exists("theme"):
            tn=self.cfg_store.get("theme").get("name","Роза")
            if tn in THEMES: self.theme_name=tn; C.update(THEMES[tn])
        if self.cfg_store.exists("categories"):
            cats=self.cfg_store.get("categories").get("list",[])
            if cats: self.categories=cats
        if self.cfg_store.exists("weekly_goal"):
            self.weekly_goal=self.cfg_store.get("weekly_goal").get("value",80)

    def _save_config(self):
        self.cfg_store.put("profile",    name=self.user_name)
        self.cfg_store.put("theme",      name=self.theme_name)
        self.cfg_store.put("categories", list=self.categories)
        self.cfg_store.put("weekly_goal",value=self.weekly_goal)

    # stat_lbl placeholder
    @property
    def stat_lbl(self):
        return getattr(self, "_stat_lbl_obj", None) or type("_",(),{"text":""})()


if __name__ == "__main__":
    DailyTodoApp().run()
