#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4; max-line-length: 100 -*-

####################################################################################################
# CHECKMK RULESETS: SAP ASE (Sybase) Databases (check plug-ins)
#
# Parameter definitions for the "check_sybase_*" check plug-ins and the discovery of the backup
# services. The checks are part of the "check_sybase" agent plug-in.
####################################################################################################

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    List,
    MatchingScope,
    Percentage,
    RegularExpression,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)

_HELP_AGENT = (
    "<br>To use this service, install the <b>check_sybase</b> agent plug-in on the monitored host."
)


def _state(title: Title, help_text: Help, default: int) -> DictElement:
    return DictElement(
        parameter_form=ServiceState(
            title=title,
            help_text=help_text,
            prefill=DefaultValue(default),
        ),
        required=True,
    )


####################################################################################################
# Instance
####################################################################################################


def _parameter_form_check_sybase_instance() -> Dictionary:
    return Dictionary(
        title=Title("Check parameters"),
        help_text=Help(
            "States of the SAP ASE instance service: connection via isql, dataserver and "
            "backupserver process." + _HELP_AGENT
        ),
        elements={
            "state_connect_failed": _state(
                Title("State if the connection fails"),
                Help("State if isql cannot connect or does not return any database."),
                ServiceState.CRIT,
            ),
            "state_dataserver": _state(
                Title("State if the dataserver is not running"),
                Help("State if no dataserver process of the instance's OS user is found."),
                ServiceState.CRIT,
            ),
            "state_backupserver": _state(
                Title("State if the backupserver is not running"),
                Help("State if no backupserver process of the instance's OS user is found."),
                ServiceState.CRIT,
            ),
        },
    )


rule_spec_check_sybase_instance = CheckParameters(
    name="check_sybase_instance",
    title=Title("SAP ASE (Sybase) Instance"),
    parameter_form=_parameter_form_check_sybase_instance,
    topic=Topic.DATABASES,
    condition=HostAndItemCondition(item_title=Title("Instance (SID)")),
)


####################################################################################################
# Data and log usage
####################################################################################################


def _usage_form(what: str, warn: float, crit: float) -> Dictionary:
    return Dictionary(
        title=Title("Check parameters"),
        help_text=(
            Help("Levels for the usage of the %s segments of SAP ASE databases." + _HELP_AGENT)
            % what
        ),
        elements={
            "used_percent": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Used space"),
                    help_text=Help(
                        "Upper levels for the used space in percent of the total size."
                    ),
                    form_spec_template=Percentage(custom_validate=(NumberInRange(min_value=0, max_value=100),)),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(warn, crit)),
                ),
                required=True,
            ),
            "free": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Free space"),
                    help_text=Help(
                        "Lower levels for the absolute free space. Useful for large "
                        "databases, where a few percent are still a lot of space."
                    ),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[IECMagnitude.MEBI, IECMagnitude.GIBI],
                    ),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint(value=(10 * 1024**3, 5 * 1024**3)),
                ),
            ),
        },
    )


def _parameter_form_check_sybase_data() -> Dictionary:
    return _usage_form("data", 90.0, 95.0)


def _parameter_form_check_sybase_log() -> Dictionary:
    return _usage_form("log", 80.0, 90.0)


rule_spec_check_sybase_data = CheckParameters(
    name="check_sybase_data",
    title=Title("SAP ASE (Sybase) Database Data Usage"),
    parameter_form=_parameter_form_check_sybase_data,
    topic=Topic.DATABASES,
    condition=HostAndItemCondition(item_title=Title("Instance and database (SID DB)")),
)


rule_spec_check_sybase_log = CheckParameters(
    name="check_sybase_log",
    title=Title("SAP ASE (Sybase) Database Log Usage"),
    parameter_form=_parameter_form_check_sybase_log,
    topic=Topic.DATABASES,
    condition=HostAndItemCondition(item_title=Title("Instance and database (SID DB)")),
)


####################################################################################################
# Backup
####################################################################################################


