from mongoengine import Document, StringField, EmailField, ListField, DateTimeField, IntField, FloatField, ReferenceField, EmbeddedDocument, EmbeddedDocumentField, BooleanField, DictField
import datetime

class Tag(Document):
    name = StringField(max_length=100, required=True)
    project = ReferenceField('Project')
    enabled = BooleanField(default=True)

    meta = {'collection': 'tags'}

class TagReference(EmbeddedDocument):
    tag_id = ReferenceField(Tag, required=True)
    name = StringField(required=True)

class ProjectReference(EmbeddedDocument):
    project_id = ReferenceField('Project', required=True)
    name = StringField(required=True)

class User(Document):
    name = StringField(max_length=100, required=True)
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)
    project_ids = ListField(StringField())
    projects = ListField(EmbeddedDocumentField(ProjectReference))
    created_at = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    is_active = BooleanField(default=True)
    
    meta = {'collection': 'users'}

class ModelVersion(EmbeddedDocument):
    version = IntField(required=True)
    path = StringField()
    format = StringField()
    size = IntField()
    architecture = StringField()
    include_top = BooleanField()
    custom_top_layers = ListField(DictField())
    custom_architecture = ListField(DictField())
    tags = ListField(EmbeddedDocumentField(TagReference))
    epochs = IntField()
    batch_size = IntField()
    img_size = IntField()
    learning_rate = FloatField()
    loss = StringField()
    metrics = ListField(StringField())
    notes = StringField()
    date_created = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))

class TrainedModel(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    project = ReferenceField('Project')
    # Architecture config: use a known Keras arch or "custom"
    architecture = StringField()          # e.g. "VGG19" or "custom"
    include_top = BooleanField(default=True)
    custom_top_layers = ListField(DictField())    # replacement top layers when include_top=False
    custom_architecture = ListField(DictField())  # full layer list when architecture="custom"
    tags = ListField(EmbeddedDocumentField(TagReference))
    # Training hyper-parameters
    epochs = IntField()
    batch_size = IntField()
    img_size = IntField()
    learning_rate = FloatField()
    loss = StringField(default='sparse_categorical_crossentropy')
    metrics = ListField(StringField(), default=lambda: ['accuracy'])
    early_stopping_patience = IntField(default=3)
    early_stopping_min_delta = FloatField(default=0.001)
    # Versioning
    current_version = IntField(default=1)
    versions = ListField(EmbeddedDocumentField(ModelVersion))
    date_created = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    date_updated = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))

    def save(self, *args, **kwargs):
        self.date_updated = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)

    def create_version(self, path=None, format=None, size=None, notes=None, tags=None):
        v = ModelVersion(
            version=self.current_version,
            path=path,
            format=format,
            size=size,
            architecture=self.architecture,
            include_top=self.include_top,
            custom_top_layers=self.custom_top_layers,
            custom_architecture=self.custom_architecture,
            tags=tags or [],
            epochs=self.epochs,
            batch_size=self.batch_size,
            img_size=self.img_size,
            learning_rate=self.learning_rate,
            loss=self.loss,
            metrics=self.metrics,
            notes=notes,
        )
        self.versions.append(v)
        return v

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

class PreTrainedDetectionModel(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    path = StringField(required=True)
    format = StringField()
    size = IntField()
    architecture = StringField()
    task = StringField()
    dataset = StringField()
    enabled = BooleanField(default=True)
    date_created = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    date_updated = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))

    def save(self, *args, **kwargs):
        self.date_updated = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)

    meta = {'collection': 'pretrained_detection_models'}

class PreTrainedDetectionModelReference(EmbeddedDocument):
    model_id = ReferenceField(PreTrainedDetectionModel, required=True)
    name = StringField(required=True)
    description = StringField()

class Project(Document):
    name = StringField(max_length=200, required=True)
    description = StringField()
    tags = ListField(EmbeddedDocumentField(TagReference))
    trained_models = ListField(EmbeddedDocumentField(TrainedModelReference))
    pretrained_models = ListField(EmbeddedDocumentField(PreTrainedModelReference))
    pretrained_detection_models = ListField(EmbeddedDocumentField(PreTrainedDetectionModelReference))
    user = ReferenceField(User)
    date_created = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    date_updated = DateTimeField(default=datetime.datetime.now(datetime.timezone.utc))
    
    def save(self, *args, **kwargs):
        self.date_updated = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)
    
    meta = {'collection': 'projects'}

class Image(Document):
    name = StringField()
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
