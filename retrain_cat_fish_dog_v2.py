#!/usr/bin/env python3.10
"""Retrain Cat-Fish-Dog model v2 with custom top layers and reduced early stopping."""
import requests, json, sys
sys.stdout.reconfigure(line_buffering=True)

BASE = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNmExMGFlMmM5MDJiYjFjZGNkMTVkOWJlIiwiZXhwIjoxNzgwMDgxMDE1fQ.ImsvEp49XFFrcqoST_d1oE0LF_4Ufsm_wL0BeWiMgs0"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
PROJECT_ID = "6a10ae58902bb1cdcd15d9cc"
MODEL_ID = "6a193a43c3e618a8c2df69cc"

# Step 1: Update model config - EfficientNetB0, custom top layers, reduced early stopping
print("Updating model config...")
update_payload = {
    "architecture": "EfficientNetB0",
    "include_top": False,
    "custom_top_layers": [
        {"type": "GlobalAveragePooling2D"},
        {"type": "Dense", "units": 1024, "activation": "relu"},
        {"type": "BatchNormalization"},
        {"type": "Dropout", "rate": 0.5},
        {"type": "Dense", "units": 256, "activation": "relu"},
        {"type": "BatchNormalization"},
        {"type": "Dropout", "rate": 0.5},
        {"type": "Dense", "units": 64, "activation": "relu"},
        {"type": "BatchNormalization"},
        {"type": "Dropout", "rate": 0.5}
    ],
    "early_stopping_patience": 2,
    "early_stopping_min_delta": 0.001,
    "epochs": 10,
    "batch_size": 32,
    "img_size": 224,
    "learning_rate": 0.001,
}

resp = requests.put(f"{BASE}/api/trained-models/{MODEL_ID}/", headers=HEADERS, json=update_payload)
if resp.status_code != 200:
    print(f"Failed to update model: {resp.status_code} {resp.text}")
    sys.exit(1)

result = resp.json()
if result.get('status') != 'success':
    print(f"Error: {result.get('message')}")
    sys.exit(1)

print(f"  Model updated: {result['trained_model']['name']}")
print(f"  Architecture: {result['trained_model'].get('architecture')}")
print(f"  Early stopping patience: {update_payload['early_stopping_patience']}")

# Step 2: Trigger training
print("\nStarting training v2...")
train_payload = {
    "trained_model_id": MODEL_ID,
    "project_id": PROJECT_ID,
    "version_notes": "v2 - EfficientNetB0 with deeper custom top (1024>256>64 + BN + Dropout 0.5), early stopping patience=2"
}

resp = requests.post(f"{BASE}/api/trained-models/train/", headers=HEADERS, json=train_payload)
if resp.status_code not in (200, 201, 202):
    print(f"Failed to start training: {resp.status_code} {resp.text}")
    sys.exit(1)

train_result = resp.json()
if train_result.get('status') != 'success':
    print(f"Error: {train_result.get('message')}")
    sys.exit(1)

job_id = train_result.get('job_id')
print(f"  Training started! Job ID: {job_id}")
print(f"\nDone! Training v2 kicked off for Cat-Fish-Dog Classifier.")
