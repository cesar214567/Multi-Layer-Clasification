#!/usr/bin/env python3.10
"""Clean all images, trained models, training jobs from DB and S3, then re-upload all datasets."""
import os, sys, json, requests
sys.stdout.reconfigure(line_buffering=True)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

BASE = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNmExMGFlMmM5MDJiYjFjZGNkMTVkOWJlIiwiZXhwIjoxNzgwMDgxMDE1fQ.ImsvEp49XFFrcqoST_d1oE0LF_4Ufsm_wL0BeWiMgs0"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
HEADERS_JSON = {**HEADERS, "Content-Type": "application/json"}
PROJECT_ID = "6a10ae58902bb1cdcd15d9cc"
USER_ID = "6a10ae2c902bb1cdcd15d9be"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FISH_ZIPS_DIR = os.path.join(SCRIPT_DIR, "NatureConservancyCroppedMerged", "zips")
CAT_ZIPS_DIR = os.path.join(SCRIPT_DIR, "CatBreeds", "zips")
DOG_ZIPS_DIR = os.path.join(SCRIPT_DIR, "stanford-dogs-images", "zips")

# ============================================================
# STEP 1: Delete all trained models and training jobs
# ============================================================
print("=" * 60)
print("STEP 1: Deleting trained models and training jobs...")
print("=" * 60)

import mongoengine
mongoengine.connect(db='myapp_db', host='localhost', port=27017, username='admin', password='password', authentication_source='admin')
from core.models import TrainedModel, TrainingJob, Image, Tag, Project

TrainingJob.objects.delete()
print(f"  Deleted all training jobs")

models = TrainedModel.objects(project=PROJECT_ID)
count = models.count()
models.delete()
print(f"  Deleted {count} trained models")

# Clean trained_models references from project
project = Project.objects(id=PROJECT_ID).first()
if project:
    project.trained_models = []
    project.save()
    print(f"  Cleared project trained_models references")

# ============================================================
# STEP 2: Delete all images from DB and S3
# ============================================================
print("\n" + "=" * 60)
print("STEP 2: Deleting all images from DB and S3...")
print("=" * 60)

import boto3
s3 = boto3.client('s3', endpoint_url='http://localhost:4566', aws_access_key_id='test', aws_secret_access_key='test', region_name='us-east-1')

# Delete all S3 objects
paginator = s3.get_paginator('list_objects_v2')
deleted_s3 = 0
for page in paginator.paginate(Bucket='images'):
    objects = page.get('Contents', [])
    if objects:
        s3.delete_objects(Bucket='images', Delete={'Objects': [{'Key': o['Key']} for o in objects]})
        deleted_s3 += len(objects)
        if deleted_s3 % 5000 == 0:
            print(f"  S3 deleted: {deleted_s3}")
print(f"  S3 total deleted: {deleted_s3}")

# Also clear trained-models bucket
try:
    for page in paginator.paginate(Bucket='trained-models'):
        objects = page.get('Contents', [])
        if objects:
            s3.delete_objects(Bucket='trained-models', Delete={'Objects': [{'Key': o['Key']} for o in objects]})
except:
    pass

# Delete all images from DB
img_count = Image.objects(project=PROJECT_ID).count()
Image.objects(project=PROJECT_ID).delete()
print(f"  DB images deleted: {img_count}")

# ============================================================
# STEP 3: Re-upload all datasets via API (zip upload)
# ============================================================
print("\n" + "=" * 60)
print("STEP 3: Re-uploading all datasets...")
print("=" * 60)

# Use existing token (login not needed)
print(f"  Using existing token")

# Get all tags
resp = requests.get(f"{BASE}/api/tags/", headers=HEADERS, params={"project_id": PROJECT_ID})
all_tags = {t['name']: t['id'] for t in resp.json().get('tags', [])}
print(f"  Found {len(all_tags)} tags")

# Ensure base tags exist
for tag_name in ['FISH', 'Cat', 'Dog']:
    if tag_name not in all_tags:
        r = requests.post(f"{BASE}/api/tags/", headers=HEADERS_JSON, json={"name": tag_name, "project_id": PROJECT_ID})
        if r.json().get('status') == 'success':
            all_tags[tag_name] = r.json()['tag']['id']
            print(f"  Created tag: {tag_name}")

FISH_TAG_ID = all_tags.get('FISH')
CAT_TAG_ID = all_tags.get('Cat')
DOG_TAG_ID = all_tags.get('Dog')

def upload_zip(zip_path, tags_list, label=""):
    """Upload a zip file via the API."""
    tags_json = json.dumps(tags_list)
    with open(zip_path, 'rb') as f:
        resp = requests.post(f"{BASE}/api/images/", headers=HEADERS,
                             data={"user_id": USER_ID, "project_id": PROJECT_ID, "tags": tags_json},
                             files={"file": (os.path.basename(zip_path), f, "application/zip")})
    data = resp.json()
    if data.get('status') == 'success':
        return len(data.get('images', []))
    else:
        print(f"    ERROR {label}: {data.get('message', 'unknown')}")
        return 0

# --- Upload Fish ---
print(f"\n  Uploading Fish ({len(os.listdir(FISH_ZIPS_DIR))} zips)...")
fish_total = 0
fish_zips = sorted([f for f in os.listdir(FISH_ZIPS_DIR) if f.endswith('.zip')])
for i, zipfile in enumerate(fish_zips):
    # Parse species from filename: train_ALB.zip -> ALB
    species = zipfile.replace('.zip', '').split('_', 1)[1] if '_' in zipfile else zipfile.replace('.zip', '')
    species_tag_id = all_tags.get(species)
    tags_list = [{"tag_id": FISH_TAG_ID, "name": "FISH"}]
    if species_tag_id:
        tags_list.append({"tag_id": species_tag_id, "name": species})

    count = upload_zip(os.path.join(FISH_ZIPS_DIR, zipfile), tags_list, zipfile)
    fish_total += count
    print(f"    [{i+1}/{len(fish_zips)}] {zipfile}: {count} images")
print(f"  Fish total: {fish_total}")

# --- Upload Cats ---
print(f"\n  Uploading Cats ({len(os.listdir(CAT_ZIPS_DIR))} zips)...")
cat_total = 0
cat_zips = sorted([f for f in os.listdir(CAT_ZIPS_DIR) if f.endswith('.zip')])
for i, zipfile in enumerate(cat_zips):
    breed = zipfile.replace('.zip', '')
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
    print(f"    [{i+1}/{len(cat_zips)}] {breed}: {count} images")
print(f"  Cats total: {cat_total}")

# --- Upload Dogs ---
print(f"\n  Uploading Dogs ({len(os.listdir(DOG_ZIPS_DIR))} zips)...")
dog_total = 0
dog_zips = sorted([f for f in os.listdir(DOG_ZIPS_DIR) if f.endswith('.zip')])
for i, zipfile in enumerate(dog_zips):
    breed = zipfile.replace('.zip', '')
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
    print(f"    [{i+1}/{len(dog_zips)}] {breed}: {count} images")
print(f"  Dogs total: {dog_total}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print(f"DONE! Uploaded: Fish={fish_total}, Cats={cat_total}, Dogs={dog_total}")
print(f"Total: {fish_total + cat_total + dog_total} images")
print("=" * 60)
