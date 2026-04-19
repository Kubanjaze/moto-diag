"""Track F — advanced diagnostics: predictive maintenance, wear analysis, fleet mgmt."""
from motodiag.advanced.comparative import (
    PeerComparison,
    PeerStats,
    compare_against_peers,
)
from motodiag.advanced.drift import (
    DriftBucket,
    DriftResult,
    compute_trend,
    detect_drifting_pids,
    summary_for_bike,
)
from motodiag.advanced.fleet_analytics import fleet_status_summary
from motodiag.advanced.fleet_repo import (
    BikeAlreadyInFleetError,
    Fleet,
    FleetNameExistsError,
    FleetNotFoundError,
    FleetRole,
)
from motodiag.advanced.models import FailurePrediction, PredictionConfidence
from motodiag.advanced.predictor import predict_failures
from motodiag.advanced.wear import WearMatch, WearPattern, analyze_wear

__all__ = [
    "FailurePrediction",
    "PredictionConfidence",
    "predict_failures",
    "PeerStats",
    "PeerComparison",
    "compare_against_peers",
    "DriftBucket",
    "DriftResult",
    "compute_trend",
    "detect_drifting_pids",
    "summary_for_bike",
    "WearPattern",
    "WearMatch",
    "analyze_wear",
    "Fleet",
    "FleetRole",
    "FleetNotFoundError",
    "FleetNameExistsError",
    "BikeAlreadyInFleetError",
    "fleet_status_summary",
]
