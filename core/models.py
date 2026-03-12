from mongoengine import Document, StringField, EmailField, ListField, DateTimeField, IntField, ReferenceField, EmbeddedDocument, EmbeddedDocumentField, BooleanField
import datetime

class Tag(Document):
    name = StringField(max_length=100, required=True)
    project = ReferenceField('Project')

    meta = {'collection': 'tags'}

class TagReference(EmbeddedDocument):
    tag_id = ReferenceField(Tag, required=True)
    name = StringField(required=True)

class User(Document):
    name = StringField(max_length=100, required=True)
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)
    project_ids = ListField(StringField())
    created_at = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    is_active = BooleanField(default=True)
    
    meta = {'collection': 'users'}

class TrainedModel(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    path = StringField(required=True)
    format = StringField()
    size = IntField()
    date_created = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    date_updated = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))

    def save(self, *args, **kwargs):
        self.date_updated = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)

    meta = {'collection': 'trained_models'}

class TrainedModelReference(EmbeddedDocument):
    model_id = ReferenceField(TrainedModel, required=True)
    name = StringField(required=True)
    description = StringField()

class PreTrainedModel(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    path = StringField(required=True)
    format = StringField()
    size = IntField()
    enabled = BooleanField()
    date_created = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    date_updated = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))

    def save(self, *args, **kwargs):
        self.date_updated = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)

    meta = {'collection': 'pretrained_models'}

class PreTrainedModelReference(EmbeddedDocument):
    model_id = ReferenceField(PreTrainedModel, required=True)
    name = StringField(required=True)
    description = StringField()

class Project(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    tags = ListField(EmbeddedDocumentField(TagReference))
    trained_models = ListField(EmbeddedDocumentField(TrainedModelReference))
    pretrained_models = ListField(EmbeddedDocumentField(PreTrainedModelReference))
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
        return super().save(*args, **kwargs)
    
    meta = {'collection': 'images'}
