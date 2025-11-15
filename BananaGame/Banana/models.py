from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

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


class OTP(models.Model):
    EMAIL = 'email'

    OTP_TYPE_CHOICES = (
        (EMAIL, 'Email'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=20, choices=OTP_TYPE_CHOICES)
    contact_info = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def _generate_code(cls):
        return f"{random.randint(100000, 999999)}"

    @classmethod
    def generate_otp(cls, user, otp_type, contact_info, validity_minutes=10):
        cls.objects.filter(
            user=user,
            otp_type=otp_type,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True)

        otp_code = cls._generate_code()
        expires_at = timezone.now() + timedelta(minutes=validity_minutes)

        return cls.objects.create(
            user=user,
            otp_code=otp_code,
            otp_type=otp_type,
            contact_info=contact_info,
            expires_at=expires_at
        )

    @classmethod
    def verify_otp(cls, user, otp_code, otp_type):
        otp = cls.objects.filter(
            user=user,
            otp_type=otp_type,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()

        if not otp:
            return False, "OTP has expired or does not exist."

        if otp.otp_code != otp_code:
            return False, "Invalid OTP provided."

        otp.is_used = True
        otp.save(update_fields=['is_used'])
        return True, "OTP verified successfully."