package com.somethingobvious.keepsake

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.drawable.Icon
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.provider.DocumentsContract
import android.provider.MediaStore
import android.webkit.MimeTypeMap
import android.widget.Toast
import java.io.File
import java.util.concurrent.CompletableFuture
import java.util.concurrent.atomic.AtomicInteger

/** What Keepsake's Python asks of the phone: opening things, the clipboard, the trash, notifications and pickers. */
object Platform {
    lateinit var context: Context
    var activity: MainActivity? = null
    private val main = Handler(Looper.getMainLooper())
    private val notes = AtomicInteger(100)

    @JvmStatic
    fun open(target: String) {
        main.post {
            if (target.startsWith("http://") || target.startsWith("https://")) {
                start(Intent(Intent.ACTION_VIEW, Uri.parse(target)))
            } else if (File(target).isDirectory) {
                showFolder(File(target))
            } else {
                withUri(File(target)) { uri, type -> start(Intent(Intent.ACTION_VIEW).setDataAndType(uri, type)) }
            }
        }
    }

    /** A phone's file manager opens folders, not selections, so this shows the folder the file is in. */
    @JvmStatic
    fun showInFolder(path: String): Boolean {
        val file = File(path)
        val folder = if (file.isDirectory) file else file.parentFile ?: return false
        main.post { showFolder(folder) }
        return folder.isDirectory
    }

    private fun showFolder(folder: File) {
        val root = "/storage/emulated/0/"
        val relative = folder.path.removePrefix(root).removePrefix("/storage/emulated/0")
        val uri = DocumentsContract.buildDocumentUri("com.android.externalstorage.documents", "primary:$relative")
        start(Intent(Intent.ACTION_VIEW).setDataAndType(uri, DocumentsContract.Document.MIME_TYPE_DIR))
    }

    /** Has MediaStore read a file again, which it does not do by itself when only the file's date changed. */
    @JvmStatic
    fun scan(path: String) {
        MediaScannerConnection.scanFile(context, arrayOf(path), null, null)
    }

    /** MediaStore hands out the content link other apps need, scanning the file first if it is new. */
    private fun withUri(file: File, then: (Uri, String) -> Unit) {
        val type = MimeTypeMap.getSingleton().getMimeTypeFromExtension(file.extension.lowercase()) ?: "*/*"
        MediaScannerConnection.scanFile(context, arrayOf(file.path), arrayOf(type)) { _, uri ->
            if (uri != null) main.post { then(uri, type) } else toast("Android could not open ${file.name}")
        }
    }

    private fun start(intent: Intent) {
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        try {
            (activity ?: context).startActivity(if (activity == null) intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK) else intent)
        } catch (_: Exception) {
            toast("There is no app on this phone that opens that")
        }
    }

    @JvmStatic
    fun clipboardText(): String {
        val clip = context.getSystemService(ClipboardManager::class.java).primaryClip ?: return ""
        return if (clip.itemCount > 0) clip.getItemAt(0).coerceToText(context).toString() else ""
    }

    @JvmStatic
    fun setClipboardText(text: String) {
        main.post { context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Keepsake", text)) }
    }

    /** Moves a file to the phone's trash, where it stays for 30 days, as Windows' Recycle Bin would keep it. */
    @JvmStatic
    fun trash(path: String): Boolean {
        val resolver = context.contentResolver
        val files = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        val columns = arrayOf(MediaStore.MediaColumns._ID, MediaStore.Files.FileColumns.MEDIA_TYPE)
        @Suppress("DEPRECATION")
        val where = "${MediaStore.MediaColumns.DATA}=?"
        val (id, type) = resolver.query(files, columns, where, arrayOf(path), null)
            ?.use { if (it.moveToFirst()) it.getLong(0) to it.getInt(1) else null } ?: (null to 0)
        // Trashing through the plain file table only marks a file pending, which Android clears after 7 days.
        val collection = when (type) {
            MediaStore.Files.FileColumns.MEDIA_TYPE_VIDEO -> MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL)
            MediaStore.Files.FileColumns.MEDIA_TYPE_AUDIO -> MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL)
            MediaStore.Files.FileColumns.MEDIA_TYPE_IMAGE -> MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL)
            else -> null
        }
        if (id != null && collection != null) {
            try {
                val trashed = ContentValues().apply { put(MediaStore.MediaColumns.IS_TRASHED, 1) }
                if (resolver.update(Uri.withAppendedPath(collection, id.toString()), trashed, null, null) > 0) return true
            } catch (_: SecurityException) {
                // Another app's file: only the person can trash it, so it is deleted as Windows would without a bin.
            }
        }
        return File(path).delete()
    }

    @JvmStatic
    fun notify(title: String, text: String) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("finished", "Finished downloads", NotificationManager.IMPORTANCE_DEFAULT))
        val open = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val note = android.app.Notification.Builder(context, "finished")
            .setSmallIcon(R.drawable.ic_note)
            .setColor(RED)
            .setLargeIcon(logo())
            .setContentTitle(title)
            .setContentText(text)
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        manager.notify(notes.incrementAndGet(), note)
    }

    /** Keepsake's red, which tints its notifications so they are told apart from Android's own downloads. */
    const val RED = 0xffd8322b.toInt()

    /** The full-colour app icon, shown on each notification beside its words. */
    fun logo(): Icon = Icon.createWithResource(context, R.mipmap.ic_launcher)

    @JvmStatic
    fun inFront(): Boolean = activity?.shown == true

    @JvmStatic
    fun toast(text: String) {
        main.post { Toast.makeText(context, text, Toast.LENGTH_LONG).show() }
    }

    /** Asks for a folder and waits for the answer, as Windows' folder dialog does. */
    @JvmStatic
    fun pickFolder(start: String): String? = ask { it.pickFolder(start) }

    @JvmStatic
    fun pickFile(): String? = ask { it.pickFile() }

    /** Opens a site to sign into and waits for its cookies, as "name=value; name=value". */
    @JvmStatic
    fun signIn(url: String): String? = ask { it.signIn(url) }

    private fun ask(launch: (MainActivity) -> CompletableFuture<String?>): String? {
        val shown = activity ?: return null
        val answer = CompletableFuture<CompletableFuture<String?>>()
        main.post { answer.complete(launch(shown)) }
        return answer.get().get()
    }
}
