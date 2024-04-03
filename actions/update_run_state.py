from cleve_service import Cleve
from st2common.runners.base_action import Action


class UpdateRunState(Action):

    def __init__(self, config, action_service):
        super().__init__(config, action_service)
        self.cleve = Cleve(
            config.get("cleve").get("host"),
            config.get("cleve").get("port"),
            config.get("cleve").get("api_key"),
        )

    def run(self, run_id: str, state: str) -> None:
        self.cleve.update_run(run_id, state=state)
