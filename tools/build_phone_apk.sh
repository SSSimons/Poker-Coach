#!/usr/bin/env bash
set -euo pipefail

# ARM64 build for modern physical Android phones, including most Samsung
# Galaxy models. Run inside WSL after activating the Buildozer venv.

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export APP_ANDROID_ARCHS=arm64-v8a

cd "$project_dir"
buildozer -v android debug

dist="$project_dir/.buildozer/android/platform/build-arm64-v8a/dists/casinocoach"
bundle="$dist/_python_bundle__arm64-v8a/_python_bundle"
hostpython="$project_dir/.buildozer/android/platform/build-arm64-v8a/build/other_builds/hostpython3/desktop/hostpython3/native-build/root/usr/local"
temporary_dir="$(mktemp -d)"

# Keep bootstrap modules importable before zlib itself is available.
unzip -q "$bundle/stdlib.zip" -d "$temporary_dir"
(
  cd "$temporary_dir"
  zip -0 -q -r "$bundle/stdlib-store.zip" .
)
mv "$bundle/stdlib-store.zip" "$bundle/stdlib.zip"

# Android loads extension modules in a restricted linker namespace, so make
# their dependency on the packaged Python runtime explicit.
find "$bundle" -type f -name '*.so' -print0 \
  | xargs -0 -n 1 "$hostpython/bin/patchelf" --add-needed libpython3.12.so

(
  cd "$dist/_python_bundle__arm64-v8a"
  tar -czf "$dist/libs/arm64-v8a/libpybundle.so" _python_bundle
)

(
  cd "$dist"
  ./gradlew clean assembleDebug
)

cp "$dist/build/outputs/apk/debug/casinocoach-debug.apk" \
  "$project_dir/bin/casinocoach-0.5.4-arm64-v8a-debug.apk"

echo "APK: $project_dir/bin/casinocoach-0.5.4-arm64-v8a-debug.apk"
