"""
DermAssist – Melanoma Detection Service
EfficientNet-B0 fine-tuned classifier for skin lesion analysis.

Classes:
    0 – Benign Nevus   (harmless mole)
    1 – Melanoma       (malignant lesion)
    2 – Healthy Skin   (no lesion detected)
"""

import io
import time
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

# Constants

MODEL_PATH = Path(__file__).parent / "melanoma_model.pth"

CLASS_LABELS = {
    0: "Benign Nevus",
    1: "Melanoma",
    2: "Healthy Skin",
}

CLASS_DESCRIPTIONS = {
    "Benign Nevus":   "A harmless, non-cancerous mole. No immediate medical concern, but monitor for changes.",
    "Melanoma":       "A potentially malignant skin lesion detected. Please consult a dermatologist urgently.",
    "Healthy Skin":   "No lesion detected. The skin appears normal with no visible abnormalities.",
}

DISCLAIMER = (
    "This is an AI-generated preliminary analysis and does NOT replace "
    "professional medical diagnosis. Always consult a qualified "
    "dermatologist for accurate assessment and treatment."
)

# Image preprocessing (must match training transforms)

_preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],   # ImageNet mean
        std=[0.229, 0.224, 0.225],    # ImageNet std
    ),
])

#  Module-level singletons

_device = "cuda" if torch.cuda.is_available() else "cpu"
_model: nn.Module | None = None


def _build_model() -> nn.Module:
    """Build EfficientNet-B0 with a custom 3-class head."""
    net = models.efficientnet_b0(weights=None)
    in_features = net.classifier[1].in_features
    net.classifier = nn.Sequential(
        nn.Dropout(p=0.3, inplace=True),
        nn.Linear(in_features, 3),   # 3 classes
    )
    return net


def load_model() -> None:
    """Load model weights at startup. Safe to call multiple times."""
    global _model
    if _model is not None:
        return

    print(f"[Model] Loading EfficientNet-B0 on {_device} …")
    _model = _build_model().to(_device)

    if MODEL_PATH.exists():
        state = torch.load(MODEL_PATH, map_location=_device)
        _model.load_state_dict(state)
        print("[Model] Weights loaded from melanoma_model.pth ✓")
    else:
        # Model file not yet trained — weights are random.
        # The API will still respond but predictions will be meaningless
        # until melanoma_model.pth is placed in the backend folder.
        print("[Model] melanoma_model.pth not found — using random weights.")
        print("[Model] Train the model first and place the .pth file here.")

    _model.eval()
    print("[Model] Ready.")


def classify(image_bytes: bytes) -> dict:
    """
    Run melanoma classification on raw image bytes.

    Returns:
        predicted_condition  str
        confidence           float  (0–1)
        all_scores           list[{"name": str, "confidence": float}]
        all_scores_json      str    (JSON for DB storage)
        analysis_time_seconds float
        description          str
        disclaimer           str
    """
    import json

    load_model()

    t0 = time.perf_counter()

    # Decode and preprocess
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = _preprocess(image).unsqueeze(0).to(_device)

    # Inference
    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0).tolist()

    elapsed = round(time.perf_counter() - t0, 3)

    # Build scores list sorted by confidence descending
    scores = [
        {"name": CLASS_LABELS[i], "confidence": round(float(p), 4)}
        for i, p in enumerate(probs)
    ]
    scores.sort(key=lambda x: x["confidence"], reverse=True)

    top = scores[0]

    return {
        "predicted_condition":  top["name"],
        "confidence":           top["confidence"],
        "all_scores":           scores,
        "all_scores_json":      json.dumps(scores),
        "analysis_time_seconds": elapsed,
        "description":          CLASS_DESCRIPTIONS[top["name"]],
        "disclaimer":           DISCLAIMER,
    }
