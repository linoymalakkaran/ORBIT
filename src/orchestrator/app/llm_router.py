"""Intelligent LLM router — Phase 22/G27.

Routes each ORBIT pipeline stage to the optimal model based on two axes:
  - task_sensitivity: public | internal | confidential | restricted
  - data_classification: public | internal | confidential | restricted

Routing table (sensitivity × classification → model):
  restricted + any          → llama3-70b-sovereign   (on-prem vLLM, air-gapped)
  confidential + any        → llama3-70b-sovereign   (on-prem vLLM)
  internal + complex        → gpt-4o                 (Azure OpenAI via LiteLLM)
  internal + simple         → gpt-4o-mini            (Azure OpenAI via LiteLLM)
  public  + any             → gpt-4o-mini            (fastest, cheapest)

Stage complexity map (used when data_classification == "internal"):
  complex: architecture_design, api_design, code_generation, code_review, security_scan
  simple:  requirements_analysis, db_schema_design, iac_generation, ci_pipeline_generation,
           test_generation, documentation, pr_review
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelName = Literal[
    "gpt-4o",
    "gpt-4o-mini",
    "llama3-70b-sovereign",
]

Sensitivity = Literal["public", "internal", "confidential", "restricted"]
Classification = Literal["public", "internal", "confidential", "restricted"]

# Pipeline stages considered "complex" (require stronger reasoning)
_COMPLEX_STAGES: frozenset[str] = frozenset({
    "architecture_design",
    "api_design",
    "code_generation",
    "code_review",
    "security_scan",
})

# Classification rank (higher = more sensitive)
_RANK: dict[str, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}


@dataclass(frozen=True)
class RoutingDecision:
    model: ModelName
    reason: str


class IntelligentLLMRouter:
    """
    Routes an ORBIT pipeline stage to the optimal LLM model.

    Usage::

        router = IntelligentLLMRouter()
        decision = router.route(
            stage="code_generation",
            task_sensitivity="internal",
            data_classification="internal",
        )
        model_to_use = decision.model
    """

    def __init__(
        self,
        sovereign_model: ModelName = "llama3-70b-sovereign",
        default_strong_model: ModelName = "gpt-4o",
        default_fast_model: ModelName = "gpt-4o-mini",
    ) -> None:
        self._sovereign = sovereign_model
        self._strong = default_strong_model
        self._fast = default_fast_model

    def route(
        self,
        stage: str,
        task_sensitivity: Sensitivity = "internal",
        data_classification: Classification = "internal",
    ) -> RoutingDecision:
        """
        Determine the best model for a given stage and data profile.

        Returns a :class:`RoutingDecision` with the model name and a human-readable reason.
        """
        effective_rank = max(_RANK.get(task_sensitivity, 1), _RANK.get(data_classification, 1))

        # Confidential or restricted → always sovereign on-prem
        if effective_rank >= _RANK["confidential"]:
            return RoutingDecision(
                model=self._sovereign,
                reason=(
                    f"stage={stage} requires on-prem sovereign model "
                    f"(sensitivity={task_sensitivity}, classification={data_classification})"
                ),
            )

        # Internal classification → route by stage complexity
        if effective_rank == _RANK["internal"]:
            if stage in _COMPLEX_STAGES:
                return RoutingDecision(
                    model=self._strong,
                    reason=f"stage={stage} is complex and data is internal → {self._strong}",
                )
            return RoutingDecision(
                model=self._fast,
                reason=f"stage={stage} is routine and data is internal → {self._fast}",
            )

        # Public — use fast/cheap model
        return RoutingDecision(
            model=self._fast,
            reason=f"stage={stage} with public data → {self._fast}",
        )


# Module-level singleton
router = IntelligentLLMRouter()


def route_for_stage(
    stage: str,
    task_sensitivity: Sensitivity = "internal",
    data_classification: Classification = "internal",
) -> str:
    """Convenience function — returns just the model name string."""
    return router.route(stage, task_sensitivity, data_classification).model
