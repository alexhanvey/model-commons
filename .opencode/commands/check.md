---
description: Run the repository checks and fix only what this change broke
agent: build
---

Run the repository's definition-of-done checks for the current change:

```sh
just lint
just typecheck
just test
```

If a web or container path changed, also run `just build`. Report each command's result. Fix
failures caused by the current change; do not rewrite unrelated research code or suppress a real
failure.
