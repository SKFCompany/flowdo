"""
CookModeScreen — пошаговый режим готовки на весь экран.

Один шаг за раз, крупный шрифт, кнопки "Назад/Далее". Если в тексте шага
удалось распознать длительность ("жарьте 10 мин") — показывается кнопка
запуска таймера на этот шаг. Пока этот экран открыт, телефон не гасит
экран (на Android) — не хочется тыкать в блокировку экрана мокрыми
от готовки руками.
"""

from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.app import App

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.scrollview import MDScrollView

from data.step_timer import parse_duration_seconds, format_mmss

GREEN = (0.18, 0.40, 0.05, 1)
GREEN_TEXT = (0.23, 0.50, 0.07, 1)
DONE_COLOR = (0.85, 0.35, 0.15, 1)


class CookModeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recipe = None
        self.steps = []
        self.current_index = 0
        self.back_screen = "recipe_detail"

        self._timer_event = None
        self._timer_seconds_left = 0
        self._timer_running = False

        self._build()

    # ---------------------------------------------------------- UI build --
    def _build(self):
        root = MDBoxLayout(orientation="vertical")

        self.toolbar = MDTopAppBar(
            title="Готовим",
            md_bg_color=GREEN,
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["close", lambda x: self._exit()]],
        )
        root.add_widget(self.toolbar)

        self.progress = MDProgressBar(value=0, size_hint_y=None, height=dp(6))
        root.add_widget(self.progress)

        self.step_counter = MDLabel(
            text="", halign="center", font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(26),
        )
        root.add_widget(self.step_counter)

        scroll = MDScrollView()
        body = MDBoxLayout(
            orientation="vertical",
            padding=[dp(24), dp(16), dp(24), dp(16)],
            spacing=dp(18),
            adaptive_height=True,
        )

        self.step_label = MDLabel(
            text="",
            font_style="H5",
            halign="left",
            theme_text_color="Primary",
            adaptive_height=True,
        )
        body.add_widget(self.step_label)

        timer_box = MDBoxLayout(orientation="vertical", spacing=dp(8),
                                 size_hint_y=None, height=dp(130))
        self.timer_label = MDLabel(
            text="",
            font_style="H3",
            halign="center",
            theme_text_color="Custom",
            text_color=GREEN_TEXT,
            size_hint_y=None, height=dp(70),
        )
        timer_box.add_widget(self.timer_label)

        self.timer_btn = MDRaisedButton(
            text="Запустить таймер",
            size_hint=(None, None), size=(dp(230), dp(46)),
            pos_hint={"center_x": 0.5},
        )
        self.timer_btn.bind(on_release=lambda x: self._toggle_timer())
        timer_box.add_widget(self.timer_btn)
        body.add_widget(timer_box)

        scroll.add_widget(body)
        root.add_widget(scroll)

        nav_row = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(64),
            padding=[dp(16), dp(8)], spacing=dp(10),
        )
        self.back_btn = MDFlatButton(
            text="Назад",
            theme_text_color="Custom", text_color=GREEN_TEXT,
        )
        self.back_btn.bind(on_release=lambda x: self._prev_step())
        self.next_btn = MDRaisedButton(text="Далее", size_hint_x=1)
        self.next_btn.bind(on_release=lambda x: self._next_step())
        nav_row.add_widget(self.back_btn)
        nav_row.add_widget(self.next_btn)
        root.add_widget(nav_row)

        self.add_widget(root)

    # ------------------------------------------------------------- data --
    def load_recipe(self, recipe, back_screen="recipe_detail"):
        self.recipe = recipe
        self.back_screen = back_screen
        steps_text = recipe.get("steps", "")
        self.steps = [s.strip() for s in steps_text.strip().split("\n") if s.strip()]
        if not self.steps:
            self.steps = ["Шаги для этого рецепта пока не указаны."]
        self.current_index = 0
        self.toolbar.title = recipe.get("name", "Готовим")
        self._render_step()

    def _render_step(self):
        self._stop_timer(reset_label=True)
        total = len(self.steps)
        idx = self.current_index

        self.step_counter.text = f"Шаг {idx + 1} из {total}"
        self.progress.value = (idx + 1) / total * 100
        self.step_label.text = self.steps[idx]

        duration = parse_duration_seconds(self.steps[idx])
        if duration:
            self._timer_seconds_left = duration
            self.timer_btn.disabled = False
            self.timer_btn.opacity = 1
            self.timer_label.opacity = 1
            self.timer_label.text_color = GREEN_TEXT
            self.timer_label.text = format_mmss(duration)
            self.timer_btn.text = "Запустить таймер"
        else:
            self.timer_label.text = ""
            self.timer_btn.disabled = True
            self.timer_btn.opacity = 0
            self.timer_label.opacity = 0

        self.back_btn.disabled = (idx == 0)
        self.next_btn.text = "Готово" if idx == total - 1 else "Далее"

    # ------------------------------------------------------------ timer --
    def _toggle_timer(self):
        if self._timer_running:
            self._stop_timer(reset_label=False)
            self.timer_btn.text = "Продолжить"
        else:
            self._timer_running = True
            self.timer_btn.text = "Пауза"
            self._timer_event = Clock.schedule_interval(self._tick, 1)

    def _tick(self, dt):
        self._timer_seconds_left -= 1
        if self._timer_seconds_left <= 0:
            self.timer_label.text = "Готово!"
            self.timer_label.text_color = DONE_COLOR
            self._stop_timer(reset_label=False)
            self.timer_btn.text = "Запустить заново"
            self._vibrate()
            return
        self.timer_label.text = format_mmss(self._timer_seconds_left)

    def _vibrate(self):
        try:
            from plyer import vibrator
            vibrator.vibrate(0.4)
        except Exception:
            pass  # нет вибро (десктоп/эмулятор) — не критично

    def _stop_timer(self, reset_label):
        self._timer_running = False
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
        if reset_label:
            self.timer_label.text = ""

    # --------------------------------------------------------- navigate --
    def _next_step(self):
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1
            self._render_step()
        else:
            self._finish()

    def _prev_step(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._render_step()

    def _finish(self):
        if self.recipe:
            db = App.get_running_app().db
            db.add_to_history(self.recipe["name"], self.recipe.get("category", "Основное"), "any")
            try:
                from kivymd.toast import toast
                toast(f"«{self.recipe['name']}» готово! Добавлено в историю")
            except Exception:
                pass
        self._exit()

    def _exit(self):
        self._stop_timer(reset_label=True)
        App.get_running_app().root.current = self.back_screen

    # -------------------------------------------------- screen lifetime --
    def on_enter(self, *args):
        self._set_keep_screen_on(True)

    def on_leave(self, *args):
        self._set_keep_screen_on(False)
        self._stop_timer(reset_label=True)

    def _set_keep_screen_on(self, on):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            WindowManager = autoclass("android.view.WindowManager$LayoutParams")
            activity = PythonActivity.mActivity
            if on:
                activity.getWindow().addFlags(WindowManager.FLAG_KEEP_SCREEN_ON)
            else:
                activity.getWindow().clearFlags(WindowManager.FLAG_KEEP_SCREEN_ON)
        except Exception:
            pass  # не Android-рантайм (например, при тестах) — просто пропускаем
