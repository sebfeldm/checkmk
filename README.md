# checkmk

Custom Checkmk monitoring plugins developed by [hivescript](https://github.com/hivescript).

## Structure

Plugins are grouped by the Checkmk mechanism they use, one subfolder per
plugin:

```
checkmk/
├── special_agents/   # Special agents (run on the Checkmk server, query an external API)
│   └── check_graph_secrets/
├── checks/           # Local checks (run via the Checkmk agent on a monitored host)
└── plugins/          # Other plugin types (inventory, notification, ...)
```

Every plugin/check name starts with `check_`.

Each plugin folder is self-contained and follows the Checkmk 2.3 extension
package (MKP) layout: `agent_based/`, `rulesets/`, `server_side_calls/`
and/or `libexec/`, `checkman/`. See each plugin's own README for setup
details.

## Plugins

- [special_agents/check_graph_secrets](special_agents/check_graph_secrets/README.md) —
  monitors expiration of Microsoft Entra app registration client secrets via
  the Microsoft Graph API.

## Building .mkp packages

`scripts/build_mkp.py` packages a plugin folder into a `.mkp` extension
package, using only the Python standard library (no Checkmk site needed):

```bash
python scripts/build_mkp.py special_agents/check_graph_secrets \
  --name check_graph_secrets \
  --version 1.0.0 \
  --title "Microsoft Graph App Secrets" \
  --author "Your Name <you@example.com>" \
  --description "What the package does." \
  --download-url "https://github.com/hivescript/checkmk/tree/main/special_agents/check_graph_secrets"
```

Built packages are checked into [`releases/`](releases/).

## Requirements

Checkmk 2.3 or newer (plug-in API v2 / Server Side Calls API v1 / Ruleset
API v1).
