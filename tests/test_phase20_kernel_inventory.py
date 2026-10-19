"""Synthetic tests; never connects to a device."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('module_inventory', ROOT / 'tools' / 'phase20_module_inventory.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestKernelModuleInventory(unittest.TestCase):
    def test_detects_ldm_and_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / 'fake.ko'
            f.write_bytes(b'\x7fELF\x02\x01' + bytes(12) + bytes([183, 0]) + bytes(16) +
                          b'get_ldm_blocks\x00spi_mt5896\x00dma_heap\x00')
            report = mod.inspect_file(f)
            self.assertEqual(report['elf_arch'], 'AArch64')
            for key in ['ldm', 'transport', 'drm_dma']:
                self.assertTrue(report['indicators'][key])

    def test_rejects_non_elf(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / 'wrong.ko'
            f.write_text('just text')
            with self.assertRaises(ValueError):
                mod.inspect_file(f)

    def test_rejects_unsupported_machine(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / 'wrong.ko'
            f.write_bytes(b'\x7fELF\x02\x01' + bytes(14))
            with self.assertRaises(ValueError):
                mod.inspect_file(f)

if __name__ == '__main__':
    unittest.main()
