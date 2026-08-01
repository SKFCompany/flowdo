"""
МоёМеню v2 — Recipe App for Android
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.utils import platform

if platform != "android":
    Window.size = (390, 844)

# Эмодзи в приложении (иконки блюд, кнопки, чипы) не рендерились на
# Android — там нет цепочки шрифтов-фолбэков, а бандловый Roboto эмодзи
# не содержит. Заменять сам Roboto шрифтом с эмодзи нельзя — многие такие
# шрифты (в т.ч. наш первый вариант, NotoEmoji) не содержат кириллицы, и
# весь текст превращается в квадраты. Поэтому эмодзи всегда идут ПОД
# ОТДЕЛЬНЫМ именем шрифта "Emoji" — Roboto остаётся как есть (кириллица),
# а виджеты, где текст — это ЧИСТО эмодзи/иконка (без кириллицы в той же
# строке), явно используют font_name="Emoji".
#
# На Windows пробуем взять системный "Segoe UI Emoji" — он гарантированно
# есть в любой Windows 10/11, не требует бандлить свой файл шрифта и не
# страдает от проблем с вариативными шрифтами (был баг: наш бандловый
# NotoEmoji.ttf оказался variable-font, и на Windows-сборке FreeType/SDL2
# рендерил из него пустые квадраты вместо глифов — на Linux это не было
# видно, там более новый FreeType с поддержкой variable-фontов). Если
# Segoe недоступен (не Windows, либо очень старая система) — используем
# бандловый NotoEmoji.ttf как запасной вариант.
import logging as _logging
_log = _logging.getLogger("moemenu.fonts")

_FALLBACK_FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "NotoEmoji.ttf")


def _find_emoji_font():
    if platform == "win":
        win_dir = os.environ.get("WINDIR", r"C:\Windows")
        candidates = [
            os.path.join(win_dir, "Fonts", "seguiemj.ttf"),  # Segoe UI Emoji
            os.path.join(win_dir, "Fonts", "seguisym.ttf"),  # Segoe UI Symbol (запасной)
        ]
        for path in candidates:
            if os.path.isfile(path):
                print(f"[MoeMenu] Шрифт эмодзи: системный {path}")
                return path
        print("[MoeMenu] Системный Segoe UI Emoji не найден, использую бандловый NotoEmoji")
    if os.path.isfile(_FALLBACK_FONT_PATH):
        print(f"[MoeMenu] Шрифт эмодзи: бандловый {_FALLBACK_FONT_PATH}")
        return _FALLBACK_FONT_PATH
    print(f"[MoeMenu] ВНИМАНИЕ: файл шрифта эмодзи не найден по пути {_FALLBACK_FONT_PATH} — эмодзи не будут отображаться!")
    return None


_emoji_font_path = _find_emoji_font()
if _emoji_font_path:
    LabelBase.register(name="Emoji", fn_regular=_emoji_font_path, fn_bold=_emoji_font_path)

from screens.home import HomeScreen
from screens.recipes import RecipesScreen
from screens.recipe_detail import RecipeDetailScreen
from screens.meal_plan import MealPlanScreen
from screens.calendar_screen import CalendarScreen
from screens.fridge import FridgeScreen
from screens.favorites import FavoritesScreen
from screens.add_recipe import AddRecipeScreen
from screens.shopping import ShoppingScreen
from screens.cook_mode import CookModeScreen
from screens.settings import SettingsScreen
from data.database import Database
from screens import theme


class RecipeApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "МоёМеню"
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.primary_hue = "800"
        self.theme_cls.accent_palette = "Amber"
        self.db = Database()

    def build(self):
        self.db.init_db()

        # Загружаем сохранённый выбор темы ДО построения экранов — иначе
        # первый кадр отрисуется со старой темой и мигнёт при первом входе.
        theme.load_from_db(self.db)
        self.theme_cls.theme_style = "Dark" if theme.is_dark() else "Light"

        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(RecipesScreen(name="recipes"))
        sm.add_widget(RecipeDetailScreen(name="recipe_detail"))
        sm.add_widget(MealPlanScreen(name="meal_plan"))
        sm.add_widget(CalendarScreen(name="calendar"))
        sm.add_widget(FridgeScreen(name="fridge"))
        sm.add_widget(ShoppingScreen(name="shopping"))
        sm.add_widget(FavoritesScreen(name="favorites"))
        sm.add_widget(AddRecipeScreen(name="add_recipe"))
        sm.add_widget(CookModeScreen(name="cook_mode"))
        sm.add_widget(SettingsScreen(name="settings"))
        sm.current = "home"
        return sm

    def on_start(self):
        self.db.seed_sample_data()

    def set_dark_mode(self, is_dark):
        """Переключение темы из экрана настроек. Persist + мгновенное
        применение: KivyMD сам реактивно перекрашивает MDCard/MDLabel/
        Window.clearcolor через theme_cls.theme_style, а экраны с
        собственным захардкоженным фоном (взятым из screens.theme)
        досборка на следующий вход — либо принудительно прямо сейчас,
        если экран уже был построен."""
        theme.set_dark(is_dark)
        theme.save_to_db(self.db)
        self.theme_cls.theme_style = "Dark" if is_dark else "Light"
        self._refresh_all_screens()

    def _refresh_all_screens(self):
        for screen in list(self.root.screens):
            name = screen.name
            if name == "settings":
                continue  # уже перерисован пользователем прямо сейчас
            if not hasattr(screen, "_build"):
                continue
            was_recipe = getattr(screen, "recipe", None)
            was_back = getattr(screen, "back_screen", None)
            theme.safe_clear(screen)
            screen._build()
            if name == "recipe_detail" and was_recipe:
                screen.load_recipe(was_recipe["id"], back_screen=was_back or "recipes")
            elif name == "cook_mode" and was_recipe:
                screen.load_recipe(was_recipe, back_screen=was_back or "recipe_detail")
            elif hasattr(screen, "on_enter"):
                screen.on_enter()


if __name__ == "__main__":
    RecipeApp().run()
