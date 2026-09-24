# checkmk

Custom Checkmk monitoring plugins by [Sebastian Feldmann](https://github.com/sebfeldm).

## Structure

Plugins are grouped by the Checkmk mechanism they use, one subfolder per
plugin:

```
checkmk/
├── special_agents/   # Special agents (run on the Checkmk server, query an external API)
│   └── check_graph_secrets/
├── checks/           # Local checks (run via the Checkmk agent on a monitored host) — not used yet
├── plugins/          # Other plugin types (inventory, notification, ...) — not used yet
├── releases/         # Built .mkp packages, one per plugin release
└── scripts/          # Repo tooling (e.g. the .mkp builder)
```

Every plugin/check name starts with `check_`.

Each plugin folder is self-contained and follows the Checkmk 2.3 extension
package (MKP) layout: `agent_based/`, `rulesets/`, `server_side_calls/`
and/or `libexec/`, `checkman/`. See each plugin's own README for setup
details.

## Plugins

- [special_agents/check_graph_secrets](special_agents/check_graph_secrets/README.md) —
  monitors expiration of Microsoft Entra app registration client secrets via
  the Microsoft Graph API. Running in production since 2026-09.

## Installing a plugin

Two ways to get a plugin onto a Checkmk site — see the plugin's own README
for the full walkthrough (Checkmk-side configuration, permissions, etc.):

1. **Download a prebuilt `.mkp`** from the
   [Releases page](https://github.com/sebfeldm/checkmk/releases) (also
   kept in [`releases/`](releases/)) and install it via **Setup →
   Maintenance → Extension packages** or `mkp install`. Since this repo is
   public, no auth is needed:
   ```bash
   wget https://github.com/sebfeldm/checkmk/releases/download/check_graph_secrets-v1.0.0/check_graph_secrets-1.0.0.mkp
   ```
2. **Clone this repo** on the Checkmk site and symlink the plugin folder
   into `~/local/lib/python3/cmk_addons/plugins/<name>/`. Best while you're
   actively iterating — updates are a `git pull` away. Needs shell access
   to the site. On a **Checkmk Appliance**, that only works on the
   Enterprise tier with SSH shell access enabled (device config menu or
   remote maintenance protocol); the **demo/free appliance blocks command
   line access entirely**, so use option 1 there.

If you clone the repo onto a site that should only ever use the symlink
method (option 2), you can keep the `.mkp` files out of that clone's
working tree with `git sparse-checkout` — they stay downloadable from
GitHub either way:
```bash
git sparse-checkout init --no-cone
printf '/*\n!/releases/\n' > .git/info/sparse-checkout
git sparse-checkout reapply
```

## Building .mkp packages

`scripts/build_mkp.py` packages a plugin folder into a `.mkp` extension
package, using only the Python standard library (no Checkmk site needed):

```bash
python3 scripts/build_mkp.py special_agents/check_graph_secrets \
  --name check_graph_secrets \
  --version 1.0.0 \
  --title "Microsoft Graph App Secrets" \
  --author "Your Name <you@example.com>" \
  --description "What the package does." \
  --download-url "https://github.com/sebfeldm/checkmk/tree/main/special_agents/check_graph_secrets"
```

Built packages are checked into [`releases/`](releases/) (tracked
deliberately — `.gitignore` blocks stray `.mkp` files elsewhere from being
added by accident, but explicitly allows `releases/*.mkp`).

## Requirements

Checkmk 2.3 or newer (plug-in API v2 / Server Side Calls API v1 / Ruleset
API v1).

## License

[MIT](LICENSE).
