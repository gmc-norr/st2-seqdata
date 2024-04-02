import cleve_service
from st2common.runners.base_action import Action


class AddRunAction(Action):

    def __init__(self, config, action_service):
        super().__init__(config, action_service)
        self.cleve = cleve_service.Cleve(
            config.get("cleve").get("host"),
            config.get("cleve").get("port"),
            config.get("cleve").get("api_key"),
        )

    def run(self,
            runparameters: str,
            path: str,
            state: str) -> None:
        self.cleve.add_run(runparameters, path, state)
