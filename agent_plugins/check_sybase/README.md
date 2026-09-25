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
| `SYBASE <SID> Instance` | isql connection, `dataserver` and `backupserver` process | SAP ASE (Sybase) Instance | CRIT if any fails |
| `SYBASE <SID> <DB> Data` | used space of the data segments | SAP ASE (Sybase) Database Data Usage | WARN 90 %, CRIT 95 %; optional levels on free space |
| `SYBASE <SID> <DB> Log` | used space of the dedicated log segment (only databases that have one) | SAP ASE (Sybase) Database Log Usage | WARN 80 %, CRIT 90 %; optional levels on free space |
| `SYBASE <SID> <DB> Backup` | age and result of the last database backup | SAP ASE (Sybase) Database Backup | WARN 26 h, CRIT 50 h; CRIT if failed (optionally only after a grace period); WARN if never backed up |
| `SYBASE <SID> Errorlog` | lines in the ASE errorlog matching an error pattern within a time window | SAP ASE (Sybase) Errorlog | CRIT from the first error |

Temporary databases (`tempdb`, `saptempdb`, …) get no backup service. How to
change thresholds and states: see
[Configuration in the Checkmk GUI](#configuration-in-the-checkmk-gui).

## Installation

### 1. Checkmk server

Two options; pick one. Both work on the Raw edition.

#### Option 1 — install the .mkp

```bash
wget https://github.com/sebfeldm/checkmk/releases/download/check_sybase-v1.0.1/check_sybase-1.0.1.mkp
mkp install check_sybase-1.0.1.mkp
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

ln -s ~/git/checkmk/agent_plugins/check_sybase \
      ~/local/lib/python3/cmk_addons/plugins/check_sybase
```

Optional, so the agent files are also offered under **Setup → Agents →
Linux** like with the .mkp:

```bash
mkdir -p ~/local/share/check_mk/agents/plugins ~/local/share/check_mk/agents/cfg_examples
ln -s ~/git/checkmk/agent_plugins/check_sybase/agents/plugins/check_sybase \
      ~/local/share/check_mk/agents/plugins/check_sybase
ln -s ~/git/checkmk/agent_plugins/check_sybase/agents/cfg_examples/check_sybase.cfg \
      ~/local/share/check_mk/agents/cfg_examples/check_sybase.cfg
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
wget -O /usr/lib/check_mk_agent/plugins/300/check_sybase \
    https://raw.githubusercontent.com/sebfeldm/checkmk/main/agent_plugins/check_sybase/agents/plugins/check_sybase
chmod 0755 /usr/lib/check_mk_agent/plugins/300/check_sybase

# Example config, first install only: don't overwrite an existing config
# with your credentials on updates
[ -e /etc/check_mk/check_sybase.cfg ] || {
    wget -O /etc/check_mk/check_sybase.cfg \
        https://raw.githubusercontent.com/sebfeldm/checkmk/main/agent_plugins/check_sybase/agents/cfg_examples/check_sybase.cfg
    chown root:root /etc/check_mk/check_sybase.cfg
    chmod 0600 /etc/check_mk/check_sybase.cfg
}
```

`main` is always the latest version. To pin a released version, replace
`main` in the URLs with the release tag, e.g. `check_sybase-v1.0.1`.

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

## Configuration in the Checkmk GUI

Everything is configured with rules; without any rule the defaults from the
[services table](#services) apply. After creating or changing rules, click
**Activate on selected sites** (yellow button at the top right) — until
then nothing changes.

### Finding the rules

- **Via a service (easiest):** open the host's service list, click the menu
  icon (☰) of e.g. `SYBASE ABC ABC Data` → **Parameters for this service**.
  The page shows the rule set that applies (*SAP ASE (Sybase) Database Data
  Usage*) and the current effective values. Click the rule set name to
  create a rule for exactly this service.
- **Via the menu:** **Setup → Services → Service monitoring rules**, type
  `SAP ASE` into the search field. There are five rule sets:
  - *SAP ASE (Sybase) Instance*
  - *SAP ASE (Sybase) Database Data Usage*
  - *SAP ASE (Sybase) Database Log Usage*
  - *SAP ASE (Sybase) Database Backup*
  - *SAP ASE (Sybase) Errorlog*
- The rule for which databases get a backup service is under
  **Setup → Services → Discovery rules**, search `SAP ASE`:
  *SAP ASE (Sybase) Database Backup Discovery*.

### Creating a rule

In the rule set, click **Add rule**, then:

1. **Value:** tick the options you want to change and enter the values.
   Options you don't tick keep their default.
2. **Conditions:**
   - **Explicit hosts:** the host(s) the rule applies to. Leave empty for
     all hosts (or use a folder / host tags).
   - **Instance and database** (or **Instance** for the instance and
     errorlog rules): tick *Specify explicit values* and enter which
     services the rule applies to. Leave it unticked for all instances /
     databases of the selected hosts.
3. **Save**, then activate the changes.

The *Instance and database* values are matched as regular expressions
against the **beginning** of the item `<SID> <DB>` (the service name without
`SYBASE` and the type):

| Value | Matches |
|---|---|
| `ABC ` | all databases of instance ABC |
| `ABC ABC$` | only database ABC of instance ABC |
| `ABC (master\|model)$` | master and model of instance ABC |
| `.* saptools$` | saptools in every instance |

Without `$` at the end, the value also matches longer names (`ABC sap`
matches `saptools` and `saptempdb`).

If several rules match a service, the first matching rule wins per option
— rules higher up in the list (and in subfolders) take precedence. So put
specific exceptions above general rules.

### Examples

**Other data levels for all SAP ASE databases:**
rule *SAP ASE (Sybase) Database Data Usage*, *Used space* = fixed levels
85 % / 92 %, no conditions except maybe a folder.

**Exception for one large database on one host:**
rule *SAP ASE (Sybase) Database Data Usage*, *Used space* = 97 % / 98 %,
*Free space* = 50 GiB / 20 GiB, explicit host `<host>`, *Instance and
database* = `ABC ABC$`. Place it above the general rule.

**Daily backups at a different interval:**
rule *SAP ASE (Sybase) Database Backup*, *Age of the last backup* =
2 days / 3 days, e.g. for all databases of instance `ABC `.

**Don't alert on a briefly set failure flag:**
SAP ASE may set `LastBackupFailed` only temporarily, e.g. after a
transaction log dump that isn't possible for databases whose log shares the
data device (`master`, `model`, `sybsystemdb`, `sybsystemprocs`, …). Rule
*SAP ASE (Sybase) Database Backup*, *Tolerate a failed backup for* = e.g.
1 hour: the service only goes CRIT once the flag has been set continuously
for an hour; before that it stays OK and shows since when the flag is set.
Without conditions this applies to all databases; to limit it, set
*Instance and database* = `.* (master|model|sybsystemdb|sybsystemprocs)$`.

**Ignore the failure flag completely for some databases:**
same rule, *State if the last backup failed* = OK, *Instance and database*
as above. The age of the last backup is still checked.

**Backupserver not needed on a host:**
rule *SAP ASE (Sybase) Instance*, *State if the backupserver is not
running* = OK, explicit host `<host>`.

**No backup service for additional databases:**
rule *SAP ASE (Sybase) Database Backup Discovery*, add e.g. `saptools` to
*Databases without backup service*. A rule replaces the default, so also
add `(sap)?tempdb\d*` if temporary databases should stay excluded. Then run
a service discovery on the affected hosts (**Setup → Hosts →** host →
**Run service discovery**) and remove the vanished services.

### What isn't configured in the GUI

Connection settings (user, password, OS user, timeout) and the errorlog
settings (path, time window, search pattern) belong to the agent plug-in and
are set in `/etc/check_mk/check_sybase.cfg` on each database host, see the
[example config](agents/cfg_examples/check_sybase.cfg). The GUI only decides
which states result from the collected data.

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
stdin, set `password_via=argv` (password via `-P`, visible in the process
list while isql runs).

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
