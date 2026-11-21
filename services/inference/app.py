"""Inference service: serves a deterministic mock model over HTTP.

Starter kit for the SDCN integrative project. The mock model stands in for a
real one (scikit-learn, Hugging Face...); the grade is about serving it in a
distributed, scalable and reliable way, not about the model itself.
"""

import hashlib
import logging
import os
import time

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel, Field

MODEL_VERSION = os.getenv("MODEL_VERSION", "mock-1.0.0")
# Synthetic CPU work per prediction, so that load actually moves the HPA.
CPU_WORK_MS = int(os.getenv("CPU_WORK_MS", "20"))
LABELS = ("negative", "neutral", "positive")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("inference")

PREDICTIONS = Counter(
    "predictions_total", "Predictions served, by label.", ["label"]
)
LATENCY = Histogram(
    "prediction_latency_seconds", "Time spent computing one prediction."
)

app = FastAPI(title="inference", version=MODEL_VERSION)
app.mount("/metrics", make_asgi_app())


class PredictRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class PredictResponse(BaseModel):
    label: str
    score: float
    model_version: str
    cached: bool


def burn_cpu(milliseconds: int) -> None:
    deadline = time.perf_counter() + milliseconds / 1000
    while time.perf_counter() < deadline:
        pass


def mock_model(text: str) -> tuple[str, float]:
    """Same input, same output: required to reason about caching."""
    digest = hashlib.sha256(text.encode()).digest()
    label = LABELS[digest[0] % len(LABELS)]
    score = round(0.5 + (digest[1] / 255) / 2, 4)
    return label, score


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    # TODO(Checkpoint 2): look the input up in Redis before computing and
    # store the result afterwards (key, TTL and consistency policy are the
    # group's decision; justify them in the report).
    with LATENCY.time():
        burn_cpu(CPU_WORK_MS)
        label, score = mock_model(request.text)
    PREDICTIONS.labels(label=label).inc()
    # TODO(Final): emit structured (JSON) logs and an OpenTelemetry span
    # correlated with the trace started at the gateway.
    log.info("prediction label=%s score=%s", label, score)
    return PredictResponse(
        label=label, score=score, model_version=MODEL_VERSION, cached=False
    )


@app.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    """Readiness: able to serve traffic."""
    # TODO(Checkpoint 2): report not ready (HTTP 503) while a required
    # dependency is unreachable, and justify which ones are required.
    return {"status": "ready", "model_version": MODEL_VERSION}
