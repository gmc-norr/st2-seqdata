from cleve_service import Cleve
from st2common.runners.base_action import Action
from typing import Any, Dict, Optional


class UpdateAnalysisAction(Action):

    def __init__(self, action_service, config):
        super().__init__(action_service, config)
        self.cleve = Cleve(
            config.get("cleve").get("host"),
            config.get("cleve").get("port"),
            config.get("cleve").get("api_key"),
        )

    def run(self,
            run_id: str,
            analysis_id: str,
            state: str,
            summary_file: Optional[str] = None) -> Dict[str, Any]:
        return self.cleve.update_analysis(
            run_id=run_id,
            analysis_id=analysis_id,
            state=state,
            summary_file=summary_file,
        )
