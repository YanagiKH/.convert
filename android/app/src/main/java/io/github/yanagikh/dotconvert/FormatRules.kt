package io.github.yanagikh.dotconvert

object FormatRules {
    private val imageInputs = setOf("png", "jpg", "jpeg", "webp", "bmp", "gif")
    private val textInputs = setOf("txt", "md", "markdown", "html", "htm", "log", "rst", "nfo")
    private val dataInputs = setOf("json", "jsonl", "csv", "tsv")

    fun extensionOf(name: String): String {
        val clean = name.substringAfterLast('/').lowercase()
        return clean.substringAfterLast('.', "")
    }

    fun targetsFor(name: String): List<String> = when (extensionOf(name)) {
        in imageInputs -> listOf("png", "jpg", "webp")
        in textInputs -> listOf("txt", "md", "html", "log", "rst", "nfo")
        in dataInputs -> listOf("json", "jsonl", "csv", "tsv")
        else -> emptyList()
    }

    fun suggestedName(sourceName: String, target: String): String {
        val base = sourceName.substringBeforeLast('.', sourceName)
        return "$base.$target"
    }

    fun mimeType(target: String): String = when (target.lowercase()) {
        "png" -> "image/png"
        "jpg", "jpeg" -> "image/jpeg"
        "webp" -> "image/webp"
        "html" -> "text/html"
        "json", "jsonl" -> "application/json"
        "csv" -> "text/csv"
        "tsv" -> "text/tab-separated-values"
        else -> "text/plain"
    }

    fun warnings(sourceName: String, target: String): List<String> {
        val source = extensionOf(sourceName)
        val output = target.lowercase()
        val warnings = mutableListOf<String>()
        if (source == output || (source == "jpeg" && output == "jpg")) {
            warnings += "same-format"
        }
        if (output in setOf("jpg", "webp")) warnings += "lossy-image"
        if (output == "jpg" && source in setOf("png", "webp", "gif")) warnings += "alpha-loss"
        if (source == "gif") warnings += "animation-loss"
        if (output in setOf("txt", "log", "rst", "nfo")) warnings += "formatting-loss"
        if (output in setOf("csv", "tsv")) warnings += "tabular-only"
        return warnings.distinct()
    }
}
