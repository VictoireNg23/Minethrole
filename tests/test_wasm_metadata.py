from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from wasm_metadata import inspect, Reader


class WasmMetadata(unittest.TestCase):
    def test_exported_function_type_without_execution(self):
        data = bytes([0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,3,2,1,0,7,7,1,3,114,117,110,0,0,10,6,1,4,0,65,0,11])
        result = inspect(data)
        self.assertEqual(result['imports'], [])
        self.assertEqual(result['exports'][0], {'name': 'run', 'kind': 0, 'index': 0, 'type': {'params': [], 'results': ['0x7f']}})
        self.assertIsNone(result['start'])

    def test_truncation_magic_and_overflow_are_errors(self):
        for data in (b'not wasm', b'\x00asm\x01\x00\x00\x00\x01\x09\x00'):
            with self.assertRaises(ValueError):
                inspect(data)
        with self.assertRaises(ValueError):
            Reader(b'\xff\xff\xff\xff\x7f').u32()
