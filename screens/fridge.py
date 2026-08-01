"""
FridgeScreen v3 — без MDChip, GridLayout для продуктов
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.app import App
from screens import theme
from screens.widgets import TapIcon
import math


class FridgeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self._last_signature = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")
        toolbar = MDTopAppBar(
            title="Мой холодильник",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
            right_action_items=[["plus", lambda x: self._open_add()]],
        )
        root.add_widget(toolbar)

        scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(12), dp(10)],
            adaptive_height=True,
        )
        scroll.add_widget(self.content)
        root.add_widget(scroll)
        self.add_widget(root)

    def _load(self):
        db = App.get_running_app().db
        items = db.get_fridge()

        # Пересборка списка холодильника не бесплатна и раньше происходила
        # при каждом входе на экран. Пропускаем, если содержимое не
        # изменилось с прошлого показа.
        signature = tuple((i["id"], i["name"], i.get("quantity")) for i in items)
        if signature == self._last_signature:
            return
        self._last_signature = signature

        theme.safe_clear(self.content)

        self.content.add_widget(MDLabel(
            text=f"В холодильнике: {len(items)} продуктов",
            font_style="Subtitle2",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(28),
        ))

        if not items:
            self.content.add_widget(MDLabel(
                text="Холодильник пуст.\nНажмите + чтобы добавить продукты",
                halign="center",
                theme_text_color="Secondary",
                size_hint_y=None, height=dp(60),
            ))
        else:
            cols = 2
            rows_count = math.ceil(len(items) / cols)
            grid = GridLayout(
                cols=cols,
                size_hint_y=None,
                height=rows_count * dp(46),
                spacing=dp(6),
            )
            for item in items:
                row = MDBoxLayout(
                    orientation="horizontal",
                    size_hint_y=None, height=dp(40),
                    spacing=dp(4),
                )
                # Кнопка-тег вместо чипа
                tag_btn = MDFlatButton(
                    text=item["name"].capitalize(),
                    size_hint_x=1,
                    height=dp(36),
                    theme_text_color="Custom",
                    text_color=theme.accent_text(),
                    md_bg_color=theme.chip_bg(),
                )
                del_btn = TapIcon(
                    icon="close",
                    color=(0.7, 0.2, 0.1, 1),
                    size_dp=32,
                )
                del_btn.bind(on_release=lambda x, iid=item["id"]: self._remove(iid))
                row.add_widget(tag_btn)
                row.add_widget(del_btn)
                grid.add_widget(row)
            self.content.add_widget(grid)

        self.content.add_widget(MDBoxLayout(size_hint_y=None, height=dp(8)))
        btn = MDRaisedButton(
            text="Что можно приготовить?",
            md_bg_color=theme.ACCENT,
            size_hint_x=1,
        )
        btn.bind(on_release=lambda x: self._check())
        self.content.add_widget(btn)

    def _check(self):
        db = App.get_running_app().db
        can_cook, partial = db.what_can_i_cook()

        if can_cook:
            card = MDCard(
                orientation="vertical", radius=[dp(12)], padding=dp(12),
                md_bg_color=theme.success_bg(),
                size_hint_y=None, adaptive_height=True,
            )
            card.add_widget(MDLabel(
                text="Можно приготовить прямо сейчас",
                font_style="Subtitle2", bold=True,
                theme_text_color="Custom", text_color=theme.success_text(),
                size_hint_y=None, height=dp(32),
            ))
            for r in can_cook:
                card.add_widget(MDLabel(
                    text=f"  {r['name']}  ·  {r['cook_time']} мин",
                    font_style="Body2", theme_text_color="Primary",
                    size_hint_y=None, height=dp(28),
                ))
            self.content.add_widget(card)

        if partial:
            shop_card = MDCard(
                orientation="vertical", radius=[dp(12)], padding=dp(12),
                md_bg_color=theme.warning_bg(),
                size_hint_y=None, adaptive_height=True,
            )
            shop_card.add_widget(MDLabel(
                text="Нужно докупить (почти всё есть)",
                font_style="Subtitle2", bold=True,
                theme_text_color="Custom", text_color=theme.warning_text(),
                size_hint_y=None, height=dp(32),
            ))
            all_missing = {}
            for p in partial:
                r = p["recipe"]
                shop_card.add_widget(MDLabel(
                    text=f"  {r['name']}",
                    font_style="Body2", theme_text_color="Primary",
                    size_hint_y=None, height=dp(26),
                ))
                for m in p["missing"]:
                    all_missing[m] = True
            if all_missing:
                shop_card.add_widget(MDLabel(
                    text="Купить:", font_style="Caption",
                    theme_text_color="Secondary",
                    size_hint_y=None, height=dp(24),
                ))
                for m in all_missing:
                    shop_card.add_widget(MDLabel(
                        text=f"  • {m.capitalize()}",
                        font_style="Body2",
                        theme_text_color="Custom",
                        text_color=(0.7, 0.2, 0.1, 1),
                        size_hint_y=None, height=dp(24),
                    ))
            self.content.add_widget(shop_card)

        if not can_cook and not partial:
            self.content.add_widget(MDLabel(
                text="Недостаточно продуктов.\nДобавьте больше в холодильник!",
                halign="center", theme_text_color="Secondary",
                size_hint_y=None, height=dp(60),
            ))

    def _open_add(self):
        self.add_field = MDTextField(
            hint_text="Название продукта...", mode="rectangle")
        self.qty_field = MDTextField(
            hint_text="Количество (необязательно)...", mode="rectangle")
        content = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_height=True)
        content.add_widget(self.add_field)
        content.add_widget(self.qty_field)
        self.dialog = MDDialog(
            title="Добавить в холодильник",
            type="custom",
            content_cls=content,
            buttons=[
                MDRaisedButton(text="Добавить",
                                md_bg_color=theme.ACCENT,
                                on_release=self._save_item),
                MDRaisedButton(text="Отмена",
                                md_bg_color=(0.6, 0.6, 0.6, 1),
                                on_release=lambda x: self.dialog.dismiss()),
            ],
        )
        self.dialog.open()

    def _save_item(self, *a):
        name = self.add_field.text.strip()
        qty  = self.qty_field.text.strip()
        if name:
            App.get_running_app().db.add_to_fridge(name, qty)
            self.dialog.dismiss()
            self._load()

    def _remove(self, item_id):
        App.get_running_app().db.remove_from_fridge(item_id)
        self._load()

    def _back(self):
        App.get_running_app().root.current = "home"

    def on_enter(self):
        self._load()
