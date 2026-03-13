"""
CLIP-based zero-shot skin condition classifier.

Loads the ViT-B/32 model once at startup and exposes a single
`classify(image_bytes)` function used by the API layer.
"""

import io
import json
import time
from typing import List, Tuple

import clip
import torch
from PIL import Image

# ── Condition prompts (prompt-engineered for dermatology) ─────────────────────
# Each tuple: (display_name, CLIP text prompt)
CONDITION_PROMPTS: List[Tuple[str, str]] = [
    ("Acne Vulgaris",    "a close-up clinical photograph of acne vulgaris on human skin"),
    ("Eczema",           "a dermatological photograph of eczema on human skin"),
    ("Psoriasis",        "a clinical image of psoriasis showing scaly plaques on skin"),
    ("Melanoma",         "a dermoscopic image of melanoma skin lesion"),
    ("Benign Nevus",     "a dermoscopic photograph of a benign nevus mole on skin"),
]

DISCLAIMER = (
    "This is an AI-generated preliminary analysis and does NOT replace "
    "professional medical diagnosis. Always consult a qualified "
    "dermatologist for accurate assessment and treatment."
)

# ── Module-level singletons (loaded once at startup) ─────────────────────────
_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = None
_preprocess = None
_text_features = None   # pre-encoded text embeddings – computed once


def _load_model() -> None:
    global _model, _preprocess, _text_features
    if _model is not None:
        return  # already loaded

    print(f"[CLIP] Loading ViT-B/32 on {_device} …")
    _model, _preprocess = clip.load("ViT-B/32", device=_device)
    _model.eval()

    # Pre-encode all text prompts – this only happens once
    texts = [prompt for _, prompt in CONDITION_PROMPTS]
    tokens = clip.tokenize(texts).to(_device)
    with torch.no_grad():
        _text_features = _model.encode_text(tokens)
        _text_features = _text_features / _text_features.norm(dim=-1, keepdim=True)

    print("[CLIP] Model ready.")


def classify(image_bytes: bytes) -> dict:
    """
    Run zero-shot CLIP classification on raw image bytes.

    Returns a dict with:
        predicted_condition  str
        confidence           float  (0–1)
        all_scores           list[{"name": str, "confidence": float}]
        all_scores_json      str    (JSON, for DB storage)
        analysis_time_seconds float
    """
    _load_model()

    t0 = time.perf_counter()

    # Decode and preprocess image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_input = _preprocess(image).unsqueeze(0).to(_device)

    # Encode image
    with torch.no_grad():
        image_features = _model.encode_image(image_input)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

    # Cosine similarity → softmax probabilities
    logits = (100.0 * image_features @ _text_features.T)
    probs = logits.softmax(dim=-1).squeeze(0).tolist()

    elapsed = round(time.perf_counter() - t0, 3)

    # Build results list sorted by confidence descending
    scores = [
        {"name": name, "confidence": round(float(prob), 4)}
        for (name, _), prob in zip(CONDITION_PROMPTS, probs)
    ]
    scores.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "predicted_condition": scores[0]["name"],
        "confidence": scores[0]["confidence"],
        "all_scores": scores,
        "all_scores_json": json.dumps(scores),
        "analysis_time_seconds": elapsed,
        "disclaimer": DISCLAIMER,
    }
