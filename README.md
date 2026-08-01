# МоёМеню — Приложение с рецептами для Android

## Структура проекта

```
recipe_app/
├── main.py                  # Точка входа, инициализация приложения
├── requirements.txt         # Python зависимости
├── buildozer.spec           # Конфиг для сборки APK под Android
├── data/
│   ├── __init__.py
│   └── database.py          # SQLite: рецепты, меню, холодильник, история
└── screens/
    ├── __init__.py
    ├── home.py              # Главный экран (нижняя навигация)
    ├── recipes.py           # Список рецептов + поиск + категории
    ├── recipe_detail.py     # Полный рецепт: ингредиенты, шаги
    ├── meal_plan.py         # Меню на неделю (завтрак/обед/ужин)
    ├── calendar_screen.py   # Календарь + история приготовлений
    ├── fridge.py            # Холодильник + подбор рецептов
    ├── favorites.py         # Избранные рецепты
    └── add_recipe.py        # Добавить свой рецепт
```

## Быстрый запуск (десктоп / тест)

```bash
# 1. Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Запустите приложение
python main.py
```

## Сборка APK для Android

```bash
# Установите buildozer
pip install buildozer

# Linux: установите системные зависимости
sudo apt install -y python3-pip build-essential git python3-dev \
    ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev \
    libsdl2-ttf-dev libportmidi-dev libswscale-dev libavformat-dev \
    libavcodec-dev zlib1g-dev

# Первая сборка (скачает NDK/SDK автоматически, ~20 мин)
buildozer android debug

# APK будет в ./bin/moemenu-1.0-armeabi-v7a-debug.apk
# Установите на телефон через ADB:
buildozer android deploy run
```

### Сборка через GitHub Actions (без установки Android SDK/NDK локально)

В репозитории уже настроен воркфлоу `.github/workflows/build-android.yml`.
Он сам поднимает Android SDK/NDK и собирает APK в облаке — не нужно
ничего ставить на свой компьютер.

1. Запушьте проект (с этим файлом и `buildozer.spec`) в свой репозиторий на GitHub.
2. Сборка запустится автоматически при пуше в ветку `main`/`master`,
   если менялись `.py`-файлы, `buildozer.spec`, `requirements.txt` или `assets/`.
   Либо запустите вручную: вкладка **Actions** → **Build Android APK** →
   **Run workflow**.
3. Первая сборка идёт долго (обычно 20-40 минут — скачивается и
   компилируется Android SDK/NDK), следующие — намного быстрее благодаря
   кэшу (`actions/cache`, ключ зависит от содержимого `buildozer.spec`).
4. Когда сборка зелёная — зайдите в неё, внизу страницы будет раздел
   **Artifacts** → `moemenu-debug-apk`. Скачайте архив, внутри — готовый
   `.apk`, можно сразу устанавливать на телефон (потребуется разрешить
   установку из неизвестных источников).

Собирается debug-версия (для тестирования, самоподписанная). Для
публикации в Google Play нужна `release`-сборка с собственной подписью
(отдельная тема — скажите, если понадобится, добавлю).

## Функциональность

| Экран          | Возможности |
|----------------|-------------|
| 📖 Рецепты      | Список, поиск, фильтр по категориям, избранное |
| 📄 Рецепт       | Ингредиенты, шаги, добавить в историю |
| 📅 Меню         | Планирование завтрак/обед/ужин на неделю |
| 🗓 Календарь    | Выбор даты, план на день, история |
| 🧊 Холодильник  | Продукты, подбор рецептов, список покупок |
| ⭐ Избранное    | Сохранённые рецепты |
| ✏️ Добавить     | Создание своих рецептов |

## База данных (SQLite)

- `recipes` — рецепты (встроенные + свои)
- `meal_plan` — меню на дни
- `cook_history` — история приготовлений
- `fridge` — содержимое холодильника

## Расширение проекта

### Добавить поиск рецептов из интернета
```python
# В data/api.py
import requests

def search_recipes_online(query: str):
    # Используйте TheMealDB API (бесплатно):
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={query}"
    r = requests.get(url, timeout=10)
    data = r.json()
    return data.get("meals") or []
```

### Добавить фото из интернета
```python
# В screens/recipe_detail.py — загрузка изображения по URL
from kivy.network.urlrequest import UrlRequest
from kivy.uix.image import AsyncImage

img = AsyncImage(source=recipe["image_url"], allow_stretch=True)
```
