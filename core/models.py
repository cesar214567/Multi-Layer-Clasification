from mongoengine import Document, StringField, EmailField, ListField, DictField, DateTimeField, IntField, ReferenceField, EmbeddedDocument, EmbeddedDocumentField, BooleanField
import datetime

class Tag(Document):
    numeric_id = IntField(required=True, unique=True)
    name = StringField(max_length=100, required=True)
    
    meta = {'collection': 'tags'}

class TagReference(EmbeddedDocument):
    tag_id = ReferenceField(Tag, required=True)
    numeric_id = IntField(required=True)

class User(Document):
    name = StringField(max_length=100, required=True)
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)
    project_ids = ListField(StringField())
    created_at = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    is_active = BooleanField(default=True)
    
    meta = {'collection': 'users'}

class Project(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    tags = DictField()
    user = ReferenceField(User)
    date_created = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    date_updated = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    
    def save(self, *args, **kwargs):
        self.date_updated = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)
    
    meta = {'collection': 'projects'}

class Image(Document):
    path = StringField(required=True)
    bucket_name = StringField(required=True)
    key = StringField(required=True)
    size = IntField()
    format = StringField()
    content_type = StringField()
    etag = StringField()
    last_modified = DateTimeField()
    project = ReferenceField(Project)
    tag_references = ListField(EmbeddedDocumentField(TagReference))
    
    def save(self, *args, **kwargs):
        # Sort tag_references by numeric_id before saving
        self.tag_references.sort(key=lambda x: x.numeric_id)
        return super().save(*args, **kwargs)
    
    meta = {'collection': 'images'}
