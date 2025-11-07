from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Player, Score

def validate_register_data(data):
    if not data.get('username') or len(data['username']) < 3:
        raise ValidationError({"username": "Username must be at least 3 characters"})
    
    if not data.get('password') or len(data['password']) < 6:
        raise ValidationError({"password": "Password must be at least 6 characters"})
    
    if data.get('password') != data.get('confirm_password'):
        raise ValidationError({"confirm_password": "Passwords don't match"})
    
    if User.objects.filter(email=data['email']).exists():
        raise ValidationError({"email": "Email already exists"})
    
    if User.objects.filter(username=data['username']).exists():
        raise ValidationError({"username": "Username taken"})
    
    return data

class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'username': {'required': True},
        }

    def validate(self, data):
        return validate_register_data(data)

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'] = serializers.CharField()
        self.fields['password'] = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise ValidationError({"detail": "Missing fields"})

        authenticated_user = authenticate(username=username, password=password)
        if not authenticated_user:
            raise ValidationError({"detail": "Invalid username or password"})

        refresh = RefreshToken.for_user(authenticated_user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'username': authenticated_user.username,
        }

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['coins', 'hints', 'freezes', 'super_bananas', 'achievements', 'high_score']

class ScoreSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Score
        fields = ['username', 'score', 'date']

        