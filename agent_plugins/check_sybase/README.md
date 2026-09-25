# check_sybase

Checkmk agent plug-in and check plug-ins for **SAP ASE (Sybase)** on Linux.
Requires Checkmk 2.3.0 or newer (works with the Raw edition).

The agent plug-in on the database host only collects raw data. All states
and thresholds are evaluated on the Checkmk server and are configured via
rules in the Checkmk GUI — per host, per instance and per database.

## Services

Multiple ASE instances per host are supported; the SID is part of every
service name.

| Service | What it checks | Rule (Setup → Services → Service monitoring rules → Databases) | Defaults |
|---|---|---|---|
| `Sybase Instance <SID>` | isql connection, `dataserver` and `backupserver` process | SAP ASE (Sybase) Instance | CRIT if any fails |
| `Sybase Data <SID> <DB>` | used space of the data segments | SAP ASE (Sybase) Database Data Usage | WARN 90 %, CRIT 95 %; optional levels on free space |
| `Sybase Log <SID> <DB>` | used space of the dedicated log segment (only databases that have one) | SAP ASE (Sybase) Database Log Usage | WARN 80 %, CRIT 90 %; optional levels on free space |
| `Sybase Backup <SID> <DB>` | age and result of the last database backup | SAP ASE (Sybase) Database Backup | WARN 26 h, CRIT 50 h; CRIT if failed; WARN if never backed up |
| `Sybase Errorlog <SID>` | lines in the ASE errorlog matching an error pattern within a time window | SAP ASE (Sybase) Errorlog | CRIT from the first error |

Which databases get **no** backup service (e.g. temporary databases) is set
by the discovery rule *SAP ASE (Sybase) Database Backup Discovery*
(default: `(sap)?tempdb\d*`).

Example — different data levels for one database on one host: create a rule
*SAP ASE (Sybase) Database Data Usage*, set the explicit host and the
condition *Instance and database* to `ABC ABC$`.

## Installation

### 1. Checkmk server

Two options; pick one. Both work on the Raw edition.

#### Option 1 — install the .mkp

```bash
wget https://github.com/sebfeldm/checkmk/releases/download/check_sybase-v1.0.0/check_sybase-1.0.0.mkp
mkp install check_sybase-1.0.0.mkp
```

(or **Setup → Maintenance → Extension packages → Upload package**). This
installs the check plug-ins, rules and graphs, and puts the agent plug-in
and the example config under **Setup → Agents → Linux**
(`~/local/share/check_mk/agents/plugins/check_sybase` and
`~/local/share/check_mk/agents/cfg_examples/check_sybase.cfg` on the site).

#### Option 2 — git clone + symlink (easier for troubleshooting)

The server-side files are used straight from a git checkout, so you can
read, `git diff` or temporarily patch exactly the code that runs, and
updating is a `git pull`. As the **site user**:

```bash
mkdir -p ~/git && cd ~/git
git clone https://github.com/sebfeldm/checkmk.git   # skip if already cloned

ln -s ~/git/checkmk/agent_plugins/check_sybase       ~/local/lib/python3/cmk_addons/plugins/check_sybase
```

Optional, so the agent files are also offered under **Setup → Agents →
Linux** like with the .mkp:

```bash
mkdir -p ~/local/share/check_mk/agents/plugins ~/local/share/check_mk/agents/cfg_examples
ln -s ~/git/checkmk/agent_plugins/check_sybase/agents/plugins/check_sybase       ~/local/share/check_mk/agents/plugins/check_sybase
ln -s ~/git/checkmk/agent_plugins/check_sybase/agents/cfg_examples/check_sybase.cfg       ~/local/share/check_mk/agents/cfg_examples/check_sybase.cfg
```

Don't combine both options on one site: if the .mkp is installed, remove it
first (`mkp remove check_sybase`), otherwise the files collide.

#### Reload after install/update (either option)

```bash
cmk-validate-plugins
cmk -U && omd restart
```

#### Troubleshooting on the server

```bash
# Raw agent output as the server sees it (look for <<<check_sybase:sep(59)>>>)
cmk -d <host> | sed -n '/<<<check_sybase/,/<<</p'

# Discover new services and run the checks for one host, with details
# (-n: don't submit the results to the core)
PLUGINS=check_sybase_instance,check_sybase_data,check_sybase_log,check_sybase_backup,check_sybase_errorlog
cmk -vI --detect-plugins=$PLUGINS <host>
cmk -nv --detect-plugins=$PLUGINS <host>
```

