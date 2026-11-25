package com.draculatheme.jetbrains.fontscaling

import kotlin.math.roundToInt

/**
 * The editor font size for a display drawn at [displayScale], chosen so the text comes out the
 * same number of pixels tall as [referenceSize] does on a display drawn at [referenceScale]:
 * 16 at 125% becomes 20 at 100% and 13 at 150%.
 *
 * The result always comes from the reference values, never from the size currently in use, so
 * calling this again for the same display cannot compound an earlier adjustment.
 */
fun calculateFontSize(
    displayScale: Float,
    referenceSize: Float = 16f,
    referenceScale: Float = 1.25f,
    minSize: Int = 10,
    maxSize: Int = 30,
): Int {
    require(displayScale > 0f) { "displayScale must be positive, was $displayScale" }
    require(minSize <= maxSize) { "minSize $minSize is above maxSize $maxSize" }

    return (referenceSize * referenceScale / displayScale).roundToInt().coerceIn(minSize, maxSize)
}
