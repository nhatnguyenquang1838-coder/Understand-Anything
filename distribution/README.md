# Understand Anything skills-only distribution

This provider recipe packages the headless `understand` skill, its agent definitions,
bundled helper scripts, core analyzer package, and the two workspace WASM grammar
packages required by `@understand-anything/core`.

It intentionally excludes:

- the graph dashboard and all web UI;
- the VS Code extension;
- marketing assets and screenshots;
- generated `.ua` or legacy `.understand-anything` data;
- historical plans/specs and repository test fixtures.

`SOURCE.lock.json` is the authoritative provenance record. Scheduled drift checks may
report that upstream changed, but they never update the lock or publish a new package
without an explicit reviewed commit.

Installation creates an empty consumer-owned `.ua/` runtime root. It does not analyze a
repository, launch a dashboard, create a task, open a branch, or publish an issue.
