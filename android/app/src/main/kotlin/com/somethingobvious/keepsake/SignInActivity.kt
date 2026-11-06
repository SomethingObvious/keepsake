package com.somethingobvious.keepsake

import android.app.Activity
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.view.WindowInsets
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.window.OnBackInvokedDispatcher

/** A site to sign into, as Windows' sign-in window is: its cookies go to Keepsake when Done is pressed. */
class SignInActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var site: Uri

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        site = Uri.parse(intent.getStringExtra(URL) ?: "about:blank")
        val bar = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(32, 16, 16, 16)
            setBackgroundColor(Color.rgb(10, 10, 10))
        }
        bar.addView(TextView(this).apply {
            text = "Sign in to ${site.host?.removePrefix("www.")}, then press Done"
            setTextColor(Color.rgb(236, 235, 230))
        }, LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f))
        val ink = Color.rgb(236, 235, 230)
        bar.addView(Button(this).apply {
            text = "Done"
            letterSpacing = 0.12f
            setTextColor(ink)
            minHeight = dp(44)
            minimumHeight = dp(44)
            setPadding(dp(18), 0, dp(18), 0)
            stateListAnimator = null
            // Keepsake's own square hairline button, not Android's grey one.
            background = RippleDrawable(
                ColorStateList.valueOf(Color.argb(64, 236, 235, 230)),
                GradientDrawable().apply { setStroke(dp(1), ink) },
                null,
            )
            setOnClickListener { done() }
        })
        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            webViewClient = WebViewClient()
        }
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(10, 10, 10))
            addView(bar, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
            addView(web, LinearLayout.LayoutParams(MATCH_PARENT, 0, 1f))
        }
        page.setOnApplyWindowInsetsListener { view, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        setContentView(page)
        if (Build.VERSION.SDK_INT >= 33) {
            onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT) { back() }
        }
        web.loadUrl(site.toString())
    }

    @Deprecated("Android 12 and older")
    override fun onBackPressed() {
        back()
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    private fun back() {
        if (web.canGoBack()) web.goBack() else done()
    }

    /** Hands over the site's cookies, from the address it was opened at and the bare domain both. */
    private fun done() {
        val cookies = CookieManager.getInstance()
        cookies.flush()
        val host = site.host.orEmpty()
        val bare = host.removePrefix("www.")
        val found = listOf(host, bare, "www.$bare").distinct().mapNotNull { cookies.getCookie("https://$it") }
        setResult(RESULT_OK, Intent().putExtra(COOKIES, found.joinToString("; ")))
        finish()
    }

    companion object {
        const val URL = "url"
        const val COOKIES = "cookies"
    }
}
