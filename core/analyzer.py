"""
CodeGraph Unified Analyzer
Multi-language code intelligence, AST parsing, and relationship graph extractor.
Supports TypeScript, JavaScript, Go, Rust, Java, C/C++, C#, Python, and web layers.
"""

import os
import ast
import re
import sqlite3
import hashlib
import time
import subprocess
import shutil
from typing import Dict, List, Set, Any, Tuple, Optional

IGNORE_DIRS = {
    '.git', '__pycache__', '.agents', '.codegraph', 'temp_files',
    'venv', '.venv', 'env', 'build', 'dist', 'node_modules', 'vendor',
    '.idea', '.vscode', '.pytest_cache', '.mypy_cache', 'eggs', '.eggs',
    'target', 'bin', 'obj'
}

EXTENSION_LANGUAGE_MAP = {
    '.py': 'python',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.html': 'html',
    '.jinja': 'jinja',
    '.jinja2': 'jinja',
    '.css': 'css',
    '.scss': 'scss',
    '.less': 'less',
    '.json': 'json',
    '.sql': 'sql',
    '.vue': 'vue',
    '.svelte': 'svelte'
}

FRONTEND_EXTENSIONS = {
    '.html', '.jinja', '.jinja2', '.css', '.scss', '.less',
    '.jsx', '.tsx', '.vue', '.svelte'
}

FRONTEND_PATH_MARKERS = {
    'templates', 'static', 'components', 'views', 'pages',
    'frontend', 'ui', 'client', 'web', 'public'
}

def detect_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, 'generic')

