#!/usr/bin/env bash
set -euo pipefail

# Run inside WSL from the project root after activating the Buildozer venv.
# CPython 3.12 needs these two packaging adjustments with the current p4a
# bootstrap on Android x86_64: bootstrap imports must be stored in stdlib.zip,
# and extension modules must explicitly depend on libpython3.12.so.

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export APP_ANDROID_ARCHS=x86_64

cd "$project_dir"
buildozer -v android debug

dist="$project_dir/.buildozer/android/platform/build-x86_64/dists/casinocoach"
bundle="$dist/_python_bundle__x86_64/_python_bundle"
hostpython="$project_dir/.buildozer/android/platform/build-x86_64/build/other_builds/hostpython3/desktop/hostpython3/native-build/root/usr/local"
temporary_dir="$(mktemp -d)"

unzip -q "$bundle/stdlib.zip" -d "$temporary_dir"
(
  cd "$temporary_dir"
  zip -0 -q -r "$bundle/stdlib-store.zip" .
)
mv "$bundle/stdlib-store.zip" "$bundle/stdlib.zip"

find "$bundle" -type f -name '*.so' -print0 \
  | xargs -0 -n 1 "$hostpython/bin/patchelf" --add-needed libpython3.12.so

(
  cd "$dist/_python_bundle__x86_64"
  tar -czf "$dist/libs/x86_64/libpybundle.so" _python_bundle
)

(
  cd "$dist"
  ./gradlew clean assembleDebug
)

cp "$dist/build/outputs/apk/debug/casinocoach-debug.apk" \
  "$project_dir/bin/casinocoach-0.5.4-x86_64-debug.apk"

echo "APK: $project_dir/bin/casinocoach-0.5.4-x86_64-debug.apk"
