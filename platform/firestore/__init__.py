"""
Firestore and Storage Module

Provides clients for:
- Cloud Firestore (document storage)
- Cloud Storage (raw assets)
- BigQuery (analytics, optional)
"""

from .firestore_client import FirestoreClient, StorageClient, BigQueryClient

__all__ = ['FirestoreClient', 'StorageClient', 'BigQueryClient']

