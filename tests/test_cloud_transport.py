"""Real HTTP transport-contract check; this is not a Valhalla engine test."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import unittest
from benchmarks.cloud_reference import call
from benchmarks.whole_drive import prepared

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def do_GET(self):
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b'{"error_code":400}')
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        valid = (self.path == '/route' and self.headers['Content-Type'] == 'application/json'
                 and data['costing'] == 'auto' and len(data['locations']) == 2)
        self.send_response(200 if valid else 400)
        self.end_headers()
        self.wfile.write(json.dumps({'trip': {'legs': []}, 'received': data} if valid
                                   else {'error_code': 400}).encode())

class CloudTransportTests(unittest.TestCase):
    def test_valhalla_sends_json_body_to_route_endpoint(self):
        server = HTTPServer(('127.0.0.1', 8002), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = call('valhalla', prepared(), 1, 4)
            self.assertIn('trip', result)
            self.assertEqual(result['received']['shape_format'], 'polyline6')
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
