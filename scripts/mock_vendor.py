from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def parse_status(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    status = int(value)
    if 100 <= status <= 599:
        return status
    return None


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        print(f"{self.command} {self.path} {body.decode('utf-8')}", flush=True)
        status = self.response_status_for(self.path, self.headers)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write((f'{{"ok":{str(status < 400).lower()},"status":{status}}}').encode())

    def log_message(self, message_format: str, *args: object) -> None:
        return

    @staticmethod
    def response_status_for(path: str, headers) -> int:
        forced_header = parse_status(headers.get("X-Mock-Status"))
        if forced_header is not None:
            return forced_header

        marker = "/fail-"
        if marker in path:
            forced_path = parse_status(path.rsplit(marker, maxsplit=1)[-1].split("/", maxsplit=1)[0])
            if forced_path is not None:
                return forced_path

        return HTTPStatus.OK


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
