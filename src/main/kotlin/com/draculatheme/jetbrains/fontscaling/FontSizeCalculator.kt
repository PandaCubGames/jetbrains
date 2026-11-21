package com.draculatheme.jetbrains.fontscaling

import kotlin.math.roundToInt

/**
 * The editor font size for a display at [displayScale], chosen so that it stands in the same
 * proportion to that display as [referenceSize] does to a display at [referenceScale]:
 * 16 at 125% becomes 19 at 106.25% and 20 at 100%.
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

private const val STANDARD_DPI = 96f

// Anything outside this range is a misreported value rather than a real desktop setting.
private val PLAUSIBLE_DPI = 48f..960f

/**
 * The scaling the desktop is set to, as a factor (1.25 for 125%).
 *
 * [runtimeScale] is what the Java runtime applies when it paints, and is the whole answer on
 * Windows, macOS and Wayland. On X11 the runtime only scales by whole numbers, so a desktop at
 * 106.25% paints at 1.0 and the setting is visible only as a font DPI of 102. [fontDpi] carries
 * that value where the desktop publishes one; the two agree at whole-number scales, and the
 * larger one is the desktop's setting when they don't.
 */
fun effectiveDisplayScale(runtimeScale: Float, fontDpi: Float?): Float {
    val fromDpi = fontDpi?.takeIf { it in PLAUSIBLE_DPI }?.let { it / STANDARD_DPI } ?: 0f
    val scale = maxOf(runtimeScale, fromDpi)
    return if (scale > 0f && scale.isFinite()) scale else 1f
}

private val XFT_DPI_LINE = Regex("""^Xft\.dpi:\s*([0-9]+(?:\.[0-9]+)?)\s*$""", RegexOption.MULTILINE)

/** The `Xft.dpi` value from the output of `xrdb -query`, or null when it isn't set. */
fun parseXftDpi(xrdbOutput: String): Float? =
    XFT_DPI_LINE.find(xrdbOutput)?.groupValues?.get(1)?.toFloatOrNull()
