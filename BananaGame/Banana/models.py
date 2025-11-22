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
    # New game mechanics
    xp = models.IntegerField(default=0)  # Experience points
    level = models.IntegerField(default=1)  # Player level
    difficulty = models.CharField(max_length=10, default='medium', choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')])
    combo_count = models.IntegerField(default=0)  # Current combo streak
    max_combo = models.IntegerField(default=0)  # Maximum combo achieved
    puzzles_solved = models.IntegerField(default=0)  # Total puzzles solved
    perfect_solves = models.IntegerField(default=0)  # Puzzles solved without hints
    last_daily_challenge = models.DateField(null=True, blank=True)  # Last daily challenge date
    daily_challenge_streak = models.IntegerField(default=0)  # Consecutive daily challenges
    puzzle_history = models.JSONField(default=list)  # Track solved puzzle IDs

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


class Contact(models.Model):
    """Contact form submissions"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class Rating(models.Model):
    """User ratings for the game"""
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user']  # One rating per user
    
    def __str__(self):
        return f"{self.user.username} - {self.rating} stars"


class Review(models.Model):
    """User reviews for the game"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    title = models.CharField(max_length=200)
    content = models.TextField()
    rating = models.IntegerField(choices=Rating.RATING_CHOICES, null=True, blank=True)
    is_approved = models.BooleanField(default=False)  # Admin can approve reviews
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"