from cleve_service import Cleve
from st2common.runners.base_action import Action
from typing import Any, Dict


class UpdateSampleSheet(Action):

    def __init__(self, config, action_service):
        super().__init__(config, action_service)
        if "cleve_service" in self.config:
            self.cleve = self.config.get("cleve_service")
        else:
            self.cleve = Cleve(
                config.get("cleve").get("host"),
                config.get("cleve").get("port"),
                config.get("cleve").get("api_key"),
            )

    def run(self, run_id: str, samplesheet: str) -> Dict[str, Any]:
        return self.cleve.update_samplesheet(
            run_id=run_id,
            samplesheet=samplesheet,
        )
