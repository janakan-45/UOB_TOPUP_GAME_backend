from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
import logging

from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    PlayerSerializer,
    ScoreSerializer,
    EmailOTPRequestSerializer,
    EmailOTPVerifySerializer,
)
from .models import Player, Score, OTP

logger = logging.getLogger(__name__)
# @api_view(['POST'])
# @permission_classes([AllowAny])
# def register(request):
#     serializer = RegisterSerializer(data=request.data)
#     if serializer.is_valid():
#         user = serializer.save()
#         refresh = RefreshToken.for_user(user)
#         return Response({
#             'refresh': str(refresh),
#             'access': str(refresh.access_token),
#             'username': user.username,
#         }, status=status.HTTP_201_CREATED)
#     return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        Player.objects.get_or_create(user=user)  # Create linked player profile
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'username': user.username,
        }, status=status.HTTP_201_CREATED)
    return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = CustomTokenObtainPairSerializer(data=request.data)
    if serializer.is_valid():
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

def send_otp_email(email, otp_code):
    try:
        subject = 'Your Banana Game Login OTP'
        message = (
            f'Your OTP for Banana Game login is: {otp_code}\n\n'
            'This OTP is valid for 10 minutes.'
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', None))
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return True
    except Exception as exc:
        logger.error("Failed to send OTP email: %s", exc)
        return False


@api_view(['POST'])
@permission_classes([AllowAny])
def request_email_otp(request):
    serializer = EmailOTPRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']

    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return Response({"detail": "User with this email was not found."}, status=status.HTTP_404_NOT_FOUND)

    otp = OTP.generate_otp(user, OTP.EMAIL, email)

    if not send_otp_email(email, otp.otp_code):
        return Response({"detail": "Failed to send OTP. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {
            "detail": "OTP sent successfully to your email.",
            "expires_in_minutes": 10
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_otp_login(request):
    serializer = EmailOTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    otp_code = serializer.validated_data['otp_code']

    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return Response({"detail": "User with this email was not found."}, status=status.HTTP_404_NOT_FOUND)

    is_valid, message = OTP.verify_otp(user, otp_code, OTP.EMAIL)
    if not is_valid:
        return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'username': user.username,
            'message': 'Login successful via OTP.'
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response({"detail": "Missing refresh token"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"detail": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_all(request):
    tokens = OutstandingToken.objects.filter(user=request.user)

    for outstanding_token in tokens:
        BlacklistedToken.objects.get_or_create(token=outstanding_token)

    return Response({"detail": "Logged out from all sessions"}, status=status.HTTP_205_RESET_CONTENT)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def player_detail(request):
    player, created = Player.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        serializer = PlayerSerializer(player)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = PlayerSerializer(player, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_score(request):
    try:
        score_value = request.data.get('score')

        if score_value is None:
            return Response({"detail": "Missing score field"}, status=status.HTTP_400_BAD_REQUEST)

        # Create the score record
        score_instance = Score.objects.create(user=request.user, score=int(score_value))

        # Update player's high score if this one is higher
        player, created = Player.objects.get_or_create(user=request.user)
        if score_instance.score > player.high_score:
            player.high_score = score_instance.score
            player.save()

        # Return lightweight response for frontend
        return Response({
            "username": request.user.username,
            "score": score_instance.score,
            "message": "Score submitted successfully"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.db.models import Max

@api_view(['GET'])
@permission_classes([AllowAny])
def leaderboard(request):
    # Get the highest score per user
    top_scores = (
        Score.objects
        .values('user__username')
        .annotate(highest_score=Max('score'))
        .order_by('-highest_score')[:10]
    )

    # Format for serializer-like output
    leaderboard_data = [
        {'username': item['user__username'], 'score': item['highest_score']}
        for item in top_scores
    ]

    return Response(leaderboard_data, status=status.HTTP_200_OK)



import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import Player

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_puzzle(request):
    try:
        res = requests.get("https://marcconrad.com/uob/banana/api.php", timeout=5)
        if res.status_code != 200:
            return JsonResponse({"error": "Failed to fetch puzzle"}, status=res.status_code)

        data = res.json()
        player, _ = Player.objects.get_or_create(user=request.user)
        player.current_puzzle = data  # Save the puzzle (includes solution)
        player.save()

        # Remove the solution before sending to the frontend
        data.pop('solution', None)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import Player

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_puzzle_answer(request):
    try:
        user_answer = str(request.data.get('answer', '')).strip()
        if not user_answer:
            return JsonResponse({"error": "Missing answer"}, status=400)

        player, _ = Player.objects.get_or_create(user=request.user)
        puzzle_data = player.current_puzzle or {}

        real_solution = str(puzzle_data.get('solution', '')).strip()
        if not real_solution:
            return JsonResponse({"error": "No puzzle stored. Please fetch again."}, status=400)

        correct = user_answer == real_solution

        # Clear the stored puzzle after checking
        player.current_puzzle = {}
        player.save()

        if correct:
            return JsonResponse({"correct": True})
        else:
            return JsonResponse({"correct": False, "correct_answer": real_solution})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




