import json
from pathlib import Path
import tempfile
import unittest

from entrypoint import configuration, prepare, sessions

TEMPLATE = Path(__file__).resolve().parents[1] / "nitter.example.conf"


class RailwayTests(unittest.TestCase):
    def setUp(self):
        self.env = {"RAILWAY_PUBLIC_DOMAIN": "test.up.railway.app", "PORT": "9123",
                    "REDISHOST": "redis.railway.internal", "REDISPASSWORD": 'a"b\\c',
                    "NITTER_HMAC_KEY": "a" * 64, "X_USERNAME": "example",
                    "X_AUTH_TOKEN": "fake-test-token", "X_CT0": "fake-test-csrf"}

    def test_runtime_files_and_railway_port(self):
        with tempfile.TemporaryDirectory() as directory:
            conf, accounts = prepare(self.env, TEMPLATE, Path(directory))
            content = conf.read_text()
            self.assertIn('port = 9123', content)
            self.assertIn('https = true', content)
            self.assertIn('enableRSS = true', content)
            self.assertIn('enableDebug = false', content)
            self.assertIn('redisPassword = "a\\"b\\\\c"', content)
            self.assertEqual(json.loads(accounts.read_text())["auth_token"], "fake-test-token")

    def test_invalid_inputs_fail_without_leaking_values(self):
        for key, value in (("PORT", "oops-private"), ("PORT", "70000"),
                           ("NITTER_HOSTNAME", "https://bad.example"),
                           ("REDISHOST", "bad\n[Config]"), ("NITTER_HMAC_KEY", "short")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError) as caught:
                configuration(dict(self.env, **{key: value}), TEMPLATE.read_text())
            self.assertNotIn(value, str(caught.exception))

    def test_missing_session_fails_before_writing(self):
        self.env.pop("X_AUTH_TOKEN")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                prepare(self.env, TEMPLATE, Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_multiple_sessions(self):
        raw = sessions(self.env)
        self.assertEqual(len(sessions({"NITTER_SESSIONS": raw + "\n" + raw}).splitlines()), 2)

    def test_malformed_session_rejected(self):
        for raw in ('{"auth_token": "sensitive", broken}', '[]', '{"kind": "oauth"}',
                    '{"kind":"cookie","username":"x","auth_token":"a","ct0":"b","id":"bad"}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                sessions({"NITTER_SESSIONS": raw})


if __name__ == "__main__":
    unittest.main()
