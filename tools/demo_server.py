#!/usr/bin/env python3
"""
Demo Web Monitor Server - Runs on PC without openpilot dependencies
Only serves playback functionality, no live data collection
"""
import json
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = 8080

class DemoHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/data':
            # Return dummy live data (not used in playback mode)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            dummy_data = {
                'timestamp': time.time(),
                'vEgoCluster': 0,
                'enabled': False,
                'statusText': 'Demo Mode - Load a log to replay'
            }
            self.wfile.write(json.dumps(dummy_data).encode())

        elif self.path == '/api/logs':
            # List available log files
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            log_files = []
            log_dir = Path(__file__).parent / 'web_monitor_logs'
            if log_dir.exists():
                for log_file in sorted(log_dir.glob('*.jsonl'), reverse=True):
                    log_files.append({
                        'filename': log_file.name,
                        'size': log_file.stat().st_size,
                        'modified': log_file.stat().st_mtime
                    })
            self.wfile.write(json.dumps(log_files).encode())

        elif self.path.startswith('/api/log/'):
            # Serve specific log file
            log_filename = self.path.split('/api/log/')[1]
            log_dir = Path(__file__).parent / 'web_monitor_logs'
            log_path = log_dir / log_filename
            if log_path.exists() and log_path.suffix == '.jsonl':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(log_path, 'r') as f:
                    self.wfile.write(f.read().encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Log file not found')

        elif self.path == '/' or self.path == '/index.html':
            # Serve main page
            self.path = '/monitor.html'
            return SimpleHTTPRequestHandler.do_GET(self)
        else:
            return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        print(f"[{self.client_address[0]}] {format % args}")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""
    pass

def get_local_ip():
    """Get local IP address"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def main():
    import os
    os.chdir(Path(__file__).parent)

    print("=" * 60)
    print("🎮 Demo Web Monitor Server (PC Mode)")
    print("=" * 60)
    print("\n⚠️  Demo mode - no live data collection")
    print("   Load a log file to replay driving sessions")

    local_ip = get_local_ip()
    log_dir = Path(__file__).parent / 'web_monitor_logs'
    log_count = len(list(log_dir.glob('*.jsonl'))) if log_dir.exists() else 0

    with ThreadedHTTPServer(("", PORT), DemoHandler) as httpd:
        print(f"\n✅ Server started successfully!")
        print(f"\n🌐 Access in your browser:")
        print(f"   http://localhost:{PORT}")
        print(f"   http://{local_ip}:{PORT}")
        print(f"\n📼 Available logs: {log_count}")
        print(f"   Click '🔄 Refresh Logs' in the web interface")
        print(f"\n🛑 Press Ctrl+C to stop server")
        print("=" * 60)
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Stopping server...")
            print("Server stopped")

if __name__ == "__main__":
    main()
