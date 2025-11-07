from django.db import models
from django.contrib.auth.models import User

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    coins = models.IntegerField(default=10)
    hints = models.IntegerField(default=0)
    freezes = models.IntegerField(default=0)
    super_bananas = models.IntegerField(default=0)
    achievements = models.JSONField(default=list)  # list of unlocked achievement ids
    high_score = models.IntegerField(default=0)
    current_puzzle = models.JSONField(default=dict, blank=True)

class Score(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)