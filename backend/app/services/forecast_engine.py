from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing

logger = logging.getLogger("luxe_tech.forecast")


class ForecastEngine:
    MIN_OBSERVATIONS_REQUIRED = 6

    @staticmethod
    def _walk_forward_predictions(
        training_values: np.ndarray,
        test_values: np.ndarray,
        predict_next: Callable[[np.ndarray, int], float],
    ) -> List[float]:
        history = [float(value) for value in training_values]
        predictions = []
        for actual in test_values:
            predictions.append(float(predict_next(np.asarray(history), len(history))))
            history.append(float(actual))
        return predictions

    @staticmethod
    def _metrics(actual: np.ndarray, predicted: List[float]) -> Dict[str, Optional[float]]:
        predictions = np.asarray(predicted, dtype=float)
        mae = float(mean_absolute_error(actual, predictions))
        rmse = float(np.sqrt(mean_squared_error(actual, predictions)))
        mape = (
            None
            if np.any(actual == 0)
            else float(np.mean(np.abs((actual - predictions) / np.abs(actual)))) * 100
        )
        return {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "mape": round(mape, 2) if mape is not None else None,
        }

    @staticmethod
    def _log_model_failure(model_name: str, exc: Exception) -> None:
        logger.warning("Forecast model %s failed (%s).", model_name, type(exc).__name__)

    @classmethod
    def generate_forecast(
        cls,
        observations: List[Dict[str, Any]],
        horizon: str = "3_months",
        trend_id: str = ""
    ) -> Dict[str, Any]:
        """
        Runs four statistical forecasting models on historical signal data, compares them via backtesting,
        and selects the optimal model.
        """
        if len(observations) < cls.MIN_OBSERVATIONS_REQUIRED:
            return {
                "status": "insufficient_data",
                "message": f"Insufficient historical observations. Found {len(observations)}, minimum required is {cls.MIN_OBSERVATIONS_REQUIRED}.",
                "data_status": "insufficient_data"
            }

        # 1. Clean and prepare series
        df = pd.DataFrame(observations)
        if "strength" not in df.columns:
            return {
                "status": "insufficient_data",
                "message": "Signal observations missing 'strength' numeric series.",
                "data_status": "insufficient_data"
            }

        # Sort chronologically if timestamp exists
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            if df["timestamp"].isna().any():
                return {
                    "status": "insufficient_data",
                    "message": "Historical observations contain invalid timestamps.",
                    "data_status": "insufficient_data"
                }
            df = df.sort_values("timestamp")

        strength = pd.to_numeric(df["strength"], errors="coerce")
        if strength.isna().any() or not np.isfinite(strength.to_numpy(dtype=float)).all():
            return {
                "status": "insufficient_data",
                "message": "Historical observations contain invalid signal values.",
                "data_status": "insufficient_data"
            }
        y = strength.to_numpy(dtype=float)
        n = len(y)

        # Hold out the last 25% (at least two points) and evaluate one step at a time.
        split_idx = max(cls.MIN_OBSERVATIONS_REQUIRED - 2, int(n * 0.75))
        y_train, y_test = y[:split_idx], y[split_idx:]
        test_len = len(y_test)

        horizon_steps = 3
        if horizon == "1_month":
            horizon_steps = 1
        elif horizon == "6_months":
            horizon_steps = 6

        evaluations: List[Dict[str, Any]] = []

        def backtest_accuracy(mape: Optional[float]) -> Optional[float]:
            return round(max(0.0, 100.0 - mape), 1) if mape is not None else None

        # --- MODEL 1: Moving Average ---
        try:
            ma_preds = cls._walk_forward_predictions(
                y_train, y_test, lambda history, _: float(np.mean(history[-min(3, len(history)):]))
            )
            metrics = cls._metrics(y_test, ma_preds)
            proj_ma = [round(float(np.mean(y[-min(3, n):])), 2)] * horizon_steps
            evaluations.append({
                "name": "moving_average",
                **metrics,
                "forecast_values": proj_ma,
                "backtest_accuracy": backtest_accuracy(metrics["mape"])
            })
        except Exception as exc:
            cls._log_model_failure("moving_average", exc)

        # --- MODEL 2: Simple Exponential Smoothing ---
        try:
            def predict_ses(history: np.ndarray, _: int) -> float:
                return float(SimpleExpSmoothing(
                    history, initialization_method="estimated"
                ).fit(smoothing_level=0.3, optimized=False).forecast(1)[0])

            ses_preds = cls._walk_forward_predictions(y_train, y_test, predict_ses)
            metrics = cls._metrics(y_test, ses_preds)
            full_ses = SimpleExpSmoothing(y, initialization_method="estimated").fit(smoothing_level=0.3, optimized=False)
            proj_ses = [round(float(v), 2) for v in full_ses.forecast(horizon_steps)]

            evaluations.append({
                "name": "simple_exponential_smoothing",
                **metrics,
                "forecast_values": proj_ses,
                "backtest_accuracy": backtest_accuracy(metrics["mape"])
            })
        except Exception as exc:
            cls._log_model_failure("simple_exponential_smoothing", exc)

        # --- MODEL 3: Holt-Winters (Double Exponential Smoothing / Additive Trend) ---
        try:
            def predict_holt_winters(history: np.ndarray, _: int) -> float:
                if len(history) < 3:
                    raise ValueError("At least three training observations are required.")
                return float(ExponentialSmoothing(
                    history, trend="add", initialization_method="estimated"
                ).fit().forecast(1)[0])

            hw_preds = cls._walk_forward_predictions(y_train, y_test, predict_holt_winters)
            metrics = cls._metrics(y_test, hw_preds)
            full_hw = ExponentialSmoothing(y, trend="add", initialization_method="estimated").fit()
            proj_hw = [round(float(v), 2) for v in full_hw.forecast(horizon_steps)]

            evaluations.append({
                "name": "holt_winters",
                **metrics,
                "forecast_values": proj_hw,
                "backtest_accuracy": backtest_accuracy(metrics["mape"])
            })
        except Exception as exc:
            cls._log_model_failure("holt_winters", exc)

        # --- MODEL 4: Linear Regression ---
        try:
            def predict_linear(history: np.ndarray, next_index: int) -> float:
                model = LinearRegression().fit(
                    np.arange(len(history)).reshape(-1, 1), history
                )
                return float(model.predict(np.array([[next_index]]))[0])

            lr_preds = cls._walk_forward_predictions(y_train, y_test, predict_linear)
            metrics = cls._metrics(y_test, lr_preds)

            X_full = np.arange(n).reshape(-1, 1)
            lr_full = LinearRegression().fit(X_full, y)
            X_proj = np.arange(n, n + horizon_steps).reshape(-1, 1)
            proj_lr = [round(float(v), 2) for v in lr_full.predict(X_proj)]

            evaluations.append({
                "name": "linear_regression",
                **metrics,
                "forecast_values": proj_lr,
                "backtest_accuracy": backtest_accuracy(metrics["mape"])
            })
        except Exception as exc:
            cls._log_model_failure("linear_regression", exc)

        if not evaluations:
            return {
                "status": "insufficient_data",
                "message": "Models could not converge on provided data.",
                "data_status": "insufficient_data"
            }

        # 3. Model comparison: choose model with lowest RMSE
        best_model = min(evaluations, key=lambda x: x["rmse"])

        # Create timeline points
        now = datetime.now(timezone.utc)
        historical_points = []
        for i, val in enumerate(y):
            t = df.iloc[i].get("timestamp") if "timestamp" in df.columns else (now - timedelta(days=30 * (n - i)))
            historical_points.append({
                "period": f"T-{n - i}",
                "timestamp": str(t),
                "value": round(float(val), 2),
                "type": "observed"
            })
            for provenance_field in ("source", "source_name", "source_url", "fetched_at"):
                provenance_value = df.iloc[i].get(provenance_field)
                if provenance_value is not None and not pd.isna(provenance_value):
                    historical_points[-1][provenance_field] = str(provenance_value)

        projected_points = []
        for step, val in enumerate(best_model["forecast_values"], start=1):
            projected_points.append({
                "period": f"T+{step}",
                "timestamp": str(now + timedelta(days=30 * step)),
                "value": round(float(val), 2),
                "type": "forecast",
                "model": best_model["name"]
            })

        return {
            "status": "success",
            "trend_id": trend_id,
            "selected_model": best_model["name"],
            "horizon": horizon,
            "forecast_value": best_model["forecast_values"][-1],
            "backtest_accuracy": best_model["backtest_accuracy"],
            "backtest_period": f"Last {test_len} observations",
            "historical_points": historical_points,
            "projected_points": projected_points,
            "model_evaluations": evaluations,
            "data_status": "forecast"
        }


forecast_engine = ForecastEngine()
