#!/usr/bin/env python3
"""Simple web-based file downloader for KA2 SD card logs.

Usage:
  python3 log_downloader.py [--port 8080] [--host 0.0.0.0] [--path /data/media/0/realdata]

Access at: http://<ka2-ip>:8080
"""
import argparse
import json
import os
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote, urlparse

DEFAULT_PORT = 8080
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOG_DIR = "/data/media/0/realdata"

LOG_DIR = None

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KA2 Log Downloader</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }
  h1 { color: #00ff88; margin-bottom: 10px; font-size: 1.2em; }
  #path { color: #888; margin-bottom: 20px; word-break: break-all; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }
  th { color: #00ff88; }
  tr:hover { background: #16213e; }
  a { color: #4fc3f7; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .dir { color: #ffd54f; }
  .size { color: #888; text-align: right; }
  .time { color: #888; }
  #back { margin-bottom: 10px; }
  #back a { color: #ffd54f; }
  .stats { color: #888; margin-top: 20px; font-size: 0.9em; }
</style>
</head>
<body>
<h1>KA2 Log Downloader</h1>
<div id="path"></div>
<div id="back"></div>
<table>
<thead><tr><th>Name</th><th>Size</th><th>Modified</th></tr></thead>
<tbody id="files"></tbody>
</table>
<div class="stats" id="stats"></div>
<script>
async function load(path) {
  const resp = await fetch('/api' + (path || ''));
  const data = await resp.json();
  document.getElementById('path').textContent = data.path;
  document.getElementById('back').innerHTML = data.parent ? `<a href="?path=${data.parent}">← Parent</a>` : '';
  const tbody = document.getElementById('files');
  tbody.innerHTML = '';
  data.entries.forEach(e => {
    const tr = document.createElement('tr');
    const size = e.dir ? '' : (e.size > 1048576 ? (e.size/1048576).toFixed(1)+'M' : e.size > 1024 ? (e.size/1024).toFixed(1)+'K' : e.size+'B');
    const name = e.dir ? `<span class="dir">📁 ${e.name}</span>` : `📄 ${e.name}`;
    const href = e.dir ? `?path=${encodeURIComponent(e.path)}` : `/download?path=${encodeURIComponent(e.path)}`;
    tr.innerHTML = `<td><a href="${href}">${name}</a></td><td class="size">${size}</td><td class="time">${e.mtime}</td>`;
    tbody.appendChild(tr);
  });
  document.getElementById('stats').textContent = `${data.entries.length} entries`;
}
const params = new URLSearchParams(window.location.search);
load(params.get('path') || '');
</script>
</body>
</html>
"""

def format_size(size):
    if size > 1048576:
        return f"{size/1048576:.1f}M"
    if size > 1024:
        return f"{size/1024:.1f}K"
    return f"{size}B"

def format_time(mtime):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))

class LogHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        elif parsed.path == '/api':
            self._handle_api(parsed)
        elif parsed.path == '/download':
            self._handle_download(parsed)
        else:
            self.send_error(404)

    def _handle_api(self, parsed):
        params = parsed.query.split('&')
        path_dict = {}
        for p in params:
            if '=' in p:
                k, v = p.split('=', 1)
                path_dict[k] = unquote(v)
        
        rel_path = path_dict.get('path', '')
        target = os.path.join(LOG_DIR, rel_path) if rel_path else LOG_DIR
        target = os.path.normpath(target)
        
        # Security: prevent path traversal
        if not target.startswith(LOG_DIR):
            self._send_json({"error": "Access denied"})
            return
        
        if not os.path.isdir(target):
            self._send_json({"error": "Not a directory"})
            return
        
        entries = []
        try:
            for name in sorted(os.listdir(target)):
                full = os.path.join(target, name)
                rel = os.path.relpath(full, LOG_DIR)
                stat = os.stat(full)
                entries.append({
                    "name": name,
                    "path": rel,
                    "dir": os.path.isdir(full),
                    "size": stat.st_size,
                    "mtime": format_time(stat.st_mtime),
                })
        except OSError as e:
            self._send_json({"error": str(e)})
            return
        
        parent = os.path.dirname(rel_path) if rel_path else ""
        self._send_json({
            "path": target,
            "parent": parent,
            "entries": entries,
        })

    def _handle_download(self, parsed):
        params = parsed.query.split('&')
        path_dict = {}
        for p in params:
            if '=' in p:
                k, v = p.split('=', 1)
                path_dict[k] = unquote(v)
        
        rel_path = path_dict.get('path', '')
        target = os.path.join(LOG_DIR, rel_path) if rel_path else LOG_DIR
        target = os.path.normpath(target)
        
        # Security: prevent path traversal
        if not target.startswith(LOG_DIR):
            self.send_error(403)
            return
        
        if not os.path.isfile(target):
            self.send_error(404)
            return
        
        try:
            stat = os.stat(target)
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(target)}"')
            self.send_header('Content-Length', str(stat.st_size))
            self.end_headers()
            with open(target, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except OSError:
            self.send_error(500)

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")

def main():
    parser = argparse.ArgumentParser(description="KA2 Log Downloader")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--path", type=str, default=DEFAULT_LOG_DIR, help="Root log directory")
    args = parser.parse_args()
    
    if not os.path.isdir(args.path):
        print(f"Error: {args.path} not found", file=sys.stderr)
        sys.exit(1)
    
    LOG_DIR = args.path
    
    server = HTTPServer((args.host, args.port), LogHandler)
    print(f"KA2 Log Downloader running at http://{args.host}:{args.port}")
    print(f"Serving: {LOG_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    main()
