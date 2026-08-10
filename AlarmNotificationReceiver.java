package org.flowdo.flowdo;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * Показывает уведомление НАПРЯМУЮ из onReceive() — без Python, без службы,
 * без "холодного" старта интерпретатора. Всё выполняется за миллисекунды
 * прямо в системном процессе, поэтому не может вызвать ANR и надёжно
 * срабатывает даже если приложение полностью закрыто/выгружено из памяти.
 *
 * Раньше будильник запускал ServiceReminder (написанный на Python) через
 * PendingIntent.getForegroundService(). Каждый такой запуск требовал
 * полной инициализации Python-рантайма (загрузка libpython.so,
 * распаковка модулей, импорт jnius) — это может занимать больше 5 секунд,
 * а Android требует, чтобы startForeground() был вызван в течение 5 секунд
 * после startForegroundService(), иначе процесс убивается с ошибкой
 * "приложение не отвечает". Этот приёмник решает проблему в корне —
 * он в принципе не запускает Python.
 */
public class AlarmNotificationReceiver extends BroadcastReceiver {

    private static final String CHANNEL_ID = "flowdo_reminders";

    @Override
    public void onReceive(Context context, Intent intent) {
        try {
            String title = intent.getStringExtra("notif_title");
            String message = intent.getStringExtra("notif_text");
            if (title == null) title = "Flow\u00b7Do";
            if (message == null) message = "";

            ensureChannel(context);

            int iconRes = getIconRes(context);

            Intent launchIntent =
                    context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
            PendingIntent contentPi = null;
            if (launchIntent != null) {
                launchIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                int piFlags = PendingIntent.FLAG_UPDATE_CURRENT;
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    piFlags |= PendingIntent.FLAG_IMMUTABLE;
                }
                contentPi = PendingIntent.getActivity(
                        context, 0, launchIntent, piFlags);
            }

            Notification notification;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Notification.Builder b = new Notification.Builder(context, CHANNEL_ID)
                        .setContentTitle(title)
                        .setContentText(message)
                        .setSmallIcon(iconRes)
                        .setAutoCancel(true)
                        .setPriority(Notification.PRIORITY_HIGH);
                if (contentPi != null) b.setContentIntent(contentPi);
                notification = b.build();
            } else {
                Notification.Builder b = new Notification.Builder(context)
                        .setContentTitle(title)
                        .setContentText(message)
                        .setSmallIcon(iconRes)
                        .setAutoCancel(true)
                        .setPriority(Notification.PRIORITY_HIGH);
                if (contentPi != null) b.setContentIntent(contentPi);
                notification = b.build();
            }

            NotificationManager nm = (NotificationManager)
                    context.getSystemService(Context.NOTIFICATION_SERVICE);
            int notifId = (int) (System.currentTimeMillis() % 100000);
            nm.notify(notifId, notification);
        } catch (Exception e) {
            // best effort — не даём приёмнику упасть
        }
    }

    private void ensureChannel(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        try {
            NotificationManager nm = (NotificationManager)
                    context.getSystemService(Context.NOTIFICATION_SERVICE);
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID, "Flow\u00b7Do \u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f",
                    NotificationManager.IMPORTANCE_HIGH);
            nm.createNotificationChannel(ch);
        } catch (Exception e) {
            // ignore
        }
    }

    private int getIconRes(Context context) {
        try {
            int icon = context.getApplicationInfo().icon;
            if (icon != 0) return icon;
        } catch (Exception e) {
            // ignore
        }
        try {
            int id = context.getResources().getIdentifier(
                    "icon", "mipmap", context.getPackageName());
            if (id != 0) return id;
        } catch (Exception e) {
            // ignore
        }
        return android.R.drawable.ic_dialog_info;
    }
}
