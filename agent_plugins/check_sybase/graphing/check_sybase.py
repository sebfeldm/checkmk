#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4; max-line-length: 100 -*-

####################################################################################################
# CHECKMK GRAPHING: SAP ASE (Sybase) Databases
#
# Metrics, graphs and perfometers of the "check_sybase_*" check plug-ins.
# This file is part of the "check_sybase" agent plug-in.
####################################################################################################

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENT = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(0))

metric_sybase_data_used_percent = metrics.Metric(
    name="sybase_data_used_percent",
    title=Title("Data used"),
    unit=UNIT_PERCENT,
    color=metrics.Color.BLUE,
)
metric_sybase_data_used = metrics.Metric(
    name="sybase_data_used",
    title=Title("Data used"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_sybase_data_free = metrics.Metric(
    name="sybase_data_free",
    title=Title("Data free"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_sybase_data_size = metrics.Metric(
    name="sybase_data_size",
    title=Title("Data size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)

metric_sybase_log_used_percent = metrics.Metric(
    name="sybase_log_used_percent",
    title=Title("Log used"),
    unit=UNIT_PERCENT,
    color=metrics.Color.PURPLE,
)
metric_sybase_log_used = metrics.Metric(
    name="sybase_log_used",
    title=Title("Log used"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_sybase_log_free = metrics.Metric(
    name="sybase_log_free",
    title=Title("Log free"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_sybase_log_size = metrics.Metric(
    name="sybase_log_size",
    title=Title("Log size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)

metric_sybase_backup_age = metrics.Metric(
    name="sybase_backup_age",
    title=Title("Age of the last backup"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)

metric_sybase_errorlog_errors = metrics.Metric(
    name="sybase_errorlog_errors",
    title=Title("Errorlog errors"),
    unit=UNIT_COUNT,
    color=metrics.Color.RED,
)


graph_sybase_data_usage = graphs.Graph(
    name="sybase_data_usage",
    title=Title("Data usage"),
    compound_lines=["sybase_data_used", "sybase_data_free"],
    simple_lines=["sybase_data_size"],
)

graph_sybase_log_usage = graphs.Graph(
    name="sybase_log_usage",
    title=Title("Log usage"),
    compound_lines=["sybase_log_used", "sybase_log_free"],
    simple_lines=["sybase_log_size"],
)


perfometer_sybase_data_used_percent = perfometers.Perfometer(
    name="sybase_data_used_percent",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["sybase_data_used_percent"],
)

perfometer_sybase_log_used_percent = perfometers.Perfometer(
    name="sybase_log_used_percent",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["sybase_log_used_percent"],
)

perfometer_sybase_backup_age = perfometers.Perfometer(
    name="sybase_backup_age",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(2 * 86400)),
    segments=["sybase_backup_age"],
)

perfometer_sybase_errorlog_errors = perfometers.Perfometer(
    name="sybase_errorlog_errors",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(10)),
    segments=["sybase_errorlog_errors"],
)
