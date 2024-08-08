from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    session_start = models.DateTimeField(verbose_name=_("Session Start"))
    session_stop = models.DateTimeField(verbose_name=_("Session Stop"))
    smartwatch_data_file_path = models.CharField(max_length=255, verbose_name=_("Smartwatch Data File Path"))
    
    def __str__(self):
        return f"{self.user.username} Session {self.session_start.strftime('%Y-%m-%d %H:%M')}"

class Equipment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    equipment_type = models.CharField(max_length=100, verbose_name=_("Equipment Type"))
    equipment_details = models.TextField(verbose_name=_("Equipment Details"))
    
    def __str__(self):
        return f"{self.user.username}'s {self.equipment_type}"
    
class SessionData(models.Model):
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, verbose_name=_("User Session"))
    data = models.JSONField(verbose_name=_("Session Data"))
    type = models.CharField(max_length=100, verbose_name=_("Data Type")) # e.g., 'smartwatch_raw', 'weather', 'processed', etc. pandas dataframe as JSON
    
    def __str__(self):
        return f"Data for {self.session} ({self.type})"