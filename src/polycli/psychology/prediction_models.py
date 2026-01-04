"""Build prediction models.

Even if they're wrong, the process of modeling forces you to think
clearly about probabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional


@dataclass
class ModelFactor:
    """A factor in a prediction model."""

    name: str
    weight: Decimal
    current_value: Optional[float] = None
    description: str = ""
    data_source: str = ""
    last_updated: Optional[datetime] = None


@dataclass
class PredictionModel:
    """A model for predicting market outcomes."""

    id: str
    name: str
    market_id: str
    market_question: str
    factors: list[ModelFactor]
    created_at: datetime
    updated_at: datetime
    base_rate: Decimal
    model_probability: Optional[Decimal] = None
    market_probability: Optional[Decimal] = None
    notes: str = ""


@dataclass
class ModelBacktest:
    """Backtest results for a model."""

    model_id: str
    predictions: int
    correct: int
    brier_score: float
    calibration_error: float
    comparison_to_market: str


class PredictionModelBuilder:
    """Build and track prediction models."""

    def __init__(self):
        """Initialize model builder."""
        self._models: dict[str, PredictionModel] = {}
        self._model_counter = 0
        self._predictions: dict[str, list[dict]] = {}

    def create_model(
        self,
        name: str,
        market_id: str,
        market_question: str,
        base_rate: Decimal,
        factors: Optional[list[dict]] = None,
        notes: str = "",
    ) -> PredictionModel:
        """Create a new prediction model.

        Args:
            name: Name for the model
            market_id: Market this model predicts
            market_question: Human-readable question
            base_rate: Starting probability before factors
            factors: List of factor definitions
            notes: Additional notes
        """
        self._model_counter += 1
        model_id = f"model_{self._model_counter:06d}"

        model_factors = []
        if factors:
            for f in factors:
                model_factors.append(
                    ModelFactor(
                        name=f.get("name", ""),
                        weight=Decimal(str(f.get("weight", 0))),
                        description=f.get("description", ""),
                        data_source=f.get("data_source", ""),
                    )
                )

        model = PredictionModel(
            id=model_id,
            name=name,
            market_id=market_id,
            market_question=market_question,
            factors=model_factors,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            base_rate=base_rate,
            notes=notes,
        )

        self._models[model_id] = model
        return model

    def update_factor(
        self,
        model_id: str,
        factor_name: str,
        value: float,
    ) -> Optional[PredictionModel]:
        """Update a factor value in a model.

        Args:
            model_id: Model to update
            factor_name: Factor to update
            value: New value for the factor
        """
        model = self._models.get(model_id)
        if not model:
            return None

        for factor in model.factors:
            if factor.name == factor_name:
                factor.current_value = value
                factor.last_updated = datetime.utcnow()
                break

        model.updated_at = datetime.utcnow()
        model.model_probability = self._calculate_probability(model)

        return model

    def _calculate_probability(self, model: PredictionModel) -> Decimal:
        """Calculate model probability from factors."""
        prob = model.base_rate

        for factor in model.factors:
            if factor.current_value is not None:
                # Simple linear adjustment
                # Value is expected to be -1 to 1
                adjustment = factor.weight * Decimal(str(factor.current_value))
                prob += adjustment

        # Clamp to valid range
        return max(Decimal("0.01"), min(Decimal("0.99"), prob))

    def compare_to_market(
        self,
        model_id: str,
        market_price: Decimal,
    ) -> dict:
        """Compare model prediction to market price.

        Args:
            model_id: Model to compare
            market_price: Current market price
        """
        model = self._models.get(model_id)
        if not model:
            return {"error": "Model not found"}

        if model.model_probability is None:
            model.model_probability = self._calculate_probability(model)

        model.market_probability = market_price
        diff = model.model_probability - market_price

        return {
            "model_probability": model.model_probability,
            "market_probability": market_price,
            "difference": diff,
            "suggested_action": self._suggest_action(diff),
            "confidence": self._calculate_confidence(model),
        }

    def _suggest_action(self, diff: Decimal) -> str:
        """Suggest action based on model vs market difference."""
        if diff > Decimal("0.15"):
            return "Strong buy signal - model significantly above market"
        elif diff > Decimal("0.08"):
            return "Buy signal - model above market"
        elif diff > Decimal("0.03"):
            return "Slight buy lean - small edge detected"
        elif diff < Decimal("-0.15"):
            return "Strong sell signal - model significantly below market"
        elif diff < Decimal("-0.08"):
            return "Sell signal - model below market"
        elif diff < Decimal("-0.03"):
            return "Slight sell lean - small negative edge"
        else:
            return "No clear signal - model and market aligned"

    def _calculate_confidence(self, model: PredictionModel) -> float:
        """Calculate confidence in model prediction."""
        # Higher confidence if:
        # - All factors have values
        # - Factors have recent updates
        # - Model has been validated

        factors_with_values = sum(
            1 for f in model.factors if f.current_value is not None
        )
        factor_coverage = factors_with_values / len(model.factors) if model.factors else 0

        # Check factor freshness
        recent_updates = 0
        for f in model.factors:
            if f.last_updated:
                hours_old = (datetime.utcnow() - f.last_updated).total_seconds() / 3600
                if hours_old < 24:
                    recent_updates += 1

        freshness = recent_updates / len(model.factors) if model.factors else 0

        return (factor_coverage * 0.6 + freshness * 0.4)

    def record_prediction(
        self,
        model_id: str,
        predicted_probability: Decimal,
        market_probability: Decimal,
    ) -> str:
        """Record a prediction for later scoring.

        Args:
            model_id: Model making prediction
            predicted_probability: Model's prediction
            market_probability: Market price at time of prediction
        """
        prediction_id = f"pred_{datetime.utcnow().timestamp()}"

        if model_id not in self._predictions:
            self._predictions[model_id] = []

        self._predictions[model_id].append({
            "id": prediction_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model_prob": float(predicted_probability),
            "market_prob": float(market_probability),
            "outcome": None,  # Filled later
        })

        return prediction_id

    def resolve_prediction(
        self,
        model_id: str,
        prediction_id: str,
        outcome: bool,
    ) -> None:
        """Resolve a prediction with actual outcome.

        Args:
            model_id: Model that made prediction
            prediction_id: Prediction to resolve
            outcome: True if event happened, False otherwise
        """
        predictions = self._predictions.get(model_id, [])
        for pred in predictions:
            if pred["id"] == prediction_id:
                pred["outcome"] = outcome
                break

    def backtest_model(self, model_id: str) -> Optional[ModelBacktest]:
        """Backtest a model against its predictions.

        Args:
            model_id: Model to backtest
        """
        predictions = self._predictions.get(model_id, [])
        resolved = [p for p in predictions if p.get("outcome") is not None]

        if len(resolved) < 5:
            return None

        # Calculate metrics
        correct = 0
        brier_sum = 0.0
        calibration_errors = []

        for pred in resolved:
            model_prob = pred["model_prob"]
            market_prob = pred["market_prob"]
            outcome = 1 if pred["outcome"] else 0

            # Correct if model was on right side
            if (model_prob > 0.5 and outcome == 1) or (model_prob < 0.5 and outcome == 0):
                correct += 1

            # Brier score
            brier_sum += (model_prob - outcome) ** 2

            # Calibration
            calibration_errors.append(abs(model_prob - outcome))

        brier = brier_sum / len(resolved)
        calibration = sum(calibration_errors) / len(calibration_errors)

        # Compare to market baseline
        market_correct = sum(
            1 for p in resolved
            if (p["market_prob"] > 0.5 and p["outcome"]) or
               (p["market_prob"] < 0.5 and not p["outcome"])
        )

        if correct > market_correct:
            comparison = f"Model beat market ({correct} vs {market_correct} correct)"
        elif correct < market_correct:
            comparison = f"Market beat model ({market_correct} vs {correct} correct)"
        else:
            comparison = "Model matched market performance"

        return ModelBacktest(
            model_id=model_id,
            predictions=len(resolved),
            correct=correct,
            brier_score=brier,
            calibration_error=calibration,
            comparison_to_market=comparison,
        )

    def get_model(self, model_id: str) -> Optional[PredictionModel]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def list_models(self) -> list[PredictionModel]:
        """List all models."""
        return list(self._models.values())

    def get_model_template(self, market_type: str) -> dict:
        """Get a template for building a model.

        Args:
            market_type: Type of market (election, economic, etc.)
        """
        templates = {
            "election": {
                "suggested_base_rate": 0.5,
                "factors": [
                    {"name": "polling_average", "weight": 0.2, "description": "Aggregate polling data"},
                    {"name": "fundamentals", "weight": 0.15, "description": "Economic/approval fundamentals"},
                    {"name": "momentum", "weight": 0.1, "description": "Recent polling trend"},
                    {"name": "expert_forecasts", "weight": 0.1, "description": "538/other forecaster consensus"},
                    {"name": "prediction_markets", "weight": 0.1, "description": "Other market consensus"},
                ],
            },
            "economic": {
                "suggested_base_rate": 0.5,
                "factors": [
                    {"name": "fed_guidance", "weight": 0.25, "description": "Fed communications"},
                    {"name": "economic_data", "weight": 0.2, "description": "Recent economic releases"},
                    {"name": "market_implied", "weight": 0.15, "description": "Fed funds futures"},
                    {"name": "expert_consensus", "weight": 0.1, "description": "Economist forecasts"},
                ],
            },
            "binary_event": {
                "suggested_base_rate": 0.5,
                "factors": [
                    {"name": "base_rate", "weight": 0.15, "description": "Historical frequency"},
                    {"name": "recent_news", "weight": 0.2, "description": "Recent relevant news"},
                    {"name": "insider_signals", "weight": 0.15, "description": "Smart money positioning"},
                    {"name": "time_factor", "weight": 0.1, "description": "Time until resolution"},
                ],
            },
        }

        return templates.get(market_type, templates["binary_event"])