### 2. Database host

The Raw edition has no agent bakery, so the agent plug-in and its config
are copied to each host manually (or with your configuration management).

**Hosts with internet access** — download directly from GitHub, as root:

```bash
# Agent plug-in, runs asynchronously every 300 seconds
mkdir -p /usr/lib/check_mk_agent/plugins/300
wget -O /usr/lib/check_mk_agent/plugins/300/check_sybase     https://raw.githubusercontent.com/sebfeldm/checkmk/main/agent_plugins/check_sybase/agents/plugins/check_sybase
chmod 0755 /usr/lib/check_mk_agent/plugins/300/check_sybase

# Example config, first install only: don't overwrite an existing config
# with your credentials on updates
[ -e /etc/check_mk/check_sybase.cfg ] || {
    wget -O /etc/check_mk/check_sybase.cfg         https://raw.githubusercontent.com/sebfeldm/checkmk/main/agent_plugins/check_sybase/agents/cfg_examples/check_sybase.cfg
    chown root:root /etc/check_mk/check_sybase.cfg
    chmod 0600 /etc/check_mk/check_sybase.cfg
}
```

`main` is always the latest version. To pin a released version, replace
`main` in the URLs with the release tag, e.g. `check_sybase-v1.0.0`.

**Hosts without internet access** — download the files from the Checkmk
server (**Setup → Agents → Linux**) or copy them from a checkout, then:

```bash
install -D -m 0755 check_sybase /usr/lib/check_mk_agent/plugins/300/check_sybase
install -m 0600 -o root -g root check_sybase.cfg /etc/check_mk/check_sybase.cfg
```

Edit `/etc/check_mk/check_sybase.cfg`: one `[SID]` section per instance with
at least `user` and `password`. All options are described in the
[example config](agents/cfg_examples/check_sybase.cfg).

Requirements on the host: `bash` 4+, `isql` in the login environment of the
instance's OS user (default `syb<sid>`), GNU `date`, `timeout`, `pgrep`. The
login needs `mon_role` for `monOpenDatabases`.

Test it as root:

```bash
/usr/lib/check_mk_agent/plugins/300/check_sybase
```

Then run a service discovery for the host in Checkmk.

## How it works

For each configured instance the plug-in:

- checks for `dataserver` and `backupserver` processes of the OS user
  (`pgrep -u`),
- runs one SQL query via `su - <os user> -c isql` (with a timeout) that
  returns size, used space, log size, free log space, the age of the last
  backup and the last backup's failure flag per database from
  `master..sysusages` and `master..monOpenDatabases`,
- searches the ASE errorlog for the error pattern and sends the number of
  matching lines within the time window and the latest 20 of them.

The password is handed to `isql` via stdin by default, so it doesn't show up
in the process list. If your `isql` build doesn't read the password from
stdin, set `password_via=argv` (old behavior with `-P`).

Agent output (section `check_sybase`, separated by `;`):

```
<<<check_sybase:sep(59)>>>
instance;ABC;dataserver;1
instance;ABC;backupserver;1
instance;ABC;connect;0;OK
db;ABC;ABC;102400.00;81920.00;20480.00;18432.00;1739260800;0
db;ABC;saptempdb;4096.00;12.00;0.00;0.00;;0
errorlog;ABC;ok;24;1;/sybase/ABC/ASE-16_0/install/ABC.log
errorlog_line;ABC;2025/02/11 10:15:32;Error: 1105, Severity: 17, State: 4
```

## Migrating from the old local check

The previous version was a local check (`/usr/lib/check_mk_agent/local/300/…`
plus an external `.sql` file) with thresholds in the script. To switch:

1. Install the `.mkp` and create the rules for your current thresholds
   (including host-specific exceptions) in the GUI.
2. On each host: deploy plug-in and config as described above, then remove
   the old local check script and its `.sql` file.
3. Run a service discovery: the old `SYBASE …` services vanish, the new
   `Sybase …` services appear. Service names and metrics changed, so graph
   history starts anew.

Behavioral differences to the old local check:

- A failed or hanging isql connection now turns the instance service CRIT
  (previously the database services just went stale).
- The backup service also checks the **age** of the last backup, not only
  the failure flag.
- The errorlog pattern is matched case-insensitively by default, so ASE's
  own `Error: …` lines are found too (set `errorlog_ignore_case=no` for the
  old behavior).
- The errorlog window is exactly the last N hours (default 24).
