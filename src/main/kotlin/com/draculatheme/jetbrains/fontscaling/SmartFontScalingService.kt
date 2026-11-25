package com.draculatheme.jetbrains.fontscaling

import com.draculatheme.jetbrains.settings.SmartFontScalingSettings
import com.draculatheme.jetbrains.settings.SmartFontScalingState
import com.intellij.ide.ui.UISettings
import com.intellij.ide.ui.UISettingsListener
import com.intellij.ide.ui.UISettingsUtils
import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.ModalityState
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.editor.EditorFactory
import com.intellij.openapi.editor.EditorKind
import com.intellij.openapi.editor.colors.EditorColorsListener
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.openapi.editor.ex.EditorEx
import com.intellij.openapi.util.Key
import com.intellij.ui.scale.JBUIScale
import java.awt.Component
import java.beans.PropertyChangeListener
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * Applies Smart Font Scaling to open editors.
 *
 * The size is set on each editor as a view-level override, the same mechanism Ctrl+mouse wheel
 * zoom uses. Nothing is written to the color scheme or to the editor font settings, so:
 *  - the font size the user chose stays stored exactly as it was, and turning the feature off
 *    (or removing the plugin) puts every editor back on it;
 *  - read-only bundled schemes and schemes carried by Settings Sync are never modified;
 *  - two windows on monitors with different scaling can each get their own size.
 *
 * An editor is only managed while its size is either the IDE's own default or the size this
 * service gave it. Any other size was set by someone else (the user zooming that editor, or a
 * text field that sizes its embedded editor to match the dialog) and is left alone until the
 * editor is back on the default.
 */
@Service(Service.Level.APP)
class SmartFontScalingService : Disposable {

    companion object {
        val instance: SmartFontScalingService get() = service()

        private val APPLIED_SIZE = Key.create<Float>("pandracula.smartFontScaling.appliedSize")
        private val LISTENER = Key.create<PropertyChangeListener>("pandracula.smartFontScaling.listener")

        private const val GRAPHICS_CONFIGURATION_PROPERTY = "graphicsConfiguration"

        private fun same(a: Float, b: Float) = abs(a - b) < 0.01f

        fun fontSizeFor(displayScale: Float, state: SmartFontScalingState): Int = calculateFontSize(
            displayScale = displayScale,
            referenceSize = state.referenceFontSize.toFloat(),
            referenceScale = state.referenceScalePercent / 100f,
            minSize = state.minFontSize,
            maxSize = state.maxFontSize,
        )
    }

    private val refreshQueued = AtomicBoolean()

    // With "update on monitor change" off, the scale is read once and kept for the session.
    @Volatile
    private var pinnedScale: Float? = null

    /**
     * The scale the IDE draws with on the monitor showing [component], or on the main monitor.
     *
     * This is deliberately not the desktop's scaling setting. On Windows, macOS and Wayland the
     * two are the same, but on X11 the runtime only scales by whole numbers: a desktop at 125%
     * is drawn at 1.0, so a font size of 19 really is 19 pixels there while 16 on Windows at 125%
     * is 20. What the text ends up looking like depends on the drawing scale alone.
     */
    fun displayScale(component: Component? = null): Float =
        JBUIScale.sysScale(component).takeIf { it > 0f && it.isFinite() } ?: 1f

    init {
        val connection = ApplicationManager.getApplication().messageBus.connect(this)
        connection.subscribe(EditorColorsManager.TOPIC, EditorColorsListener { scheduleRefresh() })
        connection.subscribe(UISettingsListener.TOPIC, UISettingsListener { scheduleRefresh() })
        // Editors opened before this service existed (the plugin was installed without a restart).
        EditorFactory.getInstance().allEditors.forEach(::track)
        scheduleRefresh()
    }

    fun editorCreated(editor: Editor) {
        track(editor)
        // Deferred so that whoever created the editor finishes configuring it first; a text
        // field gives its editor a size of its own, and that is how we know not to touch it.
        scheduleRefresh()
    }

    fun editorReleased(editor: Editor) = untrack(editor)

