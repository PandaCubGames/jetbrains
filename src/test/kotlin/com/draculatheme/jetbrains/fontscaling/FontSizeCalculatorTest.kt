package com.draculatheme.jetbrains.fontscaling

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class FontSizeCalculatorTest {

    @Test
    fun `reproduces the owner's two setups`() {
        // Windows at 125%: the runtime draws at 1.25.
        assertEquals(16, calculateFontSize(1.25f))
        // KDE on X11 at 125%: the runtime draws at 1.0, so the same text needs 20.
        assertEquals(20, calculateFontSize(1f))
    }

    @Test
    fun `known scaling factors`() {
        val expected = mapOf(1.0f to 20, 1.0625f to 19, 1.25f to 16, 1.5f to 13, 1.75f to 11, 2.0f to 10)
        for ((scale, size) in expected) {
            assertEquals("at ${scale * 100}%", size, calculateFontSize(scale))
        }
    }

    @Test
    fun `result stays within the limits`() {
        assertEquals(10, calculateFontSize(4f))
        assertEquals(30, calculateFontSize(0.25f))
        assertEquals(14, calculateFontSize(2f, minSize = 14, maxSize = 18))
        assertEquals(18, calculateFontSize(1f, minSize = 14, maxSize = 18))
    }

    @Test
    fun `custom reference values`() {
        assertEquals(19, calculateFontSize(1.0625f, referenceSize = 19f, referenceScale = 1.0625f))
        assertEquals(16, calculateFontSize(1.25f, referenceSize = 19f, referenceScale = 1.0625f))
    }

    @Test
    fun `rejects impossible input`() {
        assertThrows(IllegalArgumentException::class.java) { calculateFontSize(0f) }
        assertThrows(IllegalArgumentException::class.java) { calculateFontSize(-1f) }
        assertThrows(IllegalArgumentException::class.java) { calculateFontSize(1f, minSize = 20, maxSize = 10) }
    }
}
