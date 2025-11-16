from django.apps import AppConfig

class ThangkaGallaryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Thangka_gallary'

    def ready(self):
        import Thangka_gallary.signals
