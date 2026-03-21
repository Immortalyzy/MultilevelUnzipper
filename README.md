# MultilevelUnzipper

MultilevelUnzipper recursively extracts multi-layer, password-protected archives on Windows. It supports both **7-Zip** and **Bandizip**, retries the alternate backend automatically when both are configured, and can continue through disguised archive files such as `.mp4` polyglots.

## Features

- Recursively extracts nested archives until the configured maximum depth
- Tries the preferred backend first, then falls back to the alternate backend automatically when available
- Applies each password candidate across all configured backends before moving on
- Safely cleans up only the resolved members of a split archive after successful extraction
- Keeps genuine video outputs terminal while allowing disguised media files that are still archives to recurse
- Installs Windows right-click menu entries for file and folder extraction

## Requirements

- Windows
- Python 3.0+ when running from source
- At least one supported backend:
  - [7-Zip](https://www.7-zip.org/)
  - [Bandizip](https://www.bandisoft.com/bandizip/)

When both backends are configured, fallback is enabled automatically. When only one backend is configured, installation still succeeds and extraction uses that single tool.

For release builders:

- PyInstaller (`python -m pip install pyinstaller`)

## Installation

1. Download and unzip a release package that includes:
   - `install.exe`
   - `MultilevelUnzipper/`
2. Run `install.exe`.
3. In the installer:
   - Choose which backend to prefer first
   - Set the 7-Zip and Bandizip executable paths
   - Review the core unzip settings
4. Click **Validate** to confirm the configuration, then **Install**.
5. The installer copies the payload into your user `AppData` folder, saves the settings file, and registers the context-menu entries.

The installer preserves the existing settings keys used by the main application, so upgrading does not require a settings migration.

## Usage

After installation, right-click a file or folder and use one of these entries:

- `Unzip all files under this directory`
- `Unzip this file`

Password discovery works in this order:

1. No password
2. Passwords derived from the archive file name
3. Passwords from `passwords.txt` or `.passwords.txt` in the current directory
4. Passwords from `%USERPROFILE%\.passwords.txt`

## Auto-delete Behavior

When `autodelete` is enabled, archive cleanup happens only after a successful extraction. For split archives, the program resolves the exact archive family first and deletes only those members. Failed extractions leave every archive part in place.

## Final-level Detection

Video-like outputs remain terminal when every configured backend rejects them as non-archives. Media-looking files that can still be opened by an available backend stay eligible for deeper extraction, which covers the disguised `.mp4` samples shipped in the repository.

## Build Release Package

Run the release build script from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1 -Version 1.4.0 -Zip
```

What this command does:

- Builds the main payload from `MultilevelUnzipper.spec`
- Builds the installer from `install.spec`
- Stages release output under `dist/release/<version>/`
- Validates required artifacts:
  - `dist/release/<version>/install.exe`
  - `dist/release/<version>/MultilevelUnzipper/MultilevelUnzipper.exe`
- Optionally creates `dist/release/MultilevelUnzipper_<version>.zip` when `-Zip` is provided

## Important Warning

If you set `autodeleteexisting` to `True`, existing extraction directories are removed before a fresh extraction starts. Keep backups of anything you cannot afford to lose.

## Example `.passwords.txt`

```txt
1234
password
letmein
admin
```

## Troubleshooting

- Preferred backend path invalid: fix the executable path in the installer or switch the preferred backend
- Alternate backend missing: installation still works, but automatic fallback is disabled
- Nothing happens on right-click: run `install.exe` again as administrator

## Feedback

Open an [issue](https://github.com/Immortalyzy/MultilevelUnzipper/issues) or submit a pull request if you find a bug or want to improve the workflow.
