"""Model routing — which Claude tier answers this session.

`model_routing` is the pure policy (tiers, Opus 24h budget, forced-model escape);
`router_runtime` is its I/O shell (reads disclosure severity from Postgres, runs
the preset classifier, decides). Session-sticky by design: the model is chosen
when a session OPENS and holds for its lifetime.
"""

from persona_runner.routing.model_routing import ModelChoice, OpusBudget, select_model
from persona_runner.routing.router_runtime import RoutingDecision, route_for_session

__all__ = [
    "ModelChoice",
    "OpusBudget",
    "RoutingDecision",
    "route_for_session",
    "select_model",
]
