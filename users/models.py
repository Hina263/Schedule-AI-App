from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    google_id = models.CharField(max_length=200, blank=True, null=True, unique=True)

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return self.user.username
