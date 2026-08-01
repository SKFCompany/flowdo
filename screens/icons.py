"""
Соответствия "смысл -> иконка Material Design Icons".

История вопроса: изначально везде использовались обычные Unicode-эмодзи
(🍕⭐📌 и т.д.). На Windows-сборке Kivy (kivy_deps.sdl2) выяснился
подтверждённый баг text-провайдера "sdl2": Unicode-символы за пределами
BMP (код U+10000 и выше — а это почти все современные эмодзи, включая
все продуктовые/природные пиктограммы) обрезаются до младших 16 бит перед
поиском глифа в шрифте (see: github.com/kivy/kivy/issues/2761). Из-за
этого 🍕 (U+1F355) фактически ищется в шрифте как U+F355 — случайный не
существующий символ, вне зависимости от того, какой шрифт подключён (в
этом проекте перепробованы три: вариативный NotoEmoji, статический
NotoEmoji, системный Segoe UI Emoji — результат одинаковый).

Собственные иконки KivyMD (Material Design Icons, шрифт "Icons",
зарегистрированный самим KivyMD) на этой же Windows-сборке РАБОТАЮТ
(проверено: шестерёнка настроек, домик, стрелки календаря, иконка
корзины покупок в интерфейсе отображались нормально). Поэтому вместо
Unicode-эмодзи используем иконки из этого шрифта везде, где раньше было
"чистое" эмодзи (не смешанное с кириллицей в той же строке).
"""

from kivymd.icon_definitions import md_icons

FALLBACK_ICON = "silverware-fork-knife"

# Категория рецепта -> иконка (используется как заглушка фото рецепта,
# когда картинка не загрузилась/не задана)
CATEGORY_ICONS = {
    "Завтрак": "egg-fried",
    "Суп": "pot-steam-outline",
    "Салат": "food-apple-outline",
    "Основное": "silverware-fork-knife",
    "Паста": "pasta",
    "Десерт": "cupcake",
    "Напиток": "tea",
}

MEAL_TYPE_ICONS = {
    "breakfast": "egg-fried",
    "lunch": "pot-steam-outline",
    "dinner": "silverware-fork-knife",
}

TAG_ICONS = {
    "Вегетарианское": "leaf",
    "Острое": "chili-hot",
    "Без глютена": "grain",
}

GREETING_ICONS = {
    "morning": "weather-sunny",
    "day": "weather-partly-cloudy",
    "evening": "weather-sunset",
    "night": "weather-night",
}

MENU_SECTION_ICONS = {
    "recipes": "book-open-page-variant-outline",
    "meal_plan": "calendar-month-outline",
    "calendar": "calendar-text-outline",
    "fridge": "fridge-outline",
    "shopping": "cart-outline",
    "favorites": "star-outline",
}


def icon_char(name, default=FALLBACK_ICON):
    """Возвращает символ шрифта Icons для заданного имени MDI-иконки.
    Если имя не существует в этой версии KivyMD — берёт default, чтобы
    никогда не выбросить KeyError из-за опечатки/версии библиотеки."""
    return md_icons.get(name, md_icons[default])


def category_icon(category):
    return icon_char(CATEGORY_ICONS.get(category, FALLBACK_ICON))


def meal_type_icon(meal_type):
    return icon_char(MEAL_TYPE_ICONS.get(meal_type, FALLBACK_ICON))
