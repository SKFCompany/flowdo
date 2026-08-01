"""
RecipeDetailScreen v2 — фото, ингредиенты, шаги, кнопка назад
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.app import App

from screens.widgets import build_recipe_image
from screens.icons import icon_char
from screens import theme

GREEN = (0.18, 0.40, 0.05, 1)


class RecipeDetailScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recipe = None
        self.back_screen = "recipes"
        self._build()

    def _build(self):
        self.root_box = MDBoxLayout(orientation="vertical")

        self.toolbar = MDTopAppBar(
            title="Рецепт",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
            right_action_items=[["star-outline", lambda x: self._toggle_fav()]],
        )
        self.root_box.add_widget(self.toolbar)

        scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(0),
            adaptive_height=True,
        )
        scroll.add_widget(self.content)
        self.root_box.add_widget(scroll)
        self.add_widget(self.root_box)

    def load_recipe(self, recipe_id, back_screen="recipes"):
        self.back_screen = back_screen
        db = App.get_running_app().db
        self.recipe = db.get_recipe(recipe_id)
        self._render()

    def _render(self):
        r = self.recipe
        if not r:
            return
        theme.safe_clear(self.content)
        self.toolbar.title = r["name"]
        fav_icon = "star" if r.get("is_favorite") else "star-outline"
        self.toolbar.right_action_items = [[fav_icon, lambda x: self._toggle_fav()]]

        # Hero image
        img_box = MDBoxLayout(size_hint_y=None, height=dp(220))
        img = build_recipe_image(r.get("image_url"), r.get("category"), font_style="H1", icon_override=r.get("emoji"))
        img_box.add_widget(img)
        self.content.add_widget(img_box)

        # Title + cuisine badge
        header = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(72),
            padding=[dp(16), dp(10), dp(16), dp(4)],
        )
        header.add_widget(MDLabel(
            text=r["name"],
            font_style="H6",
            bold=True,
            theme_text_color="Primary",
            size_hint_y=None, height=dp(32),
        ))
        header.add_widget(MDLabel(
            text=f"{r.get('cuisine', '')}  ·  {r.get('category', '')}",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=theme.accent_text(),
            size_hint_y=None, height=dp(22),
        ))
        self.content.add_widget(header)

        # Meta chips
        from kivy.uix.scrollview import ScrollView
        meta_scroll = ScrollView(size_hint_y=None, height=dp(64), do_scroll_y=False, bar_width=0)
        meta_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            spacing=dp(10),
            padding=[dp(16), dp(8)],
            adaptive_width=True,
        )
        for icon, val in [("timer-outline", f"{r['cook_time']} мин"),
                           ("fire", f"{r['calories']} ккал"),
                           ("account", f"{r['servings']} порц."),
                           ("target", r.get("difficulty", "Средний"))]:
            chip = MDCard(
                orientation="vertical",
                radius=[dp(10)],
                padding=dp(8),
                elevation=1,
                size_hint_x=None,
                width=dp(84),
            )
            chip.add_widget(MDLabel(
                text=icon_char(icon),
                halign="center",
                font_name="Icons",
                font_style="Caption",
                theme_text_color="Primary",
                size_hint_y=None, height=dp(18),
            ))
            chip.add_widget(MDLabel(
                text=val,
                halign="center",
                font_style="Caption",
                theme_text_color="Primary",
            ))
            meta_row.add_widget(chip)
        meta_scroll.add_widget(meta_row)
        self.content.add_widget(meta_scroll)

        # БЖУ (nutrition) + diet tags
        protein, fat, carbs = r.get("protein") or 0, r.get("fat") or 0, r.get("carbs") or 0
        if protein or fat or carbs:
            nutrition_card = MDCard(
                orientation="vertical",
                radius=[dp(12)],
                elevation=1,
                padding=[dp(14), dp(10)],
                spacing=dp(4),
                size_hint_y=None,
                adaptive_height=True,
                pos_hint={"center_x": 0.5},
                size_hint_x=0.92,
            )
            nutrition_card.add_widget(MDLabel(
                text="БЖУ на порцию", font_style="Caption",
                theme_text_color="Secondary",
                size_hint_y=None, height=dp(18),
            ))
            nutrition_card.add_widget(MDLabel(
                text=f"Белки {protein:.0f} г   ·   Жиры {fat:.0f} г   ·   Углеводы {carbs:.0f} г",
                font_style="Body2", bold=True,
                theme_text_color="Primary",
                size_hint_y=None, height=dp(22),
            ))
            tags = (r.get("tags") or "").strip()
            if tags:
                tag_line = ", ".join(t for t in tags.split("|") if t)
                nutrition_card.add_widget(MDLabel(
                    text=tag_line, font_style="Caption",
                    theme_text_color="Custom", text_color=theme.accent_text(),
                    size_hint_y=None, height=dp(20),
                ))
            self.content.add_widget(nutrition_card)
            self.content.add_widget(MDBoxLayout(size_hint_y=None, height=dp(8)))

        body = MDBoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(12)],
            spacing=dp(10),
            adaptive_height=True,
        )

        # Ingredients
        body.add_widget(MDLabel(
            text="Ингредиенты",
            font_style="Subtitle1",
            bold=True,
            theme_text_color="Primary",
            size_hint_y=None, height=dp(32),
        ))
        ingr_list = [i.strip() for i in r.get("ingredients", "").split("|") if i.strip()]
        for ingr in ingr_list:
            row = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None, height=dp(28),
                spacing=dp(8),
            )
            dot = MDLabel(
                text=icon_char("circle-medium"),
                font_name="Icons",
                size_hint=(None, 1), width=dp(16),
                theme_text_color="Custom",
                text_color=theme.accent_text(),
                font_style="Caption",
            )
            lbl = MDLabel(
                text=ingr.capitalize(),
                font_style="Body1",
                theme_text_color="Primary",
            )
            row.add_widget(dot)
            row.add_widget(lbl)
            body.add_widget(row)

        # Divider line
        divider = Widget(size_hint_y=None, height=dp(1))
        with divider.canvas:
            from kivy.graphics import Color, Rectangle
            Color(0.85, 0.88, 0.82, 1)
            divider._rect = Rectangle(pos=divider.pos, size=divider.size)
        divider.bind(pos=lambda w, v: setattr(w._rect, 'pos', v))
        divider.bind(size=lambda w, v: setattr(w._rect, 'size', v))
        body.add_widget(divider)

        # Steps
        body.add_widget(MDLabel(
            text="Приготовление",
            font_style="Subtitle1",
            bold=True,
            theme_text_color="Primary",
            size_hint_y=None, height=dp(32),
        ))
        steps_text = r.get("steps", "")
        for i, step in enumerate(steps_text.strip().split("\n")):
            step = step.strip()
            if not step:
                continue
            step_card = MDCard(
                orientation="horizontal",
                radius=[dp(10)],
                padding=[dp(10), dp(8)],
                spacing=dp(10),
                size_hint_y=None,
                adaptive_height=True,
                elevation=0,
            )
            step_lbl = MDLabel(
                text=step,
                font_style="Body2",
                theme_text_color="Primary",
                adaptive_height=True,
            )
            step_card.add_widget(step_lbl)
            body.add_widget(step_card)

        body.add_widget(MDBoxLayout(size_hint_y=None, height=dp(8)))

        # Action buttons row
        btn_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(46),
            spacing=dp(8),
        )
        go_cook_btn = MDRaisedButton(
            text="Готовить",
            size_hint_x=0.42,
            md_bg_color=GREEN,
        )
        go_cook_btn.bind(on_release=lambda x: self._start_cook_mode())
        cook_btn = MDFlatButton(
            text="Готово",
            theme_text_color="Custom",
            text_color=theme.accent_text(),
            size_hint_x=0.28,
        )
        cook_btn.bind(on_release=lambda x: self._mark_cooked())
        plan_btn = MDFlatButton(
            text="+ В меню",
            theme_text_color="Custom",
            text_color=theme.accent_text(),
            size_hint_x=0.3,
        )
        plan_btn.bind(on_release=lambda x: self._add_to_plan())
        btn_row.add_widget(go_cook_btn)
        btn_row.add_widget(cook_btn)
        btn_row.add_widget(plan_btn)
        body.add_widget(btn_row)
        body.add_widget(MDBoxLayout(size_hint_y=None, height=dp(20)))

        self.content.add_widget(body)

    def _toggle_fav(self):
        if not self.recipe:
            return
        db = App.get_running_app().db
        is_fav = db.toggle_favorite(self.recipe["id"])
        self.recipe["is_favorite"] = is_fav
        icon = "star" if is_fav else "star-outline"
        self.toolbar.right_action_items = [[icon, lambda x: self._toggle_fav()]]

    def _mark_cooked(self):
        if not self.recipe:
            return
        db = App.get_running_app().db
        db.add_to_history(
            self.recipe["name"],
            self.recipe.get("category", "Основное"),
            "any",
        )
        try:
            from kivymd.toast import toast
            toast(f"«{self.recipe['name']}» добавлено в историю!")
        except Exception:
            pass

    def _start_cook_mode(self):
        if not self.recipe:
            return
        app = App.get_running_app()
        cook_screen = app.root.get_screen("cook_mode")
        cook_screen.load_recipe(self.recipe, back_screen="recipe_detail")
        app.root.current = "cook_mode"

    def _add_to_plan(self):
        if not self.recipe:
            return
        app = App.get_running_app()
        plan_screen = app.root.get_screen("meal_plan")
        plan_screen.pending_recipe = {"id": self.recipe["id"], "name": self.recipe["name"]}
        app.root.current = "meal_plan"

    def _back(self):
        App.get_running_app().root.current = self.back_screen