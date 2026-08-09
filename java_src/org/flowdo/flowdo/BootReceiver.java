package org.flowdo.flowdo;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * Android полностью снимает ВСЕ запланированные AlarmManager-будильники
 * при перезагрузке устройства (а некоторые прошивки — и при обновлении
 * самого приложения). Без этого приёмника напоминания переставали
 * приходить после ребута телефона, пока пользователь сам не открывал
 * приложение (которое пересобирает будильники при старте).
 *
 * Этот класс НЕ требует Python-рантайма — только запускает
 * ServiceReminder с действием RESCHEDULE_ALARMS, которое уже написано
 * на Python (reminder.py) и само перечитывает tasks.json и заново
 * расставляет будильники (нацеленные на AlarmNotificationReceiver).
 */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (action == null) {
            return;
        }
        if (action.equals(Intent.ACTION_BOOT_COMPLETED)
                || action.equals("android.intent.action.QUICKBOOT_POWERON")
                || action.equals(Intent.ACTION_MY_PACKAGE_REPLACED)) {
            try {
                Intent svc = new Intent(context, ServiceReminder.class);
                svc.setAction("org.flowdo.flowdo.RESCHEDULE_ALARMS");
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(svc);
                } else {
                    context.startService(svc);
                }
            } catch (Exception e) {
                // best effort — если не получилось, будильники всё равно
                // пересоберутся при следующем открытии приложения
            }
        }
    }
}
