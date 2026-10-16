"""
CodeGraph Live Server
Serves the dark minimal visualizer studio and provides live incremental
APIs for multi-language ASTs, web templates, and dependency graphs.
"""

import http.server
import socketserver
import json
import os
import threading
import time
import urllib.parse
from typing import Dict, Any

from .analyzer import CodeGraphEngine

WATCHED_EXTENSIONS = (
    '.py', '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
    '.go', '.rs', '.java', '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',
    '.cs', '.php', '.rb', '.swift', '.kt', '.vue', '.svelte',
    '.html', '.jinja', '.jinja2', '.css', '.scss', '.less', '.json', '.sql'
)

class FileWatcher(threading.Thread):
    def __init__(self, engine: CodeGraphEngine, interval: float = 0.8):
        super().__init__(daemon=True)
        self.engine = engine
        self.interval = interval
        self.running = True
        self.file_mtimes: Dict[str, float] = {}
        self._init_mtimes()

    def _get_watched_files(self) -> Dict[str, float]:
        mtimes = {}
        ignore_dirs = {
            '.git', '__pycache__', '.agents', '.codegraph', 'temp_files',
            'venv', '.venv', 'env', 'build', 'dist', 'node_modules', 'vendor',
            '.idea', '.vscode', 'target', 'bin', 'obj'
        }
        for root, dirs, files in os.walk(self.engine.root_dir):
            if any(ign in root for ign in ignore_dirs):
                continue
            for f in files:
                if f.endswith(WATCHED_EXTENSIONS):
                    p = os.path.join(root, f)
                    try:
                        mtimes[p] = os.path.getmtime(p)
                    except Exception:
                        pass
        return mtimes

    def _init_mtimes(self):
        self.file_mtimes = self._get_watched_files()

    def run(self):
        while self.running:
            time.sleep(self.interval)
            if self.engine.sync_paused:
                continue

            current_mtimes = self._get_watched_files()
            changed = False

            if set(current_mtimes.keys()) != set(self.file_mtimes.keys()):
                changed = True
            else:
                for path, mtime in current_mtimes.items():
                    if mtime > self.file_mtimes.get(path, 0):
                        changed = True
                        break

            if changed:
                self.file_mtimes = current_mtimes
                try:
                    self.engine.get_full_graph(force_refresh=True)
                except Exception as e:
                    print(f"Sync error: {e}")

    def stop(self):
        self.running = False


def create_handler(engine: CodeGraphEngine, base_dir: str):
    candidate_html = [
        os.path.join(base_dir, "web", "index.html"),
        os.path.join(base_dir, "web", "codegraph_visualizer.html"),
        os.path.join(base_dir, "codegraph_visualizer.html"),
        os.path.join(base_dir, "index.html")
    ]
    html_file = candidate_html[0]
    for p in candidate_html:
        if os.path.exists(p):
            html_file = p
            break

    candidate_vendor = [
        os.path.join(base_dir, "web", "vendor"),
        os.path.join(base_dir, "vendor")
    ]
    vendor_dir = candidate_vendor[0]
    for vp in candidate_vendor:
        if os.path.exists(vp):
            vendor_dir = vp
            break

    candidate_assets = [
        os.path.join(base_dir, "web", "assets"),
        os.path.join(base_dir, "assets")
    ]
    assets_dir = candidate_assets[0]
    for ap in candidate_assets:
        if os.path.exists(ap):
            assets_dir = ap
            break

    class CodeGraphHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            clean_path = parsed.path

            if clean_path in ("/", "/index.html"):
                self.serve_html()
            elif clean_path == "/api/graph":
                self.serve_graph()
            elif clean_path == "/api/status":
                self.serve_status()
            elif clean_path == "/api/dead_code":
                self.serve_dead_code(parsed.query)
            elif clean_path.startswith("/vendor/"):
                self.serve_vendor(clean_path[len("/vendor/"):])
            elif clean_path.startswith("/assets/"):
                self.serve_asset(clean_path[len("/assets/"):])
            elif clean_path in ("/logo.png", "/favicon.ico"):
                self.serve_asset(clean_path.lstrip("/"))
            else:
                self.send_error(404, "Not Found")

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            clean_path = parsed.path

            if clean_path == "/api/sync":
                self.handle_sync()
            elif clean_path == "/api/pause":
                self.handle_pause()
            else:
                self.send_error(404, "Not Found")

        def serve_html(self):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                data = content.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Error reading HTML visualizer: {e}")

        def serve_vendor(self, filename: str):
            filepath = os.path.join(vendor_dir, filename)
            if not os.path.exists(filepath) or not os.path.abspath(filepath).startswith(vendor_dir):
                self.send_error(404, "Vendor file not found")
                return

            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Error reading vendor file: {e}")

        def serve_asset(self, filename: str):
            filepath = os.path.join(assets_dir, filename)
            if not os.path.exists(filepath):
                alt_filepath = os.path.join(base_dir, "assets", filename)
                if os.path.exists(alt_filepath):
                    filepath = alt_filepath
                else:
                    self.send_error(404, "Asset file not found")
                    return

            ext = os.path.splitext(filename)[1].lower()
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.ico': 'image/x-icon',
                '.svg': 'image/svg+xml',
                '.webp': 'image/webp'
            }
            content_type = mime_types.get(ext, 'application/octet-stream')

            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Error reading asset file: {e}")

        def serve_graph(self):
            try:
                graph_data = engine.get_full_graph()
                data = json.dumps(graph_data).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Error processing graph data: {e}")

        def serve_status(self):
            try:
                latest = engine.get_full_graph()
                status_obj = {
                    "online": True,
                    "sync_paused": engine.sync_paused,
                    "last_sync": engine.last_sync_time,
                    "stats": latest.get('stats'),
                    "diff": latest.get('diff')
                }
                data = json.dumps(status_obj).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Error getting status: {e}")

        def serve_dead_code(self, query: str):
            try:
                latest = engine.get_full_graph()
                dead_code = latest.get('dead_code', [])
                params = urllib.parse.parse_qs(query)
                if params.get('format', [''])[0] == 'csv':
                    lines = ["ID,Name,Kind,FilePath,Line,LOC"]
                    for d in dead_code:
                        lines.append(f'"{d["id"]}","{d["name"]}","{d["kind"]}","{d.get("file_path","")}","{d.get("line",1)}","{d.get("loc",1)}"')
                    csv_data = "\n".join(lines).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/csv')
                    self.send_header('Content-Disposition', 'attachment; filename="dead_code_report.csv"')
                    self.send_header('Content-Length', str(len(csv_data)))
                    self.end_headers()
                    self.wfile.write(csv_data)
                else:
                    data = json.dumps({"dead_code": dead_code}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Error getting dead code: {e}")

        def handle_sync(self):
            try:
                graph_data = engine.get_full_graph(force_refresh=True)
                data = json.dumps(graph_data).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Error syncing: {e}")

        def handle_pause(self):
            engine.sync_paused = not engine.sync_paused
            data = json.dumps({"sync_paused": engine.sync_paused}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return CodeGraphHandler


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
