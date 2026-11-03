import org.jetbrains.changelog.Changelog
import org.jetbrains.intellij.platform.gradle.IntelliJPlatformType
import org.jetbrains.intellij.platform.gradle.models.ProductRelease
import org.jetbrains.intellij.platform.gradle.tasks.VerifyPluginTask

fun properties(key: String) = project.findProperty(key).toString()

plugins {
    id("java")
    id("org.jetbrains.kotlin.jvm") version "2.1.0"
    id("org.jetbrains.intellij.platform") version "2.17.0"
    id("org.jetbrains.changelog") version "2.2.1"
}

group = properties("pluginGroup")
version = properties("pluginVersion")

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        create(properties("platformType"), properties("platformVersion"))
        // Plugin verifier for compatibility checks
        pluginVerifier()
    }
}

changelog {
    version.set(properties("pluginVersion"))
    path.set("${project.projectDir}/CHANGELOG.md")
    groups.set(emptyList())
}

val pluginDescription = """
    <div>
      <p>
        Pandacub Dracula is a fork of the
        <a href="https://github.com/dracula/jetbrains">Dracula theme for JetBrains IDEs</a>.
        It keeps the earlier interface colors of the dark variants and follows every
        other upstream improvement.
      </p>
      <p>
        Includes Pandacub Dracula, Pandacub Dracula Colorful and Pandacub Dracula Alucard, each
        also in an Islands version. Not affiliated with the official Dracula Theme.
      </p>
      <p><a href="https://github.com/PandaCubGames/jetbrains">Source code</a></p>
      <h2>Licence</h2>
      <p><a href="https://github.com/PandaCubGames/jetbrains/blob/master/LICENSE">MIT Licence</a></p>
    </div>
""".trimIndent()

intellijPlatform {
    buildSearchableOptions = false
    pluginConfiguration {
        name = properties("pluginName")
        version = properties("pluginVersion")
        description = pluginDescription
        changeNotes = provider {
            changelog.renderItem(changelog.getLatest(), Changelog.OutputType.HTML)
        }
        ideaVersion {
            untilBuild = provider { null }
        }
    }
    publishing {
        // Prefer the environment variable: a -D system property is visible to anything that can
        // list processes on the machine. The property stays supported for local one-off publishes.
        token = System.getenv("JETBRAINS_TOKEN") ?: System.getProperty("jetbrains.token")
    }
    pluginVerification {
        ides {
            recommended()
            select {
                types = listOf(IntelliJPlatformType.IntellijIdeaUltimate)
                channels = listOf(ProductRelease.Channel.RELEASE)
                sinceBuild = "253"
            }
        }
        failureLevel = listOf(
            VerifyPluginTask.FailureLevel.COMPATIBILITY_PROBLEMS, VerifyPluginTask.FailureLevel.INVALID_PLUGIN
        )
    }
}

// Preview the plugin on the latest released IDE without changing the build target.
// `./gradlew runIdeLatest` launches this; `./gradlew runIde` still uses platformVersion.
val runIdeLatest by intellijPlatformTesting.runIde.registering {
    type = IntelliJPlatformType.IntellijIdeaUltimate
    version = "2026.1.3"
}
