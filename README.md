# MultilevelUnzipper

MultilevelUnzipper is a utility tool that recursively unzips **multi-layered, password-protected archives** using a pre-defined list of passwords. It supports archives that are compatible with **7-Zip**.

---

## ✨ Features

- Automatically extracts nested compressed files
- Supports password-protected archives using a user-provided password list
- Integrates into Windows right-click menu for quick access:
  - "Unzip all files under this directory"
  - "Unzip this file"
- Silent background installation

---

## 🛠 Requirements

- **Python 3.0+**
- **[7-Zip](https://www.7-zip.org/)** must be installed and available in your system PATH

---

## 📦 Installation & Usage

1. Download and unzip this repository.
2. Run `install.exe`.
3. Set your initial configuration in the prompted window.
4. Click **Install**.
5. The program will install itself to a folder under your user’s **AppData** directory.
6. Right-click any file or folder to see new options:
   - **Unzip all files under this directory**
   - **Unzip this file**
7. Store all your passwords in a file named `.passwords.txt` under your **home directory**.
8. If you have rarely used passwords, you can add them to the `.passwords.txt` file in the same directory as the archive.

---

## ⚠️ Important Warning

If you set the configuration option `autodeleteexisting` to `True`, **all existing extracted files will be deleted** before a new extraction begins.

> **Make sure to back up important data such as game save files** or any other content you don’t want to lose. Deleted files **cannot be recovered**.

---

## 📁 Example `.passwords.txt`

```txt
1234
password
letmein
admin
```

The program will try these passwords in order until it finds the correct one for each archive level.

---

## 🧰 Troubleshooting

- **7-Zip not recognized?** Make sure the `7z` executable is added to your system PATH.
- **Nothing happens on right-click?** Try re-running `install.exe` as administrator.

---

## 💬 Feedback

Feel free to open an [issue](https://github.com/Immortalyzy/MultilevelUnzipper/issues) or submit a pull request if you have suggestions or encounter bugs!
