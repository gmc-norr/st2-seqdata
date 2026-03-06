from st2common.runners.base_action import Action


class GetFileDestinationAction(Action):
    def run(self, type, platform):
        config_destination = f"{type}_destinations"
        for d in self.config.get(config_destination, []):
            if d.get("platform") == platform:
                return d.get("path")
        return None
