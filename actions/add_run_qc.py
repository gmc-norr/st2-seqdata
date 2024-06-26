import cleve_service
from st2common.runners.base_action import Action
import sys
from typing import Any, Dict


class AddRunQcAction(Action):

    def __init__(self, config, action_service):
        super().__init__(config, action_service)
        if "cleve_service" in self.config:
            self.cleve = self.config.get("cleve_service")
        else:
            self.cleve = cleve_service.Cleve(
                config.get("cleve").get("host"),
                config.get("cleve").get("port"),
                config.get("cleve").get("api_key"),
            )

    def run(self, run_id: str) -> Dict[str, Any]:
        try:
            return self.cleve.add_run_qc(run_id=run_id)
        except cleve_service.CleveError as e:
            self.logger.error(e)
            sys.exit(1)
