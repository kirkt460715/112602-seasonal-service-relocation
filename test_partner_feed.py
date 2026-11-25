from http.client import HTTPConnection
import json
from threading import Thread
from urllib.parse import urlencode
import unittest

from partner_feed import PartnerFeed


class PartnerFeedTest(unittest.TestCase):
    def setUp(self):
        self.server = PartnerFeed(0)
        self.addCleanup(self.server.server_close)
        thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(self.server.shutdown)

    def fetch(self, path):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_arrival_feed(self):
        self.assertTrue(self.server.register)
        self.assertEqual(self.fetch("/register"), (200, self.server.register))
        status, first = self.fetch("/intake?limit=2")
        self.assertEqual((status, first["cursor"], len(first["items"])), (200, 2, 2))
        status, second = self.fetch("/intake?since=2")
        self.assertEqual(status, 200)
        self.assertTrue(second["items"])
        self.assertEqual(first["items"] + second["items"], self.server.intake)
        self.assertEqual(self.fetch("/intake?since=-1")[0], 400)

    def test_partner_retrieval(self):
        self.assertTrue(self.server.receipts)
        for identity, row in self.server.receipts.items():
            with self.subTest(receipt=identity):
                path = "/receipt?" + urlencode(dict(zip(("action", "desk", "ref"), identity)))
                if row["delayed"]:
                    self.assertEqual(self.fetch(path)[0], 503)
                self.assertEqual(self.fetch(path), (200, {"evidence": row["evidence"]}))
        self.assertEqual(self.fetch("/receipt?ref=unregistered")[0], 404)


if __name__ == "__main__":
    unittest.main()
