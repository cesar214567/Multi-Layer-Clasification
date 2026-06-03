#!/usr/bin/env python3
"""
Standalone training worker script.
Runs independently of the Django server so training survives server restarts.
Streams images from S3 in batches to avoid OOM.

Usage:
    python3 train_worker.py <job_id> <trained_model_id> <project_id> <version_number>
"""
import sys
import os

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import json
import argparse
import datetime
import tempfile
import shutil

import mongoengine
import boto3
import numpy as np


def connect_db():
    mongoengine.connect(
        db='myapp_db',
        host='localhost',
        port=27017,
        username='admin',
        password='password',
        authentication_source='admin'
    )


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url='http://localhost:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )


def main():
    parser = argparse.ArgumentParser(description='Training worker')
    parser.add_argument('job_id', type=str)
    parser.add_argument('trained_model_id', type=str)
    parser.add_argument('project_id', type=str)
    parser.add_argument('version_number', type=int)
    args = parser.parse_args()

    connect_db()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from core.models import TrainingJob, TrainedModel, Project, Image, EpochMetrics

    job = TrainingJob.objects(id=args.job_id).first()
    if not job:
        print(f"ERROR: Job {args.job_id} not found", file=sys.stderr)
        sys.exit(1)

    job.status = 'running'
    job.message = 'Training process started'
    job.save()

    try:
        import tensorflow as tf
        import tensorflow.keras as keras

        trained_model = TrainedModel.objects(id=args.trained_model_id).first()
        project = Project.objects(id=args.project_id).first()

        if not trained_model or not project:
            raise ValueError("TrainedModel or Project not found")

        # --- Collect image metadata (not the actual images) ---
        s3_keys = []
        bucket_names = []
        label_indices = []

        unique_tag_names = sorted([t.name for t in trained_model.tags])
        label_to_idx = {name: i for i, name in enumerate(unique_tag_names)}
        num_classes = len(trained_model.tags)

        for tag_ref in trained_model.tags:
            tag_images = Image.objects(project=project, tag_references__tag_id=tag_ref.tag_id)
            idx = label_to_idx[tag_ref.name]
            for img in tag_images:
                s3_keys.append(img.key)
                bucket_names.append(img.bucket_name)
                label_indices.append(idx)

        if not s3_keys:
            job.status = 'error'
            job.message = 'No images found for the trained model tags in this project'
            job.finished_at = datetime.datetime.utcnow()
            job.save()
            return

        total_images = len(s3_keys)
        epochs = trained_model.epochs
        batch_size = trained_model.batch_size
        img_size = trained_model.img_size
        lr = trained_model.learning_rate

        job.message = f'Preparing training: {total_images} images, {num_classes} classes'
        job.save()

        # --- Stratified split ---
        from collections import defaultdict
        class_indices = defaultdict(list)
        for i, l in enumerate(label_indices):
            class_indices[l].append(i)
        rng = np.random.default_rng(42)
        train_indices = []
        val_indices = []
        for cls, idxs in class_indices.items():
            idxs = rng.permutation(idxs).tolist()
            val_size = max(1, int(len(idxs) * 0.2))
            val_indices.extend(idxs[:val_size])
            train_indices.extend(idxs[val_size:])

        # --- Preprocessing function ---
        preprocess_fn = None
        arch_modules = {
            'MobileNetV2': keras.applications.mobilenet_v2,
            'EfficientNetB0': keras.applications.efficientnet,
            'EfficientNetB1': keras.applications.efficientnet,
            'EfficientNetB2': keras.applications.efficientnet,
            'ResNet50': keras.applications.resnet,
            'VGG19': keras.applications.vgg19,
            'InceptionV3': keras.applications.inception_v3,
        }
        module = arch_modules.get(trained_model.architecture)
        if module:
            preprocess_fn = module.preprocess_input

        # --- S3 streaming generator ---
        s3_client = get_s3_client()

        def s3_batch_generator(indices, shuffle=False):
            """Yields (batch_images, batch_labels) by streaming from S3."""
            idx_array = np.array(indices)
            while True:
                if shuffle:
                    rng.shuffle(idx_array)
                for start in range(0, len(idx_array), batch_size):
                    batch_idx = idx_array[start:start + batch_size]
                    batch_images = []
                    batch_labels = []
                    for i in batch_idx:
                        try:
                            response = s3_client.get_object(Bucket=bucket_names[i], Key=s3_keys[i])
                            img_bytes = response['Body'].read()
                            img = tf.io.decode_jpeg(img_bytes, channels=3, try_recover_truncated=True, acceptable_fraction=0.5)
                            img = tf.image.resize(img, [img_size, img_size])
                            img = tf.cast(img, tf.float32)
                            if preprocess_fn is not None:
                                img = preprocess_fn(img)
                            else:
                                img = img / 255.0
                            batch_images.append(img)
                            batch_labels.append(label_indices[i])
                        except Exception:
                            continue  # skip corrupt images
                    if not batch_images:
                        continue
                    images_tensor = tf.stack(batch_images)
                    labels_tensor = tf.keras.utils.to_categorical(batch_labels, num_classes=num_classes)
                    yield images_tensor.numpy(), labels_tensor

        # Create tf.data.Dataset from generator
        output_sig = (
            tf.TensorSpec(shape=(None, img_size, img_size, 3), dtype=tf.float32),
            tf.TensorSpec(shape=(None, num_classes), dtype=tf.float32),
        )

        train_steps = len(train_indices) // batch_size
        val_steps = len(val_indices) // batch_size

        train_ds = tf.data.Dataset.from_generator(
            lambda: s3_batch_generator(train_indices, shuffle=True),
            output_signature=output_sig
        ).prefetch(2)

        val_ds = tf.data.Dataset.from_generator(
            lambda: s3_batch_generator(val_indices, shuffle=False),
            output_signature=output_sig
        ).prefetch(2)

        # --- Build model ---
        input_shape = (img_size, img_size, 3)

        if trained_model.architecture == 'custom':
            keras_model = keras.Sequential()
            for layer_def in trained_model.custom_architecture:
                layer_type = layer_def.get('type')
                layer_cls = getattr(keras.layers, layer_type, None)
                if layer_cls is None:
                    raise ValueError(f'Unknown layer type "{layer_type}"')
                params = {k: v for k, v in layer_def.items() if k != 'type'}
                keras_model.add(layer_cls(**params))
        else:
            arch_class = getattr(keras.applications, trained_model.architecture)
            base = arch_class(
                weights='imagenet',
                include_top=trained_model.include_top,
                input_shape=input_shape if not trained_model.include_top else None,
            )

            if trained_model.include_top:
                base.trainable = False
                base_out = base.layers[-2].output
                output = keras.layers.Dense(num_classes, activation='softmax')(base_out)
                keras_model = keras.Model(inputs=base.input, outputs=output)
            else:
                base.trainable = False
                layers = [base]
                if trained_model.custom_top_layers:
                    for layer_def in trained_model.custom_top_layers:
                        layer_type = layer_def.get('type')
                        layer_cls = getattr(keras.layers, layer_type, None)
                        if layer_cls is None:
                            raise ValueError(f'Unknown layer type "{layer_type}"')
                        params = {k: v for k, v in layer_def.items() if k != 'type'}
                        layers.append(layer_cls(**params))
                else:
                    layers.append(keras.layers.GlobalAveragePooling2D())
                    layers.append(keras.layers.Dense(num_classes, activation='softmax'))
                keras_model = keras.Sequential(layers)

        resolved_metrics = []
        for m in (trained_model.metrics or ['accuracy']):
            if m == 'f1_score':
                resolved_metrics.append(keras.metrics.F1Score(average='macro', name='f1_score'))
            else:
                resolved_metrics.append(m)

        keras_model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=lr),
            loss=trained_model.loss or 'categorical_crossentropy',
            metrics=resolved_metrics,
        )

        # --- Train ---
        class EpochProgressCallback(keras.callbacks.Callback):
            def on_epoch_end(self, epoch, logs=None):
                job.reload()
                job.message = f'Epoch {epoch + 1}/{epochs} completed'
                job.metrics = {k: float(v) for k, v in (logs or {}).items()}
                job.epoch_history.append(EpochMetrics(epoch=epoch+1, metrics={k: float(v) for k, v in (logs or {}).items()}))
                job.save()

        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=trained_model.early_stopping_patience or 3,
            min_delta=trained_model.early_stopping_min_delta or 0.001, restore_best_weights=True
        )

        history = keras_model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=epochs,
            steps_per_epoch=train_steps,
            validation_steps=val_steps,
            callbacks=[early_stop, EpochProgressCallback()]
        )

        # --- Save weights to S3 ---
        with tempfile.NamedTemporaryFile(suffix='.weights.h5', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            keras_model.save_weights(tmp_path)
            file_size = os.path.getsize(tmp_path)
            with open(tmp_path, 'rb') as f:
                model_bytes = f.read()
        finally:
            os.unlink(tmp_path)

        bucket_name = 'trained-models'
        try:
            s3_client.create_bucket(Bucket=bucket_name)
        except:
            pass
        s3_key = f'trained-models/{trained_model.name}_v{args.version_number}.weights.h5'
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=model_bytes)

        s3_path = f's3://{bucket_name}/{s3_key}'

        # --- Mark version as ready ---
        trained_model.reload()
        for v in trained_model.versions:
            if v.version == args.version_number:
                v.path = s3_path
                v.format = 'h5'
                v.size = file_size
                v.ready = True
                break
        trained_model.save()

        final_metrics = {k: float(v[-1]) for k, v in history.history.items()}

        job.reload()
        job.status = 'success'
        job.message = 'Model trained and saved'
        job.metrics = final_metrics
        job.finished_at = datetime.datetime.utcnow()
        job.save()

        print(f"Training completed successfully. Job: {args.job_id}")

    except Exception as e:
        job.reload()
        job.status = 'error'
        job.message = str(e)
        job.finished_at = datetime.datetime.utcnow()
        job.save()
        print(f"Training failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