    /** Call after the settings were changed: re-reads the display and updates every editor. */
    fun settingsChanged() {
        pinnedScale = null
        scheduleRefresh()
    }

    private fun track(editor: Editor) {
        if (editor !is EditorEx || editor.getUserData(LISTENER) != null) return
        val listener = PropertyChangeListener { event ->
            when (event.propertyName) {
                // The window moved to another monitor, or the monitor's scaling changed.
                GRAPHICS_CONFIGURATION_PROPERTY -> scheduleRefresh()
                // The size was reset to the default, for instance by "Reset Font Size".
                EditorEx.PROP_FONT_SIZE -> scheduleRefresh()
            }
        }
        editor.putUserData(LISTENER, listener)
        editor.contentComponent.addPropertyChangeListener(GRAPHICS_CONFIGURATION_PROPERTY, listener)
        editor.addPropertyChangeListener(listener)
    }

    private fun untrack(editor: Editor) {
        val listener = editor.getUserData(LISTENER) ?: return
        editor.putUserData(LISTENER, null)
        editor.contentComponent.removePropertyChangeListener(GRAPHICS_CONFIGURATION_PROPERTY, listener)
        (editor as? EditorEx)?.removePropertyChangeListener(listener)
    }

    private fun scheduleRefresh() {
        if (!refreshQueued.compareAndSet(false, true)) return
        val app = ApplicationManager.getApplication()
        app.invokeLater({
            refreshQueued.set(false)
            refreshAll()
        }, ModalityState.any()) { app.isDisposed }
    }

    private fun refreshAll() {
        val state = SmartFontScalingSettings.instance.snapshot()
        // Presentation mode has a font size of its own, picked for the audience.
        val active = state.enabled && !UISettings.getInstance().presentationMode
        for (editor in EditorFactory.getInstance().allEditors) {
            if (editor.isDisposed) continue
            if (active && isCodeEditor(editor)) apply(editor, state) else restore(editor)
        }
    }

    private fun isCodeEditor(editor: Editor) =
        editor is EditorEx &&
            !editor.isOneLineMode &&
            (editor.editorKind == EditorKind.MAIN_EDITOR || editor.editorKind == EditorKind.DIFF)

    private fun scaleFor(editor: Editor, state: SmartFontScalingState): Float {
        if (state.updateOnMonitorChange) return displayScale(editor.contentComponent)
        return pinnedScale ?: displayScale().also { pinnedScale = it }
    }

    private fun apply(editor: Editor, state: SmartFontScalingState) {
        val zoom = UISettingsUtils.getInstance()
        val current = editor.colorsScheme.editorFontSize2D
        val applied = editor.getUserData(APPLIED_SIZE)
        val managed = (applied != null && same(current, applied)) || same(current, zoom.scaledEditorFontSize)
        if (!managed) {
            editor.putUserData(APPLIED_SIZE, null)
            return
        }

        // IDE zoom (View | Appearance | Zoom IDE) enlarges the whole IDE on purpose; keep honoring it.
        val target = zoom.scaleFontSize(fontSizeFor(scaleFor(editor, state), state).toFloat()).roundToInt()
        if (!same(current, target.toFloat())) {
            (editor as EditorEx).setFontSize(target)
        }
        editor.putUserData(APPLIED_SIZE, editor.colorsScheme.editorFontSize2D)
    }

    private fun restore(editor: Editor) {
        val applied = editor.getUserData(APPLIED_SIZE) ?: return
        editor.putUserData(APPLIED_SIZE, null)
        // Only undo our own size. Setting the default clears the override, so the editor follows
        // the font settings again.
        if (editor is EditorEx && same(editor.colorsScheme.editorFontSize2D, applied)) {
            editor.setFontSize(UISettingsUtils.getInstance().scaledEditorFontSize)
        }
    }

    override fun dispose() {
        val app = ApplicationManager.getApplication()
        if (app.isDisposed) return
        // The plugin is being unloaded while the IDE keeps running: hand the editors back.
        val editors = app.getServiceIfCreated(EditorFactory::class.java)?.allEditors ?: return
        for (editor in editors) {
            untrack(editor)
            if (!editor.isDisposed) restore(editor)
        }
    }
}