def _parameter_form_check_sybase_backup() -> Dictionary:
    return Dictionary(
        title=Title("Check parameters"),
        help_text=Help("Parameters for the last backup of SAP ASE databases." + _HELP_AGENT),
        elements={
            "age": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Age of the last backup"),
                    help_text=Help(
                        "Upper levels for the time since the start of the last database "
                        "backup. The default values are 26 hours (WARN) and 50 hours (CRIT), "
                        "suitable for daily backups."
                    ),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY, TimeMagnitude.HOUR],
                        custom_validate=(NumberInRange(min_value=0),),
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(26 * 3600.0, 50 * 3600.0)),
                ),
                required=True,
            ),
            "state_failed": _state(
                Title("State if the last backup failed"),
                Help("State if SAP ASE reports the last backup of the database as failed."),
                ServiceState.CRIT,
            ),
            "failed_grace": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Tolerate a failed backup for"),
                    help_text=Help(
                        "SAP ASE can set the failure flag of the last backup only briefly, "
                        "for example after a transaction log dump that is not possible for "
                        "databases without a dedicated log segment (master, model, "
                        "sybsystemdb, sybsystemprocs, ...). With this option, the state "
                        "above applies only once the flag has been set continuously for "
                        "this time; before that, the service stays OK and shows since when "
                        "the flag is set.<br>Without this option, the state applies "
                        "immediately."
                    ),
                    displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.MINUTE],
                    custom_validate=(NumberInRange(min_value=0),),
                    prefill=DefaultValue(3600.0),
                ),
            ),
            "state_never": _state(
                Title("State if no backup exists"),
                Help("State if the database has never been backed up."),
                ServiceState.WARN,
            ),
        },
    )


rule_spec_check_sybase_backup = CheckParameters(
    name="check_sybase_backup",
    title=Title("SAP ASE (Sybase) Database Backup"),
    parameter_form=_parameter_form_check_sybase_backup,
    topic=Topic.DATABASES,
    condition=HostAndItemCondition(item_title=Title("Instance and database (SID DB)")),
)


def _parameter_form_check_sybase_backup_discovery() -> Dictionary:
    return Dictionary(
        title=Title("Discovery parameters"),
        elements={
            "exclude": DictElement(
                parameter_form=List[str](
                    title=Title("Databases without backup service"),
                    help_text=Help(
                        "Regular expressions matching database names for which no backup "
                        "service is created, for example temporary databases.<br>Without "
                        "a rule, <tt>(sap)?tempdb\\d*</tt> is excluded (tempdb, saptempdb, "
                        "tempdb2, ...). A rule replaces this default, so add it to the list "
                        "if you still want to exclude the temporary databases."
                    ),
                    element_template=RegularExpression(
                        title=Title("Database name"),
                        predefined_help_text=MatchingScope.FULL,
                        custom_validate=(LengthInRange(min_value=1),),
                    ),
                    editable_order=False,
                ),
                required=True,
            ),
        },
    )


rule_spec_check_sybase_backup_discovery = DiscoveryParameters(
    name="check_sybase_backup_discovery",
    title=Title("SAP ASE (Sybase) Database Backup Discovery"),
    parameter_form=_parameter_form_check_sybase_backup_discovery,
    topic=Topic.DATABASES,
)


####################################################################################################
# Errorlog
####################################################################################################


def _parameter_form_check_sybase_errorlog() -> Dictionary:
    return Dictionary(
        title=Title("Check parameters"),
        help_text=Help(
            "Parameters for the errorlog of SAP ASE instances. The time window and the search "
            "pattern are configured in the agent plug-in configuration (check_sybase.cfg)."
            + _HELP_AGENT
        ),
        elements={
            "errors": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of errors"),
                    help_text=Help(
                        "Upper levels for the number of matching errorlog lines within the "
                        "time window. The default is CRIT from the first error."
                    ),
                    form_spec_template=Integer(custom_validate=(NumberInRange(min_value=0),)),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(1, 1)),
                ),
                required=True,
            ),
            "state_missing": _state(
                Title("State if the errorlog is not readable"),
                Help("State if the errorlog file does not exist or cannot be read."),
                ServiceState.WARN,
            ),
        },
    )


rule_spec_check_sybase_errorlog = CheckParameters(
    name="check_sybase_errorlog",
    title=Title("SAP ASE (Sybase) Errorlog"),
    parameter_form=_parameter_form_check_sybase_errorlog,
    topic=Topic.DATABASES,
    condition=HostAndItemCondition(item_title=Title("Instance (SID)")),
)
