"""
RecipesScreen v2 — кухни мира, фото через AsyncImage, поиск
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock

from screens.widgets import build_recipe_image, TapIcon
from data.database import DIET_TAGS, CUISINES
from screens import theme
from screens.icons import icon_char

# MDI не умеет во флаги стран — используем нейтральную иконку "глобус",
# название кухни всё равно всегда идёт рядом читаемым текстом.
CUISINE_ICON = "earth"


class RecipeCard(MDCard):
    def __init__(self, recipe, on_press=None, **kwargs):
        super().__init__(**kwargs)
        self.recipe = recipe
        self.on_press_cb = on_press
        self.orientation = "vertical"
        self.size_hint = (1, None)
        self.height = dp(200)
        self.radius = [dp(14)]
        self.elevation = 2
        self.ripple_behavior = True
        self.bind(on_release=lambda x: self._pressed())
        self._build()

    def _build(self):
        r = self.recipe

        # Photo area. Раньше здесь стоял FloatLayout, чтобы бейдж кухни
        # лежал поверх фото overlay'ем — но у Kivy FloatLayout.add_widget()
        # завязывает ребёнка на bound-метод родителя (child.bind(pos=...)),
        # и если родителя убирают через clear_widgets() у ВНЕШНЕГО
        # контейнера (а не напрямую), эта связка не освобождается и виджеты
        # остаются в памяти навсегда — то самое нарастающее подвисание.
        # Пожертвовали красивым наложением ради стабильности: бейдж кухни
        # теперь просто компактная строка над фото на обычном BoxLayout.
        badge_row = BoxLayout(size_hint_y=None, height=dp(22), padding=[dp(6), 0], spacing=dp(4))
        badge_row.add_widget(MDLabel(
            text=icon_char(CUISINE_ICON),
            font_name="Icons",
            font_style="Caption",
            size_hint=(None, 1), width=dp(20),
        ))
        badge_row.add_widget(MDLabel(
            text=r.get('cuisine',''),
            font_style="Caption",
            theme_text_color="Secondary",
            halign="left",
        ))
        self.add_widget(badge_row)

        img_box = BoxLayout(size_hint_y=None, height=dp(120))
        img = build_recipe_image(r.get("image_url"), r.get("category"), font_style="H2", icon_override=r.get("emoji"))
        img_box.add_widget(img)
        self.add_widget(img_box)

        # Info row
        info_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(76),
            padding=[dp(10), dp(6), dp(6), dp(6)],
            spacing=dp(2),
        )

        name_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28))
        name_row.add_widget(MDLabel(
            text=r["name"],
            font_style="Subtitle1",
            bold=True,
            theme_text_color="Primary",
        ))
        is_fav = r.get("is_favorite")
        self.fav_btn = TapIcon(
            icon="star",
            color=(0.85, 0.55, 0.05, 1) if is_fav else (0.75, 0.75, 0.75, 1),
            size_dp=36,
            font_style="H5",
        )
        self.fav_btn.bind(on_release=lambda x: self._toggle_fav())
        name_row.add_widget(self.fav_btn)
        info_box.add_widget(name_row)

        meta = MDLabel(
            text=f"{r['cook_time']} мин  ·  {r['calories']} ккал  ·  {r.get('difficulty','Средний')}",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(22),
        )
        info_box.add_widget(meta)

        tags = r.get("tags") or ""
        tag_suffix = ""
        if tags:
            tag_suffix = "  ·  " + ", ".join(t for t in tags.split("|") if t)

        cat_lbl = MDLabel(
            text=f"  {r.get('category', '')} · {r['servings']} порц.{tag_suffix}",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=theme.accent_text(),
            size_hint_y=None,
            height=dp(20),
        )
        info_box.add_widget(cat_lbl)

        self.add_widget(info_box)

    def _pressed(self):
        if self.on_press_cb:
            self.on_press_cb(self.recipe)

    def _toggle_fav(self):
        db = App.get_running_app().db
        is_fav = db.toggle_favorite(self.recipe["id"])
        self.fav_btn.text_color = (0.85, 0.55, 0.05, 1) if is_fav else (0.75, 0.75, 0.75, 1)
        self.recipe["is_favorite"] = is_fav


class RecipesScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_cuisine = "Все кухни"
        self.current_tag = None
        self.search_text = ""
        self._last_signature = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")

        toolbar = MDTopAppBar(
            title="МоёМеню",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["home", lambda x: self._go_home()]],
            right_action_items=[["plus-circle-outline", lambda x: self._go_add()]],
        )
        root.add_widget(toolbar)

        # Search
        search_box = MDBoxLayout(
            size_hint_y=None, height=dp(56),
            padding=[dp(12), dp(4)], spacing=dp(8),
        )
        self.search_field = MDTextField(
            hint_text="Поиск рецептов...",
            mode="rectangle",
            line_color_normal=(0.75, 0.85, 0.65, 1),
        )
        self.search_field.bind(text=self._on_search)
        search_box.add_widget(self.search_field)
        root.add_widget(search_box)

        # Cuisine horizontal scroll
        cuisine_scroll = ScrollView(
            size_hint_y=None, height=dp(52),
            do_scroll_y=False,
            bar_width=0,
        )
        self.cuisine_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            spacing=dp(8),
            padding=[dp(12), dp(8)],
            adaptive_width=True,
        )
        self._build_cuisine_btns()
        cuisine_scroll.add_widget(self.cuisine_box)
        root.add_widget(cuisine_scroll)

        # Diet tag chips (Вегетарианское / Острое / Без глютена)
        tag_scroll = ScrollView(
            size_hint_y=None, height=dp(46),
            do_scroll_y=False,
            bar_width=0,
        )
        self.tag_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            spacing=dp(8),
            padding=[dp(12), dp(4)],
            adaptive_width=True,
        )
        self._build_tag_btns()
        tag_scroll.add_widget(self.tag_box)
        root.add_widget(tag_scroll)

        # Count label
        self.count_lbl = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(22),
            padding=[dp(14), 0],
        )
        root.add_widget(self.count_lbl)

        # Recipe list
        scroll = MDScrollView()
        self.recipe_list = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(12), dp(4), dp(12), dp(16)],
            adaptive_height=True,
        )
        scroll.add_widget(self.recipe_list)
        root.add_widget(scroll)

        self.add_widget(root)

    def _build_cuisine_btns(self):
        theme.safe_clear(self.cuisine_box)
        for c in CUISINES:
            is_active = c == self.current_cuisine
            btn = MDRaisedButton(
                text=c,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1) if is_active else (0.18, 0.40, 0.05, 1),
                size_hint=(None, None),
                height=dp(34),
                elevation=1 if is_active else 0,
            )
            btn.bind(on_release=lambda x, cu=c: self._select_cuisine(cu))
            self.cuisine_box.add_widget(btn)

    def _select_cuisine(self, cuisine):
        self.current_cuisine = cuisine
        self._build_cuisine_btns()
        self._load_recipes()

    def _build_tag_btns(self):
        theme.safe_clear(self.tag_box)
        options = ["Все"] + DIET_TAGS
        for t in options:
            is_active = (t == "Все" and self.current_tag is None) or (t == self.current_tag)
            btn = MDRaisedButton(
                text=t,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1) if is_active else theme.accent_text(),
                md_bg_color=theme.ACCENT if is_active else theme.chip_bg(),
                size_hint=(None, None),
                height=dp(32),
                elevation=1 if is_active else 0,
            )
            btn.bind(on_release=lambda x, tg=t: self._select_tag(tg))
            self.tag_box.add_widget(btn)

    def _select_tag(self, tag):
        self.current_tag = None if tag == "Все" else tag
        self._build_tag_btns()
        self._load_recipes()

    def _on_search(self, instance, value):
        self.search_text = value
        self._load_recipes()

    def _load_recipes(self):
        db = App.get_running_app().db
        recipes = db.get_all_recipes(
            search=self.search_text,
            cuisine=self.current_cuisine,
            tag=self.current_tag,
        )

        # Пересобирать 20-30 карточек рецептов — не бесплатно (реально
        # измерено: ~0.6-0.9 сек даже на мощной машине, на телефоне будет
        # ещё заметнее). Раньше это происходило при КАЖДОМ входе на экран,
        # даже если пользователь просто вернулся назад и ничего не менял.
        # Сравниваем "подпись" текущего запроса+результата с прошлой — если
        # ничего не изменилось (тот же фильтр, те же рецепты, тот же статус
        # избранного), просто оставляем уже построенные карточки как есть.
        signature = (
            self.search_text, self.current_cuisine, self.current_tag,
            tuple((r["id"], r.get("is_favorite")) for r in recipes),
        )
        if signature == self._last_signature:
            return
        self._last_signature = signature

        theme.safe_clear(self.recipe_list)
        self.count_lbl.text = f"  Найдено рецептов: {len(recipes)}"

        if not recipes:
            self.recipe_list.add_widget(MDLabel(
                text="Рецепты не найдены\nПопробуйте другой фильтр",
                halign="center",
                theme_text_color="Secondary",
                size_hint_y=None, height=dp(80),
            ))
            return

        for r in recipes:
            card = RecipeCard(recipe=r, on_press=self._open_recipe)
            self.recipe_list.add_widget(card)

    def _open_recipe(self, recipe):
        app = App.get_running_app()
        detail = app.root.get_screen("recipe_detail")
        detail.load_recipe(recipe["id"], back_screen="recipes")
        app.root.current = "recipe_detail"

    def _go_add(self):
        App.get_running_app().root.current = "add_recipe"

    def _go_home(self):
        App.get_running_app().root.current = "home"

    def on_enter(self):
        self._load_recipes()