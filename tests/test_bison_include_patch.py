from pathlib import Path
import tempfile
import subprocess
import unittest


class BisonIncludePatch(unittest.TestCase):
    def test_renamed_header_include_is_updated_without_changing_grammar(self):
        root = Path(__file__).resolve().parents[1]
        patch = (root / 'patches/chromium71/blink-bison-generated-header-include.patch').read_text()
        self.assertEqual([line for line in patch.splitlines() if line.startswith('+++ ')], ['+++ b/third_party/blink/renderer/build/scripts/rule_bison.py'])
        # Run the actual added replacement block against a synthetic Bison output.
        block = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / 'xpath_grammar.cc'
            cpp.write_text('#include "xpath_grammar.hh"\nint generated_parser;\n')
            namespace = {'os': __import__('os'), 'outputCpp': str(cpp), 'outputHTmp': str(Path(directory) / 'xpath_grammar.hh'), 'outputH': str(Path(directory) / 'xpath_grammar.h')}
            exec(block, namespace)
            self.assertEqual(cpp.read_text(), '#include "xpath_grammar.h"\nint generated_parser;\n')
