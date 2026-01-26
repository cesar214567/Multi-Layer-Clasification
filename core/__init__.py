import mongoengine
from django.conf import settings

# MongoDB connection
mongoengine.connect(
    db='myapp_db',
    host='localhost',
    port=27017,
    username='admin',
    password='password',
    authentication_source='admin'
)
