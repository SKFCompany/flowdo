# Flow·Do — структура репозитория для сборки APK

Buildozer собирает всё **относительно того места, где лежит `buildozer.spec`**
(это и есть `source.dir = .` в спеке). Значит `buildozer.spec` должен лежать
в корне репозитория, а всё остальное — строго в тех подпапках, которые
указаны в самом спеке. Ниже — полное дерево, которое должно получиться
у вас в GitHub-репозитории.

```
ваш-репозиторий/                     ← корень репо (сюда клонируется GitHub Actions)
│
├── main.py                          ← главный файл приложения (Kivy/KivyMD)
├── buildozer.spec                   ← настройки сборки, ОБЯЗАТЕЛЬНО в корне
├── p4a_hook.py                      ← добавляет <receiver> в манифест в обход бага buildozer
│
├── service/                         ← папка фоновой службы
│   └── reminder.py                  ← сама служба (AlarmManager + цикл проверки)
│
├── java_src/                        ← Java-код, который встраивается в APK
│   └── org/                         ← путь ВНУТРИ java_src = ваш package.domain +
│       └── flowdo/                    package.name из buildozer.spec, то есть
│           └── flowdo/                package.domain=org.flowdo, package.name=flowdo
│               ├── BootReceiver.java            → пересобирает будильники после ребута
│               └── AlarmNotificationReceiver.java → показывает пуш мгновенно, без Python
│
├── res/                             ← Android-ресурсы
│   └── xml/
│       └── file_provider_paths.xml  ← нужен для "Поделиться" файлом
│
├── icons/                           ← иконка приложения + экран загрузки
│   ├── icon.png                     ← обычная плоская иконка (запасной вариант)
│   ├── icon_fg.png                  ← adaptive-иконка: передний план (галочка)
│   ├── icon_bg.png                  ← adaptive-иконка: фон (градиент), без прозрачности
│   └── presplash.png                ← экран при запуске приложения
│
└── .github/
    └── workflows/
        └── build.yml                ← один из ваших build (1).yml / build (2).yml
                                        (переименуйте в build.yml или любое имя —
                                         главное чтобы лежал именно в этой папке)
```

## Почему пути именно такие

Каждая папка привязана к конкретной строчке в `buildozer.spec`:

| Строка в buildozer.spec                                   | Что она означает                                         |
|-------------------------------------------------------------|-----------------------------------------------------------|
| `source.dir = .`                                             | всё ищется от корня репозитория                            |
| `package.domain = org.flowdo`  +  `package.name = flowdo`     | вместе дают Java/Android package `org.flowdo.flowdo`        |
| `p4a.hook = p4a_hook.py`                                      | файл должен лежать рядом со spec, в корне. Он вызывается python-for-android'ом ПОСЛЕ генерации `AndroidManifest.xml`, но ДО того как gradle его прочитает — правит файл напрямую в Python, без командной строки |
| `services = Reminder:service/reminder.py:foreground`          | служба лежит по пути `service/reminder.py` от корня         |
| `android.add_src = java_src`                                  | buildozer возьмёт ВСЁ из `java_src/` и скомпилирует как Java-исходники проекта. Внутри этой папки структура папок обязана повторять package, поэтому `java_src/org/flowdo/flowdo/BootReceiver.java` |
| `android.add_xml = res/xml/file_provider_paths.xml`           | файл должен лежать по этому пути от корня                    |
| `icon.filename` / `icon.adaptive_foreground.filename` / `icon.adaptive_background.filename` / `presplash.filename` | все четыре файла лежат в папке `icons/` от корня               |

Если поменяете `package.domain` или `package.name` в `buildozer.spec` —
обязательно поменяйте и путь к `BootReceiver.java` внутри `java_src/`, и
пакет (`package org.flowdo.flowdo;`) в первой строке обоих Java-файлов, и
XML внутри `p4a_hook.py` (`org.flowdo.flowdo.AlarmNotificationReceiver` /
`BootReceiver`) — иначе Android не найдёт классы.

## ⚠️ История двух исправлений манифеста (важно понимать, почему так)

**Попытка №1** — ключ `android.manifestmodifications`. Такого ключа в
buildozer/python-for-android **не существует**. Он не выдавал ошибку —
просто молча игнорировался при сборке, поэтому `<receiver>` никогда не
попадали в `AndroidManifest.xml`, хотя сами Java-классы честно
компилировались через `android.add_src`.

**Попытка №2** — правильный, официально существующий ключ
`android.extra_manifest_application_arguments`. Тоже не сработал — но
уже по другой причине: это **подтверждённый баг апстрима** в
buildozer/p4a (имя опции является подстрокой другого существующего
аргумента парсера командной строки), из-за которого кавычки внутри
переданного XML портятся при сборке командной строки — причём
независимо от того, использовать в XML `'` или `"`. Манифест на выходе
получался невалидным, и `processDebugMainManifest` падал с
`Error parsing AndroidManifest.xml`.

**Финальное решение** — `p4a.hook = p4a_hook.py`. Хук — это обычный
Python-файл, который python-for-android импортирует и выполняет
напрямую в своём процессе (без прохождения через командную строку и
её экранирование). Функция `after_apk_build`/`before_apk_build` в нём
открывает уже сгенерированный `AndroidManifest.xml` и вставляет наши
`<receiver>` перед `</application>` обычным `str.replace()` — никакой
командной строки, никакого экранирования, никаких сюрпризов.

## Что нужно сделать руками

1. Скачайте все файлы из этого чата.
2. Разложите их по дереву выше (переименуйте `main (5).py` → `main.py`,
   `buildozer (4).spec` → `buildozer.spec` и т.д. — цифры в скобках были
   добавлены при загрузке, в репозитории их быть не должно).
3. Удалите из репозитория старые `android_manifest_mod.xml` и
   `android_manifest_application.xml`, если они там остались — они
   больше не используются.
4. Закоммитьте и запушьте — GitHub Actions (`build.yml`) соберёт APK
   автоматически при пуше в `main`.

## Быстрая проверка перед пушем

Находясь в корне репозитория, выполните:

```bash
test -f buildozer.spec && echo OK: buildozer.spec
test -f main.py && echo OK: main.py
test -f p4a_hook.py && echo OK: p4a_hook.py
test -f service/reminder.py && echo OK: service/reminder.py
test -f java_src/org/flowdo/flowdo/BootReceiver.java && echo OK: BootReceiver.java
test -f java_src/org/flowdo/flowdo/AlarmNotificationReceiver.java && echo OK: AlarmNotificationReceiver.java
test -f res/xml/file_provider_paths.xml && echo OK: file_provider_paths.xml
```

Если все семь строк напечатались — структура верна, можно собирать.

