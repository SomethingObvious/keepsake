package com.somethingobvious.keepsake

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PorterDuff
import android.graphics.PorterDuffColorFilter
import android.graphics.RectF
import android.graphics.drawable.Icon
import android.media.AudioManager
import android.media.MediaMetadata
import android.media.MediaMetadataRetriever
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * Keeps the viewer playing with the screen off, and gives it a player in the notification bar, on the
 * lock screen and on headphone buttons. The page does the playing, and this only holds the phone
 * awake and passes the buttons back to it.
 */
class Playback : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent?.getStringExtra(PRESS)?.let { press(it) }
        val note = shown
        if (note != null && holding) {
            startForeground(NOTE, note, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            stopSelf()
        }
        return START_NOT_STICKY
    }

    companion object {
        private const val NOTE = 2
        private const val CHANNEL = "player"
        private const val PRESS = "press"

        private val main = Handler(Looper.getMainLooper())
        private val worker = Executors.newSingleThreadExecutor()
        private var session: MediaSession? = null
        private var shown: Notification? = null
        private var holding = false
        private var awake: PowerManager.WakeLock? = null
        private var unplugged: BroadcastReceiver? = null
        private var art: Pair<String, Bitmap>? = null
        private var pressed = 0L

        /** What the page says about its playback, or null when the viewer closed. */
        fun update(context: Context, state: JSONObject?) {
            // Whether it may hold the phone awake is settled now, as a picture can take a second to find
            // and by then Keepsake may be out of sight, where Android lets no foreground service start.
            val allowed = Platform.inFront() || SystemClock.elapsedRealtime() - pressed < 5000
            worker.execute {
                val picture = state?.let { artFor(it) }
                main.post { apply(context, state, picture, allowed) }
            }
        }

        /**
         * A button pressed on the notification, the lock screen or headphones, passed to the page.
         * Android lets a player start its service from the background for a few seconds after one.
         */
        private fun press(action: String, value: Double = 0.0) {
            pressed = SystemClock.elapsedRealtime()
            Platform.activity?.media(action, value)
        }

        private fun apply(context: Context, state: JSONObject?, picture: Bitmap?, allowed: Boolean) {
            if (state == null || picture == null) {
                stop(context)
                return
            }
            val playing = state.optBoolean("playing")
            val background = state.optBoolean("background", true)
            val controls = state.optBoolean("controls", true)
            val title = state.optString("title")
            val place = "${state.optInt("index") + 1} of ${state.optInt("count")}"
            val list = state.optString("list").ifEmpty { "Keepsake" }
            val s = sessionFor(context)
            s.setMetadata(
                MediaMetadata.Builder()
                    .putString(MediaMetadata.METADATA_KEY_TITLE, title)
                    .putString(MediaMetadata.METADATA_KEY_ARTIST, list)
                    .putString(MediaMetadata.METADATA_KEY_ALBUM, place)
                    .putLong(MediaMetadata.METADATA_KEY_DURATION, (state.optDouble("duration", 0.0) * 1000).toLong())
                    .putBitmap(MediaMetadata.METADATA_KEY_ART, picture)
                    .build(),
            )
            s.setPlaybackState(stateOf(context, state, playing))
            s.isActive = controls
            if (playing) hold(context) else letGo()
            val note = noteFor(context, s, title, list, place, picture, playing, controls)
            shown = note
            val wanted = background && playing
            if (wanted && !holding && allowed) {
                holding = runCatching { context.startForegroundService(Intent(context, Playback::class.java)) }.isSuccess
            }
            if (holding || controls) {
                context.getSystemService(NotificationManager::class.java).notify(NOTE, note)
            }
            if (!background && holding) {
                holding = false
                context.stopService(Intent(context, Playback::class.java))
            }
            Platform.activity?.keepRenderer(holding)
        }

        private fun stop(context: Context) {
            letGo()
            session?.release()
            session = null
            shown = null
            if (holding) {
                holding = false
                context.stopService(Intent(context, Playback::class.java))
            }
            context.getSystemService(NotificationManager::class.java).cancel(NOTE)
            Platform.activity?.keepRenderer(false)
        }

        private fun sessionFor(context: Context): MediaSession =
            session ?: MediaSession(context, "Keepsake").also {
                it.setCallback(
                    object : MediaSession.Callback() {
                        override fun onPlay() = press("play")
                        override fun onPause() = press("pause")
                        override fun onSkipToNext() = press("next")
                        override fun onSkipToPrevious() = press("previous")
                        override fun onStop() = press("stop")
                        override fun onSeekTo(pos: Long) = press("seek", pos / 1000.0)
                        override fun onCustomAction(action: String, extras: android.os.Bundle?) = press(action)
                    },
                    main,
                )
                it.setSessionActivity(openApp(context))
                session = it
            }

        private fun stateOf(context: Context, state: JSONObject, playing: Boolean): PlaybackState {
            val after = state.optString("after")
            val builder = PlaybackState.Builder()
                .setActions(
                    PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE or
                        PlaybackState.ACTION_SKIP_TO_NEXT or PlaybackState.ACTION_SKIP_TO_PREVIOUS or
                        PlaybackState.ACTION_SEEK_TO or PlaybackState.ACTION_STOP,
                )
                .setState(
                    if (playing) PlaybackState.STATE_PLAYING else PlaybackState.STATE_PAUSED,
                    (state.optDouble("position", 0.0) * 1000).toLong(),
                    if (playing) state.optDouble("rate", 1.0).toFloat() else 0f,
                )
            if (state.optBoolean("canShuffle")) {
                val on = state.optBoolean("shuffle")
                builder.addCustomAction(
                    PlaybackState.CustomAction.Builder(
                        "shuffle",
                        if (on) "Shuffle is on" else "Shuffle",
                        if (on) R.drawable.ic_shuffle_on else R.drawable.ic_shuffle_off,
                    ).build(),
                )
            }
            val (words, icon) = when (after) {
                "around" -> "Starts over after the last" to R.drawable.ic_after_around
                "next" -> "Plays the next one" to R.drawable.ic_after_next
                else -> "Stops after this one" to R.drawable.ic_after_stop
            }
            builder.addCustomAction(PlaybackState.CustomAction.Builder("repeat", words, icon).build())
            return builder.build()
        }

        private fun noteFor(
            context: Context,
            s: MediaSession,
            title: String,
            list: String,
            place: String,
            picture: Bitmap,
            playing: Boolean,
            controls: Boolean,
        ): Notification {
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel(CHANNEL, "Player", NotificationManager.IMPORTANCE_LOW))
            val builder = Notification.Builder(context, CHANNEL)
                .setSmallIcon(R.drawable.ic_note)
                .setColor(Platform.RED)
                .setContentTitle(title)
                .setContentText(list)
                .setSubText(place)
                .setContentIntent(openApp(context))
                .setDeleteIntent(button(context, "stop", 9))
                .setVisibility(Notification.VISIBILITY_PUBLIC)
                .setCategory(Notification.CATEGORY_TRANSPORT)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setOngoing(playing)
            if (!controls) return builder.build()
            return builder
                .setLargeIcon(picture)
                .setColorized(true)
                .addAction(action(context, android.R.drawable.ic_media_previous, "Previous", "previous", 1))
                .addAction(
                    if (playing) {
                        action(context, android.R.drawable.ic_media_pause, "Pause", "pause", 2)
                    } else {
                        action(context, android.R.drawable.ic_media_play, "Play", "play", 3)
                    },
                )
                .addAction(action(context, android.R.drawable.ic_media_next, "Next", "next", 4))
                .setStyle(Notification.MediaStyle().setMediaSession(s.sessionToken).setShowActionsInCompactView(0, 1, 2))
                .build()
        }

        private fun action(context: Context, icon: Int, label: String, press: String, code: Int) =
            Notification.Action.Builder(Icon.createWithResource(context, icon), label, button(context, press, code)).build()

        private fun button(context: Context, press: String, code: Int): PendingIntent =
            PendingIntent.getService(
                context,
                code,
                Intent(context, Playback::class.java).putExtra(PRESS, press),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
            )

        private fun openApp(context: Context): PendingIntent =
            PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)

        /**
         * While playing: the processor kept awake, and unplugged headphones heard. The page's web view
         * takes audio focus itself, and asking for it here as well took it from the page and paused it.
         */
        private fun hold(context: Context) {
            if (awake == null) {
                awake = context.getSystemService(PowerManager::class.java)
                    .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Keepsake:playing")
                    .apply { setReferenceCounted(false) }
            }
            awake?.acquire(6 * 60 * 60 * 1000L)
            if (unplugged == null) {
                val receiver = object : BroadcastReceiver() {
                    override fun onReceive(c: Context, intent: Intent) = press("pause")
                }
                Platform.context.registerReceiver(receiver, IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY), Context.RECEIVER_NOT_EXPORTED)
                unplugged = receiver
            }
        }

        private fun letGo() {
            awake?.takeIf { it.isHeld }?.release()
            unplugged?.let { Platform.context.unregisterReceiver(it) }
            unplugged = null
        }

        // ---- the picture on the notification and lock screen ----

        /** The download's own thumbnail, else a frame of the video itself, else the sound's waveform. */
        private fun artFor(state: JSONObject): Bitmap {
            val path = state.optString("path")
            val thumb = state.optString("picture")
            val wave = state.optString("wave")
            val key = "$path|$thumb|$wave"
            art?.takeIf { it.first == key }?.let { return it.second }
            val found = thumb.takeIf { it.isNotEmpty() }?.let { BitmapFactory.decodeFile(it) }
                ?: runCatching { pictureIn(path, state.optString("kind") == "video") }.getOrNull()
            val made = if (found != null && !blank(found)) covering(found) else waveOf(wave)
            art = key to made
            return made
        }

        /** A frame a fifth of the way into a video, or a sound's cover. */
        private fun pictureIn(path: String, video: Boolean): Bitmap? {
            val reader = MediaMetadataRetriever()
            try {
                reader.setDataSource(path)
                if (!video) return reader.embeddedPicture?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }
                val length = reader.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
                return reader.getScaledFrameAtTime(length * 200, MediaMetadataRetriever.OPTION_CLOSEST_SYNC, 960, 540)
            } finally {
                reader.release()
            }
        }

        /** A recording saved as a video is all black, and a black square says nothing. */
        private fun blank(picture: Bitmap): Boolean {
            var brightest = 0
            for (y in 0 until 12) {
                for (x in 0 until 12) {
                    val c = picture.getPixel(x * (picture.width - 1) / 11, y * (picture.height - 1) / 11)
                    brightest = maxOf(brightest, Color.red(c), Color.green(c), Color.blue(c))
                }
            }
            return brightest < 24
        }

        /** The picture filling a 16:9 frame, cut at its edges rather than squeezed. */
        private fun covering(picture: Bitmap): Bitmap {
            val out = Bitmap.createBitmap(960, 540, Bitmap.Config.ARGB_8888)
            val scale = maxOf(960f / picture.width, 540f / picture.height)
            val w = picture.width * scale
            val h = picture.height * scale
            Canvas(out).drawBitmap(picture, null, RectF((960 - w) / 2, (540 - h) / 2, (960 + w) / 2, (540 + h) / 2), Paint(Paint.FILTER_BITMAP_FLAG))
            return out
        }

        /**
         * With no picture to show: the sound itself, its waveform drawn edge to edge in the yellow the
         * library gives sound, on Keepsake's matte black. Each track's is its own.
         */
        private fun waveOf(wave: String): Bitmap {
            val out = Bitmap.createBitmap(960, 540, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(out)
            canvas.drawColor(0xff0a0a0a.toInt())
            val line = wave.takeIf { it.isNotEmpty() }?.let { BitmapFactory.decodeFile(it) } ?: return out
            val ink = Paint(Paint.FILTER_BITMAP_FLAG).apply {
                colorFilter = PorterDuffColorFilter(0xffe2b00e.toInt(), PorterDuff.Mode.SRC_IN)
            }
            canvas.drawBitmap(line, null, RectF(0f, 170f, 960f, 430f), ink)
            return out
        }
    }
}
