#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4; max-line-length: 100 -*-

####################################################################################################
# CHECKMK RULESET: Microsoft Graph App Secrets (check plug-in)
#
# Parameter definitions for the "check_graph_secrets" check plug-in. The check is part of the
# "check_graph_secrets" special agent.
####################################################################################################

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    List,
    MatchingScope,
    RegularExpression,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_check_graph_secrets_params() -> Dictionary:
    return Dictionary(
        title=Title("Check parameters"),
        help_text=Help(
            "Parameters for the expiration of Microsoft Entra app registration client secrets."
            "<br>To use this service, you need to set up the <b>Microsoft Graph app secrets</b> "
            "special agent."
        ),
        elements={
            "secret_expiration": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Secret expiration"),
                    help_text=Help(
                        "Lower levels for the remaining validity of the app secret that "
                        "expires next.<br>The default values are 30 days (WARN) and 14 days "
                        "(CRIT).<br>To ignore the secret expiration, select 'No levels'."
                    ),
                    form_spec_template=TimeSpan(
                        custom_validate=(NumberInRange(min_value=0),),
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                        ],
                    ),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(2592000.0, 1209600.0)),
                ),
            ),
            "secret_exclude": DictElement(
                parameter_form=List[str](
                    title=Title("Exclude secrets"),
                    help_text=Help(
                        "Specify a list of regular expressions matching secret descriptions "
                        "that you do not want to monitor, for example secrets that are "
                        "rotated automatically by another process."
                    ),
                    element_template=RegularExpression(
                        title=Title("Secret description"),
                        predefined_help_text=MatchingScope.PREFIX,
                        custom_validate=(LengthInRange(min_value=1),),
                    ),
                    editable_order=False,
                ),
            ),
        },
    )


rule_spec_check_graph_secrets_params = CheckParameters(
    name="check_graph_secrets",
    title=Title("Microsoft Graph App Secrets"),
    parameter_form=_parameter_form_check_graph_secrets_params,
    topic=Topic.CLOUD,
    condition=HostAndItemCondition(item_title=Title("Application")),
)
