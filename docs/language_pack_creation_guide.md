# Language Pack Creation Guide

## 1. Implement a Pack
Create a module exporting a `LanguagePack` instance (or `register()` returning one).

Required:
- `manifest: PackManifest`
- `emit(lowered, context) -> str`
- `scaffold(emitted_code, context) -> OutputBundle`

## 2. Define Manifest Carefully
At minimum:
- `target`, `stability`, `file_extension`
- `block_model`, `statement_termination`
- `type_strategy`, `runtime_helpers`
- `feature_coverage`

## 3. Register and Test
```bash
icl pack validate --pack my_pack_module:register
icl compile --code 'x := 1;' --target my_target --pack my_pack_module:register
icl contract test --target my_target --pack my_pack_module:register
```

## 4. Stability Promotion Rule
A pack must not be marked `stable` unless it passes all required contract cases.

## 5. Best Practices
- Keep pack logic syntax-only; semantic logic belongs to IR/lowering.
- Fail explicitly for unsupported features.
- Emit deterministic output for reproducibility.
- Document helper runtime assumptions in pack docs.
