from __future__ import annotations

import unittest

from icl.main import compile_source


PROGRAM = '''
fn add(a, b):Num => a + b;
x:Num := 1;
y := @add(x, 2);
if y > 2 ? { @print(y); } : { @print(0); }
loop i in 0..3 { @print(i); }
'''


class ExpanderTests(unittest.TestCase):
    def test_python_backend_emits_expected_constructs(self) -> None:
        artifacts = compile_source(PROGRAM, target='python')
        code = artifacts.code
        self.assertIn('def add(a, b):', code)
        self.assertIn('if (y > 2):', code)
        self.assertIn('for i in range(0, 3):', code)

    def test_js_backend_emits_expected_constructs(self) -> None:
        artifacts = compile_source(PROGRAM, target='js')
        code = artifacts.code
        self.assertIn('function add(a, b) {', code)
        self.assertIn('if ((y > 2)) {', code)
        self.assertIn('for (let i = 0; i < 3; i++) {', code)

    def test_rust_backend_emits_expected_constructs(self) -> None:
        artifacts = compile_source(PROGRAM, target='rust')
        code = artifacts.code
        self.assertIn('fn add(a: f64, b: f64) -> f64 {', code)
        self.assertIn('fn main() {', code)
        self.assertIn('let mut x = 1;', code)
        self.assertIn('for i in (0 as i64)..(3 as i64) {', code)


if __name__ == '__main__':
    unittest.main()
