#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4; max-line-length: 100 -*-

####################################################################################################
# CHECKMK RULESET: Microsoft Graph App Secrets (special agent)
#
# Parameter definitions for the "check_graph_secrets" special agent, which retrieves the
# expiration dates of Microsoft Entra app registration client secrets via the Microsoft
# Graph API.
####################################################################################################

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    Password,
    Proxy,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, MatchRegex, NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

_GUID_REGEX = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


def _parameter_form_check_graph_secrets() -> Dictionary:
    return Dictionary(
        title=Title("Microsoft Graph app secrets"),
        help_text=Help(
            "This special agent retrieves the expiration dates of client secrets "
            "(<b>passwordCredentials</b>) of Microsoft Entra app registrations using the "
            "<b>Microsoft Graph API</b>.<br>To monitor a tenant, apply this rule to a "
            "<b>single host</b>.<br>You must create a dedicated Microsoft Entra app "
            "registration for this agent and grant it the application permission "
            "<tt>Application.Read.All</tt> with admin consent."
        ),
        elements={
            "tenant_id": DictElement(
                parameter_form=String(
                    title=Title("Tenant ID / directory ID"),
                    help_text=Help(
                        "The unique ID of the Microsoft Entra tenant to monitor.<br>You can find "
                        "this ID on the <b>Overview</b> page of the app registration."
                    ),
                    field_size=FieldSize.LARGE,
                    custom_validate=[
                        MatchRegex(
                            regex=_GUID_REGEX,
                            error_msg=Message(
                                "The <b>Tenant ID / directory ID</b> must be in 36-character GUID "
                                "format (e.g., <tt>123e4567-e89b-12d3-a456-426614174000</tt>)."
                            ),
                        ),
                        LengthInRange(
                            min_value=36,
                            error_msg=Message(
                                "The <b>Tenant ID / directory ID</b> must be in 36-character GUID "
                                "format (e.g., <tt>123e4567-e89b-12d3-a456-426614174000</tt>)."
                            ),
                        ),
                    ],
                ),
                required=True,
            ),
            "app_id": DictElement(
                parameter_form=String(
                    title=Title("Client ID / application ID"),
                    help_text=Help(
                        "The application (client) ID of the app registration that this special "
                        "agent uses to query the Microsoft Graph API."
                    ),
                    field_size=FieldSize.LARGE,
                    custom_validate=[
                        MatchRegex(
                            regex=_GUID_REGEX,
                            error_msg=Message(
                                "The <b>Client ID / application ID</b> must be in 36-character "
                                "GUID format (e.g., <tt>123e4567-e89b-12d3-a456-426614174000</tt>)."
                            ),
                        ),
                        LengthInRange(
                            min_value=36,
                            error_msg=Message(
                                "The <b>Client ID / application ID</b> must be in 36-character "
                                "GUID format (e.g., <tt>123e4567-e89b-12d3-a456-426614174000</tt>)."
                            ),
                        ),
                    ],
                ),
                required=True,
            ),
            "app_secret": DictElement(
                parameter_form=Password(
                    title=Title("Client secret"),
                    help_text=Help(
                        "The client secret value of the app registration used to authenticate "
                        "this special agent against the Microsoft Graph API.<br><b>Note:</b> "
                        "this secret itself will also show up as a monitored service once "
                        "discovered, so you can track its own expiration too."
                    ),
                ),
                required=True,
            ),
            "proxy": DictElement(
                parameter_form=Proxy(
                    title=Title("HTTP proxy"),
                    help_text=Help(
                        "Configure HTTP proxy settings for the API connections.<br><br>"
                        "If not configured, the system environment proxy settings will be used."
                    ),
                ),
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("API request timeout"),
                    help_text=Help(
                        "Timeout (in seconds) for each API request, including the token "
                        "request.<br>If not specified, the default timeout is <b>10 seconds</b>."
                    ),
                    displayed_magnitudes=[TimeMagnitude.SECOND],
                    custom_validate=[
                        NumberInRange(
                            min_value=3,
                            max_value=600,
                            error_msg=Message(
                                "The <b>API request timeout</b> must be between 3s and 600s."
                            ),
                        ),
                    ],
                    prefill=DefaultValue(10.0),
                ),
            ),
        },
    )


rule_spec_check_graph_secrets = SpecialAgent(
    name="check_graph_secrets",
    title=Title("Microsoft Graph app secrets"),
    parameter_form=_parameter_form_check_graph_secrets,
    topic=Topic.CLOUD,
)
