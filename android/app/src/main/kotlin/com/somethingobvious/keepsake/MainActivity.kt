package com.somethingobvious.keepsake

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import android.provider.Settings
import android.view.RoundedCorner
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.window.OnBackInvokedDispatcher
import org.json.JSONObject
import java.io.File
import java.util.concurrent.CompletableFuture
import java.util.concurrent.Executors
import kotlin.math.ceil
import kotlin.math.sqrt

/** Keepsake's own window, the one Windows shows, in a WebView with Python behind it. */
class MainActivity : Activity() {
    private lateinit var web: Page
    private lateinit var frame: FrameLayout
    private val pool = Executors.newCachedThreadPool()
    private var answer: CompletableFuture<String?>? = null
    private var loaded = false
    private var shared: String? = null
    private var fullscreen: View? = null
    /** What the page keeps its contents clear of at the left, right and bottom, then how much of each side is a system bar, in the page's pixels. */
    private var safe = floatArrayOf(0f, 0f, 0f, 0f, 0f)
    private var leaveFullscreen: WebChromeClient.CustomViewCallback? = null
    var shown = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Platform.context = applicationContext
        Platform.activity = this
        Shell.start(applicationContext)
        web = Page()
        frame = FrameLayout(this).apply { setBackgroundColor(0xff0a0a0a.toInt()) }
        frame.addView(web, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        setContentView(frame)
        // The page reaches the screen's sides and bottom, so the tab bar's colours run under the gesture
        // bar and to the edges. Its contents keep clear of the bars, the camera's cutout and the rounded
        // corners, which the page is told about. The status bar and the keyboard still shorten it.
        frame.setOnApplyWindowInsetsListener { view, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            val system = insets.getInsets(WindowInsets.Type.systemBars())
            val keyboard = insets.getInsets(WindowInsets.Type.ime()).bottom
            view.setPadding(0, bars.top, 0, keyboard)
            val bottom = (bars.bottom - keyboard).coerceAtLeast(0)
            val low = if (keyboard > 0) Int.MAX_VALUE else bottom
            val left = maxOf(bars.left, corner(insets, RoundedCorner.POSITION_TOP_LEFT, bars.top), corner(insets, RoundedCorner.POSITION_BOTTOM_LEFT, low))
            val right = maxOf(bars.right, corner(insets, RoundedCorner.POSITION_TOP_RIGHT, bars.top), corner(insets, RoundedCorner.POSITION_BOTTOM_RIGHT, low))
            val density = resources.displayMetrics.density
            safe = floatArrayOf(left / density, right / density, bottom / density, system.left / density, system.right / density)
            tellSafe()
            insets
        }
        web.setBackgroundColor(0xff0a0a0a.toInt())
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            // The page is a file, as it is on Windows, and it plays and shows the downloads from their files.
            @Suppress("DEPRECATION")
            allowFileAccessFromFileURLs = true
            mediaPlaybackRequiresUserGesture = false
            // An app's window does not zoom; android.js also makes the page's viewport fixed.
            setSupportZoom(false)
        }
        web.addJavascriptInterface(Bridge(), "KeepsakeAndroid")
        web.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                loaded = true
                tellSafe()
                shared?.let { share(it) }
                shared = null
            }
        }
        web.webChromeClient = Chrome()
        web.loadUrl("file:///android_asset/ui/index.html")
        if (Build.VERSION.SDK_INT >= 33) {
            onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT) { back() }
        }
        askForAccess()
        take(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        take(intent)
    }

    override fun onStart() {
        super.onStart()
        shown = true
    }

    override fun onStop() {
        shown = false
        super.onStop()
    }

    override fun onDestroy() {
        if (Platform.activity === this) {
            Platform.activity = null
            // The page did the playing, so the player in the notification bar goes with it.
            Playback.update(applicationContext, null)
        }
        // Swiped away, the page would otherwise play on unseen, out of reach of the notification's buttons.
        web.destroy()
        super.onDestroy()
    }

    @Deprecated("Android 12 and older")
    override fun onBackPressed() {
        back()
    }

    /** Tells the page what to keep its contents clear of, once it is there to be told. */
    private fun tellSafe() {
        if (!::web.isInitialized) return
        web.evaluateJavascript("window.keepsakeSafe && keepsakeSafe(${safe.joinToString()})", null)
    }

    /** How far a rounded corner of the screen reaches in from the side where the page starts, `edge` pixels from the top or bottom. */
    private fun corner(insets: WindowInsets, position: Int, edge: Int): Int {
        if (Build.VERSION.SDK_INT < 31) return 0
        val radius = insets.getRoundedCorner(position)?.radius?.toDouble() ?: return 0
        val up = radius - edge
        return if (up <= 0) 0 else ceil(radius - sqrt(radius * radius - up * up)).toInt()
    }

    /** Back closes what is open on the page first, then leaves Keepsake running behind. */
    private fun back() {
        leaveFullscreen?.let {
            it.onCustomViewHidden()
            return
        }
        web.evaluateJavascript("window.keepsakeBack ? keepsakeBack() : false") { handled ->
            if (handled != "true") moveTaskToBack(true)
        }
    }

    /** A link shared from another app goes into the paste box, as a pasted one would. */
    private fun take(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val text = intent.getStringExtra(Intent.EXTRA_TEXT) ?: return
        if (loaded) share(text) else shared = text
    }

    private fun share(text: String) {
        web.evaluateJavascript("window.keepsakeShare && keepsakeShare(${JSONObject.quote(text)})", null)
    }

    /** Keepsake saves into the phone's own folders and reads them back for its library, as it does on Windows. */
    private fun askForAccess() {
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        if (Environment.isExternalStorageManager()) return
        AlertDialog.Builder(this, android.R.style.Theme_Material_Dialog_Alert)
            .setTitle("Let Keepsake Use Your Folders")
            .setMessage(
                "Keepsake saves what it downloads into a Keepsake folder in Download, and reads it back for its " +
                    "library. Android calls that access to all files. Turn it on for Keepsake on the next screen.",
            )
            .setPositiveButton("Open Settings") { _, _ ->
                startActivity(Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName")))
            }
            .setNegativeButton("Not Now", null)
            .show()
    }

    fun pickFolder(start: String): CompletableFuture<String?> {
        val picker = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
        val relative = start.removePrefix(Environment.getExternalStorageDirectory().path).trim('/')
        if (start.isNotEmpty()) {
            val inside = DocumentsContract.buildDocumentUri("com.android.externalstorage.documents", "primary:$relative")
            picker.putExtra(DocumentsContract.EXTRA_INITIAL_URI, inside)
        }
        return ask(picker, FOLDER)
    }

    fun signIn(url: String): CompletableFuture<String?> =
        ask(Intent(this, SignInActivity::class.java).putExtra(SignInActivity.URL, url), SIGN_IN)

    fun pickFile(): CompletableFuture<String?> =
        ask(Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*"), FILE)

    private fun ask(intent: Intent, code: Int): CompletableFuture<String?> {
        answer?.complete(null)
        val future = CompletableFuture<String?>()
        answer = future
        startActivityForResult(intent, code)
        return future
    }

    @Deprecated("The plain Activity has no newer way")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val uri = data?.data
        val path = if (requestCode == SIGN_IN) {
            data?.getStringExtra(SignInActivity.COOKIES)
        } else if (resultCode != RESULT_OK || uri == null) {
            null
        } else if (requestCode == FOLDER) {
            folderPath(uri)
        } else {
            copyIn(uri)
        }
        answer?.complete(path)
        answer = null
    }

    /** Keepsake works with paths, so a picked folder is turned back into one. */
    private fun folderPath(uri: Uri): String {
        val (volume, rest) = DocumentsContract.getTreeDocumentId(uri).split(":", limit = 2).let { it[0] to it.getOrElse(1) { "" } }
        val root = if (volume == "primary") Environment.getExternalStorageDirectory().path else "/storage/$volume"
        return File(root, rest).path
    }

    /** A picked file may not be a file at all, so it is copied somewhere Keepsake can read it. */
    private fun copyIn(uri: Uri): String {
        val name = contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { if (it.moveToFirst()) it.getString(0) else null } ?: "picked"
        val file = File(cacheDir, "picked/$name").apply { parentFile?.mkdirs() }
        contentResolver.openInputStream(uri)?.use { input -> file.outputStream().use { input.copyTo(it) } }
        return file.path
    }

    /** What the page calls `window.pywebview.api`, answered on a worker thread so the page never waits on Python. */
    /** A player button pressed outside the window, for the page to act on. */
    fun media(action: String, value: Double) {
        runOnUiThread { web.evaluateJavascript("window.keepsakeMedia && keepsakeMedia(${JSONObject.quote(action)}, $value)", null) }
    }

    /** While something plays out of sight, the page's renderer keeps its place instead of being the first thing Android drops. */
    fun keepRenderer(hold: Boolean) {
        runOnUiThread {
            web.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, !hold)
            web.playing = hold
        }
    }

    /**
     * Chromium pauses a page's video once the page is out of sight, so while the player holds on
     * the page is not told it went, as a browser that plays in the background does.
     */
    inner class Page : WebView(this@MainActivity) {
        private var window = View.VISIBLE
        var playing = false
            set(on) {
                if (field == on) return
                field = on
                super.onWindowVisibilityChanged(if (on) View.VISIBLE else window)
            }

        override fun onWindowVisibilityChanged(visibility: Int) {
            window = visibility
            if (!playing || visibility == View.VISIBLE) super.onWindowVisibilityChanged(visibility)
        }
    }

    inner class Bridge {
        @JavascriptInterface
        fun media(state: String) {
            if (Platform.activity !== this@MainActivity) return
            Playback.update(applicationContext, if (state == "null") null else JSONObject(state))
        }

        @JavascriptInterface
        fun call(id: Int, name: String, args: String) {
            pool.execute {
                val reply = Shell.call(name, args)
                runOnUiThread { web.evaluateJavascript("window.__keepsake($id,$reply)", null) }
            }
        }
    }

    /** The viewer's full-screen button: the video takes the whole screen, bars hidden. */
    inner class Chrome : WebChromeClient() {
        override fun onShowCustomView(view: View, callback: CustomViewCallback) {
            fullscreen = view
            leaveFullscreen = callback
            (window.decorView as ViewGroup).addView(view, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
            window.insetsController?.apply {
                hide(WindowInsets.Type.systemBars())
                systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        }

        override fun onHideCustomView() {
            fullscreen?.let { (window.decorView as ViewGroup).removeView(it) }
            fullscreen = null
            leaveFullscreen = null
            window.insetsController?.show(WindowInsets.Type.systemBars())
        }
    }

    private companion object {
        const val FOLDER = 1
        const val FILE = 2
        const val SIGN_IN = 3
    }
}
