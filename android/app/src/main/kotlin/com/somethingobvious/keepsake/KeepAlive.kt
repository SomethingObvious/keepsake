package com.somethingobvious.keepsake

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import org.json.JSONObject

/** Holds the app in the foreground while the queue has work, or Android would stop a long download halfway. */
class KeepAlive : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTE, note(this, "Downloading", -1.0), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        return START_NOT_STICKY
    }

    companion object {
        private const val NOTE = 1

        @Volatile
        private var running = false

        fun update(context: Context, state: JSONObject) {
            val active = state.optInt("running")
            val waiting = state.optInt("waiting")
            if (active + waiting == 0) {
                if (running) {
                    running = false
                    context.stopService(Intent(context, KeepAlive::class.java))
                }
                return
            }
            // Android only lets a foreground service start while the app is on screen.
            if (!running && Platform.inFront()) {
                running = true
                context.startForegroundService(Intent(context, KeepAlive::class.java))
            }
            if (running) {
                val title = state.optString("title").ifEmpty { "Waiting to start" }
                val more = if (active + waiting > 1) " and ${active + waiting - 1} more" else ""
                context.getSystemService(NotificationManager::class.java)
                    .notify(NOTE, note(context, "$title$more", state.optDouble("pct", -1.0)))
            }
        }

        private fun note(context: Context, text: String, pct: Double): Notification {
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel("downloads", "Downloads", NotificationManager.IMPORTANCE_LOW))
            val open = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
            return Notification.Builder(context, "downloads")
                .setSmallIcon(R.drawable.ic_note)
                .setColor(Platform.RED)
                .setLargeIcon(Platform.logo())
                .setContentTitle(text)
                .setContentIntent(open)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setProgress(100, pct.coerceAtLeast(0.0).toInt(), pct < 0)
                .build()
        }
    }
}
