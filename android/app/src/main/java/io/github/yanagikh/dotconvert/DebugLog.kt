package io.github.yanagikh.dotconvert

import android.util.Log
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CopyOnWriteArrayList

object DebugLog {
    @Volatile
    var enabled: Boolean = false

    private const val maxLines = 500
    private val lines = CopyOnWriteArrayList<String>()
    private val listeners = CopyOnWriteArrayList<(String) -> Unit>()

    fun addListener(listener: (String) -> Unit) {
        listeners += listener
    }

    fun removeListener(listener: (String) -> Unit) {
        listeners -= listener
    }

    fun info(message: String) = append("INFO", message, null)

    fun debug(message: String) {
        if (enabled) append("DEBUG", message, null)
    }

    fun error(message: String, throwable: Throwable? = null) = append("ERROR", message, throwable)

    fun clear() {
        lines.clear()
        listeners.forEach { it("") }
    }

    fun text(): String = lines.joinToString("\n")

    private fun append(level: String, message: String, throwable: Throwable?) {
        val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).format(Date())
        val detail = throwable?.let { " — ${it::class.java.simpleName}: ${it.message}" }.orEmpty()
        val line = "$timestamp $level $message$detail"
        when (level) {
            "ERROR" -> Log.e("dotconvert", line, throwable)
            "DEBUG" -> Log.d("dotconvert", line)
            else -> Log.i("dotconvert", line)
        }
        lines += line
        while (lines.size > maxLines) lines.removeAt(0)
        listeners.forEach { it(line) }
    }
}
