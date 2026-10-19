"""Regression guard only: never contacts TV or fabricates LDM data."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("guard", ROOT / "tools/ldm158_output_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class TestOutputBufferGate(unittest.TestCase):
    def test_offsets_are_distinct(self):
        self.assertEqual(guard.AIDL_RETURN_VECTOR_OFFSET, 8)
        self.assertEqual(guard.RENDER_COPY_DESTINATION_OFFSET, 12)

    def test_explicit_block(self):
        self.assertFalse(guard.TV_TRANSACTION_158_ALLOWED)

    def test_zero_length_provides_no_telemetry(self):
        self.assertEqual(guard.classify_copy(None, None, None, 0), "NO_PAYLOAD")

    def test_unknown_buffer_blocks(self):
        self.assertEqual(guard.classify_copy(None, None, None, 360), "BLOCK_UNVERIFIED_VECTOR_STATE")

    def test_no_capacity_blocks(self):
        self.assertEqual(guard.classify_copy(0, 0, 0, 360), "BLOCK_INSUFFICIENT_TAIL_CAPACITY")

    def test_preallocated_full_vector_blocks(self):
        self.assertEqual(guard.classify_copy(1000, 1360, 1360, 360), "BLOCK_INSUFFICIENT_TAIL_CAPACITY")

    def test_even_if_tail_has_space_copy_to_end_is_not_a_valid_vector_write(self):
        self.assertEqual(guard.classify_copy(1000, 1010, 1200, 12), "BLOCK_SEMANTICALLY_WRONG_END_POINTER")

    def test_overflow_and_invalid_lengths_rejected(self):
        for n in (-1, 65537, 1.5, True, "360"):
            with self.subTest(n=n), self.assertRaises(ValueError):
                guard.classify_copy(1000, 1000, 1400, n)

    def test_no_hardware_dispatch_in_source(self):
        client = (ROOT / "src/main.cpp").read_text(encoding="utf-8")
        self.assertNotIn("kGetLdmBlockData", client)
        self.assertNotIn("--read-block-data", client)

if __name__ == "__main__":
    unittest.main()
