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

The controlled fork `nhatnguyenquang1838-coder/Understand-Anything@main` is the
publication source of truth. Every reviewed change merged to that branch may build and
publish a new immutable UA package and synchronize `power-dist`.

`SOURCE.lock.json` retains controlled-fork and vendor provenance baselines. The scheduled
vendor check reports when `Egonex-AI/Understand-Anything@main` changes, but vendor drift
is advisory only. It never blocks controlled-fork development, release publication, or
`power-dist` synchronization. Vendor changes are imported deliberately through normal
reviewed pull requests when they are useful.

Installation creates an empty consumer-owned `.ua/` runtime root. It does not analyze a
repository, launch a dashboard, create a task, open a branch, or publish an issue.
