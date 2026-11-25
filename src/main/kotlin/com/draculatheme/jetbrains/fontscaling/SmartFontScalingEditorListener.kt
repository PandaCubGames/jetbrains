package com.draculatheme.jetbrains.fontscaling

import com.intellij.openapi.editor.event.EditorFactoryEvent
import com.intellij.openapi.editor.event.EditorFactoryListener

class SmartFontScalingEditorListener : EditorFactoryListener {
    override fun editorCreated(event: EditorFactoryEvent) = SmartFontScalingService.instance.editorCreated(event.editor)

    override fun editorReleased(event: EditorFactoryEvent) = SmartFontScalingService.instance.editorReleased(event.editor)
}
