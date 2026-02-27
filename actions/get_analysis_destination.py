from st2common.runners.base_action import Action

class GetAnalysisDestinationAction(Action):
    def run(self, platform):
        for d in self.config.get("analysis_destinations", []):
            if d.get("platform") == platform:
                return d.get("path")
        return None
