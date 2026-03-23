"""
Tasks package for Celery background jobs
"""
from .celery import celery

__all__ = ['celery']
