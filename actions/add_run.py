import cleve_service
from st2common.runners.base_action import Action
from typing import Any, Dict


class AddRunAction(Action):

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

    def run(self,
            path: str,
            state: str) -> Dict[str, Any]:
        return self.cleve.add_run(
            path=path,
            state=state,
        )
