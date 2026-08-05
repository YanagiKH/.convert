package io.github.yanagikh.dotconvert

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FormatRulesTest {
    @Test
    fun imageTargetsAreSafeNativeOutputs() {
        assertEquals(listOf("png", "jpg", "webp"), FormatRules.targetsFor("photo.GIF"))
    }

    @Test
    fun unsupportedFilesHaveNoTargets() {
        assertTrue(FormatRules.targetsFor("archive.zip").isEmpty())
    }

    @Test
    fun suggestedNameReplacesTheLastExtension() {
        assertEquals("report.json", FormatRules.suggestedName("report.csv", "json"))
    }
}
