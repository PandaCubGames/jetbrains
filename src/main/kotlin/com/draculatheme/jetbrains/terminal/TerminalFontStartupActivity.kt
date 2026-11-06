package com.draculatheme.jetbrains.terminal

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity

class TerminalFontStartupActivity : ProjectActivity, DumbAware {
    override suspend fun execute(project: Project) {
        ApplicationManager.getApplication().getService(PandraculaTerminalFonts::class.java).requestApply()
    }
}
