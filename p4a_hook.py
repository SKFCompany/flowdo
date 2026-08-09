"""
p4a-хук для FlowDo.

Ключ buildozer'а `android.extra_manifest_application_arguments`
(и в целом любой флаг `--extra-manifest-application-arguments`) в текущей
связке buildozer/python-for-android содержит известный баг: имя опции
является подстрокой другого существующего аргумента парсера, из-за чего
её значение уродуется при сборке командной строки (кавычки внутри XML
экранируются накопительно, независимо от того ' или " используются) —
итоговый AndroidManifest.xml оказывается невалидным XML и
`processDebugMainManifest` падает с "Error parsing AndroidManifest.xml".

Обходим баг полностью: редактируем AndroidManifest.xml напрямую в Python,
уже ПОСЛЕ того как p4a сгенерировал его из шаблона, но ДО того как gradle
запустит фактическую сборку APK (в этот момент правки хука уже видны
gradle). Никакой командной строки, никакого экранирования — обычный
питоновский str.replace() / re.sub().
"""
import re
from pathlib import Path

RECEIVERS_XML = """
    <receiver
        android:name="org.flowdo.flowdo.AlarmNotificationReceiver"
        android:exported="false"
        android:enabled="true" />

    <receiver
        android:name="org.flowdo.flowdo.BootReceiver"
        android:exported="true"
        android:enabled="true">
        <intent-filter>
            <action android:name="android.intent.action.BOOT_COMPLETED" />
            <action android:name="android.intent.action.QUICKBOOT_POWERON" />
            <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />
        </intent-filter>
    </receiver>
"""

# FileProvider — нужен, чтобы отдавать файл задачи другим приложениям
# (мессенджер, почта и т.д.) через content:// URI вместо голого file://
# (Android 7+ запрещает file:// между приложениями — FileUriExposedException).
# Пути, которые provider разрешает раздавать, описаны в
# res/xml/file_provider_paths.xml (уже подключён в buildozer.spec через
# android.add_xml — здесь только регистрируем сам provider в манифесте).
FILEPROVIDER_XML = """
    <provider
        android:name="androidx.core.content.FileProvider"
        android:authorities="org.flowdo.flowdo.fileprovider"
        android:exported="false"
        android:grantUriPermissions="true">
        <meta-data
            android:name="android.support.FILE_PROVIDER_PATHS"
            android:resource="@xml/file_provider_paths" />
    </provider>
"""

# Intent-filter на открытие файла задачи "через" приложение — например,
# когда пользователь получил .json-файл задачи (в мессенджере, почте, из
# Загрузок) и в системном меню "Открыть с помощью" выбрал Flow·Do.
# Регистрируем на MIME "application/json": более узкий кастомный MIME-тип
# не гарантированно распознаётся файловыми менеджерами по расширению
# (они обычно определяют тип именно по системной таблице расширений),
# а "application/json" там есть всегда. Побочный эффект — Flow·Do будет
# предлагаться как один из вариантов для ЛЮБОГО .json-файла, не только
# наших: это ожидаемо и безвредно, handle_shared_file()/_apply_imported_data()
# в main.py корректно показывают ошибку импорта, если файл не наш.
VIEW_INTENT_FILTER_XML = """
        <intent-filter android:label="Открыть задачу Flow\u00b7Do">
            <action android:name="android.intent.action.VIEW" />
            <category android:name="android.intent.category.DEFAULT" />
            <category android:name="android.intent.category.BROWSABLE" />
            <data android:scheme="content" />
            <data android:scheme="file" />
            <data android:mimeType="application/json" />
        </intent-filter>
"""


def _patch(manifest_file: Path):
    if not manifest_file.exists():
        print(f"[p4a_hook] WARNING: manifest not found at {manifest_file}")
        return
    manifest = manifest_file.read_text(encoding="utf-8")
    changed = False

    if "org.flowdo.flowdo.AlarmNotificationReceiver" not in manifest:
        if "</application>" not in manifest:
            raise RuntimeError(
                "[p4a_hook] </application> tag not found — cannot insert receivers")
        manifest = manifest.replace("</application>", RECEIVERS_XML + "\n</application>")
        changed = True
        print("[p4a_hook] receivers inserted")
    else:
        print("[p4a_hook] receivers already present, skipping")

    if "org.flowdo.flowdo.fileprovider" not in manifest:
        if "</application>" not in manifest:
            raise RuntimeError(
                "[p4a_hook] </application> tag not found — cannot insert FileProvider")
        manifest = manifest.replace("</application>", FILEPROVIDER_XML + "\n</application>")
        changed = True
        print("[p4a_hook] FileProvider inserted")
    else:
        print("[p4a_hook] FileProvider already present, skipping")

    if 'android.intent.action.VIEW" />\n            <category android:name="android.intent.category.DEFAULT" />\n            <category android:name="android.intent.category.BROWSABLE" />\n            <data android:scheme="content"' not in manifest:
        # Вставляем intent-filter внутрь <activity> главной PythonActivity,
        # прямо перед её закрывающим тегом — НЕ перед </application>,
        # иначе это будет отдельная (пустая) секция вне какой-либо activity
        # и Android её просто проигнорирует.
        m = re.search(
            r'(<activity[^>]*android:name="org\.kivy\.android\.PythonActivity"[^>]*>)(.*?)(</activity>)',
            manifest, re.DOTALL)
        if not m:
            print("[p4a_hook] WARNING: PythonActivity block not found — "
                  "skipping VIEW intent-filter (share-to-open won't work, "
                  "но остальное приложение соберётся нормально)")
        else:
            new_activity_block = m.group(1) + m.group(2) + VIEW_INTENT_FILTER_XML + m.group(3)
            manifest = manifest[:m.start()] + new_activity_block + manifest[m.end():]
            changed = True
            print("[p4a_hook] VIEW intent-filter inserted into PythonActivity")
    else:
        print("[p4a_hook] VIEW intent-filter already present, skipping")

    if changed:
        manifest_file.write_text(manifest, encoding="utf-8")
        print(f"[p4a_hook] manifest updated: {manifest_file}")


def after_apk_build(toolchain):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    _patch(manifest_file)


def before_apk_build(toolchain):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    _patch(manifest_file)
