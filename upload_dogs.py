#!/usr/bin/env python3.10
import os, json, requests, sys
sys.stdout.reconfigure(line_buffering=True)

BASE = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNmExMGFlMmM5MDJiYjFjZGNkMTVkOWJlIiwiZXhwIjoxNzgwMDgxMDE1fQ.ImsvEp49XFFrcqoST_d1oE0LF_4Ufsm_wL0BeWiMgs0"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
PROJECT_ID = "6a10ae58902bb1cdcd15d9cc"
USER_ID = "6a10ae2c902bb1cdcd15d9be"
DOG_TAG_ID = "6a189015c3e618a8c2de3e3e"
ZIPS_DIR = "/workplace/cesarmg/PersonalProject/stanford-dogs-images/zips"

# Fetch all existing tags and build name->id map
resp = requests.get(f"{BASE}/api/tags/", headers=HEADERS)
all_tags = {t['name']: t['id'] for t in resp.json().get('tags', [])}
print(f"Existing tags: {len(all_tags)}")

# Get zip list
zips = sorted([f for f in os.listdir(ZIPS_DIR) if f.endswith('.zip')])

# Create missing breed tags
for zipfile_name in zips:
    breed = zipfile_name.replace('.zip', '')
    if breed not in all_tags:
        r = requests.post(f"{BASE}/api/tags/", headers={**HEADERS, "Content-Type": "application/json"},
                          json={"name": breed, "project_id": PROJECT_ID})
        d = r.json()
        if d.get('status') == 'success':
            all_tags[breed] = d['tag']['id']
            print(f"  Created: {breed}")

print(f"\nUploading {len(zips)} zip files...")
for i, zipfile_name in enumerate(zips):
    breed = zipfile_name.replace('.zip', '')
    breed_tag_id = all_tags.get(breed)
    if not breed_tag_id:
        print(f"  [{i+1}/{len(zips)}] SKIP {breed} - no tag id")
        continue

    tags = json.dumps([
        {"tag_id": DOG_TAG_ID, "name": "Dog"},
        {"tag_id": breed_tag_id, "name": breed}
    ])

    zip_path = os.path.join(ZIPS_DIR, zipfile_name)
    with open(zip_path, 'rb') as f:
        resp = requests.post(f"{BASE}/api/images/", headers=HEADERS,
                             data={"user_id": USER_ID, "project_id": PROJECT_ID, "tags": tags},
                             files={"file": (zipfile_name, f, "application/zip")})

    data = resp.json()
    if data.get('status') == 'success':
        count = len(data.get('images', []))
        print(f"  [{i+1}/{len(zips)}] {breed}: {count} images uploaded")
    else:
        print(f"  [{i+1}/{len(zips)}] {breed}: ERROR - {data.get('message')}")

print("\nDone!")
