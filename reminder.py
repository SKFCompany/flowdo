# service/reminder.py — Flow·Do фоновая служба + обработчик AlarmManager
#
# Два режима работы:
# 1) Запуск от AlarmManager (Intent с action SHOW_NOTIFICATION):
#    → немедленно показывает уведомление и завершает работу
# 2) Прямой запуск из приложения (startService без action):
#    → входит в цикл проверки задач каждые 30 секунд

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


def _get_service_and_ctx():
    from jnius import autoclass, cast
    PythonService = autoclass("org.kivy.android.PythonService")
    service = PythonService.mService
    ctx = service.getApplicationContext()
    return service, ctx


def _ensure_channel(ctx, channel_id, name_str, importance):
    try:
        from jnius import autoclass, cast
        BuildVersion = autoclass("android.os.Build$VERSION")
        if BuildVersion.SDK_INT < 26:
            return
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        Context = autoclass("android.content.Context")
        String = autoclass("java.lang.String")
        nm = cast("android.app.NotificationManager",
                  ctx.getSystemService(Context.NOTIFICATION_SERVICE))
        ch = NotificationChannel(channel_id,
                                 cast("java.lang.CharSequence",
                                      String(name_str)),
                                 importance)
        nm.createNotificationChannel(ch)
    except Exception as e:
        _log(f"_ensure_channel error: {e!r}")


def _get_icon(ctx):
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
    return icon_res or 17301659


def _show_notification(ctx, title, message, channel_id="flowdo_reminders"):
    """Показывает системное push-уведомление."""
    _log(f"_show_notification: '{title}'")
    try:
        from jnius import autoclass, cast
        Context = autoclass("android.content.Context")
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        BuildVersion = autoclass("android.os.Build$VERSION")
        String = autoclass("java.lang.String")

        _ensure_channel(ctx, channel_id,
                        "Flow\u00b7Do \u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f",
                        4)  # IMPORTANCE_HIGH

        if BuildVersion.SDK_INT >= 26:
            builder = NotificationBuilder(ctx, channel_id)
        else:
            builder = NotificationBuilder(ctx)

        builder.setContentTitle(cast("java.lang.CharSequence", String(title)))
        builder.setContentText(cast("java.lang.CharSequence", String(message)))
        builder.setSmallIcon(_get_icon(ctx))
        builder.setAutoCancel(True)
        if BuildVersion.SDK_INT < 26:
            builder.setPriority(1)

        nm = cast("android.app.NotificationManager",
                  ctx.getSystemService(Context.NOTIFICATION_SERVICE))
        notif_id = int(time.time()) % 100000
        nm.notify(notif_id, builder.build())
        _log(f"_show_notification: notify(id={notif_id}) OK")
    except Exception as e:
        _log(f"_show_notification ERROR: {e!r}")


def _start_foreground_minimal(service, ctx):
    """Минимальное foreground-уведомление чтобы служба не была убита."""
    try:
        from jnius import autoclass, cast
        BuildVersion = autoclass("android.os.Build$VERSION")
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        String = autoclass("java.lang.String")

        _ensure_channel(ctx, "flowdo_service",
                        "Flow\u00b7Do", 2)  # IMPORTANCE_LOW

        if BuildVersion.SDK_INT >= 26:
            builder = NotificationBuilder(ctx, "flowdo_service")
        else:
            builder = NotificationBuilder(ctx)

        builder.setContentTitle(
            cast("java.lang.CharSequence",
                 String("Flow\u00b7Do")))
        builder.setContentText(
            cast("java.lang.CharSequence",
                 String("\u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f \u0430\u043a\u0442\u0438\u0432\u043d\u044b")))
        builder.setSmallIcon(_get_icon(ctx))
        builder.setOngoing(True)
        if BuildVersion.SDK_INT < 26:
            builder.setPriority(-2)

        notif = builder.build()
        if BuildVersion.SDK_INT >= 29:
            try:
                service.startForeground(1, notif, 0x40000000)
            except Exception:
                service.startForeground(1, notif)
        else:
            service.startForeground(1, notif)
        _log("_start_foreground_minimal: OK")
    except Exception as e:
        _log(f"_start_foreground_minimal ERROR: {e!r}")


