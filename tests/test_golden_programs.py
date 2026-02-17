from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from icl.main import compile_source


GOLDEN_PROGRAMS: list[tuple[str, str]] = [
    (
        "factorial",
        "fn fact(n:Num):Num { if n <= 1 ? { ret 1; } : { ret n * @fact(n - 1); } } @print(@fact(5));",
    ),
    (
        "loop_sum",
        "sum := 0; loop i in 0..5 { sum := sum + i; } @print(sum);",
    ),
    (
        "nested_conditional",
        "x := 3; if x > 2 ? { if x < 10 ? { @print(1); } : { @print(2); } } : { @print(0); }",
    ),
    (
        "function_chain",
        "fn add(a:Num,b:Num):Num => a + b; fn twice(v:Num):Num => @add(v, v); @print(@twice(7));",
    ),
    (
        "logic_gate",
        "ok := true && !false; if ok ? { @print(1); } : { @print(0); }",
    ),
]


class GoldenCompileTests(unittest.TestCase):
    def test_stable_targets_compile_all_golden_programs(self) -> None:
        for name, source in GOLDEN_PROGRAMS:
            for target in ["python", "js", "rust", "web"]:
                artifacts = compile_source(source, target=target)
                self.assertTrue(artifacts.code.strip(), msg=f"empty output for {name}/{target}")

                if target == "web":
                    self.assertIn("index.html", artifacts.bundle.files)
                    self.assertIn("styles.css", artifacts.bundle.files)
                    self.assertIn("app.js", artifacts.bundle.files)
                elif target == "python":
                    self.assertIn("main.py", artifacts.bundle.files)
                elif target == "js":
                    self.assertIn("main.js", artifacts.bundle.files)
                elif target == "rust":
                    self.assertIn("main.rs", artifacts.bundle.files)


class GoldenRunnablePythonJsTests(unittest.TestCase):
    def test_python_and_js_runnable(self) -> None:
        for name, source in GOLDEN_PROGRAMS:
            with self.subTest(program=name, target="python"):
                py = compile_source(source, target="python")
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "main.py"
                    path.write_text(py.code, encoding="utf-8")
                    proc = subprocess.run(
                        [sys.executable, str(path)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(proc.returncode, 0, msg=proc.stderr)
                    self.assertTrue(proc.stdout.strip(), msg=f"no python output for {name}")

            with self.subTest(program=name, target="js"):
                js = compile_source(source, target="js")
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "main.js"
                    path.write_text(js.code, encoding="utf-8")
                    proc = subprocess.run(
                        ["node", str(path)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(proc.returncode, 0, msg=proc.stderr)
                    self.assertTrue(proc.stdout.strip(), msg=f"no js output for {name}")


@unittest.skipUnless(shutil.which("rustc"), "rustc not installed")
class GoldenRunnableRustTests(unittest.TestCase):
    def test_rust_runnable_for_core_static_programs(self) -> None:
        # These cover recursion, loops, branching, and function calls in static target emission.
        static_programs = [
            GOLDEN_PROGRAMS[0],
            GOLDEN_PROGRAMS[1],
            GOLDEN_PROGRAMS[3],
        ]

        for name, source in static_programs:
            with self.subTest(program=name):
                artifacts = compile_source(source, target="rust")
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    src = tmp_path / "main.rs"
                    bin_path = tmp_path / "main"
                    src.write_text(artifacts.code, encoding="utf-8")

                    compile_proc = subprocess.run(
                        ["rustc", str(src), "-O", "-o", str(bin_path)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(compile_proc.returncode, 0, msg=compile_proc.stderr)

                    run_proc = subprocess.run(
                        [str(bin_path)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(run_proc.returncode, 0, msg=run_proc.stderr)
                    self.assertTrue(run_proc.stdout.strip(), msg=f"no rust output for {name}")


if __name__ == "__main__":
    unittest.main()
