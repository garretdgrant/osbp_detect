# Install Requirements (macOS)

These steps ensure a clean, reproducible environment on modern Intel or Apple
Silicon Macs.

## 1. Homebrew

Homebrew provides the latest Python builds and supporting tools. Paste the
following command into your mac terminal. For more details see the official
[documentation](https://brew.sh/).
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen instructions to add Homebrew to your shell profile (usually
`~/.zprofile`). Confirm the install with:
```bash
which brew
```
The path (e.g., `/opt/homebrew/bin/brew`) should be printed; open a new terminal
session if it is not found. (i.e. exit the terminal and open a new one)

## 2. Install `just`

Just is a small task runner that automates the remaining steps. Once Homebrew is
ready, install it via:
```bash
brew install just
just --list
```
Seeing the recipe list confirms `just` is installed. Run any recipe with `just
<recipe>` (e.g., `just install-python`).

Great work! Once these prerequisites are in place you’re ready to follow the
main instructions and get the detector running—your future self (and your
client) will thank you.
