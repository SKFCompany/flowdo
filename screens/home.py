"""
HomeScreen v5 — главный экран.

Карточка "Сегодня" с планом на день вместо чистой сетки, плюс компактная
сетка остальных разделов ниже.

ВАЖНО про производительность: тулбар и сетка из 6 плиток разделов НЕ
меняются между визитами на этот экран, поэтому строятся один раз в
__init__. on_enter() обновляет только то, что реально может измениться
(карточка "Сегодня", счётчик покупок) — раньше здесь был полный
clear_widgets()+пересборка при КАЖДОМ заходе на главную, что на слабом
телефоне ощущалось как подвисание, ведь главный экран — самый частый
пункт навигации в приложении.
"""

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.app import App
from datetime import date, datetime

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.toolbar import MDTopAppBar

from screens import theme
from screens.icons import icon_char, meal_type_icon, MENU_SECTION_ICONS, GREETING_ICONS

GREEN = theme.ACCENT

WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]

MEAL_TYPES = [
    ("breakfast", "Завтрак"),
    ("lunch", "Обед"),
    ("dinner", "Ужин"),
]

MENU_ITEMS = [
    ("recipes",   "Рецепты",     "98 блюд, кухни мира"),
    ("meal_plan", "Меню недели", "Планирование на 7 дней"),
    ("calendar",  "Календарь",   "История приготовлений"),
    ("fridge",    "Холодильник", "Что приготовить из того, что есть"),
    ("shopping",  "Покупки",     "Список покупок"),
    ("favorites", "Избранное",   "Любимые рецепты"),
]


def _greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Доброе утро!", GREETING_ICONS["morning"]
    if 12 <= hour < 17:
        return "Добрый день!", GREETING_ICONS["day"]
    if 17 <= hour < 23:
        return "Добрый вечер!", GREETING_ICONS["evening"]
    return "Доброй ночи!", GREETING_ICONS["night"]


def _today_str():
    d = date.today()
    return f"{WEEKDAYS[d.weekday()].capitalize()}, {d.day} {MONTHS_GEN[d.month - 1]}"


