import os
import sys

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        is_runserver = 'runserver' in sys.argv
        is_reloader_parent = (
            is_runserver
            and os.environ.get('RUN_MAIN') != 'true'
            and '--noreload' not in sys.argv
        )
        if is_reloader_parent:
            return

        from . import inference
        inference.get_classifier()