def detect_category(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in FRONTEND_EXTENSIONS:
        return 'frontend'
    normalized = file_path.replace('\\', '/').lower().strip('/')
    parts = set(normalized.split('/'))
    if bool(parts & FRONTEND_PATH_MARKERS):
        return 'frontend'
    return 'backend'

def get_file_hash(filepath: str) -> str:
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

class CyclomaticComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

def calc_complexity(node: ast.AST) -> int:
    visitor = CyclomaticComplexityVisitor()
    visitor.visit(node)
    return visitor.complexity

class TemplateAndWebScanner:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def scan_web_layer(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        nodes = []
        edges = []
        problems = []

        template_dirs = []
        for r, dirs, files in os.walk(self.root_dir):
            if any(ign in r for ign in IGNORE_DIRS):
                continue
            if os.path.basename(r) in {"templates"}:
                template_dirs.append(r)

        found_templates = {}
        for tdir in template_dirs:
            for root, _, files in os.walk(tdir):
                for f in files:
                    if f.endswith(('.html', '.jinja', '.jinja2')):
                        abs_p = os.path.join(root, f)
                        rel_p = os.path.relpath(abs_p, self.root_dir).replace('\\', '/')
                        found_templates[f] = (rel_p, abs_p)
                        found_templates[rel_p] = (rel_p, abs_p)

        for short_name, (rel_p, abs_p) in found_templates.items():
            if short_name != os.path.basename(rel_p):
                continue

            tmpl_id = f"template:{rel_p}"
            try:
                with open(abs_p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue

            loc = len(content.splitlines())
            nodes.append({
                "id": tmpl_id,
                "kind": "template",
                "name": os.path.basename(rel_p),
                "qualified_name": rel_p,
                "file_path": rel_p,
                "language": "jinja",
                "loc": loc,
                "complexity": 1,
                "docstring": f"HTML / Jinja template located at {rel_p}",
                "category": "frontend"
            })

            extends_matches = re.findall(r"""\{%\s*extends\s+['"]([^'"]+)['"]\s*%\}""", content)
            for ext in extends_matches:
                target_tmpl_id = f"template:{ext}"
                edges.append({
                    "source": tmpl_id,
                    "target": target_tmpl_id,
                    "kind": "extends",
                    "label": f"extends '{ext}'"
                })
                if ext not in found_templates and f"web/templates/{ext}" not in found_templates:
                    problems.append({
                        "type": "missing_template",
                        "severity": "error",
                        "message": f"Template '{rel_p}' extends '{ext}', but '{ext}' was not found on disk.",
                        "file": rel_p,
                        "line": 1
                    })

            includes_matches = re.findall(r"""\{%\s*include\s+['"]([^'"]+)['"]\s*%\}""", content)
            for inc in includes_matches:
                target_tmpl_id = f"template:{inc}"
                edges.append({
                    "source": tmpl_id,
                    "target": target_tmpl_id,
                    "kind": "includes",
                    "label": f"includes '{inc}'"
                })
                if inc not in found_templates and f"web/templates/{inc}" not in found_templates:
                    problems.append({
                        "type": "missing_template",
                        "severity": "error",
                        "message": f"Template '{rel_p}' includes '{inc}', but '{inc}' was not found on disk.",
                        "file": rel_p,
                        "line": 1
                    })

            block_matches = re.findall(r"""\{%\s*block\s+([a-zA-Z0-9_]+)\s*%\}""", content)
            for blk in block_matches:
                blk_id = f"block:{rel_p}:{blk}"
                nodes.append({
                    "id": blk_id,
                    "kind": "block",
                    "name": blk,
                    "qualified_name": f"{rel_p}:block:{blk}",
                    "file_path": rel_p,
                    "language": "jinja",
                    "parent": tmpl_id,
                    "loc": 1,
                    "complexity": 1,
                    "docstring": f"Jinja block '{blk}' in {os.path.basename(rel_p)}",
                    "category": "frontend"
                })
                edges.append({
                    "source": tmpl_id,
                    "target": blk_id,
                    "kind": "contains"
                })

            url_for_matches = re.findall(r"""url_for\(\s*['"]([a-zA-Z0-9_\.]+)['"]""", content)
            for endpoint in url_for_matches:
                if endpoint == "static":
                    continue
                edges.append({
                    "source": tmpl_id,
                    "target": f"route_ref:{endpoint}",
                    "kind": "links_to",
                    "label": f"links to {endpoint}"
                })

            form_matches = re.finditer(r"""<form\b([^>]*)>""", content, re.IGNORECASE)
            for idx, fm in enumerate(form_matches):
                attrs = fm.group(1)
                action_match = re.search(r"""action=['"]([^'"]*)['"]""", attrs)
                method_match = re.search(r"""method=['"]([^'"]*)['"]""", attrs)
                action = action_match.group(1) if action_match else "#"
                method = (method_match.group(1) if method_match else "GET").upper()

                form_id = f"form:{rel_p}:form_{idx+1}"
                nodes.append({
                    "id": form_id,
                    "kind": "form",
                    "name": f"form_{idx+1} ({method})",
                    "qualified_name": f"{rel_p}:form_{idx+1}",
                    "file_path": rel_p,
                    "language": "html",
                    "parent": tmpl_id,
                    "docstring": f"HTML Form method={method} action={action}",
                    "category": "frontend",
                    "loc": 1,
                    "complexity": 1
                })
                edges.append({
                    "source": tmpl_id,
                    "target": form_id,
                    "kind": "contains"
                })

                act_ep_match = re.search(r"""url_for\(\s*['"]([a-zA-Z0-9_\.]+)['"]""", action)
                if act_ep_match:
                    target_ep = act_ep_match.group(1)
                    edges.append({
                        "source": form_id,
                        "target": f"route_ref:{target_ep}",
                        "kind": "submits_to",
                        "label": f"{method} {target_ep}"
                    })

            static_matches = re.findall(r"""url_for\(\s*['"]static['"]\s*,\s*filename=['"]([^'"]+)['"]""", content)
            script_srcs = re.findall(r"""<script[^>]+src=['"]([^'"]+)['"]""", content)
            link_hrefs = re.findall(r"""<link[^>]+href=['"]([^'"]+)['"]""", content)

            all_statics = set(static_matches)
            for s in script_srcs + link_hrefs:
                if "/static/" in s:
                    clean = s.split("/static/")[-1]
                    all_statics.add(clean)

            for st in all_statics:
                static_id = f"static:{st}"
                nodes.append({
                    "id": static_id,
                    "kind": "static",
                    "name": os.path.basename(st),
                    "qualified_name": f"static/{st}",
                    "file_path": f"web/static/{st}",
                    "language": "css" if st.endswith('.css') else ("js" if st.endswith('.js') else "asset"),
                    "category": "frontend",
                    "loc": 1,
                    "complexity": 1
                })
                edges.append({
                    "source": tmpl_id,
                    "target": static_id,
                    "kind": "loads",
                    "label": f"loads '{os.path.basename(st)}'"
                })

        return nodes, edges, problems

class CodeGraphEngine:
    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.db_path = os.path.join(self.root_dir, ".codegraph", "codegraph.db")
        self.web_scanner = TemplateAndWebScanner(self.root_dir)
        self.file_hashes: Dict[str, str] = {}
        self.last_sync_time: float = time.time()
        self.previous_nodes_set: Set[str] = set()
        self.previous_edges_set: Set[Tuple[str, str, str]] = set()
        self.sync_paused: bool = False
        self.cached_graph: Optional[Dict[str, Any]] = None

    def get_full_graph(self, force_refresh: bool = False) -> Dict[str, Any]:
        if not force_refresh and self.cached_graph is not None:
            return self.cached_graph

        codegraph_bin = shutil.which("codegraph")

        if force_refresh and os.path.exists(self.db_path) and codegraph_bin:
            try:
                subprocess.run([codegraph_bin, "sync", "-q", self.root_dir], check=False, capture_output=True, timeout=10)
            except Exception:
                pass

        if not os.path.exists(self.db_path) and codegraph_bin:
            try:
                subprocess.run([codegraph_bin, "init", self.root_dir], check=False, capture_output=True, timeout=30)
            except Exception:
                pass

        db_nodes = []
        db_edges = []
        db_files = []

        if os.path.exists(self.db_path):
            try:
                con = sqlite3.connect(self.db_path)
                con.row_factory = sqlite3.Row
                cur = con.cursor()
                db_nodes = [dict(r) for r in cur.execute("SELECT * FROM nodes").fetchall()]
                db_edges = [dict(r) for r in cur.execute("SELECT * FROM edges").fetchall()]
                db_files = [dict(r) for r in cur.execute("SELECT * FROM files").fetchall()]
                con.close()
            except Exception as e:
                print(f"Warning reading codegraph.db: {e}")

        if not db_nodes:
            db_nodes, db_edges, db_files = self._extract_pure_python_ast()

        ast_meta = self._scan_python_ast_meta()
        web_nodes, web_edges, problems = self.web_scanner.scan_web_layer()

        all_nodes: Dict[str, Dict[str, Any]] = {}
        file_imports_map: Dict[str, List[str]] = {}

        for n in db_nodes:
            nid = n['id']
            kind = n.get('kind', '')
            file_p = n.get('file_path', '')

            if kind == 'import':
                for e in db_edges:
                    if e['target'] == nid and e.get('kind') == 'contains':
                        file_p_id = e['source']
                        file_imports_map.setdefault(file_p_id, []).append(n.get('name', ''))
                continue

            meta_key = (file_p, n.get('name'))
            comp = n.get('complexity', 1)
            loc = n.get('loc', 1)
            route_info = None

            if meta_key in ast_meta:
                meta = ast_meta[meta_key]
                comp = meta.get('complexity', comp)
                loc = meta.get('loc', loc)
                if meta.get('is_route'):
                    kind = 'route'
                    route_info = meta

            n['category'] = detect_category(file_p)
            if not n.get('language'):
                n['language'] = detect_language(file_p)

            n['complexity'] = comp
            n['loc'] = loc
            if route_info:
                n['kind'] = 'route'
                n['route_path'] = route_info.get('route_path', '')
                n['route_methods'] = route_info.get('route_methods', ['GET'])
                n['signature'] = f"[{'/'.join(n['route_methods'])}] {n['route_path']}"

            if not n.get('parent'):
                for e in db_edges:
                    if e['target'] == nid and e.get('kind') == 'contains':
                        n['parent'] = e['source']
                        break

            all_nodes[nid] = n

        for wn in web_nodes:
            all_nodes[wn['id']] = wn

        for file_id, imp_list in file_imports_map.items():
            if file_id in all_nodes:
                all_nodes[file_id]['imports_list'] = sorted(list(set(imp_list)))

        unique_edges: List[Dict[str, Any]] = []
        seen_edge_keys: Set[Tuple[str, str, str]] = set()

        for e in db_edges:
            s, t = e['source'], e['target']
            k = e.get('kind', 'rel')

            if t.startswith('import:') or s.startswith('import:'):
                continue

            if s in all_nodes and t in all_nodes and s != t:
                ekey = (s, t, k)
                if ekey not in seen_edge_keys:
                    seen_edge_keys.add(ekey)
                    unique_edges.append({
                        "source": s,
                        "target": t,
                        "kind": k,
                        "label": e.get('metadata') or k
                    })

        for we in web_edges:
            s, t = we['source'], we['target']
            k = we.get('kind')

            if t.startswith('route_ref:'):
                ep = t[len('route_ref:'):]
                matched_target = None
                for nid, n in all_nodes.items():
                    if n.get('kind') == 'route':
                        if n.get('name') == ep or n.get('route_path') == ep or f"auth.{n.get('name')}" == ep or f"auth_bp.{n.get('name')}" == ep:
                            matched_target = nid
                            break
                if matched_target:
                    t = matched_target
                    we['target'] = matched_target
                else:
                    problems.append({
                        "type": "broken_url_for",
                        "severity": "warning",
                        "message": f"Template '{s}' links to url_for('{ep}'), but no matching route was found.",
                        "file": all_nodes.get(s, {}).get('file_path', s),
                        "line": 1
                    })
                    continue

            if t.startswith('template:'):
                t_clean = t[len('template:'):]
                matched_target = None
                for nid, n in all_nodes.items():
                    if n.get('kind') == 'template':
                        if n.get('name') == t_clean or n.get('qualified_name') == t_clean or n['id'] == t:
                            matched_target = nid
                            break
                if matched_target:
                    t = matched_target
                    we['target'] = matched_target

            if s in all_nodes and t in all_nodes and s != t:
                ekey = (s, t, k)
                if ekey not in seen_edge_keys:
                    seen_edge_keys.add(ekey)
                    unique_edges.append(we)

        for render_item in ast_meta.get('__renders__', []):
            caller_id = render_item['caller_id']
            tmpl_name = render_item['template']
            matched_tmpl_id = None
            for nid, n in all_nodes.items():
                if n.get('kind') == 'template':
                    if n.get('name') == tmpl_name or n.get('qualified_name') == tmpl_name or n.get('qualified_name') == f"web/templates/{tmpl_name}":
                        matched_tmpl_id = nid
                        break

            if matched_tmpl_id and caller_id in all_nodes:
                ekey = (caller_id, matched_tmpl_id, 'renders')
                if ekey not in seen_edge_keys:
                    seen_edge_keys.add(ekey)
                    unique_edges.append({
                        "source": caller_id,
                        "target": matched_tmpl_id,
                        "kind": "renders",
                        "label": f"renders '{tmpl_name}'"
                    })
            elif not matched_tmpl_id and caller_id in all_nodes:
                problems.append({
                    "type": "missing_template",
                    "severity": "error",
                    "message": f"Route '{all_nodes[caller_id].get('name')}' calls render_template('{tmpl_name}'), but template does not exist on disk.",
                    "file": all_nodes[caller_id].get('file_path', ''),
                    "line": render_item.get('line', 1)
                })

        degree_map: Dict[str, int] = {nid: 0 for nid in all_nodes}
        for e in unique_edges:
            degree_map[e['source']] = degree_map.get(e['source'], 0) + 1
            degree_map[e['target']] = degree_map.get(e['target'], 0) + 1

        node_list = []
        for nid, n in all_nodes.items():
            n['degree'] = degree_map.get(nid, 0)
            node_list.append(n)

        dead_code_items = self._compute_dead_code(all_nodes, unique_edges)

        current_nodes_set = set(all_nodes.keys())
        current_edges_set = seen_edge_keys
        added_nodes = list(current_nodes_set - self.previous_nodes_set)
        removed_nodes = list(self.previous_nodes_set - current_nodes_set)
        added_edges = [f"{s}->{t}:{k}" for (s, t, k) in (current_edges_set - self.previous_edges_set)]
        removed_edges = [f"{s}->{t}:{k}" for (s, t, k) in (self.previous_edges_set - current_edges_set)]

        diff_summary = "Synced"
        if added_nodes or removed_nodes or added_edges or removed_edges:
            parts = []
            if added_nodes: parts.append(f"+{len(added_nodes)} nodes")
            if removed_nodes: parts.append(f"-{len(removed_nodes)} nodes")
            if added_edges: parts.append(f"+{len(added_edges)} edges")
            if removed_edges: parts.append(f"-{len(removed_edges)} edges")
            diff_summary = f"Diff: {', '.join(parts)}"

        self.previous_nodes_set = current_nodes_set
        self.previous_edges_set = current_edges_set
        self.last_sync_time = time.time()

        node_kinds_count: Dict[str, int] = {}
        languages_count: Dict[str, int] = {}
        for n in node_list:
            k = n.get('kind', 'other')
            lang = n.get('language', 'generic')
            node_kinds_count[k] = node_kinds_count.get(k, 0) + 1
            languages_count[lang] = languages_count.get(lang, 0) + 1

        edge_kinds_count: Dict[str, int] = {}
        for e in unique_edges:
            k = e.get('kind', 'other')
            edge_kinds_count[k] = edge_kinds_count.get(k, 0) + 1

        graph_result = {
            "status": "ok",
            "nodes": node_list,
            "edges": unique_edges,
            "files": db_files,
            "problems": problems,
            "dead_code": dead_code_items,
            "diff": {
                "added_nodes": added_nodes,
                "removed_nodes": removed_nodes,
                "added_edges": added_edges,
                "removed_edges": removed_edges,
                "summary": diff_summary
            },
            "stats": {
                "total_nodes": len(node_list),
                "total_edges": len(unique_edges),
                "total_files": len(db_files) or len([n for n in node_list if n.get('kind') == 'file']),
                "node_kinds": node_kinds_count,
                "edge_kinds": edge_kinds_count,
                "languages": languages_count,
                "timestamp": self.last_sync_time
            }
        }

        self.cached_graph = graph_result
        return graph_result

    def _extract_pure_python_ast(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        nodes = []
        edges = []
        files_info = []

        py_files = []
        for root, dirs, files in os.walk(self.root_dir):
            if any(ign in root for ign in IGNORE_DIRS):
                continue
            for f in files:
                if f.endswith('.py'):
                    abs_p = os.path.join(root, f)
                    rel_p = os.path.relpath(abs_p, self.root_dir).replace('\\', '/')
                    py_files.append((rel_p, abs_p))

        symbol_name_to_id: Dict[str, List[str]] = {}

        for rel_p, abs_p in py_files:
            file_id = f"file:{rel_p}"
            try:
                with open(abs_p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                tree = ast.parse(content, filename=rel_p)
            except Exception:
                continue

            file_loc = len(content.splitlines())
            file_size = os.path.getsize(abs_p)

            files_info.append({
                "path": rel_p,
                "size": file_size,
                "node_count": 0
            })

            nodes.append({
                "id": file_id,
                "kind": "file",
                "name": os.path.basename(rel_p),
                "qualified_name": rel_p,
                "file_path": rel_p,
                "language": "python",
                "loc": file_loc,
                "complexity": 1,
                "docstring": ast.get_docstring(tree) or f"Python module {rel_p}",
                "category": detect_category(rel_p)
            })

            for stmt in tree.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_id = f"function:{rel_p}:{stmt.name}"
                    func_comp = calc_complexity(stmt)
                    func_loc = (stmt.end_lineno - stmt.lineno + 1) if hasattr(stmt, 'end_lineno') and stmt.end_lineno else 1

                    nodes.append({
                        "id": func_id,
                        "kind": "function",
                        "name": stmt.name,
                        "qualified_name": f"{rel_p}:{stmt.name}",
                        "file_path": rel_p,
                        "language": "python",
                        "start_line": stmt.lineno,
                        "loc": func_loc,
                        "complexity": func_comp,
                        "parent": file_id,
                        "docstring": ast.get_docstring(stmt) or "",
                        "category": detect_category(rel_p)
                    })
                    edges.append({
                        "source": file_id,
                        "target": func_id,
                        "kind": "contains"
                    })
                    symbol_name_to_id.setdefault(stmt.name, []).append(func_id)

                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Call):
                            called_name = ""
                            if isinstance(sub.func, ast.Name):
                                called_name = sub.func.id
                            elif isinstance(sub.func, ast.Attribute):
                                called_name = sub.func.attr
                            if called_name:
                                edges.append({
                                    "source": func_id,
                                    "target": f"call_ref:{called_name}",
                                    "kind": "calls"
                                })

                elif isinstance(stmt, ast.ClassDef):
                    class_id = f"class:{rel_p}:{stmt.name}"
                    class_comp = calc_complexity(stmt)
                    class_loc = (stmt.end_lineno - stmt.lineno + 1) if hasattr(stmt, 'end_lineno') and stmt.end_lineno else 1

                    nodes.append({
                        "id": class_id,
                        "kind": "class",
                        "name": stmt.name,
                        "qualified_name": f"{rel_p}:{stmt.name}",
                        "file_path": rel_p,
                        "language": "python",
                        "start_line": stmt.lineno,
                        "loc": class_loc,
                        "complexity": class_comp,
                        "parent": file_id,
                        "docstring": ast.get_docstring(stmt) or "",
                        "category": detect_category(rel_p)
                    })
                    edges.append({
                        "source": file_id,
                        "target": class_id,
                        "kind": "contains"
                    })
                    symbol_name_to_id.setdefault(stmt.name, []).append(class_id)

                    for item in stmt.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_id = f"method:{rel_p}:{stmt.name}:{item.name}"
                            m_comp = calc_complexity(item)
                            m_loc = (item.end_lineno - item.lineno + 1) if hasattr(item, 'end_lineno') and item.end_lineno else 1

                            nodes.append({
                                "id": method_id,
                                "kind": "method",
                                "name": item.name,
                                "qualified_name": f"{rel_p}:{stmt.name}.{item.name}",
                                "file_path": rel_p,
                                "language": "python",
                                "start_line": item.lineno,
                                "loc": m_loc,
                                "complexity": m_comp,
                                "parent": class_id,
                                "docstring": ast.get_docstring(item) or "",
                                "category": detect_category(rel_p)
                            })
                            edges.append({
                                "source": class_id,
                                "target": method_id,
                                "kind": "contains"
                            })
                            symbol_name_to_id.setdefault(item.name, []).append(method_id)

                            for sub in ast.walk(item):
                                if isinstance(sub, ast.Call):
                                    called_name = ""
                                    if isinstance(sub.func, ast.Name):
                                        called_name = sub.func.id
                                    elif isinstance(sub.func, ast.Attribute):
                                        called_name = sub.func.attr
                                    if called_name:
                                        edges.append({
                                            "source": method_id,
                                            "target": f"call_ref:{called_name}",
                                            "kind": "calls"
                                        })

                elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    if isinstance(stmt, ast.Import):
                        for alias in stmt.names:
                            edges.append({
                                "source": file_id,
                                "target": f"import_ref:{alias.name}",
                                "kind": "imports"
                            })
                    elif isinstance(stmt, ast.ImportFrom) and stmt.module:
                        edges.append({
                            "source": file_id,
                            "target": f"import_ref:{stmt.module}",
                            "kind": "imports"
                        })

        resolved_edges = []
        for e in edges:
            t = e['target']
            s = e['source']
            if t.startswith('call_ref:'):
                called = t[len('call_ref:'):]
                matched_targets = symbol_name_to_id.get(called, [])
                if matched_targets:
                    chosen = matched_targets[0]
                    for cand in matched_targets:
                        if s.split(':')[1] in cand:
                            chosen = cand
                            break
                    if chosen != s:
                        resolved_edges.append({
                            "source": s,
                            "target": chosen,
                            "kind": "calls"
                        })
            elif t.startswith('import_ref:'):
                mod = t[len('import_ref:'):]
                target_file_id = None
                for n in nodes:
                    if n['kind'] == 'file':
                        clean_mod = mod.replace('.', '/')
                        if n['file_path'].startswith(clean_mod) or n['file_path'].endswith(f"{clean_mod}.py"):
                            target_file_id = n['id']
                            break
                if target_file_id and target_file_id != s:
                    resolved_edges.append({
                        "source": s,
                        "target": target_file_id,
                        "kind": "imports"
                    })
            else:
                resolved_edges.append(e)

        return nodes, resolved_edges, files_info

    def _scan_python_ast_meta(self) -> Dict[Any, Any]:
        results = {'__renders__': []}
        for root, dirs, files in os.walk(self.root_dir):
            if any(ign in root for ign in IGNORE_DIRS):
                continue
            for f in files:
                if f.endswith('.py'):
                    abs_p = os.path.join(root, f)
                    rel_p = os.path.relpath(abs_p, self.root_dir).replace('\\', '/')
                    try:
                        with open(abs_p, 'r', encoding='utf-8', errors='ignore') as fp:
                            tree = ast.parse(fp.read(), filename=rel_p)
                    except Exception:
                        continue

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            comp = calc_complexity(node)
                            loc = (node.end_lineno - node.lineno + 1) if hasattr(node, 'end_lineno') and node.end_lineno else 1

                            is_route = False
                            route_path = ""
                            route_methods = ["GET"]

                            for dec in node.decorator_list:
                                if isinstance(dec, ast.Call):
                                    dec_func = dec.func
                                    attr_name = ""
                                    if isinstance(dec_func, ast.Attribute):
                                        attr_name = dec_func.attr
                                    elif isinstance(dec_func, ast.Name):
                                        attr_name = dec_func.id

                                    if attr_name in ('route', 'get', 'post', 'put', 'delete', 'patch'):
                                        is_route = True
                                        if attr_name != 'route':
                                            route_methods = [attr_name.upper()]
                                        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                                            route_path = dec.args[0].value
                                        for kw in dec.keywords:
                                            if kw.arg == 'methods' and isinstance(kw.value, (ast.List, ast.Tuple)):
                                                route_methods = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
                                elif isinstance(dec, ast.Attribute) and dec.attr == 'route':
                                    is_route = True

                            results[(rel_p, node.name)] = {
                                "complexity": comp,
                                "loc": loc,
                                "is_route": is_route,
                                "route_path": route_path,
                                "route_methods": route_methods
                            }

                            caller_func_id = f"function:{rel_p}:{node.name}" if not is_route else f"route:{rel_p}:{node.name}"
                            for sub in ast.walk(node):
                                if isinstance(sub, ast.Call):
                                    fname = ""
                                    if isinstance(sub.func, ast.Name):
                                        fname = sub.func.id
                                    elif isinstance(sub.func, ast.Attribute):
                                        fname = sub.func.attr
                                    if fname == "render_template" and sub.args and isinstance(sub.args[0], ast.Constant) and isinstance(sub.args[0].value, str):
                                        results['__renders__'].append({
                                            "caller_id": caller_func_id,
                                            "template": sub.args[0].value,
                                            "line": sub.lineno
                                        })

                        elif isinstance(node, ast.ClassDef):
                            comp = calc_complexity(node)
                            loc = (node.end_lineno - node.lineno + 1) if hasattr(node, 'end_lineno') and node.end_lineno else 1
                            results[(rel_p, node.name)] = {
                                "complexity": comp,
                                "loc": loc
                            }

        return results

    def _compute_dead_code(self, all_nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        incoming_counts = {}
        for e in edges:
            k = e.get('kind')
            if k in ('calls', 'references', 'instantiates', 'imports', 'implements', 'renders', 'links_to', 'submits_to'):
                tgt = e['target']
                incoming_counts[tgt] = incoming_counts.get(tgt, 0) + 1

        dead_items = []
        for nid, n in all_nodes.items():
            kind = n.get('kind')
            name = n.get('name', '')

            if kind not in ('function', 'method', 'class', 'struct', 'interface', 'type'):
                continue

            if name.startswith('__') and name.endswith('__'):
                continue
            if name in ('main', 'start_server', 'create_app', 'init_db', 'app', 'run', 'init'):
                continue
            if kind == 'route':
                continue

            if incoming_counts.get(nid, 0) == 0:
                dead_items.append({
                    "id": nid,
                    "name": name,
                    "kind": kind,
                    "file_path": n.get('file_path'),
                    "line": n.get('start_line', 1),
                    "loc": n.get('loc', 1)
                })

        return dead_items

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    engine = CodeGraphEngine(target)
    res = engine.get_full_graph()
    print("Graph built successfully for:", engine.root_dir)
    print("Nodes:", res['stats']['total_nodes'])
    print("Edges:", res['stats']['total_edges'])
    print("Languages:", res['stats'].get('languages', {}))
    print("Node kinds:", res['stats']['node_kinds'])
    print("Problems:", len(res['problems']))
    print("Dead code items:", len(res['dead_code']))
