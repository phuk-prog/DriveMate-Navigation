import unittest
from tools.privacy_guard import inspect_file


class PrivacyGuardTests(unittest.TestCase):
    def test_public_source_without_pii_passes(self):
        self.assertEqual(inspect_file("engine/algorithm.py", b"def route():\n    return 1\n"), [])

    def test_sensitive_path_never_uploaded(self):
        self.assertTrue(inspect_file("traces/user-drive.txt", b"synthetic") )
        self.assertTrue(inspect_file("benchmarks/fixtures/sample.gpx", b"synthetic"))

    def test_credentials_without_ever_storing_real_tokens(self):
        fake = ("ghp_" + "a"*35).encode()
        self.assertIn("potential credential", inspect_file("notes.txt", fake))

    def test_email_pattern_uses_fabricated_address(self):
        fake = ("example" + "@" + "example.invalid").encode()
        self.assertIn("possible personal email address", inspect_file("notes.txt", fake))

    def test_embedded_location_recording_is_rejected(self):
        self.assertTrue(inspect_file("fixture.txt", b"<gpx><trkpt lat='1' lon='2'/></gpx>"))

    def test_fixture_requires_synthetic_provenance(self):
        self.assertIn("fixture lacks explicit synthetic classification",
                      inspect_file("benchmarks/fixtures/unlabelled.json", b'{"data":123}'))
        self.assertEqual(inspect_file("benchmarks/fixtures/synthetic.json", b'{"classification":"synthetic"}'), [])

    def test_nontext_and_oversize_rejected(self):
        self.assertIn("oversized or binary file", inspect_file("file.txt", b"a\x00b"))
        self.assertIn("oversized or binary file", inspect_file("file.txt", b"a" * 1000001))
