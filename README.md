<p align="center">
  <img src="assets/logo.png" alt="CodeGraph Studio" width="180" style="border-radius: 20px;" />
  <h1 align="center">CodeGraph Studio</h1>
  <p align="center">
    <strong>Portable codebase visualizer and architecture map for multi-language projects</strong>
  </p>
  <p align="center">
    <em>Built by <a href="https://github.com/kissuHQ">KissuHQ</a> (PR)</em>
  </p>
</p>

---

## Overview

CodeGraph Studio is a lightweight, offline-friendly tool for exploring a codebase as a live architecture graph. It helps you understand how files, classes, routes, templates, imports, and functions connect across a project.

It works well for:

- onboarding into unfamiliar repositories
- investigating dependencies and call paths
- identifying hotspots and dead code
- understanding routing and front-end/back-end connections
- tracking how a project evolves as files change

CodeGraph supports Python, TypeScript, JavaScript, Go, Rust, Java, C/C++, C#, and many other languages through the built-in analyzer and optional CLI indexing.

---

## Features

- Universal file and symbol parsing
- Live graph updates while files change
- Network view and flowchart-style hierarchy view
- File, function, class, route, template, and import inspection
- Dead-code detection with CSV export
- Built-in HTML/JavaScript visualizer served locally
- Offline mode with bundled frontend libraries
- Automatic fallback when the desktop CLI is missing

---

## Quick Start

### 1. Run from the repo folder

```bash
python codegraph.py
```

### 2. Analyze a specific project

```bash
python codegraph.py "C:/path/to/your/project"
```

### 3. Windows launcher

Double-click `run.bat` or drag a project folder onto it.

---

## Missing desktop CLI behavior

If `codegraph` is not installed on your system, CodeGraph Studio will now ask for permission before downloading a portable launcher automatically.

This keeps the app usable even when the desktop dependency is missing, while giving the user control before any download begins.

---

## Prerequisites

Python 3.8+ is required.

The tool can operate in a fallback mode without the external CLI, but the desktop `codegraph` binary can improve indexing and cross-file analysis if present.

Check if it is installed:

```bash
codegraph --version
```

---

## Usage examples

### Current directory

```bash
python codegraph.py .
```

### Custom port

```bash
python codegraph.py --port 5055 .
```

### Start without browser auto-open

```bash
python codegraph.py --no-browser .
```

### Force reindexing if CLI is available

```bash
python codegraph.py --reindex .
```

---

## Keyboard shortcuts

- `1` — Network view
- `2` — Hierarchy / flow view
- `-` / `+` — Adjust spacing
- `F` — Fit camera
- `/` or `Ctrl + K` — Search symbols
- `B` — Toggle filter sidebar
- `?` — Show shortcuts

---

## Project structure

```text
CodeGraph_Studio/
├── codegraph.py          # launcher and local server
├── run.bat              # Windows helper launcher
├── README.md            # project documentation
├── LICENSE              # Apache 2.0 license
├── core/
│   ├── analyzer.py      # graph extraction and analysis
│   ├── server.py        # HTTP server and live watcher
│   └── __init__.py
├── web/
│   ├── index.html       # visualizer UI
│   ├── assets/
│   └── vendor/
└── assets/
```

---

## Troubleshooting

### Browser does not open automatically

Use the printed localhost URL directly in your browser:

```text
http://localhost:5050/
```

### Port already in use

CodeGraph Studio will automatically choose the next available port.

### No desktop CLI installed

The app will prompt you before downloading a portable launcher. If you skip it, the app still starts in fallback mode.

---

## Contributing

1. Fork the project
2. Create a feature branch
3. Make your changes
4. Commit and push
5. Open a pull request

---

## License

This project is distributed under the Apache License 2.0.

---

## Maintainer

- GitHub: https://github.com/kissuHQ
- Repository: https://github.com/kissuHQ/CodeGraph_Studio
