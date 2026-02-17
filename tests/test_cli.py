from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-m', 'icl.cli', *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class CLITests(unittest.TestCase):
    def test_compile_inline_python(self) -> None:
        result = run_cli('compile', '--code', 'x := 1 + 2;', '--target', 'python')
        self.assertEqual(result.returncode, 0)
        self.assertIn('x = (1 + 2)', result.stdout)

    def test_check_ok(self) -> None:
        result = run_cli('check', '--code', 'fn add(a,b)=>a+b; x := @add(1,2);')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'OK')

    def test_explain_json(self) -> None:
        result = run_cli('explain', '--code', 'x := 1;')
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn('ast', payload)
        self.assertIn('graph', payload)

    def test_compile_error_exit_code(self) -> None:
        result = run_cli('compile', '--code', 'ret 1;', '--target', 'python')
        self.assertEqual(result.returncode, 1)
        self.assertIn('SEM008', result.stderr)

    def test_compile_with_macro_plugin(self) -> None:
        result = run_cli(
            'compile',
            '--code',
            '#echo(9);',
            '--target',
            'python',
            '--plugin',
            'icl.plugins.std_macros:register',
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('print(9)', result.stdout)

    def test_compile_rust_target(self) -> None:
        result = run_cli('compile', '--code', 'x := 1;', '--target', 'rust')
        self.assertEqual(result.returncode, 0)
        self.assertIn('fn main() {', result.stdout)

    def test_compile_web_requires_directory_for_multifile_output(self) -> None:
        result = run_cli('compile', '--code', '@print(1);', '--target', 'web', '--output', 'out.js')
        self.assertEqual(result.returncode, 1)
        self.assertIn('CLI010', result.stderr)

    def test_compile_with_natural_aliases(self) -> None:
        result = run_cli(
            'compile',
            '--code',
            'mkfn add(a,b)=>a+b; out := add(1,2); prnt(out);',
            '--target',
            'python',
            '--natural',
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('def add(a, b):', result.stdout)
        self.assertIn('print(out)', result.stdout)

    def test_alias_list_json(self) -> None:
        result = run_cli('alias', 'list', '--mode', 'extended', '--json')
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        canonical = {item['canonical'] for item in payload}
        self.assertIn('fn', canonical)
        self.assertIn('lam', canonical)


if __name__ == '__main__':
    unittest.main()
