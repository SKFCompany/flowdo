[app]
title = FlowDo
package.name = flowdo
package.domain = org.flowdo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 4.0

# Иконка приложения (значок на рабочем столе / в списке приложений) и
# экран загрузки. icon.filename — обычная плоская иконка (для старых
# Android и как запасной вариант). icon.adaptive_* — современная
# adaptive-иконка (Android 8.0+): система сама накладывает свою маску
# (круг/квадрат/капля в зависимости от прошивки), поэтому фон и передний
# план — отдельные слои.
icon.filename = %(source.dir)s/icons/icon.png
icon.adaptive_foreground.filename = %(source.dir)s/icons/icon_fg.png
icon.adaptive_background.filename = %(source.dir)s/icons/icon_bg.png
presplash.filename = %(source.dir)s/icons/presplash.png
android.presplash_color = #F0714A

requirements = python3==3.14.2,kivy==2.3.1,kivymd==1.2.0,plyer,fpdf2,fonttools,defusedxml,openpyxl,et_xmlfile
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, RECORD_AUDIO, POST_NOTIFICATIONS, WAKE_LOCK, FOREGROUND_SERVICE, FOREGROUND_SERVICE_SPECIAL_USE, RECEIVE_BOOT_COMPLETED, SCHEDULE_EXACT_ALARM, USE_EXACT_ALARM
android.api = 34
android.minapi = 23
p4a.extra_args = --allow-minsdk-ndkapi-mismatch
android.ndk = 27.3.13750724
android.ndk_api = 21
android.archs = arm64-v8a
android.build_tools_version = 34.0.0
android.sdk_path = /usr/local/lib/android/sdk
android.ndk_path = /usr/local/lib/android/sdk/ndk/27.3.13750724
orientation = portrait
android.add_resources = res

# ВАЖНО: ключа "android.manifestmodifications" в buildozer/p4a НЕ
# существует — он молча игнорировался, поэтому <receiver> так и не
# попадали в реальный AndroidManifest.xml.
#
# Правильный ключ "android.extra_manifest_application_arguments" ТОЖЕ не
# использовать — в текущей связке buildozer/p4a это подтверждённый баг
# апстрима (имя опции — подстрока другого существующего аргумента
# парсера), из-за которого кавычки внутри XML портятся при сборке
# командной строки вне зависимости от того ' или " использовать, и
# processDebugMainManifest падает с "Error parsing AndroidManifest.xml".
#
# Обходим это p4a-хуком (p4a_hook.py, лежит в корне репозитория) — он
# правит AndroidManifest.xml напрямую в Python, без командной строки:
p4a.hook = p4a_hook.py

services = Reminder:service/reminder.py:foreground

# BootReceiver.java / AlarmNotificationReceiver.java — компилируются как
# часть APK. Папка должна содержать
# java_src/org/flowdo/flowdo/BootReceiver.java (путь = package).
android.add_src = java_src

# Для отправки файлов через "Поделиться" нужен FileProvider
android.add_xml = res/xml/file_provider_paths.xml

# FileProvider (androidx.core.content.FileProvider) используется для
# отправки задачи файлом (см. p4a_hook.py — регистрирует <provider> в
# манифесте) — без androidx-зависимости класс FileProvider не соберётся.
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.12.0

[buildozer]
log_level = 2
warn_on_root = 1
