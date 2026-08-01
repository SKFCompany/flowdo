"""
CalendarScreen v2 — с кнопкой назад
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton, MDIconButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.app import App
from screens import theme
from screens.icons import category_icon
from datetime import date, timedelta
import calendar

DAYS_SHORT = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
MONTHS_RU  = ["Январь","Февраль","Март","Апрель","Май","Июнь",
               "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
MEAL_LABELS = {"breakfast":"Завтрак","lunch":"Обед","dinner":"Ужин","any":""}


class CalendarScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        today = date.today()
        self.view_year  = today.year
        self.view_month = today.month
        self.selected_day = today
        self._last_signature = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")

        toolbar = MDTopAppBar(
            title="Календарь",
            md_bg_color=(0.18, 0.40, 0.05, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self._back()]],
        )
        root.add_widget(toolbar)

        nav = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                          height=dp(44), padding=[dp(4), 0],
                          md_bg_color=theme.chip_bg())
        nav.add_widget(MDIconButton(icon="chevron-left",
                                    on_release=lambda x: self._prev_month()))
        self.month_label = MDLabel(text="", halign="center",
                                   font_style="Subtitle1", bold=True,
                                   theme_text_color="Primary")
        nav.add_widget(self.month_label)
        nav.add_widget(MDIconButton(icon="chevron-right",
                                    on_release=lambda x: self._next_month()))
        root.add_widget(nav)

        day_hdr = GridLayout(cols=7, size_hint_y=None, height=dp(28),
                             padding=[dp(8), 0])
        for d in DAYS_SHORT:
            day_hdr.add_widget(MDLabel(text=d, halign="center",
                                       font_style="Caption",
                                       theme_text_color="Secondary"))
        root.add_widget(day_hdr)

        self.cal_grid = GridLayout(cols=7, size_hint_y=None,
                                   padding=[dp(8), dp(2)], spacing=dp(2))
        root.add_widget(self.cal_grid)

        self.day_detail = MDCard(
            orientation="vertical", radius=[dp(12)], padding=dp(12),
            size_hint_y=None, height=dp(1),
        )
        root.add_widget(self.day_detail)

        scroll = MDScrollView()
        self.history_box = MDBoxLayout(
            orientation="vertical", spacing=dp(4),
            padding=[dp(12), dp(8)], adaptive_height=True,
        )
        scroll.add_widget(self.history_box)
        root.add_widget(scroll)
        self.add_widget(root)

    def _prev_month(self):
        self.view_month -= 1
        if self.view_month < 1:
            self.view_month = 12; self.view_year -= 1
        self._render()

    def _next_month(self):
        self.view_month += 1
        if self.view_month > 12:
            self.view_month = 1; self.view_year += 1
        self._render()

    def _render(self):
        db = App.get_running_app().db
        first    = date(self.view_year, self.view_month, 1)
        last_day = calendar.monthrange(self.view_year, self.view_month)[1]
        plan_rows = db.get_week_plan(first)
        plan_dates = frozenset(r["plan_date"] for r in plan_rows)
        today = date.today()
        day_plan = db.get_day_plan(str(self.selected_day))
        history = db.get_history(limit=20)

        # Пересборка сетки календаря + истории — не бесплатна, и раньше
        # происходила при КАЖДОМ входе на экран, даже если пользователь
        # просто вернулся назад, ничего не поменяв. Сравниваем "подпись"
        # того, что реально должно быть на экране, с прошлой — если
        # ничего не изменилось, оставляем уже построенное как есть.
        signature = (
            self.view_year, self.view_month, plan_dates, self.selected_day,
            tuple((d.get("recipe_name"), d.get("meal_type")) for d in day_plan),
            tuple((h.get("recipe_name"), h.get("cooked_at")) for h in history),
        )
        if signature == self._last_signature:
            return
        self._last_signature = signature

        self.month_label.text = f"{MONTHS_RU[self.view_month-1]} {self.view_year}"

        theme.safe_clear(self.cal_grid)
        first_wd = first.weekday()
        rows_n   = (first_wd + last_day + 6) // 7
        self.cal_grid.height = dp(rows_n * 40)

        for _ in range(first_wd):
            self.cal_grid.add_widget(MDLabel(text=""))

        for dn in range(1, last_day + 1):
            dd = date(self.view_year, self.view_month, dn)
            ds = str(dd)
            is_today = dd == today
            is_sel   = dd == self.selected_day
            has_plan = ds in plan_dates

            bg  = theme.ACCENT if is_today \
                  else (theme.chip_bg() if is_sel else (0,0,0,0))
            tc  = (1,1,1,1) if is_today else \
                  (theme.accent_text() if is_sel else None)

            label = f"{dn}·" if has_plan else str(dn)
            btn = MDFlatButton(
                text=label,
                size_hint=(None, None), size=(dp(38), dp(36)),
                md_bg_color=bg,
                theme_text_color="Custom" if tc else "Primary",
                text_color=tc if tc else (0, 0, 0, 1),
            )
            btn.bind(on_release=lambda x, d2=dd: self._select_day(d2))
            self.cal_grid.add_widget(btn)

        self._show_day_detail()
        self._load_history()

    def _select_day(self, dd):
        self.selected_day = dd
        self._render()

    def _show_day_detail(self):
        theme.safe_clear(self.day_detail)
        db = App.get_running_app().db
        ds = str(self.selected_day)
        day_plan = db.get_day_plan(ds)
        if day_plan:
            h = dp(20 + len(day_plan)*30 + 16)
            self.day_detail.height = h
            self.day_detail.add_widget(MDLabel(
                text=f"{self.selected_day.day} {MONTHS_RU[self.selected_day.month-1]}",
                font_style="Subtitle2", bold=True,
                theme_text_color="Primary", size_hint_y=None, height=dp(28),
            ))
            for row in day_plan:
                ml = MEAL_LABELS.get(row["meal_type"], "")
                txt = f"{ml}: {row.get('recipe_name','—')}" if ml \
                      else row.get("recipe_name","—")
                self.day_detail.add_widget(MDLabel(
                    text=txt, font_style="Body2",
                    theme_text_color="Primary",
                    size_hint_y=None, height=dp(26),
                ))
        else:
            self.day_detail.height = dp(1)

    def _load_history(self):
        db = App.get_running_app().db
        history = db.get_history(limit=20)
        theme.safe_clear(self.history_box)
        self.history_box.add_widget(MDLabel(
            text="История приготовлений",
            font_style="Subtitle1", bold=True,
            theme_text_color="Primary",
            size_hint_y=None, height=dp(32),
        ))
        if not history:
            self.history_box.add_widget(MDLabel(
                text="Ещё ничего не готовили",
                halign="center", theme_text_color="Secondary",
                size_hint_y=None, height=dp(48),
            ))
            return
        for h in history:
            row = MDBoxLayout(orientation="horizontal",
                              size_hint_y=None, height=dp(48),
                              spacing=dp(10), padding=[0, dp(4)])
            circle = MDCard(size_hint=(None, None), size=(dp(38), dp(38)),
                            radius=[dp(19)], md_bg_color=theme.chip_bg())
            circle.add_widget(MDLabel(text=category_icon(h.get("recipe_emoji")),
                                      halign="center", valign="center",
                                      font_name="Icons", font_style="Subtitle1"))
            row.add_widget(circle)
            info = MDBoxLayout(orientation="vertical")
            info.add_widget(MDLabel(text=h["recipe_name"], font_style="Subtitle2",
                                    theme_text_color="Primary"))
            ml = MEAL_LABELS.get(h.get("meal_type",""), "")
            info.add_widget(MDLabel(
                text=f"{h.get('day', h.get('cooked_at','')[:10])}  {ml}".strip(),
                font_style="Caption", theme_text_color="Secondary"))
            row.add_widget(info)
            self.history_box.add_widget(row)

    def _back(self):
        App.get_running_app().root.current = "home"

    def on_enter(self):
        self._render()