from __future__ import annotations

import unittest

from icl.main import build_plugin_manager, compile_source


class PluginTests(unittest.TestCase):
    def test_macro_plugin_expansion(self) -> None:
        manager = build_plugin_manager(['icl.plugins.std_macros:register'])
        artifacts = compile_source('#echo(42);', target='python', plugin_manager=manager)
        self.assertIn('print(42)', artifacts.code)

    def test_macro_plugin_dbg_expansion(self) -> None:
        manager = build_plugin_manager(['icl.plugins.std_macros'])
        artifacts = compile_source('#dbg(7);', target='js', plugin_manager=manager)
        self.assertIn('print("dbg:")', artifacts.code)
        self.assertIn('print(7)', artifacts.code)


if __name__ == '__main__':
    unittest.main()
