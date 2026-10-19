"""Synthetic safety checks. Real vendor ELFs stay offline and out of GitHub."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "tools" / "ldm158_offline_audit.py"
spec = importlib.util.spec_from_file_location("ldm158_offline_audit", MOD)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Ldm158PreflightTests(unittest.TestCase):
    def test_nonzero_reads_are_blocked(self):
        for n in (1, 10, 18, 180, 360, 65536):
            with self.subTest(size=n):
                self.assertEqual(audit.model(n), "BLOCKED_UNVERIFIED_DESTINATION")

    def test_zero_bytes_yield_no_telemetry(self):
        self.assertEqual(audit.model(0), "NO_DATA")

    def test_bad_lengths_fail_closed(self):
        for n in (-1, 65537, 0.5, "180", None):
            with self.subTest(value=n):
                with self.assertRaises(ValueError):
                    audit.model(n)

    def test_foreign_elf_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "render.so"
            file.write_bytes(b"not an approved TCL V643 binary")
            with self.assertRaises(ValueError):
                audit.audit(file, file)

    def test_158_stays_out_of_television_executable(self):
        code = (ROOT / "src" / "main.cpp").read_text(encoding="utf-8")
        self.assertNotIn("kGetLdmBlockData", code)
        self.assertNotIn("--read-block-data", code)
        self.assertNotIn("AIBinder_transact(binder, 158", code)

    def test_known_instruction_count(self):
        self.assertEqual(sum(map(len, audit.CHECKS.values())), 13)


if __name__ == "__main__":
    unittest.main()
