# Understand Anything Power distribution

This provider recipe packages the core `understand` producer skill and the companion
skills that consume or extend its `.ua/knowledge-graph.json` output:

- `understand-chat`
- `understand-explain`
- `understand-diff`
- `understand-dashboard`
- `understand-domain`
- `understand-onboard`
- `understand-knowledge`
- `understand-figma`

The package also includes the agent definitions, bundled helper scripts, core analyzer,
dashboard runtime package, and the two workspace WASM grammar packages required by
`@understand-anything/core`.

It intentionally excludes:

- the VS Code extension;
- standalone application source outside the packaged dashboard runtime;
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
repository, launch the dashboard automatically, create a task, open a branch, or publish
an issue. Companion skills become available to configured hosts through the package
entrypoint list; they operate only when explicitly invoked.
