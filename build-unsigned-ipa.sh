#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$ROOT_DIR/build/unsigned-ipa"
PAYLOAD_DIR="$BUILD_DIR/Payload"
APP_NAME="Dashboard.app"
IPA_PATH="$ROOT_DIR/Dashboard-unsigned.ipa"
XCODEBUILD="/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild"
SDK="iphoneos7.1"

rm -rf "$BUILD_DIR" "$IPA_PATH"
mkdir -p "$PAYLOAD_DIR"

"$XCODEBUILD" \
  -project "$ROOT_DIR/Dashboard.xcodeproj" \
  -scheme Dashboard \
  -configuration Release \
  -sdk "$SDK" \
  CONFIGURATION_BUILD_DIR="$BUILD_DIR" \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY="" \
  clean build

cp -R "$BUILD_DIR/$APP_NAME" "$PAYLOAD_DIR/$APP_NAME"

(
  cd "$BUILD_DIR"
  /usr/bin/zip -qry "$IPA_PATH" Payload
)

echo "Unsigned IPA written to: $IPA_PATH"