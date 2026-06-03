#!/usr/bin/env python3
"""Re-upload NatureConservancyCroppedMerged images with JPEG validation."""
import os
import sys
import datetime
import mongoengine
import boto3
import tensorflow as tf

# Suppress TF warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

mongoengine.connect(db='myapp_db', host='localhost', port=27017, username='admin', password='password', authentication_source='admin')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.models import Image, Tag, Project, TagReference

# Config
USER_ID = '6a10ae2c902bb1cdcd15d9be'
PROJECT_ID = '6a10ae58902bb1cdcd15d9cc'
BUCKET = 'images'
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'NatureConservancyCroppedMerged')
FISH_TAG_ID = '6a10aface0727390cb67df81'

SPECIES_TAG_IDS = {
    'ALB': '6a10ae35902bb1cdcd15d9bf',
    'BET': '6a10ae35902bb1cdcd15d9c0',
    'DOL': '6a10ae35902bb1cdcd15d9c1',
    'LAG': '6a10ae35902bb1cdcd15d9c2',
    'MugilCephalus': '6a10ae35902bb1cdcd15d9c3',
    'OTHER': '6a10ae35902bb1cdcd15d9c4',
    'RhinobatosCemiculus': '6a10ae35902bb1cdcd15d9c5',
    'ScomberJaponicus': '6a10ae35902bb1cdcd15d9c6',
    'SHARK': '6a10ae35902bb1cdcd15d9c7',
    'TetrapturusBelone': '6a10ae35902bb1cdcd15d9c8',
    'Trout': '6a10ae35902bb1cdcd15d9c9',
    'YFT': '6a10ae35902bb1cdcd15d9ca',
}

def validate_image(data):
    """Return True if image is fully decodable and resizable."""
    try:
        img = tf.io.decode_jpeg(data, channels=3, try_recover_truncated=True, acceptable_fraction=0.8)
        img = tf.image.resize(img, [224, 224])
        img.numpy()
        return True
    except:
        return False

def main():
    s3 = boto3.client('s3', endpoint_url='http://localhost:4566', aws_access_key_id='test', aws_secret_access_key='test', region_name='us-east-1')
    try:
        s3.create_bucket(Bucket=BUCKET)
    except:
        pass

    project = Project.objects(id=PROJECT_ID).first()
    fish_tag = Tag.objects(id=FISH_TAG_ID).first()

    uploaded = 0
    invalid = 0
    invalid_files = []

    for split in ['train', 'test']:
        split_dir = os.path.join(BASE_DIR, split)
        if not os.path.isdir(split_dir):
            continue
        for species in sorted(os.listdir(split_dir)):
            species_dir = os.path.join(split_dir, species)
            if not os.path.isdir(species_dir) or species not in SPECIES_TAG_IDS:
                continue

            species_tag = Tag.objects(id=SPECIES_TAG_IDS[species]).first()
            tag_refs = [
                TagReference(tag_id=fish_tag, name='FISH'),
                TagReference(tag_id=species_tag, name=species),
            ]

            files = sorted(os.listdir(species_dir))
            for filename in files:
                filepath = os.path.join(species_dir, filename)
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    continue

                with open(filepath, 'rb') as f:
                    data = f.read()

                if not validate_image(data):
                    invalid += 1
                    invalid_files.append(f'{split}/{species}/{filename}')
                    continue

                s3_key = f'{USER_ID}/{PROJECT_ID}/{os.urandom(4).hex()}_{filename}'
                s3.put_object(Bucket=BUCKET, Key=s3_key, Body=data)

                img = Image(
                    name=filename,
                    path=f's3://{BUCKET}/{s3_key}',
                    bucket_name=BUCKET,
                    key=s3_key,
                    size=len(data),
                    format=filename.rsplit('.', 1)[-1],
                    content_type='image/jpeg',
                    project=project,
                    tag_references=tag_refs,
                )
                img.save()
                uploaded += 1

                if uploaded % 1000 == 0:
                    print(f'Uploaded: {uploaded} | Invalid: {invalid}')

    print(f'\nDone! Uploaded: {uploaded} | Invalid: {invalid}')
    if invalid_files:
        print(f'\nInvalid files:')
        for f in invalid_files:
            print(f'  {f}')

if __name__ == '__main__':
    main()
