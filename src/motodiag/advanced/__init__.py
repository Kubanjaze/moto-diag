"""Track F — advanced diagnostics: predictive maintenance, wear analysis, fleet mgmt."""
from motodiag.advanced.models import FailurePrediction, PredictionConfidence
from motodiag.advanced.predictor import predict_failures

__all__ = ["FailurePrediction", "PredictionConfidence", "predict_failures"]
