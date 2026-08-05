package io.github.yanagikh.dotconvert

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.Gravity
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private companion object {
        const val REQUEST_SOURCE = 100
        const val REQUEST_OUTPUT = 101
        const val REQUEST_LOG = 102
    }

    private var language = "en"
    private var sourceUri: Uri? = null
    private var sourceName = ""
    private var targets: List<String> = emptyList()
    private var pendingTarget = ""
    private var logsVisible = false

    private lateinit var subtitle: TextView
    private lateinit var languageTitle: TextView
    private lateinit var sourceTitle: TextView
    private lateinit var sourceLabel: TextView
    private lateinit var chooseButton: Button
    private lateinit var targetTitle: TextView
    private lateinit var targetSpinner: Spinner
    private lateinit var qualityLabel: TextView
    private lateinit var qualityValue: TextView
    private lateinit var qualitySeek: SeekBar
    private lateinit var debugCheck: CheckBox
    private lateinit var logToggleButton: Button
    private lateinit var clearLogButton: Button
    private lateinit var exportLogButton: Button
    private lateinit var logText: TextView
    private lateinit var logContainer: LinearLayout
    private lateinit var convertButton: Button
    private lateinit var statusLabel: TextView

    private val logListener: (String) -> Unit = {
        runOnUiThread { renderLog() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        applyLanguage()
        DebugLog.addListener(logListener)
        DebugLog.info("Android interface started")
    }

    override fun onDestroy() {
        DebugLog.removeListener(logListener)
        super.onDestroy()
    }

    private fun buildUi() {
        val scroll = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(18), dp(20), dp(28))
        }
        scroll.addView(root)

        root.addView(TextView(this).apply {
            text = ".convert"
            textSize = 30f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        })
        subtitle = TextView(this).apply {
            textSize = 15f
            setPadding(0, dp(4), 0, dp(16))
        }
        root.addView(subtitle)

        languageTitle = sectionTitle(root)
        val languageRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        listOf("en" to "English", "zh" to "繁體中文", "ja" to "日本語").forEach { (code, label) ->
            languageRow.addView(Button(this).apply {
                text = label
                isAllCaps = false
                setOnClickListener {
                    language = code
                    applyLanguage()
                    DebugLog.info("Interface language changed to $code")
                }
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        }
        root.addView(languageRow)

        sourceTitle = sectionTitle(root)
        sourceLabel = TextView(this).apply {
            textSize = 14f
            setPadding(dp(10), dp(10), dp(10), dp(10))
            setBackgroundColor(0xFFF0F2F6.toInt())
        }
        root.addView(sourceLabel, fullWidth())
        chooseButton = Button(this).apply {
            isAllCaps = false
            setOnClickListener { chooseSource() }
        }
        root.addView(chooseButton, fullWidth(top = 8))

        targetTitle = sectionTitle(root)
        targetSpinner = Spinner(this)
        root.addView(targetSpinner, fullWidth())

        val qualityRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(10), 0, 0)
        }
        qualityLabel = TextView(this)
        qualityValue = TextView(this).apply { text = "92" }
        qualitySeek = SeekBar(this).apply {
            max = 50
            progress = 42
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                    qualityValue.text = (50 + progress).toString()
                }
                override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit
                override fun onStopTrackingTouch(seekBar: SeekBar?) = Unit
            })
        }
        qualityRow.addView(qualityLabel)
        qualityRow.addView(qualitySeek, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        qualityRow.addView(qualityValue)
        root.addView(qualityRow, fullWidth())

        debugCheck = CheckBox(this).apply {
            isAllCaps = false
            setOnCheckedChangeListener { _, enabled ->
                DebugLog.enabled = enabled
                DebugLog.info(if (enabled) t("debug_on") else t("debug_off"))
                if (enabled && !logsVisible) toggleLogs()
            }
        }
        root.addView(debugCheck, fullWidth(top = 10))
        logToggleButton = Button(this).apply {
            isAllCaps = false
            setOnClickListener { toggleLogs() }
        }
        root.addView(logToggleButton, fullWidth())

        logContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
            setPadding(0, dp(8), 0, dp(8))
        }
        val logActions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        clearLogButton = Button(this).apply {
            isAllCaps = false
            setOnClickListener { DebugLog.clear() }
        }
        exportLogButton = Button(this).apply {
            isAllCaps = false
            setOnClickListener { exportLog() }
        }
        logActions.addView(clearLogButton, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        logActions.addView(exportLogButton, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        logContainer.addView(logActions)
        logText = TextView(this).apply {
            typeface = android.graphics.Typeface.MONOSPACE
            textSize = 11f
            setTextIsSelectable(true)
            setPadding(dp(10), dp(10), dp(10), dp(10))
            setBackgroundColor(0xFF101318.toInt())
            setTextColor(0xFFF2F4F8.toInt())
            minHeight = dp(160)
        }
        logContainer.addView(logText, fullWidth(top = 6))
        root.addView(logContainer, fullWidth())

        statusLabel = TextView(this).apply {
            textSize = 14f
            setPadding(0, dp(14), 0, dp(8))
        }
        root.addView(statusLabel, fullWidth())
        convertButton = Button(this).apply {
            isAllCaps = false
            isEnabled = false
            setOnClickListener { confirmAndChooseOutput() }
        }
        root.addView(convertButton, fullWidth())

        setContentView(scroll)
    }

    private fun sectionTitle(root: LinearLayout): TextView = TextView(this).also { view ->
        view.textSize = 18f
        view.setTypeface(view.typeface, android.graphics.Typeface.BOLD)
        view.setPadding(0, dp(18), 0, dp(8))
        root.addView(view, fullWidth())
    }

    private fun fullWidth(top: Int = 0): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        ).apply { topMargin = dp(top) }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun t(key: String): String = MobileStrings.get(language, key)

    private fun applyLanguage() {
        title = ".convert"
        subtitle.text = t("subtitle")
        languageTitle.text = t("language")
        sourceTitle.text = t("source")
        sourceLabel.text = if (sourceName.isBlank()) t("no_file") else sourceName
        chooseButton.text = t("choose")
        targetTitle.text = t("target")
        qualityLabel.text = t("quality")
        debugCheck.text = t("debug")
        logToggleButton.text = t(if (logsVisible) "hide_log" else "show_log")
        clearLogButton.text = t("clear")
        exportLogButton.text = t("export")
        convertButton.text = t("convert")
        statusLabel.text = if (sourceName.isBlank()) t("unsupported") else t("ready")
        renderTargets()
    }

    private fun chooseSource() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
        }
        startActivityForResult(intent, REQUEST_SOURCE)
    }

    private fun confirmAndChooseOutput() {
        val uri = sourceUri ?: return
        if (targets.isEmpty()) return
        val target = targetSpinner.selectedItem?.toString()?.lowercase() ?: return
        val warningCodes = FormatRules.warnings(sourceName, target)
        val continueAction = {
            pendingTarget = target
            val outputIntent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = FormatRules.mimeType(target)
                putExtra(Intent.EXTRA_TITLE, FormatRules.suggestedName(sourceName, target))
                addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            }
            startActivityForResult(outputIntent, REQUEST_OUTPUT)
        }
        if (warningCodes.isEmpty()) {
            continueAction()
        } else {
            val message = warningCodes.joinToString("\n") { "• ${t(it)}" }
            AlertDialog.Builder(this)
                .setTitle(t("warning_title"))
                .setMessage(message)
                .setNegativeButton(t("cancel"), null)
                .setPositiveButton(t("continue")) { _, _ -> continueAction() }
                .show()
        }
        DebugLog.debug("Output selection requested for $uri as $target")
    }

    @Deprecated("Kept for API 26 compatibility without an AndroidX dependency")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        when (requestCode) {
            REQUEST_SOURCE -> selectSource(uri, data.flags)
            REQUEST_OUTPUT -> performConversion(uri)
            REQUEST_LOG -> writeLog(uri)
        }
    }

    private fun selectSource(uri: Uri, flags: Int) {
        try {
            val persistFlags = flags and
                (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            contentResolver.takePersistableUriPermission(uri, persistFlags)
        } catch (exception: SecurityException) {
            DebugLog.debug("Provider did not grant persistable access: ${exception.message}")
        }
        val name = displayName(uri)
        val available = FormatRules.targetsFor(name)
        sourceUri = if (available.isEmpty()) null else uri
        sourceName = if (available.isEmpty()) "" else name
        targets = available
        sourceLabel.text = if (available.isEmpty()) t("no_file") else name
        statusLabel.text = if (available.isEmpty()) t("unsupported") else t("ready")
        convertButton.isEnabled = available.isNotEmpty()
        renderTargets()
        if (available.isEmpty()) {
            AlertDialog.Builder(this)
                .setTitle(t("failed"))
                .setMessage(t("unsupported"))
                .setPositiveButton("OK", null)
                .show()
            DebugLog.info("Rejected unsupported source: $name")
        } else {
            DebugLog.info("Selected source: $name")
        }
    }

    private fun renderTargets() {
        val labels = targets.map { it.uppercase() }
        targetSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            labels,
        )
    }

    private fun performConversion(destination: Uri) {
        val source = sourceUri ?: return
        val target = pendingTarget
        val quality = qualityValue.text.toString().toIntOrNull() ?: 92
        convertButton.isEnabled = false
        statusLabel.text = t("working")
        DebugLog.info("Starting conversion: $sourceName -> $target")
        Thread {
            runCatching {
                ConversionCore.convert(this, source, sourceName, destination, target, quality)
            }.onSuccess {
                runOnUiThread {
                    convertButton.isEnabled = true
                    statusLabel.text = t("complete")
                    Toast.makeText(this, t("complete"), Toast.LENGTH_LONG).show()
                }
            }.onFailure { exception ->
                DebugLog.error("Conversion failed", exception)
                runOnUiThread {
                    convertButton.isEnabled = true
                    statusLabel.text = t("failed")
                    AlertDialog.Builder(this)
                        .setTitle(t("failed"))
                        .setMessage(exception.message ?: exception::class.java.simpleName)
                        .setPositiveButton("OK", null)
                        .show()
                }
            }
        }.start()
    }

    private fun toggleLogs() {
        logsVisible = !logsVisible
        logContainer.visibility = if (logsVisible) View.VISIBLE else View.GONE
        logToggleButton.text = t(if (logsVisible) "hide_log" else "show_log")
        renderLog()
    }

    private fun renderLog() {
        if (::logText.isInitialized) logText.text = DebugLog.text()
    }

    private fun exportLog() {
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "text/plain"
            putExtra(Intent.EXTRA_TITLE, "dotconvert-debug.log")
            addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        }
        startActivityForResult(intent, REQUEST_LOG)
    }

    private fun writeLog(destination: Uri) {
        runCatching {
            contentResolver.openOutputStream(destination, "w")?.bufferedWriter(Charsets.UTF_8)?.use {
                it.write(DebugLog.text())
                it.newLine()
            } ?: error("Unable to open log output")
        }.onFailure { DebugLog.error("Unable to export debug log", it) }
    }

    private fun displayName(uri: Uri): String {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (index >= 0) return cursor.getString(index)
            }
        }
        return uri.lastPathSegment ?: "source"
    }
}
