package com.somethingobvious.keepsake

import android.content.Context
import android.os.Environment
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import kotlin.concurrent.thread

/** Keepsake's Python, started once per process and shared by every window. */
object Shell {
    private val ready = CountDownLatch(1)
    private var module: PyObject? = null
    private var failure = ""
    private var started = false

    @Synchronized
    fun start(context: Context) {
        if (started) return
        started = true
        thread(name = "python") {
            try {
                if (!Python.isStarted()) Python.start(AndroidPlatform(context))
                val shell = Python.getInstance().getModule("android_shell")
                val storage = Environment.getExternalStorageDirectory().path
                shell.callAttr("start", context.filesDir.path, context.applicationInfo.nativeLibraryDir, storage)
                module = shell
            } catch (problem: Exception) {
                failure = problem.message ?: problem.javaClass.simpleName
                android.util.Log.e("keepsake", "Python did not start", problem)
            } finally {
                ready.countDown()
            }
            watch(context)
        }
    }

    /** Runs one of the window's requests, waiting for Python to finish starting if it has not yet. */
    fun call(name: String, args: String): String {
        ready.await()
        val shell = module ?: return JSONObject().put("error", "Keepsake could not start: $failure").toString()
        return shell.callAttr("call", name, args).toString()
    }

    /** Looks at the queue every 2 seconds, so a download keeps running with the window closed. */
    private fun watch(context: Context) {
        val shell = module ?: return
        while (true) {
            try {
                KeepAlive.update(context, JSONObject(shell.callAttr("busy").toString()))
            } catch (_: Exception) {
                // A missed look is made up 2 seconds later.
            }
            Thread.sleep(2000)
        }
    }
}
