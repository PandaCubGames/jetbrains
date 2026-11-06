import org.jetbrains.changelog.Changelog
import org.jetbrains.intellij.platform.gradle.IntelliJPlatformType
import org.jetbrains.intellij.platform.gradle.models.ProductRelease
import org.jetbrains.intellij.platform.gradle.tasks.VerifyPluginTask
import org.jetbrains.intellij.platform.gradle.TestFrameworkType

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
    testImplementation("junit:junit:4.13.2")
    intellijPlatform {
        create(properties("platformType"), properties("platformVersion"))
        bundledPlugin("org.jetbrains.plugins.terminal")
        testFramework(TestFrameworkType.Platform)
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
        pandracula is a fork of the Dracula theme for JetBrains IDEs,
        maintained by PandaCub Games. It provides customized theme colors and
        pandracula variants based on the original Dracula themes.
      </p>
      <h2>Credits</h2>
      <p>
        Based on <a href="https://github.com/dracula/jetbrains">Dracula for JetBrains</a>.
        Credit for the original themes goes to the Dracula authors and contributors.
        The following links and donation information belong to the original Dracula project.
      </p>
      <h3>Original Dracula Installation Guide</h3>
      <p>
        Installation instructions for the original Dracula plugin can be found at
        <a href="https://draculatheme.com/jetbrains">draculatheme.com/jetbrains</a>.
      </p>
      <h3>Dracula PRO</h3>
      <p>
        <a href="https://gumroad.com/a/477820019">
          <img
            alt="Dracula Pro"
            src="https://raw.githubusercontent.com/dracula/jetbrains/master/docs/screenshots/dracula-pro.png"
          />
        </a>
      </p>
      <p>
        Dracula PRO is a color scheme and UI theme tailored for programming. Made
        for terminal emulators, code editors, and syntax highlighters. Designed to
        be aesthetically pleasing while keeping you focused.
      </p>
      <p><a href="https://gumroad.com/a/477820019">Get it now</a></p>
      <h3>Licence</h3>
      <p>
        <a href="https://raw.githubusercontent.com/dracula/jetbrains/master/LICENSE">
          MIT Licence
        </a>
      </p>
      <h3>Support the Original Dracula Maintainer</h3>
      <p>
        To support the original Dracula for JetBrains maintainer, you can
        <a href="https://www.buymeacoffee.com/nszihan">buy them a cup of coffee</a>.
        Thank you!
      </p>
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
