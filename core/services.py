import boto3
from pymongo import MongoClient
from django.conf import settings

class S3Service:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
    
    def create_bucket(self, bucket_name):
        try:
            return self.client.create_bucket(Bucket=bucket_name)
        except:
            pass  # Bucket might already exist
    
    def upload_file(self, bucket_name, key, data):
        response = self.client.put_object(Bucket=bucket_name, Key=key, Body=data)
        
        # Get object metadata
        obj_info = self.client.head_object(Bucket=bucket_name, Key=key)
        
        return {
            'etag': response.get('ETag', '').strip('"'),
            'size': obj_info.get('ContentLength'),
            'content_type': obj_info.get('ContentType'),
            'last_modified': obj_info.get('LastModified'),
            'path': f's3://{bucket_name}/{key}'
        }
