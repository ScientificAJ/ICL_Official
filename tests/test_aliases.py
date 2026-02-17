from __future__ import annotations

import unittest

from icl.main import compile_source
from icl.plugins.natural_aliases import normalize_aliases


class AliasNormalizationTests(unittest.TestCase):
    def test_normalize_aliases_skips_strings_and_comments(self) -> None:
        source = 'prnt("mkfn") // prnt in comment\nmkfn add(a,b)=>a+b; prnt(add(1,2));'
        normalized, replacements = normalize_aliases(
            source,
            {"prnt": "print", "mkfn": "fn"},
        )

        self.assertIn('print("mkfn")', normalized)
        self.assertIn('// prnt in comment', normalized)
        self.assertIn('fn add(a,b)=>a+b;', normalized)
        self.assertGreaterEqual(len(replacements), 3)

    def test_extended_mode_aliases_compile(self) -> None:
        artifacts = compile_source(
            'ok := yes and not no; prnt(ok);',
            target='python',
            natural_aliases=True,
            alias_mode='extended',
        )
        self.assertIn('ok = (True and (not False))', artifacts.code)
        self.assertIn('print(ok)', artifacts.code)

    def test_compile_artifacts_include_alias_metadata(self) -> None:
        artifacts = compile_source(
            'mkfn add(a,b)=>a+b; prnt(add(1,2));',
            target='python',
            natural_aliases=True,
            alias_mode='core',
        )
        metadata = artifacts.plugin_metadata or {}
        self.assertIn('natural_aliases', metadata)
        self.assertGreater(metadata['natural_aliases']['count'], 0)


if __name__ == '__main__':
    unittest.main()
