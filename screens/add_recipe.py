"""
AddRecipeScreen v3 — MDChip заменён на MDRaisedButton
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.app import App
from screens import theme
from screens.icons import icon_char

CATEGORIES = ["Завтрак", "Суп", "Салат", "Основное", "Паста", "Десерт", "Напиток"]
CUISINES   = ["Казахская", "Японская", "Итальянская", "Русская",
              "Азиатская", "Средиземноморская", "Американская", "Европейская"]
# Иконки Material Design Icons вместо Unicode-эмодзи — на Windows-сборке
# Kivy (kivy_deps.sdl2) обычные emoji не рендерятся (см. screens/icons.py
# за подробным объяснением), а собственный шрифт иконок KivyMD работает
# надёжно везде.
ICONS = ["silverware-fork-knife", "food-apple-outline", "egg-fried", "pasta",
         "pot-steam-outline", "food-steak", "pizza", "food-variant",
         "bowl-mix-outline", "noodles", "food-croissant", "rice",
         "fish", "food-drumstick", "bread-slice", "cupcake"]


def make_selector_row(items, on_select):
    """Горизонтальная прокрутка кнопок-выборов, возвращает (ScrollView, dict btn, list selected)"""
    selected = [items[0]]
    sv = ScrollView(size_hint_y=None, height=dp(44), do_scroll_y=False, bar_width=0)
    box = MDBoxLayout(orientation="horizontal", spacing=dp(6),
                      padding=[0, dp(4)], size_hint_x=None, adaptive_width=True)
    btns = {}

    def pick(val):
        selected[0] = val
        for v, b in btns.items():
            b.md_bg_color = theme.ACCENT if v == val else theme.chip_bg()
            b.theme_text_color = "Custom"
            b.text_color = (1, 1, 1, 1) if v == val else theme.accent_text()
        on_select(val)

    for item in items:
        is_first = (item == items[0])
        btn = MDRaisedButton(
            text=item,
            size_hint=(None, None),
            height=dp(34),
            md_bg_color=theme.ACCENT if is_first else theme.chip_bg(),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1) if is_first else theme.accent_text(),
            elevation=0,
        )
        btn.bind(on_release=lambda x, v=item: pick(v))
        btns[item] = btn
        box.add_widget(btn)

    sv.add_widget(box)
    return sv, btns, selected


class AddRecipeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sel_category = [CATEGORIES[0]]
        self.sel_cuisine   = [CUISINES[0]]
        self.sel_emoji     = [ICONS[0]]
        self._build()

    def _lbl(self, txt):
        return MDLabel(text=txt, font_style="Caption",
                       theme_text_color="Secondary",
                       size_hint_y=None, height=dp(22))

    def _build(self):
        root = MDBoxLayout(orientation="vertical")

        toolbar = MDTopAppBar(
            title="Добавить рецепт",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
        )
        root.add_widget(toolbar)

        scroll = MDScrollView()
        form = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(16), dp(12), dp(16), dp(24)],
            adaptive_height=True,
        )

        # Name
        form.add_widget(self._lbl("Название блюда *"))
        self.name_field = MDTextField(
            hint_text="Например: Борщ домашний",
            mode="rectangle",
        )
        form.add_widget(self.name_field)

        # Icon grid (Material Design Icons вместо emoji — см. screens/icons.py)
        form.add_widget(self._lbl("Иконка блюда"))
        emoji_grid = GridLayout(cols=8, size_hint_y=None, height=dp(44), spacing=dp(4))
        self.emoji_btns = {}
        for em in ICONS:
            btn = MDRaisedButton(
                text=icon_char(em),
                font_name="Icons",
                size_hint=(None, None), size=(dp(40), dp(36)),
                md_bg_color=theme.ACCENT if em == ICONS[0] else theme.chip_bg(),
                elevation=0,
            )
            btn.bind(on_release=lambda x, e=em: self._pick_emoji(e))
            emoji_grid.add_widget(btn)
            self.emoji_btns[em] = btn
        form.add_widget(emoji_grid)

        # Category
        form.add_widget(self._lbl("Категория"))
        cat_sv, self.cat_btns, self.sel_category = make_selector_row(
            CATEGORIES, lambda v: None)
        form.add_widget(cat_sv)

        # Cuisine
        form.add_widget(self._lbl("Кухня"))
        cui_sv, self.cui_btns, self.sel_cuisine = make_selector_row(
            CUISINES, lambda v: None)
        form.add_widget(cui_sv)

        # Numbers
        form.add_widget(self._lbl("Калории  /  Время (мин)  /  Порции"))
        nums = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                           height=dp(56), spacing=dp(8))
        self.cal_field  = MDTextField(hint_text="ккал",  mode="rectangle", input_filter="int")
        self.time_field = MDTextField(hint_text="мин",   mode="rectangle", input_filter="int")
        self.serv_field = MDTextField(hint_text="порц.", mode="rectangle", input_filter="int")
        nums.add_widget(self.cal_field)
        nums.add_widget(self.time_field)
        nums.add_widget(self.serv_field)
        form.add_widget(nums)

        # Ingredients
        form.add_widget(self._lbl("Ингредиенты (через | вертикальная черта)"))
        self.ingr_field = MDTextField(
            hint_text="яйца|молоко|сыр|соль",
            mode="rectangle",
            multiline=True,
            size_hint_y=None, height=dp(72),
        )
        form.add_widget(self.ingr_field)

        # Steps
        form.add_widget(self._lbl("Шаги приготовления *"))
        self.steps_field = MDTextField(
            hint_text="1. Нарежьте...\n2. Обжарьте...\n3. Подавайте...",
            mode="rectangle",
            multiline=True,
            size_hint_y=None, height=dp(140),
        )
        form.add_widget(self.steps_field)

        form.add_widget(MDBoxLayout(size_hint_y=None, height=dp(12)))

        save_btn = MDRaisedButton(
            text="Сохранить рецепт",
            md_bg_color=theme.ACCENT,
            size_hint_x=1,
            height=dp(46),
        )
        save_btn.bind(on_release=self._save)
        form.add_widget(save_btn)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def _pick_emoji(self, emoji):
        self.sel_emoji[0] = emoji
        for em, btn in self.emoji_btns.items():
            btn.md_bg_color = theme.ACCENT if em == emoji \
                               else theme.chip_bg()

    def _save(self, *a):
        name  = self.name_field.text.strip()
        steps = self.steps_field.text.strip()
        if not name or not steps:
            try:
                from kivymd.toast import toast
                toast("Заполните название и шаги!")
            except Exception:
                pass
            return

        App.get_running_app().db.add_custom_recipe(
            name=name,
            category=self.sel_category[0],
            cuisine=self.sel_cuisine[0],
            calories=int(self.cal_field.text or 0),
            cook_time=int(self.time_field.text or 30),
            servings=int(self.serv_field.text or 2),
            emoji=self.sel_emoji[0],
            ingredients=self.ingr_field.text.strip(),
            steps=steps,
        )
        try:
            from kivymd.toast import toast
            toast(f"«{name}» сохранён!")
        except Exception:
            pass
        self._clear()
        self._back()

    def _clear(self):
        for f in (self.name_field, self.cal_field, self.time_field,
                  self.serv_field, self.ingr_field, self.steps_field):
            f.text = ""

    def _back(self):
        App.get_running_app().root.current = "home"
