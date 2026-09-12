# check_graph_secrets

Checkmk special agent that monitors the expiration of Microsoft Entra app
registration client secrets via the Microsoft Graph API, so you can rotate
them before they expire and cause an outage.

Requires Checkmk **2.3** or newer (Checkmk plug-in API v2 / Server Side Calls
API v1 / Ruleset API v1).

## What it does

- Queries `GET /v1.0/applications` in the configured Entra tenant.
- For every app registration with at least one client secret
  (`passwordCredentials`), creates one Checkmk service: **Graph Secret
  \<app name\>**.
- The service reports the remaining validity of the secret that expires
  next (WARN/CRIT thresholds configurable, default 30 / 14 days), plus
  details for all of the app's secrets.

Certificates (`keyCredentials`) and federated credentials are intentionally
out of scope for this check.

## Prerequisites: Microsoft Entra app registration

Create a dedicated app registration used only by this special agent:

1. Entra admin center → **App registrations** → **New registration**.
2. **API permissions** → add **Microsoft Graph** → **Application permissions**
   → `Application.Read.All` → **Grant admin consent**.
3. **Certificates & secrets** → **New client secret** → note the value (you
   won't be able to read it again).
4. Note the **Application (client) ID** and **Directory (tenant) ID** from
   the app's **Overview** page.

`Application.Read.All` is read-only and only grants visibility into the
tenant's own app registrations and their metadata (not secret *values* —
Graph never returns those).

## Installation

Directory layout follows the Checkmk 2.3 extension package (MKP) convention:

```
special_agents/check_graph_secrets/
├── agent_based/check_graph_secrets.py       # check plug-in + section parser
├── checkman/check_graph_secrets             # man page
├── libexec/agent_check_graph_secrets        # the special agent script itself
├── rulesets/check_graph_secrets.py          # special agent WATO rule
├── rulesets/check_graph_secrets_params.py   # check parameter WATO rule
└── server_side_calls/check_graph_secrets.py # maps rule params to CLI args
```

To install on a Checkmk site, copy the contents of
`special_agents/check_graph_secrets/` into
`~/local/lib/python3/cmk_addons/plugins/check_graph_secrets/` on the site
(same sub-folder names), then:

```bash
cmk-validate-plugins
omd restart apache
```

(Packaging this as a proper `.mkp` via `mkp package`/the Extension Packages
GUI is the recommended distribution method once this is finalized — not yet
set up in this repo.)

## Configuration

1. Create a host to represent the Entra tenant (no Checkmk agent needed on
   it — the special agent runs on the Checkmk server itself).
2. **Setup → Agents → Other integrations → Microsoft Graph app secrets**:
   set tenant ID, client ID and client secret (stored in the Checkmk
   password store) from the app registration above.
3. Optionally adjust thresholds / exclusions under **Setup → Service
   monitoring rules → Microsoft Graph App Secrets**.
4. Run service discovery on the host.

## Status

Initial version, not yet tested against a live Checkmk site or tenant.
Before relying on it in production:

- Validate with `cmk-validate-plugins` on an actual Checkmk 2.3 site.
- Confirm discovery and check output against a real Entra tenant.
- Consider adding a custom graph template for the
  `check_graph_secrets_remaining_validity` metric.
