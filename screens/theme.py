"""
Единый источник цветов приложения — было размазано по 10 файлам
(каждый экран сам решал, что такое "белая карточка" или "зелёный акцент").
Теперь любой экран берёт цвета отсюда: screens.theme.screen_bg(),
screens.theme.card_bg() и т.д. — а не пишет (1, 1, 1, 1) напрямую.

Второе назначение модуля — тёмная тема: он хранит текущий режим
(light/dark) в памяти процесса и знает, как персистентно сохранить его
через Database.get_setting/set_setting (таблица meta), чтобы выбор
пользователя пережил перезапуск приложения.

Третье назначение — safe_clear()/release_theme_bindings(): обход
утечки подписок на theme_cls, которую оставляют почти все виджеты
KivyMD (см. подробности в docstring release_theme_bindings ниже).
"""

from kivy.app import App

# Акцентный зелёный — фирменный цвет бренда, одинаково хорошо читается
# и на светлом, и на тёмном фоне, поэтому не меняется между темами.
ACCENT = (0.18, 0.40, 0.05, 1)

_dark = False


def is_dark():
    return _dark


def set_dark(value):
    global _dark
    _dark = bool(value)


def load_from_db(db):
    """Вызывается один раз при старте приложения — читает сохранённый
    выбор пользователя из БД и применяет его к этому модулю."""
    set_dark(db.get_setting("dark_mode", "0") == "1")


def save_to_db(db):
    db.set_setting("dark_mode", "1" if is_dark() else "0")


def screen_bg():
    """Фон экрана целиком (за карточками)."""
    return (0.07, 0.09, 0.07, 1) if _dark else (0.96, 0.98, 0.94, 1)


def card_bg():
    """Фон обычной карточки/плитки поверх экрана."""
    return (0.15, 0.17, 0.15, 1) if _dark else (1, 1, 1, 1)


def chip_bg():
    """Фон неактивного чипа/бейджа (мягкий, приглушённый)."""
    return (0.18, 0.22, 0.17, 1) if _dark else (0.93, 0.96, 0.89, 1)


def chip_bg_soft():
    """Ещё более тихий фон (напр. плашка напоминания) — оттенок акцента."""
    return (0.14, 0.20, 0.13, 1) if _dark else (0.94, 0.98, 0.90, 1)


def accent_text():
    """Акцентный текст на карточке (напр. подпись категории). На тёмном
    фоне обычный ACCENT слишком тёмный и нечитаемый — берём светлее."""
    return (0.55, 0.85, 0.40, 1) if _dark else (0.23, 0.50, 0.07, 1)


def divider_color():
    return (0.28, 0.30, 0.28, 1) if _dark else (0.85, 0.88, 0.82, 1)


def _safe_unbind(dispatcher, **kwargs):
    try:
        dispatcher.unbind(**kwargs)
    except Exception:
        pass


# Свойства theme_cls, на которые подписываются разные виджеты KivyMD
# (MDCard, MDLabel, MDRaisedButton/MDFlatButton, MDTopAppBar, MDTextField,
# MDSwitch, MDTabs и т.д. — у каждого своё имя метода-обработчика, но все
# слушают именно эти свойства). Список составлен по исходникам kivymd
# 1.2.0 (uix/behaviors/backgroundcolor_behavior.py, uix/card/card.py,
# uix/label/label.py, uix/button/button.py, uix/toolbar/toolbar.py,
# uix/textfield/textfield.py, uix/selectioncontrol/selectioncontrol.py,
# uix/tab/tab.py) — если в новой версии KivyMD появятся новые свойства,
# их нужно будет дописать сюда.
_THEME_CLS_PROPS = (
    "theme_style", "primary_palette", "accent_palette", "material_style",
    "primary_color", "device_orientation", "disabled_hint_text_color",
)


def release_theme_bindings(widget):
    """
    KivyMD-виджеты (MDCard, MDLabel, MDRaisedButton, MDTopAppBar,
    MDTextField, MDSwitch и почти всё остальное) подписываются на общий
    app.theme_cls в своём __init__ и никогда не отписываются сами.
    theme_cls живёт всё время работы приложения, поэтому каждый экран,
    который пересобирает список виджетов при обновлении данных (рецепты,
    календарь, холодильник, покупки...), навсегда оставлял "мёртвые"
    подписки на нём. Это и есть причина нарастающего подвисания при
    каждом переходе — реальная утечка памяти и колбэков, а не выдумка.

    У каждого типа виджета своё имя метода-обработчика, и угадывать их
    все по названию ненадёжно (список меняется между версиями KivyMD).
    Поэтому вместо этого мы напрямую идём по уже подписанным
    наблюдателям theme_cls и снимаем именно те, что принадлежат (по
    идентичности объекта) виджетам, которые мы выбрасываем — какой бы
    метод не использовался внутри.

    Вызывайте на поддереве виджетов ПРЯМО ПЕРЕД тем, как его выбросить
    (перед clear_widgets()) — обычно удобнее звать safe_clear() ниже.
    """
    app = App.get_running_app()
    theme_cls = getattr(app, "theme_cls", None)
    if theme_cls is None:
        return

    to_remove = set()

    def collect(w):
        to_remove.add(w)
        for ch in list(getattr(w, "children", [])):
            collect(ch)

    collect(widget)

    for prop_name in _THEME_CLS_PROPS:
        try:
            observers = list(theme_cls.get_property_observers(prop_name))
        except Exception:
            continue
        for obs in observers:
            owner = getattr(obs, "__self__", None)
            if owner is not None and owner in to_remove:
                _safe_unbind(theme_cls, **{prop_name: obs})


def safe_clear(container):
    """
    clear_widgets(), который не течёт — сначала отвязывает всё поддерево
    от theme_cls (см. release_theme_bindings выше), потом убирает его из
    дерева виджетов.

    Важно: не используйте внутри пересобираемых списков вложенные layout'ы
    с собственной логикой в add_widget()/remove_widget() (в частности,
    FloatLayout — он в add_widget() делает child.bind(pos=self._trigger_layout),
    и если такой layout убирают через clear_widgets() у ВНЕШНЕГО контейнера,
    а не его собственный remove_widget(), эта связка не освобождается, и
    виджеты остаются в памяти навсегда — см. историю в screens/recipes.py,
    откуда FloatLayout пришлось убрать именно поэтому).
    """
    release_theme_bindings(container)
    container.clear_widgets()


def success_bg():
    """Карточка «можно приготовить прямо сейчас»."""
    return (0.10, 0.22, 0.09, 1) if _dark else (0.90, 0.96, 0.82, 1)


def success_text():
    return (0.55, 0.85, 0.45, 1) if _dark else (0.10, 0.45, 0.10, 1)


def warning_bg():
    """Карточка «нужно докупить»."""
    return (0.24, 0.19, 0.07, 1) if _dark else (0.99, 0.96, 0.88, 1)


def warning_text():
    return (0.90, 0.70, 0.30, 1) if _dark else (0.60, 0.35, 0.0, 1)
