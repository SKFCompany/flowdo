"""
ShoppingScreen — список покупок с галочками
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from screens.widgets import TapIcon
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivy.metrics import dp
from kivy.app import App
from screens import theme


class ShoppingScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self._last_signature = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")
        toolbar = MDTopAppBar(
            title="Список покупок",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
            right_action_items=[
                ["plus", lambda x: self._open_add()],
                ["delete-sweep", lambda x: self._clear_checked()],
            ],
        )
        root.add_widget(toolbar)

        hint = MDLabel(
            text="  Нажмите на кружок, чтобы отметить купленное",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(28),
        )
        root.add_widget(hint)

        scroll = MDScrollView()
        self.items_box = MDBoxLayout(
            orientation="vertical", spacing=dp(6),
            padding=[dp(12), dp(8)], adaptive_height=True,
        )
        scroll.add_widget(self.items_box)
        root.add_widget(scroll)
        self.add_widget(root)

    def _load(self):
        db = App.get_running_app().db
        items = db.get_shopping_list()

        signature = tuple((i["id"], i.get("name"), i.get("quantity"), i.get("is_checked")) for i in items)
        if signature == self._last_signature:
            return
        self._last_signature = signature

        theme.safe_clear(self.items_box)

        if not items:
            self.items_box.add_widget(MDLabel(
                text="Список покупок пуст.\nНажмите + чтобы добавить!",
                halign="center", theme_text_color="Secondary",
                size_hint_y=None, height=dp(80),
            ))
            return

        pending   = [i for i in items if not i["is_checked"]]
        completed = [i for i in items if i["is_checked"]]

        if pending:
            self.items_box.add_widget(MDLabel(
                text=f"Купить ({len(pending)})",
                font_style="Subtitle2", bold=True,
                theme_text_color="Primary",
                size_hint_y=None, height=dp(28),
            ))
        for item in pending:
            self.items_box.add_widget(self._make_row(item, False))

        if completed:
            self.items_box.add_widget(MDLabel(
                text=f"Куплено ({len(completed)})",
                font_style="Subtitle2", bold=True,
                theme_text_color="Secondary",
                size_hint_y=None, height=dp(28),
            ))
        for item in completed:
            self.items_box.add_widget(self._make_row(item, True))

    def _make_row(self, item, checked):
        row = MDCard(
            orientation="horizontal",
            radius=[dp(10)],
            padding=[dp(10), dp(6)],
            spacing=dp(8),
            size_hint_y=None, height=dp(48),
            elevation=0 if checked else 1,
        )
        check_btn = TapIcon(
            icon="checkbox-marked-circle" if checked else "checkbox-blank-circle-outline",
            color=(0.18, 0.50, 0.05, 1) if checked else (0.6, 0.6, 0.6, 1),
            size_dp=36,
        )
        check_btn.bind(on_release=lambda x, iid=item["id"]: self._toggle(iid))
        row.add_widget(check_btn)

        name_lbl = MDLabel(
            text=item["name"].capitalize(),
            font_style="Body1",
            theme_text_color="Secondary" if checked else "Primary",
        )
        if checked:
            name_lbl.font_style = "Body2"
        row.add_widget(name_lbl)

        if item.get("quantity"):
            row.add_widget(MDLabel(
                text=item["quantity"],
                font_style="Caption",
                theme_text_color="Secondary",
                size_hint=(None, 1), width=dp(60),
                halign="right",
            ))

        del_btn = TapIcon(
            icon="close",
            color=(0.65, 0.2, 0.1, 1),
            size_dp=28,
        )
        del_btn.bind(on_release=lambda x, iid=item["id"]: self._delete(iid))
        row.add_widget(del_btn)
        return row

    def _toggle(self, iid):
        App.get_running_app().db.toggle_shopping_item(iid)
        self._load()

    def _delete(self, iid):
        App.get_running_app().db.delete_shopping_item(iid)
        self._load()

    def _clear_checked(self):
        App.get_running_app().db.clear_checked_shopping()
        self._load()

    def _open_add(self):
        self.add_field = MDTextField(
            hint_text="Название продукта...",
            mode="rectangle",
            text_color_normal=(0.1, 0.1, 0.1, 1),
        )
        self.qty_field = MDTextField(
            hint_text="Количество (напр. 1 кг)",
            mode="rectangle",
            text_color_normal=(0.1, 0.1, 0.1, 1),
        )
        content = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_height=True)
        content.add_widget(self.add_field)
        content.add_widget(self.qty_field)
        self.dialog = MDDialog(
            title="Добавить в список",
            type="custom",
            content_cls=content,
            buttons=[
                MDRaisedButton(text="Добавить",
                                on_release=self._save),
                MDRaisedButton(text="Отмена",
                                on_release=lambda x: self.dialog.dismiss()),
            ],
        )
        self.dialog.open()

    def _save(self, *a):
        name = self.add_field.text.strip()
        qty  = self.qty_field.text.strip()
        if name:
            App.get_running_app().db.add_to_shopping(name, qty)
            self.dialog.dismiss()
            self._load()

    def _back(self):
        App.get_running_app().root.current = "home"

    def on_enter(self):
        self._load()