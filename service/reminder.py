# ═══════════════════════════════════════════════════════════════════════════
#  service/reminder.py
#  Фоновая служба Android для Flow·Do.
#
#  Запускается из main.py через mActivity.startService(...).
#  Работает в отдельном процессе/потоке, читает tasks.json и config.json
#  из приватного хранилища приложения и шлёт push-уведомления через
#  android.app.NotificationManager, даже если основное приложение закрыто.
#
#  ВАЖНО: этот файл должен лежать по пути  service/reminder.py
#  относительно main.py, и в buildozer.spec должна быть строка:
#
#      services = Reminder:service/reminder.py
#
#  (имя "Reminder" — произвольное, но должно совпадать с тем, что
#   указано в _start_notification_service в main.py через имя класса
#   ServiceReminder — p4a генерирует имя класса из имени службы:
#   "Reminder" -> "ServiceReminder")
# ═══════════════════════════════════════════════════════════════════════════

import json
import os
import time
from datetime import datetime, timedelta

# ── Сопоставление текста напоминания со смещением в минутах ────────────────
REMIND_OFFSETS = {
    "За 10 минут": 10,
    "За 30 минут": 30,
    "За 1 час": 60,
    "За 1 день": 60 * 24,
}

CHECK_INTERVAL_SEC = 30  # как часто проверять (секунды)


def _get_storage_path():
    """Путь к приватному хранилищу приложения — там же лежат tasks.json
    и config.json, которые сохраняет основное приложение через JsonStore."""
    try:
        from android.storage import app_storage_path
        return app_storage_path()
    except Exception:
        # Фоллбэк для отладки на десктопе
        return os.path.expanduser("~")


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _send_notification(title, message):
    """Отправляет системное Android-уведомление напрямую через
    NotificationManager (без plyer, т.к. plyer внутри Service иногда
    некорректно инициализируется)."""
    try:
        from jnius import autoclass, cast
        PythonService = autoclass("org.kivy.android.PythonService")
        Context = autoclass("android.content.Context")
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        Build = autoclass("android.os.Build")
        String = autoclass("java.lang.String")

        service = PythonService.mService
        ctx = service.getApplicationContext()
        notif_manager = cast(
            "android.app.NotificationManager",
            ctx.getSystemService(Context.NOTIFICATION_SERVICE)
        )

        channel_id = "flowdo_reminders"
        # Android 8+ требует канал уведомлений
        if Build.VERSION.SDK_INT >= 26:
            channel = NotificationChannel(
                channel_id,
                cast("java.lang.CharSequence", String("Flow\u00b7Do Напоминания")),
                NotificationManager.IMPORTANCE_HIGH
            )
            notif_manager.createNotificationChannel(channel)

        builder = NotificationBuilder(ctx, channel_id)
        builder.setContentTitle(cast("java.lang.CharSequence", String(title)))
        builder.setContentText(cast("java.lang.CharSequence", String(message)))
        builder.setSmallIcon(ctx.getApplicationInfo().icon)
        builder.setAutoCancel(True)
        builder.setPriority(2)  # PRIORITY_HIGH

        notif_id = int(time.time()) % 100000
        notif_manager.notify(notif_id, builder.build())
    except Exception as e:
        # Логируем в файл для отладки (logcat иногда недоступен из службы)
        try:
            log_path = os.path.join(_get_storage_path(), "service_error.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: notify error: {e}\n")
        except Exception:
            pass


def _check_reminders(base_path, notified_keys):
    """Проверяет tasks.json на предмет задач, время которых наступило,
    и возвращает обновлённый set notified_keys.

    Формат tasks.json (пишется через kivy.storage.jsonstore.JsonStore,
    self.store.put("tasks", items=[...])):
        {"tasks": {"items": [ {...task...}, {...task...} ]}}
    """
    tasks_path = os.path.join(base_path, "tasks.json")
    data = _load_json(tasks_path)

    items = []
    if isinstance(data, dict):
        tasks_section = data.get("tasks", {})
        if isinstance(tasks_section, dict):
            items = tasks_section.get("items", [])

    now = datetime.now()
    changed = False

    for t in items:
        if not isinstance(t, dict) or t.get("done"):
            continue
        date_s = t.get("date", "")
        time_s = t.get("time", "")
        if not date_s or not time_s:
            continue
        try:
            task_dt = datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M")
        except Exception:
            continue

        tid = t.get("id", "")
        title = t.get("title", "Задача")

        # 1) Уведомление в момент времени задачи
        key_time = f"{tid}:time:{date_s}_{time_s}"
        if key_time not in notified_keys:
            if task_dt <= now <= task_dt + timedelta(minutes=2):
                _send_notification(f"Время задачи: {title}", "Flow\u00b7Do")
                notified_keys.add(key_time)
                changed = True

        # 2) Уведомление-напоминание заранее
        remind_s = t.get("reminder", "")
        offset = REMIND_OFFSETS.get(remind_s)
        if offset:
            remind_dt = task_dt - timedelta(minutes=offset)
            key_remind = f"{tid}:remind:{date_s}_{time_s}_{remind_s}"
            if key_remind not in notified_keys:
                if remind_dt <= now <= remind_dt + timedelta(minutes=2):
                    _send_notification(
                        f"Напоминание: {title} ({remind_s.lower()})",
                        "Flow\u00b7Do"
                    )
                    notified_keys.add(key_remind)
                    changed = True

    return notified_keys, changed


def main():
    base_path = _get_storage_path()
    keys_path = os.path.join(base_path, "service_notified_keys.json")

    # Загружаем ранее отправленные уведомления (общие с основным приложением
    # был бы идеал, но проще держать отдельный файл для службы)
    raw = _load_json(keys_path)
    notified_keys = set(raw.get("keys", [])) if isinstance(raw, dict) else set()

    while True:
        try:
            notified_keys, changed = _check_reminders(base_path, notified_keys)
            if changed:
                # подчищаем старые записи, чтобы файл не рос бесконечно
                if len(notified_keys) > 500:
                    notified_keys = set(list(notified_keys)[-300:])
                _save_json(keys_path, {"keys": list(notified_keys)})
        except Exception as e:
            try:
                log_path = os.path.join(base_path, "service_error.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now()}: loop error: {e}\n")
            except Exception:
                pass

        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()