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

def print_banner(target_dir: str, port: int, stats: dict):
    langs = ", ".join([l.title() for l in stats.get('languages', {}).keys() if l != 'generic'][:4]) or "Multi-Language"
    print("\n" + "=" * 70)
    print("            * CodeGraph Studio - Universal Runner *")
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
  python codegraph.py C:\\Users\\Admin\\Desktop\\MyProject
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

    if args.reindex:
        codegraph_bin = shutil.which("codegraph")
        if codegraph_bin:
            print(f"[*] Re-indexing project with codegraph CLI: {target_path} ...")
            try:
                subprocess.run([codegraph_bin, "index", target_path], check=False)
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

if __name__ == "__main__":
    main()
