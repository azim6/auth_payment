plugins {
    kotlin("jvm") version "2.0.0"
}

group = "com.example.authplatform"
version = "0.1.0"

repositories { mavenCentral() }

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
}
