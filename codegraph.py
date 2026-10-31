#!/usr/bin/env python3
"""
CodeGraph Studio — Universal CLI & Visualizer Runner
"""

import sys
import os
import argparse
import socket
import webbrowser
import time
import shutil
import subprocess
import threading
import urllib.request
import zipfile
import stat

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

from core.analyzer import CodeGraphEngine
from core.server import create_handler, ThreadedHTTPServer, FileWatcher


def find_available_port(start_port: int = 5050, max_attempts: int = 15) -> int:
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return start_port


def prompt_yes_no(message: str) -> bool:
    try:
        answer = input(message).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ('', 'y', 'yes')


def ensure_codegraph_cli() -> bool:
    """Install a local portable launcher if the codegraph CLI is missing."""
    if shutil.which('codegraph'):
        return True

    print("\n[!] The 'codegraph' CLI was not found on your PATH.")
    if not prompt_yes_no("Do you want CodeGraph Studio to download a portable launcher automatically? [Y/n]: "):
        print("[*] Download skipped. Continuing in built-in fallback mode.")
        return False

    try:
        home_dir = os.path.expanduser('~')
        install_root = os.path.join(home_dir, 'CodeGraph_Studio_Portable')
        os.makedirs(install_root, exist_ok=True)

        archive_name = 'CodeGraph_Studio-main.zip'
        archive_url = 'https://github.com/kissuHQ/CodeGraph_Studio/archive/refs/heads/main.zip'
        archive_path = os.path.join(install_root, archive_name)

        print(f"[*] Downloading CodeGraph Studio into: {install_root}")
        urllib.request.urlretrieve(archive_url, archive_path)

        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(install_root)

        extracted_candidates = [
            os.path.join(install_root, 'CodeGraph_Studio-main'),
            os.path.join(install_root, 'CodeGraph_Studio'),
            os.path.join(install_root, 'CodeGraph_Studio-master')
        ]

        extracted_dir = None
        for candidate in extracted_candidates:
            if os.path.exists(os.path.join(candidate, 'codegraph.py')):
                extracted_dir = candidate
                break

        if not extracted_dir:
            raise FileNotFoundError("Downloaded archive did not contain the expected CodeGraph Studio project.")

        repo_root = extracted_dir
        launcher_name = 'codegraph'
        if os.name == 'nt':
            launcher_name += '.bat'

        if os.name == 'nt':
            wrapper_dir = os.path.join(home_dir, 'AppData', 'Local', 'Microsoft', 'WindowsApps')
        else:
            wrapper_dir = os.path.join(home_dir, '.local', 'bin')
        os.makedirs(wrapper_dir, exist_ok=True)
        launcher_path = os.path.join(wrapper_dir, launcher_name)

        if os.name == 'nt':
            launcher_content = (
                '@echo off\r\n'
                f'set "SCRIPT_DIR={repo_root}"\r\n'
                'python "%SCRIPT_DIR%\\codegraph.py" %*\r\n'
            )
        else:
            launcher_content = (
                '#!/usr/bin/env bash\n'
                f'python3 "{repo_root}/codegraph.py" "$@"\n'
            )

        with open(launcher_path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(launcher_content)

        if os.name != 'nt':
            os.chmod(launcher_path, os.stat(launcher_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        if os.name != 'nt':
            PATH = os.environ.get('PATH', '')
            if wrapper_dir not in PATH.split(os.pathsep):
                os.environ['PATH'] = wrapper_dir + os.pathsep + PATH

        print(f"[*] Portable launcher installed: {launcher_path}")
        return shutil.which('codegraph') is not None or os.path.exists(launcher_path)
    except Exception as exc:
        print(f"[!] Automatic download failed: {exc}")
        print("[*] You can still run the project manually from this folder.")
        return False


def print_banner(target_dir: str, port: int, stats: dict):
    langs = ", ".join([l.title() for l in stats.get('languages', {}).keys() if l != 'generic'][:4]) or "Multi-Language"
    print("\n" + "=" * 70)
    print("            * CodeGraph Studio - Universal Runner *")
    print("               Crafted by KissuHQ (PR)")
    print("=" * 70)
    print(f" Target Project : {target_dir}")
    print(f" Visualizer URL : http://localhost:{port}/")
    print(f" Nodes Parsed   : {stats.get('total_nodes', 0)} ({stats.get('total_files', 0)} files, {stats.get('total_edges', 0)} edges)")
    print(f" Languages      : {langs}")
    print(f" Live Watcher   : Active (auto-updates on code edits)")
    print("-" * 70)
    print(" Visualizer Shortcuts:")
    print("   [1] Network Relationship Map    [2] Branching Process Flowchart")
    print("   [-] / [+] Node Spread Spacing   [F] Fit Screen Camera")
    print("   [/] or [Ctrl+K] Symbol Search   [B] Toggle Filter Sidebar")
    print("-" * 70)
    print(" Press Ctrl+C in this terminal to stop the server anytime.")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="CodeGraph Studio - Universal multi-language codebase visualizer & architecture studio.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python codegraph.py
  python codegraph.py C:\Users\Admin\Desktop\MyProject
  python codegraph.py . --port 5055
        """
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Path to the codebase directory to analyze (defaults to current working directory)."
    )
    parser.add_argument(
        "--path", "-d",
        dest="path_flag",
        default=None,
        help="Alternative flag to specify target project directory."
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=5050,
        help="Port to run the visualizer web server on (default: 5050)."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the web browser on startup."
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force re-indexing via codegraph CLI if installed."
    )

    args = parser.parse_args()

    target_path = args.path_flag or args.target or os.getcwd()
    target_path = os.path.abspath(target_path)

    if not os.path.exists(target_path) or not os.path.isdir(target_path):
        print(f"\n[ERROR] Target directory does not exist: {target_path}")
        sys.exit(1)

    ensure_codegraph_cli()

    if args.reindex:
        codegraph_bin = shutil.which('codegraph')
        if codegraph_bin:
            print(f"[*] Re-indexing project with codegraph CLI: {target_path} ...")
            cmd = 'index' if os.path.exists(os.path.join(target_path, '.codegraph')) else 'init'
            try:
                subprocess.run([codegraph_bin, cmd, target_path], check=False)
            except Exception as e:
                print(f"[!] Re-index warning: {e}")

    print(f"[*] Analyzing codebase AST at: {target_path} ...")
    engine = CodeGraphEngine(target_path)
    graph_data = engine.get_full_graph()
    stats = graph_data.get('stats', {})

    port = find_available_port(args.port)
    if port != args.port:
        print(f"[*] Port {args.port} in use, using available port: {port}")

    handler_class = create_handler(engine, TOOL_DIR)
    httpd = ThreadedHTTPServer(('127.0.0.1', port), handler_class)

    watcher = FileWatcher(engine, interval=0.8)
    watcher.start()

    print_banner(target_path, port, stats)

    if not args.no_browser:
        def open_browser():
            time.sleep(0.4)
            webbrowser.open(f"http://localhost:{port}/")
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down CodeGraph Studio server...")
    finally:
        watcher.stop()
        httpd.server_close()
        print("[*] Server stopped cleanly. Goodbye!\n")


if __name__ == '__main__':
    main()
