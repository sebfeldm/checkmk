#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4; max-line-length: 100 -*-

####################################################################################################
# CHECKMK SPECIAL AGENT CALL: Microsoft Graph App Secrets
#
# Builds the special agent command-line arguments from the parameters configured in the
# "check_graph_secrets" special agent ruleset.
####################################################################################################

from collections.abc import Iterator

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    NoProxy,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    URLProxy,
)


class Params(BaseModel):
    tenant_id: str
    app_id: str
    app_secret: Secret
    proxy: URLProxy | NoProxy | EnvProxy | None = None
    timeout: float = 10.0


def _generate_special_agent_commands(
    params: Params,
    _host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--tenant-id",
        params.tenant_id,
        "--app-id",
        params.app_id,
        "--app-secret",
        params.app_secret,
        "--timeout",
        str(params.timeout),
    ]

    if params.proxy:
        match params.proxy:
            case URLProxy(url=url):
                args += ["--proxy", url]
            case EnvProxy():
                args += ["--proxy", "FROM_ENVIRONMENT"]
            case NoProxy():
                args += ["--proxy", "NO_PROXY"]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_check_graph_secrets = SpecialAgentConfig(
    name="check_graph_secrets",
    parameter_parser=Params.model_validate,
    commands_function=_generate_special_agent_commands,
)
