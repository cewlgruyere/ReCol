from django.db import models

# Create your models here.
class recol_setting(models.Model):
    default_ui = models.BooleanField(default=False, help_text="If set to true it will default to the normal BallsDex UI while still adding the user parameter.")

