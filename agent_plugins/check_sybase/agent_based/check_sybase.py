#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4; max-line-length: 100 -*-

####################################################################################################
# CHECKMK CHECK PLUG-IN: SAP ASE (Sybase) Databases
#
# Evaluates the data of the "check_sybase" agent plug-in. Per ASE instance (SID) it creates an
# instance service (connection, dataserver, backupserver) and an errorlog service, per database
# a data, a log (only with a dedicated log segment) and a backup service.
# This file is part of the "check_sybase" agent plug-in.
####################################################################################################

# Example data from agent plug-in:
# <<<check_sybase:sep(59)>>>
# instance;ABC;dataserver;1
# instance;ABC;backupserver;1
# instance;ABC;connect;0;OK
# db;ABC;ABC;102400.00;81920.00;20480.00;18432.00;1739260800;0
# db;ABC;master;200.00;60.00;0.00;0.00;1739260800;0
# db;ABC;saptempdb;4096.00;12.00;0.00;0.00;;0
# errorlog;ABC;ok;24;1;/sybase/ABC/ASE-16_0/install/ABC.log
# errorlog_line;ABC;2025/02/11 10:15:32;Error: 1105, Severity: 17, State: 4

import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

MIB = 1024 * 1024


@dataclass
class Database:
    data_size: float | None
    data_used: float | None
    log_size: float | None
    log_free: float | None
    backup_time: float | None
    backup_failed: int | None


@dataclass
class Errorlog:
    status: str
    window: str
    count: int
    path: str
    lines: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Instance:
    connect_rc: int | None = None
    connect_message: str = ""
    dataserver: bool | None = None
    backupserver: bool | None = None
    databases: dict[str, Database] = field(default_factory=dict)
    errorlog: Errorlog | None = None


Section = Mapping[str, Instance]


def _float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def parse_check_sybase(string_table: StringTable) -> Section:
    parsed: dict[str, Instance] = {}
    for line in string_table:
        if len(line) < 3:
            continue
        kind, sid = line[0], line[1]
        instance = parsed.setdefault(sid, Instance())

        if kind == "instance" and len(line) >= 4:
            if line[2] == "connect":
                instance.connect_rc = _int(line[3])
                instance.connect_message = ";".join(line[4:])
            elif line[2] == "dataserver":
                instance.dataserver = line[3] == "1"
            elif line[2] == "backupserver":
                instance.backupserver = line[3] == "1"

        elif kind == "db" and len(line) >= 9:
            instance.databases[line[2]] = Database(
                data_size=_float(line[3]),
                data_used=_float(line[4]),
                log_size=_float(line[5]),
                log_free=_float(line[6]),
                backup_time=_float(line[7]),
                backup_failed=_int(line[8]),
            )

        elif kind == "errorlog" and len(line) >= 6:
            instance.errorlog = Errorlog(
                status=line[2],
                window=line[3],
                count=_int(line[4]) or 0,
                path=";".join(line[5:]),
            )

        elif kind == "errorlog_line" and len(line) >= 4 and instance.errorlog is not None:
            instance.errorlog.lines.append((line[2], ";".join(line[3:])))

    return parsed


def _split_item(item: str) -> tuple[str, str]:
    sid, _, db_name = item.partition(" ")
    return sid, db_name


def _get_database(item: str, section: Section) -> tuple[Result | None, Database | None]:
    """Returns either a result explaining why there is no data, or the database."""
    sid, db_name = _split_item(item)
    instance = section.get(sid)
    if instance is None:
        return None, None
    if instance.connect_rc != 0:
        return (
            Result(state=State.UNKNOWN, summary="No data: connection to the instance failed"),
            None,
        )
    return None, instance.databases.get(db_name)


####################################################################################################
# Instance
####################################################################################################


def discover_check_sybase_instance(section: Section) -> DiscoveryResult:
    for sid in section:
        yield Service(item=sid)


