"""Synthetic tests for the hash-pinned V643 AIDL 158 dispatcher audit.

No proprietary vendor ELF, TV, ADB, Binder or DRM is required for CI.
"""
import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "ldm158_dispatch_audit", ROOT / "tools" / "ldm158_dispatch_audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Phase18DispatchTests(unittest.TestCase):
    def fake_jump_table(self):
        size = audit.TABLE_BASE + 169 * 2 - audit.TEXT_FILE_BIAS
        data = bytearray(size)
        struct.pack_into("<H", data, audit.TABLE_BASE + 2 * 157 - audit.TEXT_FILE_BIAS,
                         (0x2a90a - audit.TABLE_BASE) // 2)
        struct.pack_into("<H", data, audit.TABLE_BASE + 2 * 146 - audit.TEXT_FILE_BIAS,
                         (0x2a592 - audit.TABLE_BASE) // 2)
        return data

    def test_jump_158_reaches_exact_handler(self):
        self.assertEqual(audit.jump_target(self.fake_jump_table(), 158), 0x2a90a)

    def test_147_control_jump_is_distinct(self):
        self.assertEqual(audit.jump_target(self.fake_jump_table(), 147), 0x2a592)

    def test_unrecognized_indices_are_rejected(self):
        for n in (0, -1, 170, 999, None, True, "158"):
            with self.subTest(n=n), self.assertRaises(ValueError):
                audit.jump_target(self.fake_jump_table(), n)

    def test_truncated_jump_table_fails_closed(self):
        with self.assertRaises(ValueError):
            audit.jump_target(b"\x00\x01", 158)

    def test_wrong_binary_fails_before_disassembly(self):
        with self.assertRaises(ValueError):
            audit.audit(ROOT / "src" / "main.cpp", ROOT / "src" / "main.cpp")

    def test_dispatch_zero_init_and_output_are_pinned(self):
        points = audit.CHECKS["aidl"]
        self.assertIn(0x2a924, points)
        self.assertIn(0x2a928, points)
        self.assertIn(0x2a95c, points)
        self.assertIn(0x2a960, points)

    def test_render_copy_to_end_is_pinned(self):
        points = audit.CHECKS["render"]
        self.assertIn(0x2e926, points)
        self.assertIn(0x2e92a, points)
        self.assertIn(0x2e92c, points)

    def test_vendor_158_not_dispatched_from_tv_client(self):
        client = (ROOT / "src" / "main.cpp").read_text(encoding="utf-8")
        self.assertNotIn("kGetLdmBlockData", client)
        self.assertNotIn("--read-block-data", client)


if __name__ == "__main__":
    unittest.main()
