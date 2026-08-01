"""
MealPlanScreen v2 — меню на неделю с кнопкой назад
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from screens.widgets import TapIcon
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivy.metrics import dp
from screens import theme
from kivy.app import App
from datetime import date, timedelta

DAYS_RU = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
MONTHS_RU = ["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
MEAL_LABELS = {"breakfast":"Завтрак","lunch":"Обед","dinner":"Ужин"}


class MealPlanScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        today = date.today()
        self.monday = today - timedelta(days=today.weekday())
        self.dialog = None
        self._pending = None
        self.pending_recipe = None
        self._last_signature = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")

        toolbar = MDTopAppBar(
            title="Меню на неделю",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
            right_action_items=[
                ["chevron-left", lambda x: self._prev_week()],
                ["chevron-right", lambda x: self._next_week()],
                ["cart-plus", lambda x: self._generate_shopping_list()],
            ],
        )
        root.add_widget(toolbar)

        self.week_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Secondary",
            font_style="Caption",
            size_hint_y=None, height=dp(28),
        )
        root.add_widget(self.week_label)

        scroll = MDScrollView()
        self.plan_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(12), dp(8)],
            adaptive_height=True,
        )
        scroll.add_widget(self.plan_box)
        root.add_widget(scroll)
        self.add_widget(root)

    def _prev_week(self):
        self.monday -= timedelta(7)
        self._load()

    def _next_week(self):
        self.monday += timedelta(7)
        self._load()

    def _load(self):
        db = App.get_running_app().db
        plan_rows = db.get_week_plan(self.monday)

        # Пересборка недели (7 дней × 3 приёма пищи, с диалогами и кнопками)
        # не бесплатна и раньше происходила при каждом входе на экран, даже
        # если ничего не изменилось с прошлого раза. Пропускаем пересборку,
        # если неделя и план на неё те же, что и в прошлый показ.
        signature = (
            self.monday,
            tuple((r["plan_date"], r["meal_type"], r.get("recipe_name"), r.get("recipe_id"))
                  for r in plan_rows),
        )
        if signature == self._last_signature:
            return
        self._last_signature = signature

        plan = {}
        for row in plan_rows:
            d = row["plan_date"]
            plan.setdefault(d, {})[row["meal_type"]] = row.get("recipe_name","")

        mon_str = f"{self.monday.day} {MONTHS_RU[self.monday.month-1]}"
        sun = self.monday + timedelta(6)
        sun_str = f"{sun.day} {MONTHS_RU[sun.month-1]}"
        self.week_label.text = f"  {mon_str} — {sun_str}"

        today = date.today()
        theme.safe_clear(self.plan_box)

        for i in range(7):
            day_date = self.monday + timedelta(i)
            date_str = str(day_date)
            is_today = day_date == today
            day_plan = plan.get(date_str, {})

            card_bg = (0.90, 0.96, 0.82, 1) if is_today else (0.98, 0.99, 0.97, 1)
            card = MDCard(
                orientation="vertical",
                radius=[dp(14)],
                padding=[dp(12), dp(10)],
                spacing=dp(5),
                size_hint_y=None,
                height=dp(148),
                elevation=2 if is_today else 0,
            )

            hdr = MDBoxLayout(orientation="horizontal",
                              size_hint_y=None, height=dp(26))
            hdr.add_widget(MDLabel(
                text=DAYS_RU[i],
                font_style="Subtitle2", bold=True,
                theme_text_color="Primary",
            ))
            d_lbl = f"{day_date.day} {MONTHS_RU[day_date.month-1]}"
            if is_today:
                d_lbl += "  · Сегодня"
            hdr.add_widget(MDLabel(
                text=d_lbl,
                font_style="Caption",
                theme_text_color="Secondary",
                halign="right",
            ))
            card.add_widget(hdr)

            for mk in ("breakfast","lunch","dinner"):
                name = day_plan.get(mk,"")
                slot = MDBoxLayout(orientation="horizontal",
                                   size_hint_y=None, height=dp(30),
                                   spacing=dp(6))
                slot.add_widget(MDLabel(
                    text=MEAL_LABELS[mk],
                    font_style="Caption",
                    theme_text_color="Custom",
                    text_color=theme.accent_text(),
                    size_hint=(None,1), width=dp(78),
                ))
                if name:
                    slot.add_widget(MDLabel(text=name, font_style="Body2",
                                            theme_text_color="Primary"))
                    del_btn = TapIcon(
                        icon="close",
                        color=(0.6, 0.2, 0.1, 1),
                        size_dp=26,
                    )
                    del_btn.bind(on_release=lambda x, ds=date_str, mk2=mk:
                                 self._delete_meal(ds, mk2))
                    slot.add_widget(del_btn)
                else:
                    slot.add_widget(MDLabel(text="не запланировано",
                                            font_style="Body2",
                                            theme_text_color="Secondary"))
                    add_btn = TapIcon(
                        icon="plus-circle-outline",
                        color=(0.18, 0.40, 0.05, 1),
                        size_dp=28,
                        font_style="Body1",
                    )
                    add_btn.bind(on_release=lambda x, ds=date_str, mk2=mk:
                                 self._open_add(ds, mk2))
                    slot.add_widget(add_btn)
                card.add_widget(slot)

            self.plan_box.add_widget(card)

    def _open_add(self, date_str, meal_key):
        self._pending = (date_str, meal_key)
        self._selected_recipe_id = None

        container = MDBoxLayout(
            orientation="vertical", spacing=dp(8),
            size_hint_y=None, height=dp(260),
        )

        self.text_field = MDTextField(
            hint_text="Впишите блюдо или найдите рецепт...",
            mode="rectangle",
            text_color_normal=(0.1, 0.1, 0.1, 1),
        )
        if self.pending_recipe:
            self.text_field.text = self.pending_recipe.get("name", "")
            self._selected_recipe_id = self.pending_recipe.get("id")
            self.pending_recipe = None
        self.text_field.bind(text=self._on_picker_search)
        container.add_widget(self.text_field)

        hint = MDLabel(
            text="Найдите рецепт из базы — тогда его ингредиенты попадут\nв автосписок покупок. Либо впишите что угодно от руки.",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(36),
        )
        container.add_widget(hint)

        results_scroll = MDScrollView()
        self.results_box = MDBoxLayout(
            orientation="vertical", spacing=dp(4),
            size_hint_y=None, adaptive_height=True,
        )
        results_scroll.add_widget(self.results_box)
        container.add_widget(results_scroll)

        self.dialog = MDDialog(
            title=MEAL_LABELS[meal_key],
            type="custom",
            content_cls=container,
            buttons=[
                MDRaisedButton(text="Сохранить как текст", on_release=self._save_meal),
                MDRaisedButton(text="Отмена", on_release=lambda x: self.dialog.dismiss()),
            ],
        )
        self.dialog.open()
        self._on_picker_search(self.text_field, self.text_field.text)

    def _on_picker_search(self, instance, value):
        theme.safe_clear(self.results_box)
        if not value or len(value.strip()) < 2:
            return
        db = App.get_running_app().db
        matches = db.get_all_recipes(search=value.strip())[:6]
        for r in matches:
            btn = MDRaisedButton(
                text=r['name'],
                size_hint=(1, None), height=dp(40),
                elevation=0,
            )
            btn.bind(on_release=lambda x, rec=r: self._pick_recipe(rec))
            self.results_box.add_widget(btn)

    def _pick_recipe(self, recipe):
        if not self._pending:
            return
        date_str, mk = self._pending
        App.get_running_app().db.set_meal(date_str, mk, recipe["name"], recipe_id=recipe["id"])
        if self.dialog:
            self.dialog.dismiss()
        self._load()

    def _save_meal(self, *a):
        if not self._pending: return
        name = self.text_field.text.strip()
        if name:
            date_str, mk = self._pending
            App.get_running_app().db.set_meal(date_str, mk, name, recipe_id=self._selected_recipe_id)
            self.dialog.dismiss()
            self._load()

    def _delete_meal(self, date_str, meal_key):
        App.get_running_app().db.delete_meal(date_str, meal_key)
        self._load()

    def _generate_shopping_list(self):
        db = App.get_running_app().db
        added, already_have = db.generate_shopping_list_for_week(self.monday)
        if added == 0 and already_have == 0:
            self._info_dialog(
                "Список покупок",
                "На эту неделю пока нет рецептов из базы.\n"
                "Добавьте блюдо через поиск рецептов (не просто текстом),\n"
                "чтобы его ингредиенты попали в список покупок.",
            )
            return
        msg = f"Добавлено в список покупок: {added}"
        if already_have:
            msg += f"\nУже есть в холодильнике, пропущено: {already_have}"
        self._info_dialog("Готово", msg, go_to_shopping=True)

    def _info_dialog(self, title, text, go_to_shopping=False):
        buttons = []
        dlg_holder = {}

        def _close(*a):
            dlg_holder["dlg"].dismiss()

        def _open_shopping(*a):
            dlg_holder["dlg"].dismiss()
            App.get_running_app().root.current = "shopping"

        buttons.append(MDRaisedButton(text="Ок", on_release=_close))
        if go_to_shopping:
            buttons.append(MDRaisedButton(text="К списку покупок", on_release=_open_shopping))

        dlg = MDDialog(title=title, text=text, buttons=buttons)
        dlg_holder["dlg"] = dlg
        dlg.open()

    def _back(self):
        App.get_running_app().root.current = "home"

    def on_enter(self):
        self._load()
        if self.pending_recipe:
            today = str(date.today())
            self._open_add(today, "dinner")