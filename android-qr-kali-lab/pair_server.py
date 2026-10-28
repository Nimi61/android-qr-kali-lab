from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8765

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index.html"):
            try:
                html = Path("index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            except FileNotFoundError:
                self.send_error(404, "index.html not found")
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path == "/pair":
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)

            print("\n[+] ANDROID PAIRING REQUEST RECEIVED")
            print(f"[+] Device address: {self.client_address[0]}")
            print("[+] Pairing accepted for testing\n")

            response = b'{"status":"paired"}'

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_error(404)

server = HTTPServer((HOST, PORT), Handler)

print(f"Kali pairing server running on port {PORT}")
print("Waiting for Android pairing requests...")

server.serve_forever()

