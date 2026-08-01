"""
Общие переиспользуемые виджеты для экранов.
"""

from kivy.uix.image import Image, AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.label import MDLabel
from kivymd.icon_definitions import md_icons

from data.image_cache import get_cached_path, cache_in_background
from screens.icons import icon_char, category_icon, FALLBACK_ICON

# Шрифт иконок Material Design Icons — регистрируется самим KivyMD под
# именем "Icons". Используем его вместо Unicode-эмодзи везде, где текст —
# это ЧИСТО иконка без кириллицы в той же строке (см. подробное
# объяснение в screens/icons.py — почему не обычные emoji).
ICON_FONT = "Icons"


def build_recipe_image(url, category=None, font_style="H2", icon_override=None):
    """
    Возвращает виджет для фото рецепта:

    1. Если картинка уже закэширована на диске — показываем её мгновенно,
       без сети (обычный Image, не AsyncImage).
    2. Если нет — грузим по URL через AsyncImage и в фоне сохраняем
       в кэш на будущее.
    3. Если картинки нет вовсе, либо загрузка не удалась (нет интернета,
       битая ссылка, 404) — показываем иконку. Если у рецепта есть своя
       валидная иконка Material Design Icons (icon_override — так
       пользователь выбирает "иконку блюда" при добавлении своего
       рецепта в screens/add_recipe.py) — используем её, иначе берём
       иконку по категории рецепта. Старые рецепты, где в этом поле
       исторически хранился обычный Unicode-эмодзи (не имя MDI-иконки),
       просто корректно откатываются на иконку категории.
    """
    if not url:
        return _icon_label(category, font_style, icon_override)

    cached = get_cached_path(url)
    if cached:
        return Image(source=cached, allow_stretch=True, keep_ratio=False)

    img = AsyncImage(source=url, allow_stretch=True, keep_ratio=False)
    # ВАЖНО: Kivy иногда дёргает on_error не из главного потока (виден
    # реальный краш "Cannot change graphics instruction outside the main
    # Kivy thread" в логе на Windows-сборке) — оборачиваем в
    # Clock.schedule_once, чтобы замена виджета гарантированно случалась
    # в главном потоке независимо от того, откуда пришло событие.
    img.bind(on_error=lambda instance, *a: Clock.schedule_once(
        lambda dt: _replace_with_icon(instance, category, font_style, icon_override)
    ))
    cache_in_background(url)
    return img


def _replace_with_icon(instance, category, font_style, icon_override=None):
    # Если on_error срабатывает ПОСЛЕ того, как карточку уже успели убрать
    # с экрана (например, список рецептов пересобрали раньше, чем сеть
    # ответила об ошибке) — instance.parent может ещё существовать
    # (внутренняя ссылка img_box -> AsyncImage никуда не делась), но сам
    # виджет уже не часть видимого дерева. Создавать замену в этом случае
    # смысла нет: она осядет на "осиротевшем" поддереве, до которого не
    # дотянется screens.theme.safe_clear() — и MDLabel всё равно навсегда
    # подпишется на theme_cls. get_root_window() надёжно отличает "всё ещё
    # на экране" от "уже выброшено, просто ещё не собрано сборщиком мусора".
    if instance.get_root_window() is None:
        return
    parent = instance.parent
    if not parent:
        return
    try:
        idx = parent.children.index(instance)
    except ValueError:
        idx = 0
    parent.remove_widget(instance)
    parent.add_widget(_icon_label(category, font_style, icon_override), index=idx)


def _icon_label(category, font_style, icon_override=None):
    if icon_override and icon_override in md_icons:
        text = md_icons[icon_override]
    else:
        text = category_icon(category)
    return MDLabel(
        text=text,
        font_style=font_style,
        font_name=ICON_FONT,
        halign="center",
        valign="center",
    )


class TapIcon(ButtonBehavior, MDLabel):
    """
    Лёгкая замена MDIconButton для мест, где виджет пересобирается очень
    часто (списки рецептов/покупок/холодильника/меню недели).

    Почему не MDIconButton: он использует внутренние KV-шаблонные
    привязки к общему app.theme_cls, которые не освобождаются
    автоматически при уничтожении виджета — даже explicit
    screens.theme.safe_clear() их не ловит (у kv-правил нет привычного
    __self__, ссылающегося на сам виджет). В экранах, которые
    пересобирают список при каждом обновлении данных, это давало
    реальную и растущую утечку.

    icon — имя иконки Material Design Icons (например "star",
    "close-circle-outline"), НЕ Unicode-эмодзи — см. screens/icons.py,
    почему обычные emoji не подходят на Windows-сборке Kivy.
    """

    def __init__(self, icon, color=None, size_dp=36, **kwargs):
        super().__init__(**kwargs)
        self.text = icon_char(icon)
        self.font_name = ICON_FONT
        self.halign = "center"
        self.valign = "center"
        self.size_hint = (None, None)
        self.size = (dp(size_dp), dp(size_dp))
        if "font_style" not in kwargs:
            self.font_style = "H6"
        if color:
            self.theme_text_color = "Custom"
            self.text_color = color

    def set_icon(self, icon):
        self.text = icon_char(icon)
