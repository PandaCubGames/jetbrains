package com.draculatheme.jetbrains.terminal

import com.intellij.ide.ui.UISettings
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.openapi.editor.colors.EditorColorsScheme
import com.intellij.openapi.editor.colors.impl.FontPreferencesImpl
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.util.ui.UIUtil
import org.jetbrains.plugins.terminal.TerminalFontSettingsService
import org.jetbrains.plugins.terminal.TerminalFontSettingsState

@Suppress("UnstableApiUsage")
class PandraculaTerminalFontsTest : BasePlatformTestCase() {
    private lateinit var fonts: PandraculaTerminalFonts
    private lateinit var terminal: TerminalFontSettingsService
    private lateinit var originalScheme: EditorColorsScheme
    private lateinit var originalTerminalState: TerminalFontSettingsState
    private var originallyApplied = false

    override fun setUp() {
        super.setUp()
        fonts = ApplicationManager.getApplication().getService(PandraculaTerminalFonts::class.java)
        terminal = TerminalFontSettingsService.getInstance()
        originalScheme = EditorColorsManager.getInstance().globalScheme
        originalTerminalState = terminal.getState()
        originallyApplied = fonts.state.applied
        fonts.loadState(TerminalFontDefaultsState())
        selectScheme("Unrelated test scheme")
        setTerminalSize(13f)
        UIUtil.dispatchAllInvocationEvents()
    }

    override fun tearDown() {
        try {
            fonts.loadState(TerminalFontDefaultsState().apply { applied = true })
            terminal.loadState(originalTerminalState)
            EditorColorsManager.getInstance().setGlobalScheme(originalScheme)
            UIUtil.dispatchAllInvocationEvents()
            fonts.loadState(TerminalFontDefaultsState().apply { applied = originallyApplied })
        } finally {
            super.tearDown()
        }
    }

    fun testAppliesMatchingFontsOnceAndPreservesLaterTerminalEdits() {
        selectScheme("_@user_Pandracula")
        fonts.requestApply()
        UIUtil.dispatchAllInvocationEvents()

        val preferences = terminal.fontPreferences
        assertEquals("JetBrains Mono", preferences.fontFamily)
        assertEquals(19.2f * UISettings.defFontScale,
                     preferences.getSize2D(preferences.fontFamily), 0.001f)
        assertEquals(1.2f, preferences.lineSpacing, 0.001f)
        assertFalse(preferences.useLigatures())
        assertEquals(1.3f, terminal.getState().COLUMN_SPACING, 0.001f)
        assertTrue(fonts.state.applied)

        setTerminalSize(21f)
        selectScheme("Pandracula Colorful")
        fonts.requestApply()
        UIUtil.dispatchAllInvocationEvents()
        assertEquals(21f, terminal.fontPreferences.getSize2D("JetBrains Mono"), 0.001f)
    }

    fun testDoesNotChangeTerminalForOtherSchemes() {
        fonts.requestApply()
        UIUtil.dispatchAllInvocationEvents()
        assertEquals(13f, terminal.fontPreferences.getSize2D("JetBrains Mono"), 0.001f)
        assertFalse(fonts.state.applied)
    }

    private fun selectScheme(name: String) {
        val scheme = originalScheme.clone() as EditorColorsScheme
        scheme.name = name
        EditorColorsManager.getInstance().setGlobalScheme(scheme)
    }

    private fun setTerminalSize(size: Float) {
        val preferences = FontPreferencesImpl().apply {
            register("JetBrains Mono", size)
            lineSpacing = 1f
        }
        terminal.loadState(TerminalFontSettingsState(preferences).apply { COLUMN_SPACING = 1.3f })
    }
}
