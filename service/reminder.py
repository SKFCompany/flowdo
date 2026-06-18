# service/reminder.py — Flow·Do background reminder service

import json
import os
import time
from datetime import datetime, timedelta

REMIND_OFFSETS = {
    "За 10 минут": 10,
    "За 30 минут": 30,
    "За 1 час":    60,
    "За 1 день":   60 * 24,
}
CHECK_INTERVAL_SEC = 30


def _get_storage_path():
    try:
        from android.storage import app_storage_path
        return app_storage_path()
    except Exception:
        return os.path.expanduser("~")


def _log(msg):
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


def _build_notification(ctx, channel_id, title, message, ongoing=False):
    """Строит Notification объект. Возвращает (notification, icon_res) или (None, 0)."""
    try:
        from jnius import autoclass, cast
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        BuildVersion = autoclass("android.os.Build$VERSION")
        String = autoclass("java.lang.String")

        if BuildVersion.SDK_INT >= 26:
            builder = NotificationBuilder(ctx, channel_id)
        else:
            builder = NotificationBuilder(ctx)

        builder.setContentTitle(cast("java.lang.CharSequence", String(title)))
        builder.setContentText(cast("java.lang.CharSequence", String(message)))
        builder.setAutoCancel(not ongoing)
        if ongoing:
            builder.setOngoing(True)

        # Иконка
        icon_res = 0
        try:
            icon_res = ctx.getApplicationInfo().icon
        except Exception:
            pass
        if not icon_res:
            try:
                icon_res = ctx.getResources().getIdentifier(
                    "icon", "mipmap", ctx.getPackageName())
            except Exception:
                pass
        if not icon_res:
            icon_res = 17301659  # ic_dialog_info
        builder.setSmallIcon(icon_res)

        if BuildVersion.SDK_INT < 26:
            builder.setPriority(-2 if ongoing else 1)

        return builder.build(), icon_res
    except Exception as e:
        _log(f"_build_notification error: {e!r}")
        return None, 0


def _ensure_channel(ctx, channel_id, name, importance):
    try:
        from jnius import autoclass, cast
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        BuildVersion = autoclass("android.os.Build$VERSION")
        String = autoclass("java.lang.String")
        Context = autoclass("android.content.Context")

        if BuildVersion.SDK_INT >= 26:
            nm = cast("android.app.NotificationManager",
                      ctx.getSystemService(Context.NOTIFICATION_SERVICE))
            ch = NotificationChannel(channel_id,
                                     cast("java.lang.CharSequence", String(name)),
                                     importance)
            nm.createNotificationChannel(ch)
    except Exception as e:
        _log(f"_ensure_channel error: {e!r}")


def _start_foreground():
    """Переводит службу в foreground. Пробуем несколько вариантов
    startForeground для совместимости с разными версиями Android."""
    _log("_start_foreground: begin")
    try:
        from jnius import autoclass, cast
        PythonService = autoclass("org.kivy.android.PythonService")
        BuildVersion = autoclass("android.os.Build$VERSION")
        service = PythonService.mService
        ctx = service.getApplicationContext()

        _ensure_channel(ctx, "flowdo_service",
                        "Flow\u00b7Do \u0421\u043b\u0443\u0436\u0431\u0430",
                        2)  # IMPORTANCE_LOW = 2

        notif, icon_res = _build_notification(
            ctx, "flowdo_service",
            "Flow\u00b7Do",
            "\u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f \u0430\u043a\u0442\u0438\u0432\u043d\u044b",
            ongoing=True)

        if notif is None:
            _log("_start_foreground: notification build failed, skip")
            return

        sdk = BuildVersion.SDK_INT
        _log(f"_start_foreground: sdk={sdk}, icon={icon_res}")

        if sdk >= 34:
            # Android 14+: требует тип сервиса
            # FOREGROUND_SERVICE_TYPE_SPECIAL_USE = 0x40000000
            try:
                service.startForeground(1, notif, 0x40000000)
                _log("_start_foreground: startForeground(1, notif, SPECIAL_USE) OK")
                return
            except Exception as e:
                _log(f"_start_foreground: SPECIAL_USE failed: {e!r}, trying without type")

        # Android 9-13 и fallback для 14+
        try:
            service.startForeground(1, notif)
            _log("_start_foreground: startForeground(1, notif) OK")
        except Exception as e:
            _log(f"_start_foreground: simple startForeground failed: {e!r}")

    except Exception as e:
        _log(f"_start_foreground: OUTER ERROR {e!r}")


def _send_notification(title, message):
    _log(f"_send_notification: '{title}'")
    try:
        from jnius import autoclass, cast
        PythonService = autoclass("org.kivy.android.PythonService")
        Context = autoclass("android.content.Context")
        NotificationManager = autoclass("android.app.NotificationManager")
        BuildVersion = autoclass("android.os.Build$VERSION")

        service = PythonService.mService
        ctx = service.getApplicationContext()

        _ensure_channel(ctx, "flowdo_reminders",
                        "Flow\u00b7Do \u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f",
                        4)  # IMPORTANCE_HIGH = 4

        notif, _ = _build_notification(ctx, "flowdo_reminders", title, message)
        if notif is None:
            _log("_send_notification: build failed")
            return

        nm = cast("android.app.NotificationManager",
                  ctx.getSystemService(Context.NOTIFICATION_SERVICE))
        notif_id = int(time.time()) % 100000
        nm.notify(notif_id, notif)
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
    _log(f"_check_reminders: {len(items)} tasks at {now.strftime('%H:%M:%S')}")

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

        tid   = t.get("id", "")
        title = t.get("title", "\u0417\u0430\u0434\u0430\u0447\u0430")

        # 1) Время самой задачи (окно 5 мин)
        key_t = f"{tid}:time:{date_s}_{time_s}"
        if key_t not in notified_keys:
            if task_dt <= now <= task_dt + timedelta(minutes=5):
                _log(f"  -> TIME: '{title}'")
                _send_notification(
                    f"\u0412\u0440\u0435\u043c\u044f \u0437\u0430\u0434\u0430\u0447\u0438: {title}",
                    "Flow\u00b7Do")
                notified_keys.add(key_t)
                changed = True

        # 2) Напоминание заранее (окно 5 мин)
        remind_s = t.get("reminder", "")
        offset   = REMIND_OFFSETS.get(remind_s)
        if offset:
            remind_dt = task_dt - timedelta(minutes=offset)
            key_r = f"{tid}:remind:{date_s}_{time_s}_{remind_s}"
            if key_r not in notified_keys:
                if remind_dt <= now <= remind_dt + timedelta(minutes=5):
                    _log(f"  -> REMIND: '{title}' ({remind_s})")
                    _send_notification(
                        f"\u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u0435: {title}",
                        f"{remind_s} \u0434\u043e {time_s}")
                    notified_keys.add(key_r)
                    changed = True

    return notified_keys, changed


def main():
    base_path = _get_storage_path()
    keys_path = os.path.join(base_path, "service_notified_keys.json")

    _log("=== Service main() START ===")
    _start_foreground()
    _log("=== After startForeground ===")

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
            if tick % 4 == 0:  # каждые 2 минуты
                _log(f"heartbeat tick={tick} at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            _log(f"loop error: {e!r}")

        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
