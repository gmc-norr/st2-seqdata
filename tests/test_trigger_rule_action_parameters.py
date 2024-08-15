import re
import unittest
import pathlib
import yaml


class TestTriggerRuleActionParameters(unittest.TestCase):

    def setUp(self):
        """Collect trigger, rule and action parameters."""
        self.triggers = {}
        self.rules = {}
        self.actions = {}

        sensordir = pathlib.Path("sensors")
        rulesdir = pathlib.Path("rules")
        actionsdir = pathlib.Path("actions")

        trigger_param_re = re.compile(r"{{\s*trigger\.([\w]+)\s*\|?.*}}")

        for sensorconfig in sensordir.glob("*.yaml"):
            sensor = yaml.safe_load(sensorconfig.read_text())
            for trigger in sensor.get("trigger_types", []):
                trigger_id = f"{trigger.get('pack')}.{trigger.get('name')}"
                trigger_params = list(trigger.get("payload_schema", {})
                                      .get("properties", {})
                                      .keys())
                self.triggers[trigger_id] = trigger_params

        for ruleconfig in rulesdir.glob("*.yaml"):
            rule = yaml.safe_load(ruleconfig.read_text())
            rule_id = f"{rule.get('pack')}.{rule.get('name')}"
            trigger_id = rule.get("trigger", {}).get("type")
            if trigger_id is None:
                continue
            self.rules[rule_id] = {
                "trigger": trigger_id,
                "action": rule.get("action", {}).get("ref"),
                "params": {},
            }
            for action_param, trigger_param in rule.get("action", {})\
                    .get("parameters", {}).items():
                m = trigger_param_re.search(trigger_param)
                if m is None:
                    continue
                self.rules[rule_id]["params"][action_param] = m.group(1)

        for actionconfig in actionsdir.glob("*.yaml"):
            action = yaml.safe_load(actionconfig.read_text())
            action_name = action.get('name')
            self.actions[action_name] = []
            for param in action.get("parameters", {}).keys():
                self.actions[action_name].append(param)

    def test_trigger_rule_action_parameters(self):
        for rule_id, values in self.rules.items():
            trigger_id = values["trigger"]
            action_id = values["action"]
            action_name = ".".join(action_id.split(".")[1:])
            rule_params = values["params"]

            for action_param, trigger_param in rule_params.items():
                if trigger_id not in self.triggers:
                    # Trigger is not defined in this package
                    continue

                self.assertIn(
                    trigger_param,
                    self.triggers[trigger_id],
                    msg=f'rule "{rule_id}": parameter "{trigger_param}" not '
                        f'in trigger payload for "{trigger_id}"',
                )

                if action_name not in self.actions:
                    # Action is not defined in this package
                    continue

                self.assertIn(
                    action_param,
                    self.actions[action_name],
                    msg=f'rule "{rule_id}": parameter "{action_param}" not '
                        f'accepted by action "{action_name}"',
                )
