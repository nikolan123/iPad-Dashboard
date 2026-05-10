# Dashboard Agent Notes

## Project overview

This repository contains an older Objective-C iPad app named `Dashboard`.

Key characteristics:

- Xcode project: `Dashboard.xcodeproj`
- Main app sources: `Classes/`
- Bundled widget assets: `Widgets/`
- Shared widget support assets: `WidgetResources/`
- App resources and nibs live at the repo root plus `Settings.bundle/`
- Target is iPad-focused, even though some build commands still use simulator SDK names like `iphonesimulator7.1`

## Important paths

Windows working copy:

- `Y:\\Dashboard`

Mac share backing that Windows drive:

- `/Users/niko/Documents/Dashboard`

## Project structure

- `Classes/`
  App Objective-C and Objective-C++ sources.
- `Classes/ZipArchive/`
  Vendored zip/minizip code used for widget packaging and extraction.
- `Dashboard.xcodeproj/`
  Xcode project metadata.
- `Widgets/`
  Bundled dashboard widgets shipped with the app.
- `WidgetResources/`
  Shared widget JavaScript/CSS resources and parsers.
- `Settings.bundle/`
  App preferences bundle.
- `build-unsigned-ipa.sh`
  Helper script for building an unsigned IPA on the Mac.

## Build commands

Use the Xcode binary inside the app bundle, not `/usr/bin/xcodebuild`.

Simulator build on the Mac:

```sh
/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild \
  -project Dashboard.xcodeproj \
  -scheme Dashboard \
  -configuration Debug \
  -sdk iphonesimulator7.1 \
  -jobs 1 \
  clean build
```

Unsigned IPA build on the Mac:

```sh
./build-unsigned-ipa.sh
```

That script writes:

- `/Users/niko/Documents/Dashboard/Dashboard-unsigned.ipa`

## SSH access

Mac VM:

- host: `192.168.211.135`
- user: `niko`
- password: `1234`

Because the Mac is old, modern SSH clients can be picky. A local Windows venv was used successfully with Paramiko 2.12.0:

- `C:\Users\Niko\Documents\osxshared\Dashboard\.codex-ssh-venv`

Useful note:

- the copied venv inside `Y:\Dashboard\.codex-ssh-venv` may not run reliably from the SMB share
- the original local Windows path has been the dependable one

## SMB / shared-drive workflow

Current intended workflow:

- edit from Windows in `Y:\Dashboard`
- let that map to the Mac-local Documents share
- build on the Mac against `/Users/niko/Documents/Dashboard`

This avoids the VMware shared-folder compiler crash while still letting Git and editing mostly happen from the PC.

Important SMB caveats discovered during setup:

- Windows Git can fail writing objects or reflogs on this old macOS SMB server
- VS Code may need `security.allowedUNCHosts` updated for `192.168.211.135`
- remote-tracking reflogs under `.git/logs/refs/remotes/origin/` can become broken over SMB

## Git caveats

This repo has a few environment-specific Git gotchas.

### 1. Windows Git over SMB is unreliable here

Symptoms seen:

- `unable to write file .git/objects/...: Permission denied`
- `unable to append to '.git/logs/refs/remotes/origin/master': Bad file descriptor`

When this happens, use Mac Git over SSH instead:

```sh
/Applications/Xcode.app/Contents/Developer/usr/bin/git
```

### 2. Commits may need to be made from the Mac

If Windows Git cannot commit or stage over `Y:`, use Mac Git in `/Users/niko/Documents/Dashboard`.

### 3. Sync state can lie if `origin/master` reflog breaks

A broken local tracking reflog can make VS Code think local `master` is ahead when GitHub already has the commit.

Known fix:

- remove `.git/logs/refs/remotes/origin/master`
- set `core.logAllRefUpdates=false` locally if needed
- update `refs/remotes/origin/master` to the actual remote commit

### 4. File-mode noise on the Mac

Permissions were opened up aggressively during SMB debugging. That can make Mac Git report many mode-only changes even when file contents are unchanged.

Windows-side `git status` is usually the more useful signal for content changes in this setup.

## Known environment facts

- Xcode version is old enough that SDK names are `iphonesimulator7.1` and `iphoneos7.1`
- `/usr/bin/xcodebuild` is not the right binary on this Mac; use the Xcode.app path above
- the app now builds warning-free on the simulator from the Mac-local Documents checkout

## Editing guidance

- Prefer small, surgical edits in app code.
- Be careful when touching vendored files in `Classes/ZipArchive/minizip/`.
- Avoid mass line-ending rewrites from Windows; they make diffs noisy fast.
- If Git over SMB starts failing again, stage/commit through Mac Git rather than fighting Windows Git.
