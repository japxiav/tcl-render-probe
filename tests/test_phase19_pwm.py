"""Phase 19: DV PWM remains scalar and LDM data (158) remains blocked."""
import unittest
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "src" / "main.cpp").read_text(encoding="utf-8")

class Phase19Safety(unittest.TestCase):
    def test_get_dv_pwm_transaction_pinned(self):
        self.assertIn("kGetDvPwmInfo = 162", SRC)

    def test_no_arbitrary_transaction_input(self):
        self.assertIn('std::strcmp(argv[1], "--read-dv-pwm")', SRC)

    def test_no_read_ldm_158(self):
        self.assertNotIn("kGetLdmBlockData", SRC)
        self.assertNotIn("--read-block-data", SRC)

    def test_two_bytes_only(self):
        self.assertIn("int8_t raw0 = 0, raw1 = 0", SRC)
        self.assertIn('AParcel_readByte(parcel, &raw0)', SRC)
        self.assertIn('AParcel_readByte(parcel, &raw1)', SRC)

    def test_return_bounds(self):
        self.assertIn("outerSize < 12 || outerSize > 64", SRC)
        self.assertIn("nestedSize < 6 || nestedSize > 32", SRC)

    def test_vendor_result_must_be_success(self):
        self.assertIn("result != 0 || nestedPresent != 1", SRC)

    def test_no_brightness_claim_in_code(self):
        self.assertIn("format/units unverified", SRC)

if __name__ == "__main__":
    unittest.main()
