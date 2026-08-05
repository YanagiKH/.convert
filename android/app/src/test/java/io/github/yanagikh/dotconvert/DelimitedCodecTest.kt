package io.github.yanagikh.dotconvert

import org.junit.Assert.assertEquals
import org.junit.Test

class DelimitedCodecTest {
    @Test
    fun quotedFieldsRoundTrip() {
        val rows = listOf(
            listOf("name", "note"),
            listOf("Miku", "comma, quote \" and newline\nkept"),
        )
        val encoded = DelimitedCodec.encode(rows, ',')
        assertEquals(rows, DelimitedCodec.parse(encoded, ','))
    }

    @Test(expected = IllegalArgumentException::class)
    fun unclosedQuoteIsRejected() {
        DelimitedCodec.parse("name\n\"broken", ',')
    }
}
