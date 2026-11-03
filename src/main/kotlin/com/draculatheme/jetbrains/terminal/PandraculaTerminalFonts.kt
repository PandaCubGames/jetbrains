package com.draculatheme.jetbrains.terminal

import com.intellij.ide.ui.UISettings
import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.ModalityState
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.editor.colors.EditorColorsListener
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.openapi.editor.colors.impl.FontPreferencesImpl
import com.intellij.openapi.editor.impl.FontFamilyService
import org.jetbrains.plugins.terminal.TerminalFontSettingsService
import org.jetbrains.plugins.terminal.TerminalFontSettingsState

class TerminalFontDefaultsState {
    var applied: Boolean = false
}

// The terminal has independent preferences in 2025.3+. Keep its integration in the
// optional Terminal descriptor, and initialize once rather than resetting user edits.
@Suppress("UnstableApiUsage")
@State(name = "PandraculaTerminalFontDefaults", storages = [Storage("pandracula-terminal-fonts.xml")])
class PandraculaTerminalFonts : PersistentStateComponent<TerminalFontDefaultsState>, Disposable {
    private var defaultsState = TerminalFontDefaultsState()
    private var disposed = false

    init {
        ApplicationManager.getApplication().messageBus.connect(this)
            .subscribe(EditorColorsManager.TOPIC, EditorColorsListener { requestApply() })
    }

    fun requestApply() {
        val application = ApplicationManager.getApplication()
        if (application.isDisposed) return
        application.invokeLater({
            if (!disposed && !defaultsState.applied) applyDefaults()
        }, ModalityState.any())
    }

    private fun applyDefaults() {
        val schemeName = EditorColorsManager.getInstance().globalScheme.name.removePrefix("_@user_")
        if (schemeName !in setOf("pandracula", "pandracula colorful", "pandracula alucub")) return

        val preferences = FontPreferencesImpl().apply {
            register("JetBrains Mono", 19.2f * UISettings.defFontScale)
            val regular = FontFamilyService.getRecommendedSubFamily("JetBrains Mono")
            regularSubFamily = regular
            boldSubFamily = FontFamilyService.getRecommendedBoldSubFamily("JetBrains Mono", regular)
            lineSpacing = 1.2f
            setUseLigatures(false)
        }
        val terminal = TerminalFontSettingsService.getInstance()
        val state = TerminalFontSettingsState(preferences).apply {
            COLUMN_SPACING = terminal.getState().COLUMN_SPACING
        }
        // Loading the state also notifies both terminal engines to refresh fonts.
        terminal.loadState(state)
        defaultsState.applied = true
    }

    override fun getState(): TerminalFontDefaultsState = defaultsState

    override fun loadState(state: TerminalFontDefaultsState) {
        defaultsState = state
    }

    override fun dispose() {
        disposed = true
    }
}
