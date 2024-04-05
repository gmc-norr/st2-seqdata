from cleve_service import Cleve
from st2common.runners.base_action import Action
from typing import Any, Dict, Optional


class AddAnalysisAction(Action):

    def __init__(self, config, action_service):
        super().__init__(config, action_service)
        self.cleve = Cleve(
            config.get("cleve").get("host"),
            config.get("cleve").get("port"),
            config.get("cleve").get("api_key"),
        )

    def run(self,
            run_id: str,
            path: str,
            state: str,
            summary_file: Optional[str]) -> Dict[str, Any]:
        return self.cleve.add_analysis(
            run_id=run_id,
            path=path,
            state=state,
            summary_file=summary_file,
        )
