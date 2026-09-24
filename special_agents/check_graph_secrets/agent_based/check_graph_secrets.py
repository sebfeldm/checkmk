#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4; max-line-length: 100 -*-

####################################################################################################
# CHECKMK CHECK PLUG-IN: Microsoft Graph App Secrets
#
# Generates one Checkmk service per Microsoft Entra app registration that has at least one
# client secret (passwordCredentials). The service reports the remaining validity of the
# secret that expires next.
# This file is part of the "check_graph_secrets" special agent.
####################################################################################################

# Example data from special agent (formatted):
# <<<check_graph_secrets:sep(0)>>>
# [
#   {
#     "app_name": "App Registration 1",
#     "app_appid": "00000000-0000-0000-0000-000000000000",
#     "app_id": "00000000-0000-0000-0000-000000000000",
#     "app_notes": "Description of App Registration 1",
#     "secrets": [
#       {
#         "secret_id": "00000000-0000-0000-0000-000000000000",
#         "secret_name": "Secret Name 1",
#         "secret_expiration": "2026-12-31T00:00:00Z"
#       }
#     ]
#   }
# ]

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict

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


class AppSecret(TypedDict):
    secret_id: str
    secret_name: str | None
    secret_expiration: str


@dataclass(frozen=True)
class AppRegistration:
    app_name: str
    app_appid: str
    app_id: str
    app_notes: str | None
    secrets: list[AppSecret]


Section = Mapping[str, AppRegistration]


def parse_check_graph_secrets(string_table: StringTable) -> Section:
    parsed = {}
    for item in json.loads("".join(string_table[0])):
        parsed[item["app_name"]] = AppRegistration(**item)
    return parsed


def discover_check_graph_secrets(section: Section) -> DiscoveryResult:
    for app_name in section:
        yield Service(item=app_name)


def check_check_graph_secrets(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    app = section.get(item)
    if not app:
        return

    params_secret_exclude_list = params.get("secret_exclude", [])
    compiled_patterns = [re.compile(pattern) for pattern in params_secret_exclude_list]

    result_details_secret_list = []
    secret_earliest_expiration = None
    for secret in app.secrets:
        secret_description = secret["secret_name"] or "(unnamed)"

        secret_expiration_timestamp = datetime.fromisoformat(
            secret["secret_expiration"]
        ).timestamp()

        secret_id = secret["secret_id"]

        # Find the secret with the earliest expiration time among the ones that are not
        # excluded by a Checkmk rule. Its expiration time drives the check result state.
        if not any(pattern.match(secret_description) for pattern in compiled_patterns) and (
            secret_earliest_expiration is None
            or secret_expiration_timestamp < secret_earliest_expiration["secret_expiration_timestamp"]
        ):
            secret_earliest_expiration = {
                "secret_expiration_timestamp": secret_expiration_timestamp,
                "secret_id": secret_id,
                "secret_description": secret_description,
            }

        secret_details_list = [
            f"Secret ID: {secret_id}",
            f" - Description: {secret_description}",
            f" - Expiration time: {render.datetime(secret_expiration_timestamp)}",
        ]
        result_details_secret_list.append("\n".join(secret_details_list))

    app_details_list = [
        f"App name: {app.app_name}",
        f"App ID: {app.app_appid}",
        f"Object ID: {app.app_id}",
        "",
        f"Description: {app.app_notes or '(not available)'}",
    ]
    result_details = "\n".join(app_details_list) + "\n\n" + "\n\n".join(result_details_secret_list)

    if secret_earliest_expiration is not None:
        secret_earliest_expiration_description = secret_earliest_expiration["secret_description"]
        secret_earliest_expiration_timestamp = secret_earliest_expiration["secret_expiration_timestamp"]

        secret_expiration_timespan = secret_earliest_expiration_timestamp - datetime.now().timestamp()

        result_summary = f"Expiration time: {render.datetime(secret_earliest_expiration_timestamp)}"
        result_summary += f", Description: {secret_earliest_expiration_description}"

        params_secret_expiration_levels = params["secret_expiration"]

        if secret_expiration_timespan > 0:
            yield from check_levels(
                secret_expiration_timespan,
                levels_lower=(params_secret_expiration_levels),
                metric_name="check_graph_secrets_remaining_validity",
                label="Remaining",
                render_func=render.timespan,
            )
        else:
            yield from check_levels(
                secret_expiration_timespan,
                levels_lower=(params_secret_expiration_levels),
                label="Expired",
                render_func=lambda x: f"{render.timespan(abs(x))} ago",
            )

            # Avoid a negative value for the metric.
            yield Metric(
                name="check_graph_secrets_remaining_validity",
                value=0.0,
                levels=params_secret_expiration_levels[1],
            )
    else:
        result_summary = "All secrets are excluded"

    yield Result(
        state=State.OK,
        summary=result_summary,
        details=f"\n{result_details}",
    )


agent_section_check_graph_secrets = AgentSection(
    name="check_graph_secrets",
    parse_function=parse_check_graph_secrets,
)


check_plugin_check_graph_secrets = CheckPlugin(
    name="check_graph_secrets",
    service_name="Graph Secret %s",
    discovery_function=discover_check_graph_secrets,
    check_function=check_check_graph_secrets,
    check_ruleset_name="check_graph_secrets_params",
    check_default_parameters={"secret_expiration": ("fixed", (2592000.0, 1209600.0))},
)
