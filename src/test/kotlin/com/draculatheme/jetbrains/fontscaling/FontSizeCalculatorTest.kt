package com.draculatheme.jetbrains.fontscaling

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class FontSizeCalculatorTest {

    @Test
    fun `reproduces the owner's two setups`() {
        assertEquals("Windows at 125%", 16, calculateFontSize(1.25f))
        assertEquals("Debian at 106.25%", 19, calculateFontSize(1.0625f))
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

    @Test
    fun `display scale is the runtime scale where the runtime does the scaling`() {
        assertEquals(1.25f, effectiveDisplayScale(1.25f, null), 0f)
        assertEquals(2f, effectiveDisplayScale(2f, 192f), 0f)
    }

    @Test
    fun `display scale comes from the font DPI on X11 fractional scaling`() {
        assertEquals(1.0625f, effectiveDisplayScale(1f, 102f), 0f)
        assertEquals(1.5f, effectiveDisplayScale(1f, 144f), 0f)
    }

    @Test
    fun `implausible values fall back`() {
        assertEquals(1f, effectiveDisplayScale(1f, 0f), 0f)
        assertEquals(1f, effectiveDisplayScale(1f, 100_000f), 0f)
        assertEquals(1f, effectiveDisplayScale(0f, null), 0f)
        assertEquals(1f, effectiveDisplayScale(Float.NaN, null), 0f)
    }

    @Test
    fun `reads the font DPI from xrdb output`() {
        val output = "Xcursor.size:\t24\nXft.antialias:\t1\nXft.dpi:\t102\nXft.hinting:\t1\n"
        assertEquals(102f, parseXftDpi(output)!!, 0f)
        assertEquals(100.5f, parseXftDpi("Xft.dpi: 100.5\n")!!, 0f)
        assertEquals(19, calculateFontSize(effectiveDisplayScale(1f, parseXftDpi(output))))
    }

    @Test
    fun `no font DPI when xrdb does not have one`() {
        assertNull(parseXftDpi(""))
        assertNull(parseXftDpi("Xcursor.size:\t24\nMyXft.dpi:\t144\n"))
        assertNull(parseXftDpi("Xft.dpi:\tlarge\n"))
    }
}
