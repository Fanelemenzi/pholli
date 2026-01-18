from django.apps import AppConfig


class PoliciesConfig(AppConfig):
    name = "policies"
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        import policies.signals
