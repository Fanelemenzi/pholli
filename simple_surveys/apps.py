from django.apps import AppConfig


class SimpleSurveysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "simple_surveys"
    verbose_name = "Simple Surveys"
    
    def ready(self):
        """Import signal handlers when the app is ready"""
        # Import any signals here if needed in the future
        pass
