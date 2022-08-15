# Installing `fping`

## Linux

`fping` is available from most of the default package repositories. For example:

```bash
sudo apt install fping # Debian/Ubuntu
sudo pacman -S fping # Arch Linux
```

## macOS

It's easiest to install `fping` using Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install fping
```

## Windows

Binaries are available from this repository:

https://github.com/badafans/fping-windows

Choose the appropriate build for your architecture and add the drectory with "fping.exe" and "cygwin1.dll" to your PATH ([instructions](https://www.c-sharpcorner.com/article/add-a-directory-to-path-environment-variable-in-windows-10/)).
