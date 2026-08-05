package io.github.yanagikh.dotconvert

object DelimitedCodec {
    fun parse(value: String, delimiter: Char): List<List<String>> {
        val rows = mutableListOf<MutableList<String>>()
        var row = mutableListOf<String>()
        val field = StringBuilder()
        var quoted = false
        var index = 0
        while (index < value.length) {
            val character = value[index]
            if (quoted) {
                if (character == '"' && index + 1 < value.length && value[index + 1] == '"') {
                    field.append('"')
                    index += 2
                    continue
                }
                if (character == '"') {
                    quoted = false
                } else {
                    field.append(character)
                }
            } else {
                when (character) {
                    '"' -> quoted = true
                    delimiter -> {
                        row += field.toString()
                        field.clear()
                    }
                    '\r' -> Unit
                    '\n' -> {
                        row += field.toString()
                        field.clear()
                        rows += row
                        row = mutableListOf()
                    }
                    else -> field.append(character)
                }
            }
            index += 1
        }
        if (quoted) throw IllegalArgumentException("Unclosed quoted field")
        if (field.isNotEmpty() || row.isNotEmpty()) {
            row += field.toString()
            rows += row
        }
        return rows.filterNot { it.size == 1 && it[0].isBlank() }
    }

    fun encode(rows: List<List<String>>, delimiter: Char): String = buildString {
        rows.forEach { row ->
            append(row.joinToString(delimiter.toString()) { escape(it, delimiter) })
            append('\n')
        }
    }

    private fun escape(value: String, delimiter: Char): String {
        if (value.any { it == delimiter || it == '"' || it == '\n' || it == '\r' }) {
            return "\"${value.replace("\"", "\"\"")}\""
        }
        return value
    }
}
