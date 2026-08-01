"""
SettingsScreen — тёмная тема, очистка кэша картинок, информация о приложении.
"""

from kivy.metrics import dp
from kivy.app import App

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDFlatButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.dialog import MDDialog

from screens import theme
from screens.icons import icon_char
from data.image_cache import clear_cache


class SettingsRow(MDCard):
    """Одна строка настройки: иконка + подпись + виджет-значение справа."""

    def __init__(self, icon, title, subtitle, value_widget, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(64)
        self.radius = [dp(12)]
        self.elevation = 1
        self.padding = [dp(14), dp(8)]
        self.spacing = dp(12)

        self.add_widget(MDLabel(
            text=icon_char(icon), size_hint=(None, 1), width=dp(30),
            font_name="Icons", font_style="H6", halign="center",
        ))
        col = MDBoxLayout(orientation="vertical")
        col.add_widget(MDLabel(
            text=title, font_style="Subtitle2", bold=True,
            theme_text_color="Primary",
            size_hint_y=None, height=dp(22),
        ))
        if subtitle:
            col.add_widget(MDLabel(
                text=subtitle, font_style="Caption",
                theme_text_color="Secondary",
                size_hint_y=None, height=dp(18),
            ))
        self.add_widget(col)
        if value_widget:
            self.add_widget(value_widget)


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_enter(self):
        theme.safe_clear(self)
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=theme.screen_bg())

        toolbar = MDTopAppBar(
            title="Настройки",
            md_bg_color=theme.ACCENT,
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
        )
        root.add_widget(toolbar)

        content = MDBoxLayout(
            orientation="vertical", spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)],
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        # Тёмная тема
        self.switch = MDSwitch(active=theme.is_dark())
        self.switch.bind(active=lambda inst, val: self._toggle_dark(val))
        content.add_widget(SettingsRow(
            "weather-night", "Тёмная тема",
            "Меняет оформление всего приложения",
            self.switch,
        ))

        # Очистка кэша картинок
        clear_row = SettingsRow(
            "trash-can-outline", "Очистить кэш картинок",
            "Фото рецептов скачаются заново при следующем открытии",
            None,
        )
        clear_row.ripple_behavior = True
        clear_row.bind(on_release=lambda x: self._clear_cache())
        content.add_widget(clear_row)

        content.add_widget(MDBoxLayout(size_hint_y=None, height=dp(8)))
        content.add_widget(MDLabel(
            text="МоёМеню · версия разработки",
            font_style="Caption", theme_text_color="Secondary",
            halign="center", size_hint_y=None, height=dp(20),
        ))

        root.add_widget(content)
        self.add_widget(root)

    def _toggle_dark(self, is_dark_now):
        app = App.get_running_app()
        app.set_dark_mode(is_dark_now)

    def _clear_cache(self):
        clear_cache()
        try:
            from kivymd.toast import toast
            toast("Кэш картинок очищен")
        except Exception:
            pass

    def _back(self):
        App.get_running_app().root.current = "home"
