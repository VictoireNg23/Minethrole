import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('browser_ready', Path(__file__).resolve().parents[1] / 'scripts/test-chromium71-browser-ready.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ProcStatus(unittest.TestCase):
    def test_parse_renderer_security_fields(self):
        fields = m.parse_status('Name:\tchrome\nUid:\t998 998 998 998\nSeccomp:\t2\nNoNewPrivs:\t1\n')
        self.assertEqual(fields['Uid'], '998 998 998 998')
        self.assertEqual(fields['Seccomp'], '2')
        self.assertEqual(fields['NoNewPrivs'], '1')

    def test_selects_renderer_without_proc_exe_access(self):
        binary = Path('/tmp/stage/browser/chrome')
        processes = [(40, str(binary) + ' --type=renderer --headless '),
                     (12, str(binary) + ' --headless '),
                     (22, str(binary) + ' --type=zygote '),
                     (99, str(binary) + '-other --type=renderer ')]
        self.assertEqual(m.select_debug_targets(processes, binary), [(12, 'browser'), (40, 'renderer')])

    def test_process_identity_ignores_spaces_in_comm(self):
        # state is field 3, start time is field 22.
        text = '123 (renderer (worker)) ' + ' '.join(['S'] + ['0'] * 18 + ['987654'])
        self.assertEqual(m.process_start_ticks(text), '987654')

    def test_unpause_signal_is_only_used_for_startup_renderer(self):
        self.assertNotIn('signal SIGUSR1', m.debugger_command(1, 'browser', True))
        self.assertNotIn('signal SIGUSR1', m.debugger_command(1, 'renderer', False))
        self.assertIn('signal SIGUSR1', m.debugger_command(1, 'renderer', True))

    def test_syscall_evidence_collected_before_detach(self):
        args = m.debugger_command(10, 'renderer', True)
        self.assertIn('p $_siginfo', args)
        self.assertIn('info registers orig_rax rax rip', args)
        self.assertLess(args.index('p $_siginfo'), args.index('detach'))

    def test_browser_rseq_opt_out_is_local_and_idempotent(self):
        original = 'glibc.malloc.arena_max=2:glibc.pthread.rseq=1'
        value = m.disable_rseq_tunable(original)
        self.assertEqual(value, 'glibc.malloc.arena_max=2:glibc.pthread.rseq=0')
        self.assertEqual(m.disable_rseq_tunable(value), value)

    def test_wasm_dom_and_counts_are_independent_evidence(self):
        text = '<pre id="wasm-result">{&quot;status&quot;:&quot;executed&quot;,&quot;mode&quot;:&quot;active&quot;,&quot;calls&quot;:20000}</pre>'
        self.assertEqual(m.wasm_result_from_dom(text)['calls'], 20000)
        self.assertEqual(m.counter_rows('1 12345.0 0\n'), [])
        row = ' '.join(map(str, [1, 2, 0, 0, 1, 0, 0, 0, 0, 0, 20000] + [0] * 11))
        self.assertEqual(m.counter_rows(row), [[20000] + [0] * 11])