def check_check_sybase_instance(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    instance = section.get(item)
    if instance is None:
        return

    if instance.connect_rc == 0:
        yield Result(state=State.OK, summary="Connected")
    else:
        yield Result(
            state=State(params["state_connect_failed"]),
            summary=f"Connection failed: {instance.connect_message or 'unknown error'}",
        )

    if instance.dataserver:
        yield Result(state=State.OK, summary="Dataserver running")
    else:
        yield Result(state=State(params["state_dataserver"]), summary="Dataserver not running")

    if instance.backupserver:
        yield Result(state=State.OK, summary="Backupserver running")
    else:
        yield Result(
            state=State(params["state_backupserver"]), summary="Backupserver not running"
        )

    if instance.connect_rc == 0:
        yield Result(state=State.OK, summary=f"Databases: {len(instance.databases)}")


####################################################################################################
# Data and log usage
####################################################################################################


def _check_usage(
    size_mb: float | None,
    used_mb: float | None,
    params: Mapping[str, Any],
    metric_prefix: str,
) -> CheckResult:
    if size_mb is None or used_mb is None:
        yield Result(state=State.UNKNOWN, summary="No size information available")
        return
    if size_mb <= 0:
        yield Result(state=State.UNKNOWN, summary="Size is 0 MB")
        return

    size = size_mb * MIB
    used = used_mb * MIB
    free = size - used

    yield from check_levels(
        100.0 * used / size,
        levels_upper=params["used_percent"],
        metric_name=f"{metric_prefix}_used_percent",
        render_func=render.percent,
        label="Used",
        boundaries=(0.0, 100.0),
    )
    yield Result(state=State.OK, summary=f"{render.bytes(used)} of {render.bytes(size)}")
    yield from check_levels(
        free,
        levels_lower=params.get("free", ("no_levels", None)),
        metric_name=f"{metric_prefix}_free",
        render_func=render.bytes,
        label="Free",
    )
    yield Metric(f"{metric_prefix}_used", used, boundaries=(0.0, size))
    yield Metric(f"{metric_prefix}_size", size)


def discover_check_sybase_data(section: Section) -> DiscoveryResult:
    for sid, instance in section.items():
        for db_name, database in instance.databases.items():
            if database.data_size:
                yield Service(item=f"{sid} {db_name}")


def check_check_sybase_data(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    error, database = _get_database(item, section)
    if error:
        yield error
    if database is None:
        return
    yield from _check_usage(database.data_size, database.data_used, params, "sybase_data")


def discover_check_sybase_log(section: Section) -> DiscoveryResult:
    # Only databases with a dedicated log segment. With data and log on the same device, the
    # log is part of the data usage.
    for sid, instance in section.items():
        for db_name, database in instance.databases.items():
            if database.log_size:
                yield Service(item=f"{sid} {db_name}")


def check_check_sybase_log(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    error, database = _get_database(item, section)
    if error:
        yield error
    if database is None:
        return
    log_used = (
        None
        if database.log_size is None or database.log_free is None
        else database.log_size - database.log_free
    )
    yield from _check_usage(database.log_size, log_used, params, "sybase_log")


####################################################################################################
# Backup
####################################################################################################


def discover_check_sybase_backup(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    patterns = [re.compile(pattern) for pattern in params.get("exclude", [])]
    for sid, instance in section.items():
        for db_name in instance.databases:
            if not any(pattern.fullmatch(db_name) for pattern in patterns):
                yield Service(item=f"{sid} {db_name}")


def check_check_sybase_backup(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    error, database = _get_database(item, section)
    if error:
        yield error
    if database is None:
        return

    if database.backup_failed:
        yield Result(state=State(params["state_failed"]), summary="Last backup failed")

    if database.backup_time is None:
        yield Result(state=State(params["state_never"]), summary="No backup found")
        return

    age = time.time() - database.backup_time
    yield Result(state=State.OK, summary=f"Last backup: {render.datetime(database.backup_time)}")
    yield from check_levels(
        max(age, 0.0),
        levels_upper=params["age"],
        metric_name="sybase_backup_age",
        render_func=render.timespan,
        label="Age",
    )


####################################################################################################
# Errorlog
####################################################################################################


def discover_check_sybase_errorlog(section: Section) -> DiscoveryResult:
    for sid, instance in section.items():
        if instance.errorlog is not None:
            yield Service(item=sid)


def check_check_sybase_errorlog(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    instance = section.get(item)
    if instance is None or instance.errorlog is None:
        return
    errorlog = instance.errorlog

    if errorlog.status != "ok":
        yield Result(
            state=State(params["state_missing"]),
            summary=f"Errorlog not readable: {errorlog.path}",
        )
        return

    yield from check_levels(
        errorlog.count,
        levels_upper=params["errors"],
        metric_name="sybase_errorlog_errors",
        render_func=lambda v: str(int(v)),
        label=f"Errors in the last {errorlog.window} hours",
    )

    if errorlog.lines:
        yield Result(state=State.OK, summary=f"Latest: {errorlog.lines[-1][1]}")
        shown = len(errorlog.lines)
        header = f"Latest {shown} of {errorlog.count} matching lines in {errorlog.path}:"
        yield Result(
            state=State.OK,
            notice="\n".join([header] + [f"{ts}  {msg}" for ts, msg in reversed(errorlog.lines)]),
        )


####################################################################################################
# Registration
####################################################################################################

agent_section_check_sybase = AgentSection(
    name="check_sybase",
    parse_function=parse_check_sybase,
)


check_plugin_check_sybase_instance = CheckPlugin(
    name="check_sybase_instance",
    sections=["check_sybase"],
    service_name="Sybase Instance %s",
    discovery_function=discover_check_sybase_instance,
    check_function=check_check_sybase_instance,
    check_ruleset_name="check_sybase_instance",
    check_default_parameters={
        "state_connect_failed": 2,
        "state_dataserver": 2,
        "state_backupserver": 2,
    },
)


check_plugin_check_sybase_data = CheckPlugin(
    name="check_sybase_data",
    sections=["check_sybase"],
    service_name="Sybase Data %s",
    discovery_function=discover_check_sybase_data,
    check_function=check_check_sybase_data,
    check_ruleset_name="check_sybase_data",
    check_default_parameters={"used_percent": ("fixed", (90.0, 95.0))},
)


check_plugin_check_sybase_log = CheckPlugin(
    name="check_sybase_log",
    sections=["check_sybase"],
    service_name="Sybase Log %s",
    discovery_function=discover_check_sybase_log,
    check_function=check_check_sybase_log,
    check_ruleset_name="check_sybase_log",
    check_default_parameters={"used_percent": ("fixed", (80.0, 90.0))},
)


check_plugin_check_sybase_backup = CheckPlugin(
    name="check_sybase_backup",
    sections=["check_sybase"],
    service_name="Sybase Backup %s",
    discovery_function=discover_check_sybase_backup,
    discovery_ruleset_name="check_sybase_backup_discovery",
    discovery_default_parameters={"exclude": [r"(sap)?tempdb\d*"]},
    check_function=check_check_sybase_backup,
    check_ruleset_name="check_sybase_backup",
    check_default_parameters={
        "age": ("fixed", (26 * 3600.0, 50 * 3600.0)),
        "state_failed": 2,
        "state_never": 1,
    },
)


check_plugin_check_sybase_errorlog = CheckPlugin(
    name="check_sybase_errorlog",
    sections=["check_sybase"],
    service_name="Sybase Errorlog %s",
    discovery_function=discover_check_sybase_errorlog,
    check_function=check_check_sybase_errorlog,
    check_ruleset_name="check_sybase_errorlog",
    check_default_parameters={
        "errors": ("fixed", (1, 1)),
        "state_missing": 1,
    },
)
