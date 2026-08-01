"""
FavoritesScreen v2 — с кнопкой назад
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivy.metrics import dp
from kivy.app import App
from screens.recipes import RecipeCard
from screens import theme


class FavoritesScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_signature = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")
        toolbar = MDTopAppBar(
            title="Избранное",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
        )
        root.add_widget(toolbar)
        scroll = MDScrollView()
        self.fav_list = MDBoxLayout(
            orientation="vertical", spacing=dp(12),
            padding=[dp(12), dp(10)], adaptive_height=True,
        )
        scroll.add_widget(self.fav_list)
        root.add_widget(scroll)
        self.add_widget(root)

    def _load(self):
        db = App.get_running_app().db
        favs = db.get_favorites()

        signature = tuple(f["id"] for f in favs)
        if signature == self._last_signature:
            return
        self._last_signature = signature

        theme.safe_clear(self.fav_list)
        if not favs:
            self.fav_list.add_widget(MDLabel(
                text="Нет избранных рецептов.\nНажмите на звёздочку у любого рецепта!",
                halign="center", theme_text_color="Secondary",
                size_hint_y=None, height=dp(100),
            ))
            return
        for r in favs:
            card = RecipeCard(recipe=r, on_press=self._open)
            self.fav_list.add_widget(card)

    def _open(self, recipe):
        app = App.get_running_app()
        detail = app.root.get_screen("recipe_detail")
        detail.load_recipe(recipe["id"], back_screen="favorites")
        app.root.current = "recipe_detail"

    def _back(self):
        App.get_running_app().root.current = "home"

    def on_enter(self):
        self._load()