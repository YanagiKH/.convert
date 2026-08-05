package io.github.yanagikh.dotconvert

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.text.Html
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.io.File
import java.io.FileOutputStream

object ConversionCore {
    private const val maxTextBytes = 32L * 1024L * 1024L
    private const val maxImagePixels = 80_000_000L

    fun convert(
        context: Context,
        source: Uri,
        sourceName: String,
        destination: Uri,
        target: String,
        quality: Int,
    ) {
        val temporary = File.createTempFile("dotconvert-", ".$target", context.cacheDir)
        try {
            DebugLog.debug("Temporary output: ${temporary.absolutePath}")
            val sourceExtension = FormatRules.extensionOf(sourceName)
            when {
                sourceExtension in setOf("png", "jpg", "jpeg", "webp", "bmp", "gif") ->
                    convertImage(context, source, temporary, target, quality)
                sourceExtension in setOf("txt", "md", "markdown", "html", "htm", "log", "rst", "nfo") ->
                    convertText(context, source, sourceExtension, temporary, target)
                sourceExtension in setOf("json", "jsonl", "csv", "tsv") ->
                    convertData(context, source, sourceExtension, temporary, target)
                else -> error("Unsupported Android source format: $sourceExtension")
            }
            require(temporary.isFile && temporary.length() > 0L) {
                "Conversion produced an empty output file"
            }
            context.contentResolver.openOutputStream(destination, "w")?.use { output ->
                temporary.inputStream().use { input -> input.copyTo(output, 1024 * 1024) }
            } ?: error("Unable to open the selected output document")
            DebugLog.info("Conversion committed to the selected document")
        } finally {
            if (!temporary.delete()) temporary.deleteOnExit()
        }
    }

    private fun convertImage(
        context: Context,
        source: Uri,
        destination: File,
        target: String,
        quality: Int,
    ) {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(source)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        } ?: error("Unable to open source image")
        require(bounds.outWidth > 0 && bounds.outHeight > 0) { "The selected image could not be decoded" }
        val pixels = bounds.outWidth.toLong() * bounds.outHeight.toLong()
        require(pixels <= maxImagePixels) { "Image dimensions exceed the 80-megapixel safety limit" }

