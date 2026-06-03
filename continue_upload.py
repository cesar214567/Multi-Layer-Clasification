#!/usr/bin/env python3.10
"""Continue uploading remaining Cats and all Dogs."""
import os, sys, json, requests
sys.stdout.reconfigure(line_buffering=True)

BASE = "http://localhost:8000"
PROJECT_ID = "6a10ae58902bb1cdcd15d9cc"
USER_ID = "6a10ae2c902bb1cdcd15d9be"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAT_ZIPS_DIR = os.path.join(SCRIPT_DIR, "CatBreeds", "zips")
DOG_ZIPS_DIR = os.path.join(SCRIPT_DIR, "stanford-dogs-images", "zips")

# Use existing token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNmExMGFlMmM5MDJiYjFjZGNkMTVkOWJlIiwiZXhwIjoxNzgwMDgxMDE1fQ.ImsvEp49XFFrcqoST_d1oE0LF_4Ufsm_wL0BeWiMgs0"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
HEADERS_JSON = {**HEADERS, "Content-Type": "application/json"}
print(f"Using token")

# Get tags
resp = requests.get(f"{BASE}/api/tags/", headers=HEADERS, params={"project_id": PROJECT_ID})
all_tags = {t['name']: t['id'] for t in resp.json().get('tags', [])}
CAT_TAG_ID = all_tags['Cat']
DOG_TAG_ID = all_tags['Dog']

# Check which cat breeds already uploaded
import mongoengine
mongoengine.connect(db='myapp_db', host='localhost', port=27017, username='admin', password='password', authentication_source='admin')
from core.models import Image, Tag

uploaded_breeds = set()
for tag_name, tag_id in all_tags.items():
    if tag_name in ('Cat', 'Dog', 'FISH'):
        continue
    tag = Tag.objects(id=tag_id).first()
    if tag and Image.objects(tag_references__tag_id=tag.id).count() > 0:
        uploaded_breeds.add(tag_name)

def upload_zip(zip_path, tags_list, label=""):
    with open(zip_path, 'rb') as f:
        resp = requests.post(f"{BASE}/api/images/", headers=HEADERS,
                             data={"user_id": USER_ID, "project_id": PROJECT_ID, "tags": json.dumps(tags_list)},
                             files={"file": (os.path.basename(zip_path), f, "application/zip")})
    data = resp.json()
    if data.get('status') == 'success':
        return len(data.get('images', []))
    print(f"    ERROR {label}: {data.get('message', 'unknown')}")
    return 0

# --- Remaining Cats ---
cat_zips = sorted([f for f in os.listdir(CAT_ZIPS_DIR) if f.endswith('.zip')])
remaining_cats = [(f, f.replace('.zip', '')) for f in cat_zips if f.replace('.zip', '') not in uploaded_breeds]
print(f"\nRemaining cat breeds to upload: {len(remaining_cats)}")
cat_total = 0
for i, (zipfile, breed) in enumerate(remaining_cats):
    breed_tag_id = all_tags.get(breed)
    if not breed_tag_id:
        r = requests.post(f"{BASE}/api/tags/", headers=HEADERS_JSON, json={"name": breed, "project_id": PROJECT_ID})
        if r.json().get('status') == 'success':
            breed_tag_id = r.json()['tag']['id']
            all_tags[breed] = breed_tag_id
    tags_list = [{"tag_id": CAT_TAG_ID, "name": "Cat"}]
    if breed_tag_id:
        tags_list.append({"tag_id": breed_tag_id, "name": breed})
    count = upload_zip(os.path.join(CAT_ZIPS_DIR, zipfile), tags_list, zipfile)
    cat_total += count
    print(f"  [{i+1}/{len(remaining_cats)}] {breed}: {count}")
print(f"Cats uploaded this run: {cat_total}")

# --- All Dogs ---
dog_zips = sorted([f for f in os.listdir(DOG_ZIPS_DIR) if f.endswith('.zip')])
remaining_dogs = [(f, f.replace('.zip', '')) for f in dog_zips if f.replace('.zip', '') not in uploaded_breeds]
print(f"\nDog breeds to upload: {len(remaining_dogs)}")
dog_total = 0
for i, (zipfile, breed) in enumerate(remaining_dogs):
    breed_tag_id = all_tags.get(breed)
    if not breed_tag_id:
        r = requests.post(f"{BASE}/api/tags/", headers=HEADERS_JSON, json={"name": breed, "project_id": PROJECT_ID})
        if r.json().get('status') == 'success':
            breed_tag_id = r.json()['tag']['id']
            all_tags[breed] = breed_tag_id
    tags_list = [{"tag_id": DOG_TAG_ID, "name": "Dog"}]
    if breed_tag_id:
        tags_list.append({"tag_id": breed_tag_id, "name": breed})
    count = upload_zip(os.path.join(DOG_ZIPS_DIR, zipfile), tags_list, zipfile)
    dog_total += count
    print(f"  [{i+1}/{len(remaining_dogs)}] {breed}: {count}")
print(f"Dogs uploaded this run: {dog_total}")

print(f"\nDONE! Cats={cat_total}, Dogs={dog_total}, Total new={cat_total+dog_total}")
