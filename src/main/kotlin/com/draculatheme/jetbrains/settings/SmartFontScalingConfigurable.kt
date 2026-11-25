package com.draculatheme.jetbrains.settings

import com.draculatheme.jetbrains.fontscaling.SmartFontScalingService
import com.intellij.openapi.options.BoundConfigurable
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.dsl.builder.Cell
import com.intellij.ui.dsl.builder.RightGap
import com.intellij.ui.dsl.builder.bindIntValue
import com.intellij.ui.dsl.builder.bindSelected
import com.intellij.ui.dsl.builder.bindValue
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.dsl.builder.selected
import java.util.Locale

class SmartFontScalingConfigurable : BoundConfigurable("Pandracula") {

    private var draft = SmartFontScalingSettings.instance.snapshot()

    override fun createPanel(): DialogPanel = panel {
        group("Smart Font Scaling") {
            lateinit var enabled: Cell<JBCheckBox>
            row {
                enabled = checkBox("Adjust the editor font size to the display scaling")
                    .bindSelected({ draft.enabled }, { draft.enabled = it })
                    .comment(
                        "Picks the editor font size from the reference below, so code looks the same " +
                            "size wherever the IDE draws at a different scale. Your own font settings are not " +
                            "changed and come back when you turn this off."
                    )
            }
            indent {
                row("Reference font size:") {
                    spinner(SmartFontScalingState.FONT_SIZE_RANGE)
                        .bindIntValue({ draft.referenceFontSize }, { draft.referenceFontSize = it })
                }
                row("Reference display scale:") {
                    spinner(50.0..400.0, 0.25)
                        .bindValue({ draft.referenceScalePercent.toDouble() }, { draft.referenceScalePercent = it.toFloat() })
                        .gap(RightGap.SMALL)
                    label("%")
                }
                row("Minimum font size:") {
                    spinner(SmartFontScalingState.FONT_SIZE_RANGE)
                        .bindIntValue({ draft.minFontSize }, { draft.minFontSize = it })
                }
                row("Maximum font size:") {
                    spinner(SmartFontScalingState.FONT_SIZE_RANGE)
                        .bindIntValue({ draft.maxFontSize }, { draft.maxFontSize = it })
                }
                row {
                    checkBox("Update when the display scale changes or the window moves to another monitor")
                        .bindSelected({ draft.updateOnMonitorChange }, { draft.updateOnMonitorChange = it })
                }
            }.enabledIf(enabled.selected)
            row {
                comment(detectedDisplay())
            }
        }
    }

    private fun detectedDisplay(): String {
        val scale = SmartFontScalingService.instance.displayScale()
        val percent = String.format(Locale.ROOT, "%.2f", scale * 100).trimEnd('0').trimEnd('.')
        val size = SmartFontScalingService.fontSizeFor(scale, SmartFontScalingSettings.instance.snapshot())
        return "The IDE draws the main display at $percent% scale, which gives font size $size with the saved settings. " +
            "On Linux with X11 this can be lower than the scaling set in the desktop."
    }

    override fun reset() {
        draft = SmartFontScalingSettings.instance.snapshot()
        super.reset()
    }

    override fun apply() {
        super.apply()
        SmartFontScalingSettings.instance.update(draft)
        // Show what was actually stored, in case a value had to be brought back into range.
        reset()
        SmartFontScalingService.instance.settingsChanged()
    }
}
