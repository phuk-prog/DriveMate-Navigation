#!/usr/bin/env bash
# Startup/input smoke only. No route, lane, timing or consumer-app score.
set -euo pipefail
sdk_root="${ANDROID_HOME:?GitHub Android SDK is required}"
out="$PWD/results/consumer-app-readiness"
mkdir -p "$out"
test -e /dev/kvm || { echo 'UNAVAILABLE: KVM absent' > "$out/status.txt"; exit 2; }
sudo chmod a+rw /dev/kvm
# The hosted Ubuntu 24.04 image does not guarantee all Android QEMU runtime libraries.
# Install only the missing pulse client dependency; no GUI/audio session is needed.
if ! ldconfig -p | grep -q 'libpulse.so.0'; then
  sudo apt-get update -qq >/dev/null
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libpulse0 >/dev/null
fi
sdkmanager_bin="$sdk_root/cmdline-tools/latest/bin/sdkmanager"
avdmanager_bin="$sdk_root/cmdline-tools/latest/bin/avdmanager"
set +o pipefail
yes | "$sdkmanager_bin" --sdk_root="$sdk_root" 'platform-tools' 'emulator' 'system-images;android-35;google_apis;x86_64' > "$out/sdk-install.log" 2>&1
install_status=${PIPESTATUS[1]}
set -o pipefail
test "$install_status" -eq 0
"$sdk_root/emulator/emulator" -accel-check > "$out/acceleration.txt"
"$sdk_root/emulator/emulator" -version > "$out/emulator-version.txt"
apk="$RUNNER_TEMP/organicmaps.apk"
curl -fsSL --retry 2 --max-time 180 'https://github.com/organicmaps/organicmaps/releases/download/2026.09.29-32-android/OrganicMaps-26092932-web-release.apk' -o "$apk"
echo "d7dbdfc3cbfdbcce6d437f11147f2cd15384c03052d2b4594fd8c1c7777dd497  $apk" | sha256sum -c - > "$out/apk-integrity.txt"
echo no | "$avdmanager_bin" create avd -n consumer_comparison -k 'system-images;android-35;google_apis;x86_64'
adb_bin="$sdk_root/platform-tools/adb"
"$adb_bin" start-server
"$sdk_root/emulator/emulator" -avd consumer_comparison -no-window -no-audio -no-boot-anim -no-snapshot -accel on -gpu swiftshader_indirect -memory 2048 > "$out/emulator.log" 2>&1 &
emu_pid=$!
trap '"$adb_bin" emu kill >/dev/null 2>&1 || true; kill "$emu_pid" 2>/dev/null || true; rm -f "$apk"' EXIT
booted=false
for i in $(seq 1 60); do
    if ! kill -0 "$emu_pid" 2>/dev/null; then echo 'FAILED: emulator exited' > "$out/status.txt"; exit 1; fi
    if "$adb_bin" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx 1; then booted=true; break; fi
    sleep 5
done
if [ "$booted" != true ]; then echo 'FAILED: boot timeout' > "$out/status.txt"; exit 1; fi
"$adb_bin" install "$apk" > "$out/install.txt"
"$adb_bin" shell monkey -p app.organicmaps -c android.intent.category.LAUNCHER 1 > "$out/launch.txt"
sleep 5
"$adb_bin" shell dumpsys activity activities > "$out/activities.txt"
grep -E 'mResumedActivity|topResumedActivity' "$out/activities.txt" | grep -q app.organicmaps
# Public Manchester centre input; no private drive or claim of lane accuracy.
"$adb_bin" emu geo fix -2.244644 53.483959 > "$out/location-input.txt"
echo 'PASSED: Organic Maps installed and resumed; emulator accepted a public UK coordinate. Navigation not tested or scored.' > "$out/status.txt"
cat "$out/status.txt"
