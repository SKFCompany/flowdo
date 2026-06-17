# ═══════════════════════════════════════════════════════════════════════════
#  service/reminder.py  — Фоновая служба напоминаний Flow·Do
#  p4a генерирует класс ServiceReminder из имени "Reminder" в buildozer.spec
# ═══════════════════════════════════════════════════════════════════════════

import json
import os
import time
from datetime import datetime, timedelta

REMIND_OFFSETS = {
    "За 10 минут": 10,
    "За 30 минут": 30,
    "За 1 час": 60,
    "За 1 день": 60 * 24,
}
CHECK_INTERVAL_SEC = 30


def _get_storage_path():
    try:
        from android.storage import app_storage_path
        return app_storage_path()
    except Exception:
        return os.path.expanduser("~")


def _log(msg):
    """Пишет в app_debug.log чтобы лог службы и приложения был в одном файле."""
    try:
        path = os.path.join(_get_storage_path(), "app_debug.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[SVC] {datetime.now()}: {msg}\n")
    except Exception:
        pass


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


def _start_foreground():
    """Переводит службу в foreground — без этого Android убивает её."""
    _log("_start_foreground: start")
    try:
        from jnius import autoclass, cast
        PythonService = autoclass("org.kivy.android.PythonService")
        Context = autoclass("android.content.Context")
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        BuildVersion = autoclass("android.os.Build$VERSION")
        String = autoclass("java.lang.String")

        service = PythonService.mService
        ctx = service.getApplicationContext()

        channel_id = "flowdo_service"
        notif_manager = cast("android.app.NotificationManager",
                             ctx.getSystemService(Context.NOTIFICATION_SERVICE))

        if BuildVersion.SDK_INT >= 26:
            channel = NotificationChannel(
                channel_id,
                cast("java.lang.CharSequence", String("Flow\u00b7Do")),
                NotificationManager.IMPORTANCE_LOW
            )
            channel.setShowBadge(False)
            notif_manager.createNotificationChannel(channel)
            builder = NotificationBuilder(ctx, channel_id)
        else:
            builder = NotificationBuilder(ctx)

        builder.setContentTitle(
            cast("java.lang.CharSequence", String("Flow\u00b7Do")))
        builder.setContentText(
            cast("java.lang.CharSequence", String("Напоминания активны")))
        builder.setOngoing(True)
        builder.setAutoCancel(False)

        icon_res = 0
        try:
            icon_res = ctx.getApplicationInfo().icon
        except Exception:
            pass
        if not icon_res:
            try:
                resources = ctx.getResources()
                icon_res = resources.getIdentifier(
                    "icon", "mipmap", ctx.getPackageName())
            except Exception:
                pass
        if not icon_res:
            icon_res = 17301659  # ic_dialog_info fallback
        builder.setSmallIcon(icon_res)

        if BuildVersion.SDK_INT < 26:
            builder.setPriority(-2)  # PRIORITY_MIN

        notif = builder.build()

        if BuildVersion.SDK_INT >= 29:
            # Android 10+ — startForeground с типом
            service.startForeground(1, notif, 0x40000000)  # FOREGROUND_SERVICE_TYPE_SPECIAL_USE = 0x40000000
        else:
            service.startForeground(1, notif)

        _log("_start_foreground: OK")
    except Exception as e:
        _log(f"_start_foreground: ERROR {e!r}")


def _send_notification(title, message):
    _log(f"_send_notification: '{title}'")
    try:
        from jnius import autoclass, cast
        PythonService = autoclass("org.kivy.android.PythonService")
        Context = autoclass("android.content.Context")
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        BuildVersion = autoclass("android.os.Build$VERSION")
        String = autoclass("java.lang.String")

        service = PythonService.mService
        ctx = service.getApplicationContext()
        notif_manager = cast("android.app.NotificationManager",
                             ctx.getSystemService(Context.NOTIFICATION_SERVICE))

        channel_id = "flowdo_reminders"
        if BuildVersion.SDK_INT >= 26:
            channel = NotificationChannel(
                channel_id,
                cast("java.lang.CharSequence", String("Flow\u00b7Do Напоминания")),
                NotificationManager.IMPORTANCE_HIGH
            )
            notif_manager.createNotificationChannel(channel)
            builder = NotificationBuilder(ctx, channel_id)
        else:
            builder = NotificationBuilder(ctx)

        builder.setContentTitle(cast("java.lang.CharSequence", String(title)))
        builder.setContentText(cast("java.lang.CharSequence", String(message)))
        builder.setAutoCancel(True)

        icon_res = 0
        try:
            icon_res = ctx.getApplicationInfo().icon
        except Exception:
            pass
        if not icon_res:
            try:
                resources = ctx.getResources()
                icon_res = resources.getIdentifier(
                    "icon", "mipmap", ctx.getPackageName())
            except Exception:
                pass
        if not icon_res:
            icon_res = 17301659
        builder.setSmallIcon(icon_res)

        if BuildVersion.SDK_INT < 26:
            builder.setPriority(1)

        notif_id = int(time.time()) % 100000
        notif_manager.notify(notif_id, builder.build())
        _log(f"_send_notification: notify(id={notif_id}) OK")
    except Exception as e:
        _log(f"_send_notification: ERROR {e!r}")


def _check_reminders(base_path, notified_keys):
    tasks_path = os.path.join(base_path, "tasks.json")
    data = _load_json(tasks_path)

    items = []
    if isinstance(data, dict):
        tasks_section = data.get("tasks", {})
        if isinstance(tasks_section, dict):
            items = tasks_section.get("items", [])

    now = datetime.now()
    changed = False
    _log(f"_check_reminders: {len(items)} tasks, now={now}")

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

        # 1) Уведомление в момент времени задачи (окно 5 минут)
        key_time = f"{tid}:time:{date_s}_{time_s}"
        if key_time not in notified_keys:
            if task_dt <= now <= task_dt + timedelta(minutes=5):
                _log(f"  -> TIME notification: '{title}'")
                _send_notification(f"Время задачи: {title}", "Flow\u00b7Do")
                notified_keys.add(key_time)
                changed = True

        # 2) Напоминание заранее (окно 5 минут)
        remind_s = t.get("reminder", "")
        offset = REMIND_OFFSETS.get(remind_s)
        if offset:
            remind_dt = task_dt - timedelta(minutes=offset)
            key_remind = f"{tid}:remind:{date_s}_{time_s}_{remind_s}"
            if key_remind not in notified_keys:
                if remind_dt <= now <= remind_dt + timedelta(minutes=5):
                    _log(f"  -> REMINDER notification: '{title}' ({remind_s})")
                    _send_notification(
                        f"Напоминание: {title}",
                        f"{remind_s} до {time_s}")
                    notified_keys.add(key_remind)
                    changed = True

    return notified_keys, changed


def main():
    base_path = _get_storage_path()
    keys_path = os.path.join(base_path, "service_notified_keys.json")

    _log("=== Service started ===")
    _start_foreground()

    raw = _load_json(keys_path)
    notified_keys = set(raw.get("keys", [])) if isinstance(raw, dict) else set()
    tick = 0

    while True:
        try:
            notified_keys, changed = _check_reminders(base_path, notified_keys)
            if changed:
                if len(notified_keys) > 500:
                    notified_keys = set(list(notified_keys)[-300:])
                _save_json(keys_path, {"keys": list(notified_keys)})
            tick += 1
            # Heartbeat каждые 2 минуты (4 тика x 30с)
            if tick % 4 == 0:
                _log(f"[SVC heartbeat] tick={tick}, alive at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            _log(f"loop error: {e!r}")

        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
