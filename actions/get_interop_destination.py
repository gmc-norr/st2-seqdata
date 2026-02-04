from st2common.runners.base_action import Action

class GetInteropDestinationAction(Action):
    def run(self, platform):
        for d in self.config.get("interop_destinations", []):
            if d.get("platform") == platform:
                return d.get("path")
        return None
