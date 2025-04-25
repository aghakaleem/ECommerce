from django.apps import AppConfig


class ApiappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apiApp'

    def ready(self):
        import apiApp.signals
        # Import the signals module to ensure that the signal handlers are registered