REMIND_OFFSETS_MIN = {
    "За 10 минут": 10,
    "За 30 минут": 30,
    "За 1 час":    60,
    "За 1 день":   60 * 24,
}


def _reschedule_all_alarms(ctx):
    """Перечитывает tasks.json и заново расставляет все будущие
    AlarmManager-будильники. Нужно, потому что Android ПОЛНОСТЬЮ снимает
    все запланированные будильники приложения при перезагрузке устройства
    (и на некоторых прошивках — при обновлении самого приложения). Без
    этой пересборки уведомления переставали приходить в фоне после
    любой перезагрузки телефона, пока пользователь сам не откроет
    приложение (которое пересобирает будильники при старте)."""
    try:
        from jnius import autoclass, cast
        base_path = _get_storage_path()
        data = _load_json(os.path.join(base_path, "tasks.json"))
        items = []
        if isinstance(data, dict):
            sect = data.get("tasks", {})
            if isinstance(sect, dict):
                items = sect.get("items", [])

        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        AlarmManager = autoclass("android.app.AlarmManager")
        BuildVersion = autoclass("android.os.Build$VERSION")
        Context = autoclass("android.content.Context")
        String = autoclass("java.lang.String")
        RTC_WAKEUP = AlarmManager.RTC_WAKEUP
        am = cast("android.app.AlarmManager",
                  ctx.getSystemService(Context.ALARM_SERVICE))
        RECEIVER_CLASS = "org.flowdo.flowdo.AlarmNotificationReceiver"
        recv_cls = autoclass(RECEIVER_CLASS)

        now = datetime.now()
        count = 0

        def _arm(trigger_dt, tid, kind, title, msg):
            nonlocal count
            try:
                intent = Intent(ctx, recv_cls)
                intent.putExtra("notif_title",
                    cast("java.lang.CharSequence", String(title)))
                intent.putExtra("notif_text",
                    cast("java.lang.CharSequence", String(msg)))
                FLAG_IMMUTABLE = 0x04000000
                FLAG_UPDATE    = 0x08000000
                flags = FLAG_IMMUTABLE | FLAG_UPDATE
                req_code = abs(hash(f"{tid}:{kind}")) % 100000
                pi = PendingIntent.getBroadcast(ctx, req_code, intent, flags)
                # datetime.timestamp() на наивном datetime использует
                # локальный часовой пояс устройства — то же самое, что
                # использует системные часы Android (AlarmManager).
                trigger_ms = int(trigger_dt.timestamp() * 1000)
                if BuildVersion.SDK_INT >= 23:
                    am.setExactAndAllowWhileIdle(RTC_WAKEUP, trigger_ms, pi)
                else:
                    am.set(RTC_WAKEUP, trigger_ms, pi)
                count += 1
            except Exception as e:
                _log(f"_reschedule_all_alarms _arm ERROR: {e!r}")

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
            if task_dt > now:
                _arm(task_dt, tid, "time",
                     "Flow\u00b7Do \u2014 \u0417\u0430\u0434\u0430\u0447\u0430",
                     f"\u0412\u0440\u0435\u043c\u044f \u0437\u0430\u0434\u0430\u0447\u0438: {title}")
            remind_s = t.get("reminder", "")
            offset = REMIND_OFFSETS_MIN.get(remind_s)
            if offset:
                remind_dt = task_dt - timedelta(minutes=offset)
                if remind_dt > now:
                    _arm(remind_dt, tid, "remind",
                         "Flow\u00b7Do \u2014 \u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u0435",
                         f"\u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u0435: {title} ({remind_s})")

        _log(f"_reschedule_all_alarms: re-armed {count} alarms after boot")
    except Exception as e:
        _log(f"_reschedule_all_alarms ERROR: {e!r}")


def _handle_reschedule_intent(service):
    """Обрабатывает запуск от BootReceiver (после перезагрузки устройства)
    — заново расставляет все будильники и завершает работу службы."""
    try:
        intent = service.getIntent()
        if intent is None:
            return False
        action = intent.getAction()
        if action != "org.flowdo.flowdo.RESCHEDULE_ALARMS":
            return False
        _log(f"_handle_reschedule_intent: action={action}")
        ctx = service.getApplicationContext()
        _reschedule_all_alarms(ctx)
        try:
            service.stopSelf()
        except Exception:
            pass
        return True
    except Exception as e:
        _log(f"_handle_reschedule_intent ERROR: {e!r}")
        return False


