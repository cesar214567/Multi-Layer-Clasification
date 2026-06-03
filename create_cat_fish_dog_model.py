#!/usr/bin/env python3.10
"""
Creates a new TrainedModel for Cat + Fish + Dog classification,
copying the architecture from the existing fish-cat model (MobileNetV2),
then triggers training to produce version 1.
"""
import requests, json, sys
sys.stdout.reconfigure(line_buffering=True)

BASE = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNmExMGFlMmM5MDJiYjFjZGNkMTVkOWJlIiwiZXhwIjoxNzgwMDgxMDE1fQ.ImsvEp49XFFrcqoST_d1oE0LF_4Ufsm_wL0BeWiMgs0"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
PROJECT_ID = "6a10ae58902bb1cdcd15d9cc"

# Step 1: Get all tags for the project
print("Fetching tags...")
resp = requests.get(f"{BASE}/api/tags/", headers=HEADERS, params={"project_id": PROJECT_ID})
if resp.status_code != 200:
    print(f"Failed to fetch tags: {resp.text}")
    sys.exit(1)

tags_data = resp.json().get('tags', [])
tag_map = {t['name']: t['id'] for t in tags_data}
print(f"Found {len(tag_map)} tags")

# Find Cat, Fish (or fish-related), and Dog tag IDs
cat_tag_id = tag_map.get('Cat')
dog_tag_id = tag_map.get('Dog')
fish_tag_id = tag_map.get('Fish')

# Try alternate names if not found
if not cat_tag_id:
    for name, tid in tag_map.items():
        if 'cat' in name.lower() and len(name) < 10:
            cat_tag_id = tid
            print(f"  Using cat tag: {name} ({tid})")
            break

if not fish_tag_id:
    for name, tid in tag_map.items():
        if 'fish' in name.lower() and len(name) < 10:
            fish_tag_id = tid
            print(f"  Using fish tag: {name} ({tid})")
            break

if not dog_tag_id:
    for name, tid in tag_map.items():
        if 'dog' in name.lower() and len(name) < 10:
            dog_tag_id = tid
            print(f"  Using dog tag: {name} ({tid})")
            break

print(f"  Cat tag: {cat_tag_id}")
print(f"  Fish tag: {fish_tag_id}")
print(f"  Dog tag: {dog_tag_id}")

if not all([cat_tag_id, fish_tag_id, dog_tag_id]):
    print("\nERROR: Could not find all required tags (Cat, Fish, Dog)")
    print("Available tags:", sorted(tag_map.keys()))
    sys.exit(1)

# Step 2: Get existing trained models to copy architecture from fish-cat model
print("\nFetching existing trained models...")
resp = requests.get(f"{BASE}/api/trained-models/", headers=HEADERS, params={"project_id": PROJECT_ID})
if resp.status_code != 200:
    print(f"Failed to fetch models: {resp.text}")
    sys.exit(1)

models = resp.json().get('trained_models', [])
print(f"Found {len(models)} trained models")

# Find the fish-cat model to copy architecture from
fish_cat_model = None
for m in models:
    tag_names = [t.get('name', '') for t in m.get('tags', [])]
    # Look for a model that has both fish and cat tags
    has_fish = any('fish' in n.lower() for n in tag_names)
    has_cat = any('cat' in n.lower() for n in tag_names)
    if has_fish and has_cat:
        fish_cat_model = m
        print(f"  Found fish-cat model: {m['name']} (id: {m['id']})")
        break

if not fish_cat_model:
    # Fall back to any model with MobileNetV2
    for m in models:
        if m.get('architecture') == 'MobileNetV2':
            fish_cat_model = m
            print(f"  Using MobileNetV2 model: {m['name']} (id: {m['id']})")
            break

if not fish_cat_model:
    print("  No existing model found, using default MobileNetV2 config")
    fish_cat_model = {
        'architecture': 'MobileNetV2',
        'include_top': False,
        'custom_top_layers': [],
        'epochs': 10,
        'batch_size': 32,
        'img_size': 224,
        'learning_rate': 0.001,
        'loss': 'categorical_crossentropy',
        'metrics': ['accuracy', 'f1_score', 'precision', 'recall', 'auc'],
    }

# Step 3: Create the new Cat-Fish-Dog model
print("\nCreating Cat-Fish-Dog trained model...")
create_payload = {
    "name": "Cat-Fish-Dog Classifier",
    "description": "3-class classifier for cats, fish, and dogs using MobileNetV2 transfer learning",
    "project_id": PROJECT_ID,
    "architecture": fish_cat_model.get('architecture', 'MobileNetV2'),
    "include_top": fish_cat_model.get('include_top', False),
    "custom_top_layers": fish_cat_model.get('custom_top_layers', []),
    "tag_ids": [cat_tag_id, fish_tag_id, dog_tag_id],
    "epochs": fish_cat_model.get('epochs', 10),
    "batch_size": fish_cat_model.get('batch_size', 32),
    "img_size": fish_cat_model.get('img_size', 224),
    "learning_rate": fish_cat_model.get('learning_rate', 0.001),
    "loss": fish_cat_model.get('loss', 'categorical_crossentropy'),
    "metrics": fish_cat_model.get('metrics', ['accuracy', 'f1_score', 'precision', 'recall', 'auc']),
    "early_stopping_patience": fish_cat_model.get('early_stopping_patience', 3),
    "early_stopping_min_delta": fish_cat_model.get('early_stopping_min_delta', 0.001),
}

resp = requests.post(f"{BASE}/api/trained-models/", headers=HEADERS, json=create_payload)
if resp.status_code not in (200, 201):
    print(f"Failed to create model: {resp.status_code} {resp.text}")
    sys.exit(1)

result = resp.json()
if result.get('status') != 'success':
    print(f"Error creating model: {result.get('message')}")
    sys.exit(1)

new_model = result['trained_model']
new_model_id = new_model['id']
print(f"  Created: {new_model['name']} (id: {new_model_id})")
print(f"  Architecture: {new_model.get('architecture')}")
print(f"  Tags: {[t['name'] for t in new_model.get('tags', [])]}")

# Step 4: Trigger training (version 1)
print("\nStarting training (version 1)...")
train_payload = {
    "trained_model_id": new_model_id,
    "project_id": PROJECT_ID,
    "version_notes": "Version 1 - Initial training with cats, fish, and dogs"
}

resp = requests.post(f"{BASE}/api/trained-models/train/", headers=HEADERS, json=train_payload)
if resp.status_code not in (200, 201, 202):
    print(f"Failed to start training: {resp.status_code} {resp.text}")
    sys.exit(1)

train_result = resp.json()
if train_result.get('status') != 'success':
    print(f"Error starting training: {train_result.get('message')}")
    sys.exit(1)

job_id = train_result.get('job_id')
print(f"  Training started! Job ID: {job_id}")
print(f"\nTo check training status:")
print(f"  curl -H 'Authorization: Bearer {TOKEN}' {BASE}/api/trained-models/train/{job_id}/")
print(f"\nDone! Model '{new_model['name']}' created and training version 1.")