        val bitmap = context.contentResolver.openInputStream(source)?.use {
            BitmapFactory.decodeStream(it)
        } ?: error("The selected image could not be decoded")
        val prepared = if (target == "jpg" && bitmap.hasAlpha()) flattenOnWhite(bitmap) else bitmap
        try {
            val format = when (target) {
                "png" -> Bitmap.CompressFormat.PNG
                "jpg" -> Bitmap.CompressFormat.JPEG
                "webp" -> if (Build.VERSION.SDK_INT >= 30) {
                    Bitmap.CompressFormat.WEBP_LOSSY
                } else {
                    @Suppress("DEPRECATION")
                    Bitmap.CompressFormat.WEBP
                }
                else -> error("Unsupported Android image target: $target")
            }
            FileOutputStream(destination).use { output ->
                require(prepared.compress(format, quality.coerceIn(1, 100), output)) {
                    "Android image encoder rejected the output"
                }
            }
        } finally {
            if (prepared !== bitmap) prepared.recycle()
            bitmap.recycle()
        }
    }

    private fun flattenOnWhite(source: Bitmap): Bitmap {
        val output = Bitmap.createBitmap(source.width, source.height, Bitmap.Config.ARGB_8888)
        Canvas(output).apply {
            drawColor(Color.WHITE)
            drawBitmap(source, 0f, 0f, null)
        }
        return output
    }

    private fun readText(context: Context, source: Uri): String {
        val bytes = context.contentResolver.openInputStream(source)?.use { input ->
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            var total = 0L
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                total += count
                require(total <= maxTextBytes) { "Text input exceeds the 32 MiB safety limit" }
                output.write(buffer, 0, count)
            }
            output.toByteArray()
        } ?: error("Unable to open source text")
        return bytes.toString(Charsets.UTF_8)
    }

    private fun convertText(
        context: Context,
        source: Uri,
        sourceExtension: String,
        destination: File,
        target: String,
    ) {
        val raw = readText(context, source)
        val plain = if (sourceExtension in setOf("html", "htm")) {
            @Suppress("DEPRECATION")
            Html.fromHtml(raw).toString()
        } else {
            raw
        }
        val output = when (target) {
            "txt", "log", "rst", "nfo", "md" -> plain
            "html" -> if (sourceExtension in setOf("html", "htm")) {
                raw
            } else {
                "<!doctype html>\n<html><head><meta charset=\"utf-8\"></head>" +
                    "<body><pre>${Html.escapeHtml(raw)}</pre></body></html>\n"
            }
            else -> error("Unsupported Android text target: $target")
        }
        destination.writeText(output, Charsets.UTF_8)
    }

    private fun convertData(
        context: Context,
        source: Uri,
        sourceExtension: String,
        destination: File,
        target: String,
    ) {
        val raw = readText(context, source)
        val value: Any = when (sourceExtension) {
            "json" -> JSONTokener(raw).nextValue()
            "jsonl" -> JSONArray().also { array ->
                raw.lineSequence().filter { it.isNotBlank() }.forEach { line ->
                    array.put(JSONTokener(line).nextValue())
                }
            }
            "csv", "tsv" -> tableToJson(
                DelimitedCodec.parse(raw, if (sourceExtension == "tsv") '\t' else ','),
            )
            else -> error("Unsupported Android data source: $sourceExtension")
        }
        val output = when (target) {
            "json" -> prettyJson(value) + "\n"
            "jsonl" -> jsonLines(value)
            "csv", "tsv" -> DelimitedCodec.encode(
                jsonToTable(value),
                if (target == "tsv") '\t' else ',',
            )
            else -> error("Unsupported Android data target: $target")
        }
        destination.writeText(output, Charsets.UTF_8)
    }

    private fun tableToJson(rows: List<List<String>>): JSONArray {
        require(rows.isNotEmpty()) { "Delimited input has no rows" }
        val headers = rows.first()
        require(headers.isNotEmpty() && headers.none { it.isBlank() }) {
            "Delimited input requires non-empty column names"
        }
        val output = JSONArray()
        rows.drop(1).forEach { row ->
            val item = JSONObject()
            headers.forEachIndexed { index, header -> item.put(header, row.getOrElse(index) { "" }) }
            output.put(item)
        }
        return output
    }

    private fun jsonToTable(value: Any): List<List<String>> {
        val records = when (value) {
            is JSONArray -> (0 until value.length()).map { value.get(it) }
            is JSONObject -> listOf(value)
            else -> error("CSV and TSV output require an object or an array of objects")
        }
        require(records.all { it is JSONObject }) { "CSV and TSV output require object rows" }
        val headers = linkedSetOf<String>()
        records.filterIsInstance<JSONObject>().forEach { record ->
            record.keys().forEachRemaining { headers += it }
        }
        val headerList = headers.toList()
        val output = mutableListOf<List<String>>(headerList)
        records.filterIsInstance<JSONObject>().forEach { record ->
            output += headerList.map { key ->
                val item = record.opt(key)
                require(item !is JSONObject && item !is JSONArray) {
                    "Nested values cannot be written to CSV or TSV"
                }
                if (item == null || item == JSONObject.NULL) "" else item.toString()
            }
        }
        return output
    }

    private fun prettyJson(value: Any): String = when (value) {
        is JSONObject -> value.toString(2)
        is JSONArray -> value.toString(2)
        else -> JSONObject.wrap(value).toString()
    }

    private fun jsonLines(value: Any): String {
        val records = if (value is JSONArray) {
            (0 until value.length()).map { value.get(it) }
        } else {
            listOf(value)
        }
        return records.joinToString(separator = "\n", postfix = "\n") { item ->
            when (item) {
                is JSONObject -> item.toString()
                is JSONArray -> item.toString()
                else -> JSONObject.valueToString(item)
            }
        }
    }
}