class MealRow(ButtonBehavior, MDBoxLayout):
    """Одна строка в карточке «Сегодня»: тип приёма пищи + что запланировано.
    Кликабельна только если привязана к настоящему рецепту (есть recipe_id)."""

    def __init__(self, meal_type, label, recipe_name, recipe_id, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(46)
        self.spacing = dp(10)
        self.padding = [dp(2), dp(2)]
        self.recipe_id = recipe_id

        self.add_widget(MDLabel(
            text=meal_type_icon(meal_type), size_hint=(None, 1), width=dp(28),
            font_name="Icons", font_style="H6", halign="center",
        ))
        col = MDBoxLayout(orientation="vertical")
        col.add_widget(MDLabel(
            text=label, font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(16),
        ))
        if recipe_name:
            name_lbl = MDLabel(
                text=recipe_name, font_style="Subtitle2", bold=True,
                theme_text_color="Primary",
                size_hint_y=None, height=dp(24), shorten=True,
            )
        else:
            name_lbl = MDLabel(
                text="Не запланировано", font_style="Subtitle2",
                theme_text_color="Hint",
                size_hint_y=None, height=dp(24),
            )
        col.add_widget(name_lbl)
        self.add_widget(col)

        if recipe_id:
            self.add_widget(MDLabel(
                text="›", size_hint=(None, 1), width=dp(18),
                font_style="H6", theme_text_color="Secondary", halign="center",
            ))

    def on_release(self):
        if not self.recipe_id:
            return
        app = App.get_running_app()
        rd = app.root.get_screen("recipe_detail")
        rd.load_recipe(self.recipe_id, back_screen="home")
        app.root.current = "recipe_detail"


class TodayCard(MDCard):
    """Карточка «Сегодня» — план на день с прямым переходом в рецепт."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.adaptive_height = True
        self.radius = [dp(18)]
        self.elevation = 3
        self.padding = [dp(16), dp(14), dp(16), dp(6)]
        self.spacing = dp(4)
        self.refresh()

    def refresh(self):
        theme.safe_clear(self)
        db = App.get_running_app().db
        today_iso = str(date.today())
        plan_rows = {r["meal_type"]: r for r in db.get_day_plan(today_iso)}

        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(4))
        title_row.add_widget(MDLabel(
            text=icon_char("calendar-today"), font_name="Icons", font_style="H6",
            size_hint=(None, 1), width=dp(24),
        ))
        title_row.add_widget(MDLabel(
            text="Сегодня", font_style="H6", bold=True,
            theme_text_color="Custom", text_color=theme.accent_text(),
        ))
        self.add_widget(title_row)
        self.add_widget(MDLabel(
            text=_today_str(), font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(18),
        ))

        any_planned = False
        for key, label in MEAL_TYPES:
            row_data = plan_rows.get(key)
            recipe_name = row_data["recipe_name"] if row_data else None
            recipe_id = row_data["recipe_id"] if row_data else None
            if recipe_name:
                any_planned = True
            self.add_widget(MealRow(key, label, recipe_name, recipe_id))

        from kivymd.uix.button import MDFlatButton
        btn_text = "Открыть меню недели" if any_planned else "Запланировать меню"
        btn = MDFlatButton(
            text=btn_text,
            theme_text_color="Custom", text_color=theme.accent_text(),
            size_hint_y=None, height=dp(36),
        )
        btn.bind(on_release=lambda x: self._open_meal_plan())
        self.add_widget(btn)

    def _open_meal_plan(self):
        App.get_running_app().root.current = "meal_plan"


class ShoppingBadge(MDCard):
    """Тонкая плашка-напоминание, если в списке покупок что-то есть."""

    def __init__(self, count, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(48)
        self.radius = [dp(12)]
        self.elevation = 1
        self.padding = [dp(14), dp(8)]
        self.md_bg_color = theme.chip_bg_soft()
        word = "товар" if count % 10 == 1 and count % 100 != 11 else (
            "товара" if 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14) else "товаров")
        self.add_widget(MDLabel(
            text=icon_char("cart-outline"), font_name="Icons", font_style="Body2",
            size_hint=(None, 1), width=dp(22),
            theme_text_color="Custom", text_color=theme.accent_text(),
        ))
        self.add_widget(MDLabel(
            text=f"В списке покупок: {count} {word}",
            font_style="Body2", theme_text_color="Custom", text_color=theme.accent_text(),
        ))
        self.add_widget(MDLabel(
            text="›", size_hint=(None, 1), width=dp(18),
            font_style="H6", theme_text_color="Custom", text_color=theme.accent_text(), halign="center",
        ))

    def on_release(self):
        App.get_running_app().root.current = "shopping"


class MenuCard(MDCard):
    """Кликабельная карточка раздела"""
    def __init__(self, icon, title, desc, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self.orientation = "vertical"
        self.size_hint = (1, None)
        self.height = dp(104)
        self.radius = [dp(14)]
        self.elevation = 1
        self.padding = [dp(8), dp(10)]
        self.spacing = dp(2)
        self.ripple_behavior = True

        self.add_widget(MDLabel(
            text=icon_char(icon), font_name="Icons", font_style="H5", halign="center",
            size_hint_y=None, height=dp(36),
        ))
        self.add_widget(MDLabel(
            text=title, font_style="Subtitle2", bold=True, halign="center",
            theme_text_color="Primary",
            size_hint_y=None, height=dp(22),
        ))
        self.add_widget(MDLabel(
            text=desc, font_style="Caption", halign="center",
            theme_text_color="Secondary", shorten=True,
        ))

    def on_release(self):
        App.get_running_app().root.current = self.target


class HomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._badge = None
        self._build()

    def on_enter(self):
        # Лёгкое обновление вместо полной пересборки: тулбар и сетка
        # разделов не меняются между визитами, пересоздавать их каждый
        # раз незачем и на слабом устройстве это тормозит переход.
        text, icon = _greeting()
        self.greeting_label.text = text
        self.greeting_emoji.text = icon_char(icon)
        self.today_card.refresh()
        self._refresh_shopping_badge()

    def _refresh_shopping_badge(self):
        db = App.get_running_app().db
        count = len([i for i in db.get_shopping_list() if not i.get("is_checked")])
        if self._badge is not None:
            self.content.remove_widget(self._badge)
            self._badge = None
        if count > 0:
            self._badge = ShoppingBadge(count)
            # Вставляем сразу после карточки "Сегодня" (индекс 0 в children,
            # т.к. Kivy хранит children в обратном порядке добавления)
            today_index = self.content.children.index(self.today_card)
            self.content.add_widget(self._badge, index=today_index)

    def _open_settings(self):
        self.manager.current = "settings"

    def _build(self):
        self._badge = None
        root = MDBoxLayout(orientation="vertical", md_bg_color=theme.screen_bg())

        toolbar = MDTopAppBar(
            title="МоёМеню",
            md_bg_color=GREEN,
            specific_text_color=(1, 1, 1, 1),
            right_action_items=[["cog-outline", lambda x: self._open_settings()]],
        )
        root.add_widget(toolbar)

        scroll = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(16), dp(14), dp(16), dp(20)],
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))
        self.content = content

        greet_text, greet_icon = _greeting()
        greeting_row = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(6),
        )
        self.greeting_label = MDLabel(
            text=greet_text,
            font_style="Subtitle1", bold=True,
            theme_text_color="Primary",
            size_hint_x=None,
        )
        self.greeting_label.bind(texture_size=lambda inst, sz: setattr(inst, "width", sz[0]))
        self.greeting_emoji = MDLabel(
            text=icon_char(greet_icon), font_name="Icons",
            font_style="Subtitle1",
        )
        greeting_row.add_widget(self.greeting_label)
        greeting_row.add_widget(self.greeting_emoji)
        content.add_widget(greeting_row)

        self.today_card = TodayCard()
        content.add_widget(self.today_card)

        content.add_widget(MDLabel(
            text="Разделы",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(20),
        ))

        grid = GridLayout(
            cols=2,
            spacing=dp(10),
            size_hint_y=None,
        )
        grid.bind(minimum_height=grid.setter("height"))
        for screen_name, title, desc in MENU_ITEMS:
            grid.add_widget(MenuCard(
                icon=MENU_SECTION_ICONS.get(screen_name, "help-circle-outline"),
                title=title, desc=desc, target=screen_name,
            ))
        content.add_widget(grid)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)
