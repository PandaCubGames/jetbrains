package com.draculatheme.jetbrains.settings

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.RoamingType
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage

class SmartFontScalingState {
    var enabled: Boolean = false
    var referenceFontSize: Int = 16
    var referenceScalePercent: Float = 125f
    var minFontSize: Int = 10
    var maxFontSize: Int = 30
    var updateOnMonitorChange: Boolean = true

    fun copy() = SmartFontScalingState().also {
        it.enabled = enabled
        it.referenceFontSize = referenceFontSize
        it.referenceScalePercent = referenceScalePercent
        it.minFontSize = minFontSize
        it.maxFontSize = maxFontSize
        it.updateOnMonitorChange = updateOnMonitorChange
    }

    /** Pulls hand-edited or out-of-date values back into the ranges the settings page allows. */
    fun sanitized() = copy().also {
        it.referenceFontSize = referenceFontSize.coerceIn(FONT_SIZE_RANGE)
        it.referenceScalePercent =
            if (referenceScalePercent.isFinite()) referenceScalePercent.coerceIn(SCALE_PERCENT_RANGE) else 125f
        it.minFontSize = minFontSize.coerceIn(FONT_SIZE_RANGE)
        it.maxFontSize = maxFontSize.coerceIn(it.minFontSize, FONT_SIZE_RANGE.last)
    }

    companion object {
        val FONT_SIZE_RANGE = 6..72
        val SCALE_PERCENT_RANGE = 50f..400f
    }
}

/**
 * Smart Font Scaling preferences. They live in their own file with roaming disabled, so each IDE
 * installation keeps its own copy and Settings Sync never carries them to another machine.
 */
@State(
    name = "PandraculaSmartFontScaling",
    storages = [Storage("pandracula-font-scaling.xml", roamingType = RoamingType.DISABLED)],
)
class SmartFontScalingSettings : PersistentStateComponent<SmartFontScalingState> {
    companion object {
        val instance: SmartFontScalingSettings
            get() = ApplicationManager.getApplication().getService(SmartFontScalingSettings::class.java)
    }

    @Volatile
    private var myState = SmartFontScalingState()

    /** A private copy: changing it does nothing until it is passed to [update]. */
    fun snapshot(): SmartFontScalingState = myState.copy()

    fun update(newState: SmartFontScalingState) {
        myState = newState.sanitized()
    }

    override fun getState(): SmartFontScalingState = myState

    override fun loadState(state: SmartFontScalingState) {
        myState = state.sanitized()
    }
}