def _handle_alarm_intent(service):
    """Обрабатывает запуск от AlarmManager — показывает уведомление
    и завершает работу службы. Возвращает True если это был alarm-запуск."""
    try:
        intent = service.getIntent()
        if intent is None:
            return False
        action = intent.getAction()
        if action != "org.flowdo.flowdo.SHOW_NOTIFICATION":
            return False

        _log(f"_handle_alarm_intent: action={action}")
        ctx = service.getApplicationContext()

        title   = intent.getStringExtra("notif_title") or "Flow\u00b7Do"
        message = intent.getStringExtra("notif_text")  or ""

        # Нужен brief foreground чтобы Android разрешил показать уведомление
        _start_foreground_minimal(service, ctx)
        _show_notification(ctx, title, message)

        # Останавливаем службу — задача выполнена
        try:
            service.stopSelf()
        except Exception:
            pass
        return True
    except Exception as e:
        _log(f"_handle_alarm_intent ERROR: {e!r}")
        return False


def _check_reminders_loop(base_path, notified_keys, service, ctx):
    """Основной цикл проверки — для прямого запуска службы."""
    tasks_path = os.path.join(base_path, "tasks.json")
    data = _load_json(tasks_path)

    items = []
    if isinstance(data, dict):
        sect = data.get("tasks", {})
        if isinstance(sect, dict):
            items = sect.get("items", [])

    now = datetime.now()
    changed = False
    _log(f"_check_reminders_loop: {len(items)} tasks at {now.strftime('%H:%M:%S')}")

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

        key_t = f"{tid}:time:{date_s}_{time_s}"
        if key_t not in notified_keys:
            if task_dt <= now <= task_dt + timedelta(minutes=60):
                _log(f"  -> TIME: '{title}'")
                _show_notification(ctx,
                    f"\u0412\u0440\u0435\u043c\u044f \u0437\u0430\u0434\u0430\u0447\u0438: {title}",
                    "Flow\u00b7Do")
                notified_keys.add(key_t)
                changed = True

        remind_s = t.get("reminder", "")
        offset = REMIND_OFFSETS.get(remind_s)
        if offset:
            remind_dt = task_dt - timedelta(minutes=offset)
            key_r = f"{tid}:remind:{date_s}_{time_s}_{remind_s}"
            if key_r not in notified_keys:
                if remind_dt <= now <= remind_dt + timedelta(minutes=60):
                    _log(f"  -> REMIND: '{title}' ({remind_s})")
                    _show_notification(ctx,
                        f"\u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u0435: {title}",
                        f"{remind_s} \u0434\u043e {time_s}")
                    notified_keys.add(key_r)
                    changed = True

    return notified_keys, changed


def main():
    _log("=== Service main() START ===")
    try:
        service, ctx = _get_service_and_ctx()
    except Exception as e:
        _log(f"FATAL: cannot get service context: {e!r}")
        return

    # Режим 1а: запущены от BootReceiver после перезагрузки устройства —
    # пересобрать все будильники (Android снимает их при ребуте) и выйти
    if _handle_reschedule_intent(service):
        _log("=== Service done (reschedule-after-boot mode) ===")
        return

    # Режим 1б: запущены от AlarmManager — показать уведомление и выйти
    if _handle_alarm_intent(service):
        _log("=== Service done (alarm mode) ===")
        return

    # Режим 2: прямой запуск — войти в цикл проверки
    _log("=== Service loop mode ===")
    _start_foreground_minimal(service, ctx)

    base_path = _get_storage_path()
    keys_path = os.path.join(base_path, "service_notified_keys.json")
    raw = _load_json(keys_path)
    notified_keys = set(raw.get("keys", [])) if isinstance(raw, dict) else set()
    tick = 0

    while True:
        try:
            notified_keys, changed = _check_reminders_loop(
                base_path, notified_keys, service, ctx)
            if changed:
                if len(notified_keys) > 500:
                    notified_keys = set(list(notified_keys)[-300:])
                _save_json(keys_path, {"keys": list(notified_keys)})
            tick += 1
            if tick % 4 == 0:
                _log(f"heartbeat tick={tick} at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            _log(f"loop error: {e!r}")
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
