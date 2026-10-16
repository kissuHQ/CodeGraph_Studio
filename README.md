# CodeGraph Studio

> A portable, standalone architectural relationship graph and execution flowchart visualizer for any codebase.

CodeGraph Studio analyzes source code across multiple programming languages (Python, TypeScript, JavaScript, Go, Rust, Java, C/C++, C#, and web layers), rendering an interactive, dark-themed visualizer studio directly in your browser.

---

## Prerequisites

> [!IMPORTANT]
> **CodeGraph CLI Required**: Make sure **`codegraph`** is pre-installed on your system and accessible from your terminal / system `PATH`.
>
> Verify the installation by running:
> ```bash
> codegraph --version
> ```
> CodeGraph Studio utilizes the `codegraph` CLI tool for Tree-sitter multi-language indexing, symbol cross-referencing, and graph database generation.

---

## Key Features

- **Universal Multi-Language Support**:
  - Works with **TypeScript, JavaScript, Go, Rust, Python, Java, C/C++, C#, PHP, Ruby**, and more.
  - Automatically indexes symbols (classes, functions, methods, interfaces, structs, types, enums, modules, traits).
  - Built-in zero-dependency AST fallback for Python projects.
- **Dual Visualizer Modes**:
  - **Network Mode**: Interactive relationship map showing imports, calls, references, inheritance, and structural hierarchies.
  - **Flow Mode**: Step-by-step orthogonal branching execution flowchart (entry points &rarr; routes/handlers &rarr; service functions &rarr; templates/outputs).
- **Web & Full-Stack Layer Awareness**:
  - Detects web routes and HTTP methods (`GET`, `POST`, `PUT`, `DELETE`).
  - Scans templates, components, forms (`action`, `method`), and static assets (`.css`, `.js`).
  - Resolves links and template relationships.
- **Code Quality & Architecture Insights**:
  - Cyclomatic complexity and lines-of-code (LOC) metrics.
  - Hotspot and complexity heatmaps.
  - Dead code detection with downloadable CSV reports.
  - Problem detection for missing references or broken links.
- **Live File Watcher**: Automatically monitors project source files and synchronizes changes incrementally to the browser studio in real time.
- **Zero External Python Dependencies & 100% Offline**:
  - Core server runs on Python 3.8+ standard libraries (`ast`, `http.server`, `sqlite3`, `hashlib`, `socket`).
  - Frontend vendor libraries (Cytoscape.js, Dagre.js, fcose) are bundled locally in `web/vendor/`.

---

## Quick Start

### 1. Run in Current Directory
To inspect the codebase in your current working directory:
```bash
python codegraph.py
```

### 2. Run for an External Codebase
Pass the path of any target folder:
```bash
python codegraph.py "C:\path\to\your\project"
```

### 3. Windows One-Click / Drag & Drop
- Double-click **`run.bat`** to analyze the current directory.
- Drag and drop any project folder directly onto **`run.bat`** to launch the visualizer for that target directory immediately.

---

## CLI Options & Flags

```bash
python codegraph.py [target] [options]
```

| Flag | Description | Default |
|---|---|---|
| `target` | Path to the codebase directory to analyze | Current working directory |
| `-d`, `--path` | Alternative flag to specify the target directory | `None` |
| `-p`, `--port` | Local port number to run the HTTP server on | `5050` (or next free port) |
| `--no-browser` | Start the server without automatically opening the browser | Opens browser automatically |
| `--reindex` | Force re-indexing via the system `codegraph` CLI if installed | `False` |

---

## Keyboard Shortcuts

| Shortcut | Description |
|---|---|
| `1` | Switch to **Network Mode** |
| `2` | Switch to **Flow Mode** |
| `-` / `+` or `[` / `]` | Decrease / Increase **Node Spacing** (repulsive cluster unpacker) |
| `F` | Fit camera view to canvas boundaries |
| `Ctrl + K` or `/` | Open **Global Symbol Search** (symbols, classes, functions, files) |
| `B` | Toggle left filter sidebar |
| `Shift + P` | Toggle FPS / latency performance monitor |
| `?` | Open keyboard shortcuts help dialog |

---

## Clean Repository Structure

```
CodeGraph/
├── codegraph.py              # Universal CLI runner & server launcher
├── run.bat                   # Windows one-click & drag-and-drop launcher
├── README.md                 # Complete project documentation
├── core/                     # Backend intelligence & server engine
│   ├── __init__.py           # Package exports
│   ├── analyzer.py           # Multi-language graph parser & metrics engine
│   └── server.py             # Multi-threaded server & live file watcher
└── web/                      # Frontend studio UI
    ├── index.html            # CodeGraph Studio web visualizer interface
    └── vendor/               # Bundled offline JavaScript graph libraries
        ├── cytoscape.min.js
        ├── dagre.min.js
        ├── cytoscape-dagre.js
        ├── cytoscape-fcose.js
        ├── cose-base.js
        └── layout-base.js
```

---

## System Requirements

- **CodeGraph CLI**: Must be installed and accessible globally in your system `PATH`.
- **Python**: Version 3.8 or higher.
- **Operating System**: Windows, macOS, or Linux.
- **Browser**: Any modern web browser (Chrome, Edge, Firefox, Brave, Safari).

---

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/) to report bugs or submit pull requests.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

Distributed under the **Apache License 2.0**. See [`LICENSE`](file:///c:/Users/Admin/Desktop/CodeGraph/LICENSE) for more information.
