import java.util.Properties

plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

// Keepsake's own Python and window come from the desktop app one folder up,
// or from another working copy named as keepsake.dir in local.properties.
val keepsakeDir: File = run {
    val local = Properties()
    rootProject.file("local.properties").takeIf { it.isFile }?.inputStream()?.use { local.load(it) }
    rootProject.file(local.getProperty("keepsake.dir") ?: "..")
}
val generated = layout.buildDirectory.dir("keepsake").get().asFile

val copyKeepsake by tasks.registering(Sync::class) {
    from(keepsakeDir.resolve("keepsake")) {
        into("python/keepsake")
        exclude("**/__pycache__/**")
    }
    from(keepsakeDir.resolve("ui")) {
        into("assets/ui")
        exclude("types.d.ts")
        // The bridge has to stand in for pywebview before the page's own script runs.
        filesMatching("index.html") {
            filter { it.replace("<script src=\"app.js\" defer></script>", "<script src=\"android.js\"></script>\n    <script src=\"app.js\" defer></script>") }
        }
    }
    from("src/main/web") { into("assets/ui") }
    into(generated)
    preserve { include("jniLibs/**", "*.tar.gz") }
}

val fetchFfmpeg by tasks.registering(Exec::class) {
    val out = generated.resolve("jniLibs/arm64-v8a")
    outputs.file(out.resolve("libffmpeg.so"))
    commandLine("py", "-3.13", rootProject.file("scripts/fetch_ffmpeg.py").path, out.path)
}

tasks.named("preBuild") { dependsOn(copyKeepsake, fetchFfmpeg) }
fetchFfmpeg { mustRunAfter(copyKeepsake) }
// Everything that reads the generated folder waits for it, which Gradle insists is said out loud.
tasks.configureEach {
    if (name != copyKeepsake.name && name != fetchFfmpeg.name && listOf("Python", "Assets", "JniLib", "NativeLibs", "Lint").any { it in name }) {
        dependsOn(copyKeepsake, fetchFfmpeg)
    }
}

android {
    namespace = "com.somethingobvious.keepsake"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.somethingobvious.keepsake"
        minSdk = 30
        targetSdk = 36
        versionCode = 19
        versionName = "1.6.1"
        ndk {
            // Chaquopy's Python 3.13 and the FFmpeg build are 64-bit ARM only.
            abiFilters += listOf("arm64-v8a")
        }
    }

    sourceSets {
        getByName("main") {
            assets.srcDir(generated.resolve("assets"))
            jniLibs.srcDir(generated.resolve("jniLibs"))
        }
    }

    buildTypes {
        release {
            // Sideloaded, so the debug key signs it until there is a store listing.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    packaging {
        // FFmpeg and QuickJS are programs, and Android only runs programs from the extracted library folder.
        jniLibs.useLegacyPackaging = true
    }
}

dependencies {
    // Remove Text's two models, run for the desktop's Python by Model.kt.
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.30.0")
}

chaquopy {
    defaultConfig {
        version = "3.13"
        buildPython("py", "-3.13")
        pip {
            install("yt-dlp==2026.8.19")
            install("yt-dlp-ejs==0.8.0")
            install("gallery-dl==1.32.16")
            // Remove Text: the newest Chaquopy builds for Python 3.13. jpeglib has none, so JPEGs are encoded again.
            install("numpy==1.26.2")
            install("pillow==11.0.0")
            for (extra in listOf("certifi", "mutagen", "requests", "websockets", "brotli", "pycryptodomex")) {
                install(extra)
            }
        }
    }
    sourceSets {
        getByName("main") {
            srcDir(generated.resolve("python"))
        }
    }
}
