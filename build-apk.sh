#!/bin/bash
set -e

echo "=== Iron Squad APK Builder ==="
echo ""

ANDROID_HOME="${ANDROID_HOME:-$HOME/android-sdk}"
PROJECT_DIR="$(cd "$(dirname "$0")/android" && pwd)"
APK_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check Java
if ! command -v java &> /dev/null; then
    echo "ERROR: Java not found. Install JDK 17:"
    echo "  sudo apt install openjdk-17-jdk"
    exit 1
fi

echo "Java: $(java -version 2>&1 | head -1)"

# Check Android SDK
if [ ! -d "$ANDROID_HOME" ]; then
    echo ""
    echo "Android SDK not found at $ANDROID_HOME"
    echo "Installing minimal SDK..."
    mkdir -p "$ANDROID_HOME/cmdline-tools"
    cd /tmp
    
    if [ ! -f "commandlinetools-linux.zip" ]; then
        wget -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" -O commandlinetools-linux.zip
    fi
    
    unzip -qo commandlinetools-linux.zip -d "$ANDROID_HOME/cmdline-tools/"
    mv "$ANDROID_HOME/cmdline-tools/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest" 2>/dev/null || true
    
    export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
    
    yes | sdkmanager --licenses > /dev/null 2>&1 || true
    sdkmanager "platforms;android-34" "build-tools;34.0.0" --channel=0 2>&1 | tail -3
fi

export ANDROID_HOME
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/34.0.0:$PATH"

echo "Android SDK: $ANDROID_HOME"
echo ""

# Copy game HTML to assets
echo "Copying game to Android assets..."
mkdir -p "$PROJECT_DIR/app/src/main/assets"
cp "$(dirname "$0")/index.html" "$PROJECT_DIR/app/src/main/assets/index.html"

# Build APK
echo "Building APK..."
cd "$PROJECT_DIR"

if [ -f "./gradlew" ]; then
    chmod +x ./gradlew
    ./gradlew assembleRelease --no-daemon
else
    # Use system gradle or download wrapper
    echo "Downloading Gradle wrapper..."
    gradle wrapper --gradle-version 8.2 2>/dev/null || true
    chmod +x ./gradlew
    ./gradlew assembleRelease --no-daemon
fi

# Find APK
APK_PATH=$(find "$PROJECT_DIR" -name "*.apk" -type f | head -1)

if [ -n "$APK_PATH" ]; then
    cp "$APK_PATH" "$APK_DIR/iron-squad.apk"
    echo ""
    echo "=== BUILD SUCCESS ==="
    echo "APK: $APK_DIR/iron-squad.apk"
    echo "Size: $(du -h "$APK_DIR/iron-squad.apk" | cut -f1)"
    echo ""
    echo "Install on device:"
    echo "  adb install iron-squad.apk"
else
    echo "ERROR: APK not found"
    exit 1
fi
