"""Connections that arrive together are all answered: the server holds more than Python's five while it is busy."""
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler

from ontlas.web.server import Server


def test_the_server_holds_a_burst_of_connections():
    assert Server.request_queue_size >= 128 and Server.daemon_threads is True


def test_a_burst_larger_than_pythons_default_queue_is_answered_whole():
    class Slow(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    httpd = Server(("127.0.0.1", 0), Slow)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    burst = 96
    go = threading.Barrier(burst)

    def one(_):
        go.wait()
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.status
        except Exception as e:
            return type(e).__name__

    try:
        got = []
        for _ in range(3):
            with ThreadPoolExecutor(burst) as ex:
                got += list(ex.map(one, range(burst)))
        assert got.count(200) == len(got), {x: got.count(x) for x in set(got)}
    finally:
        httpd.shutdown()
        httpd.server_close()
