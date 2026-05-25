---
name: feedback-python-poetry
description: For this project user prefers Python + Poetry for MongoDB work rather than raw mongosh scripts
metadata:
  type: feedback
---

For MongoDB homework / DB design tasks in this directory, the user prefers Python with Poetry-managed dependencies (pymongo) over raw mongosh `.js` scripts.

**Why:** User explicitly said "выполняй с использования python, через поетри добавь нужные библиотеки" when I offered .js scripts.

**How to apply:** When asked to demonstrate MongoDB operations, schemas, indexes, or queries — build a Poetry project (`pyproject.toml`), add `pymongo` and any helpers via `poetry add`, and write Python scripts. Do not produce mongosh `.js` files unless explicitly requested.
