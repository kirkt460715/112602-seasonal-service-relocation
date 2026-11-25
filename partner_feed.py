"""多方业务的本地合成资料端。"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit

SAMPLES = Path(__file__).resolve().parent / "samples"


def read_json(folder, filename):
    return json.loads((folder / filename).read_text(encoding="utf-8"))


class PartnerFeed(ThreadingHTTPServer):
    def __init__(self, port, folder=SAMPLES):
        self.register = read_json(folder, "register.json")
        self.intake = read_json(folder, "intake.json")
        self.receipts = {}
        for row in read_json(folder, "receipts.json"):
            key = (row["action"], row["desk"], row["ref"])
            if key in self.receipts:
                raise ValueError("重复的回执索引")
            self.receipts[key] = row
        if not isinstance(self.register, dict) or any(
            row["sequence"] != n or not isinstance(row["facts"], dict)
            for n, row in enumerate(self.intake, 1)
        ):
            raise ValueError("台账和接收序号不符合接口约定")
        self.request_lock = Lock()
        self.attempted = set()
        super().__init__(("127.0.0.1", port), FeedHandler)


class FeedHandler(BaseHTTPRequestHandler):
    def respond(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query, keep_blank_values=True)
        if url.path == "/register":
            self.respond(200, self.server.register)
        elif url.path == "/intake":
            self.list_intake(query)
        elif url.path == "/receipt":
            self.find_receipt(query)
        else:
            self.respond(404, {"error": "not_found"})

    def list_intake(self, query):
        try:
            start = int(query.get("since", ["0"])[0])
            limit = int(query.get("limit", ["50"])[0])
            if start < 0 or not 1 <= limit <= 100:
                raise ValueError
        except ValueError:
            self.respond(400, {"error": "invalid_page"})
            return
        items = self.server.intake[start:start + limit]
        self.respond(200, {"items": items, "cursor": items[-1]["sequence"] if items else start})

    def find_receipt(self, query):
        key = tuple(query.get(name, [""])[0] for name in ("action", "desk", "ref"))
        row = self.server.receipts.get(key)
        if row is None:
            self.respond(404, {"error": "receipt_not_found"})
            return
        with self.server.request_lock:
            deferred = row["delayed"] and key not in self.server.attempted
            self.server.attempted.add(key)
        if deferred:
            self.respond(503, {"error": "temporarily_unavailable"})
        else:
            self.respond(200, {"evidence": row["evidence"]})

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--samples", default=SAMPLES, type=Path)
    args = parser.parse_args()
    with PartnerFeed(args.port, args.samples) as service:
        print(f"资料端 http://127.0.0.1:{service.server_port}", flush=True)
        service.serve_forever()


if __name__ == "__main__":
    main()
