# Security policy

## Supported versions

Fixes go into the latest release only.

## Reporting a vulnerability

Please report it privately: open this repository's **Security** tab and choose **Report a vulnerability**. Do not open a public issue for it. Say what you found, how to reproduce it, and what it affects. You will get an answer as soon as possible, and credit in the release notes if you want it.

## What counts

- **The installer** writes into skills folders under your home folder, and removes only installs it made itself, which it recognises by their `.scifig-install.json`. Anything that makes it write, replace or delete outside the folder its plan named is a vulnerability.
- **The scripts** read the images and label files you give them and write their results next to the input, or where `-o` says. Anything that makes them write elsewhere, or run code from a crafted image, label file or brief, is a vulnerability.
- **The network.** The scripts make no network calls of their own: uv downloads their pinned dependencies from PyPI on the first run, and the telemetry of the OCR runtime (onnxruntime) is switched off before it loads. Anything that sends data elsewhere is a vulnerability.

Out of scope: what a host agent or its image tool does with a brief, and errors in the bundled journal data (open a normal issue for those).
