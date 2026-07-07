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
питоновский str.replace().
"""
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


def _patch(manifest_file: Path):
    if not manifest_file.exists():
        print(f"[p4a_hook] WARNING: manifest not found at {manifest_file}")
        return
    old_manifest = manifest_file.read_text(encoding="utf-8")

    if "org.flowdo.flowdo.AlarmNotificationReceiver" in old_manifest:
        print("[p4a_hook] receivers already present, skipping")
        return

    if "</application>" not in old_manifest:
        raise RuntimeError(
            "[p4a_hook] </application> tag not found in AndroidManifest.xml — "
            "cannot insert receivers")

    new_manifest = old_manifest.replace(
        "</application>", RECEIVERS_XML + "\n</application>")
    manifest_file.write_text(new_manifest, encoding="utf-8")
    print(f"[p4a_hook] receivers inserted into {manifest_file}")


def after_apk_build(toolchain):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    _patch(manifest_file)


def before_apk_build(toolchain):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    _patch(manifest_file)
