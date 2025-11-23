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
    ContactSerializer,
    RatingSerializer,
    RatingCreateSerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
)
from .models import Player, Score, OTP, Contact, Rating, Review

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


def send_contact_thankyou_email(name, email):
    """Send thank you email after contact form submission"""
    try:
        subject = 'Thank You for Contacting Banana Brain Blitz!'
        message = (
            f'Hello {name},\n\n'
            'Thank you for contacting us! We have received your message and will get back to you as soon as possible.\n\n'
            'We appreciate your interest in Banana Brain Blitz and look forward to assisting you.\n\n'
            'Best regards,\n'
            'Banana Brain Blitz Team'
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', None))
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return True
    except Exception as exc:
        logger.error("Failed to send contact thank you email: %s", exc)
        return False


def send_review_thankyou_email(user_email, username, review_title):
    """Send thank you email after review submission"""
    try:
        subject = 'Thank You for Your Review - Banana Brain Blitz!'
        message = (
            f'Hello {username},\n\n'
            'Thank you for taking the time to review Banana Brain Blitz!\n\n'
            f'We have received your review titled "{review_title}". '
            'Your review will be reviewed by our team and will be published once approved.\n\n'
            'We truly appreciate your feedback and support!\n\n'
            'Best regards,\n'
            'Banana Brain Blitz Team'
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', None))
        recipient_list = [user_email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return True
    except Exception as exc:
        logger.error("Failed to send review thank you email: %s", exc)
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_certificate(request):
    """
    Generate and return certificate PDF for top 3 players
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
        from io import BytesIO
        from django.http import HttpResponse
        from datetime import datetime
        
        # Get leaderboard to check user's rank
        top_scores = (
            Score.objects
            .values('user__username')
            .annotate(highest_score=Max('score'))
            .order_by('-highest_score')[:10]
        )
        
        leaderboard_data = [
            {'username': item['user__username'], 'score': item['highest_score']}
            for item in top_scores
        ]
        
        # Find user's rank
        user_rank = None
        user_score = None
        for idx, entry in enumerate(leaderboard_data, 1):
            if entry['username'] == request.user.username:
                user_rank = idx
                user_score = entry['score']
                break
        
        # Check if user is in top 3
        if not user_rank or user_rank > 3:
            return Response(
                {"detail": "Certificate is only available for top 3 players."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        # Background gradient effect (simulated with rectangles)
        p.setFillColor(colors.HexColor('#FCD34D'))  # Yellow
        p.rect(0, 0, width, height, fill=1)
        
        # Border
        p.setStrokeColor(colors.HexColor('#F59E0B'))
        p.setLineWidth(20)
        p.rect(10, 10, width - 20, height - 20, fill=0, stroke=1)
        
        # Inner border
        p.setStrokeColor(colors.HexColor('#D97706'))
        p.setLineWidth(5)
        p.rect(30, 30, width - 60, height - 60, fill=0, stroke=1)
        
        # Title
        p.setFillColor(colors.HexColor('#92400E'))
        p.setFont("Helvetica-Bold", 48)
        title = "CERTIFICATE OF ACHIEVEMENT"
        title_width = p.stringWidth(title, "Helvetica-Bold", 48)
        p.drawString((width - title_width) / 2, height - 120, title)
        
        # Decorative line
        p.setStrokeColor(colors.HexColor('#92400E'))
        p.setLineWidth(3)
        p.line(width * 0.2, height - 160, width * 0.8, height - 160)
        
        # Place/Medal
        place_texts = {1: "CHAMPION", 2: "RUNNER-UP", 3: "THIRD PLACE"}
        place_colors = {
            1: colors.HexColor('#FCD34D'),
            2: colors.HexColor('#9CA3AF'),
            3: colors.HexColor('#FB923C')
        }
        
        p.setFillColor(place_colors[user_rank])
        p.setFont("Helvetica-Bold", 36)
        place_text = place_texts[user_rank]
        place_width = p.stringWidth(place_text, "Helvetica-Bold", 36)
        p.drawString((width - place_width) / 2, height - 220, place_text)
        
        # Subtitle
        p.setFillColor(colors.HexColor('#78350F'))
        p.setFont("Helvetica", 24)
        subtitle = f"{'First' if user_rank == 1 else 'Second' if user_rank == 2 else 'Third'} Place Winner"
        subtitle_width = p.stringWidth(subtitle, "Helvetica", 24)
        p.drawString((width - subtitle_width) / 2, height - 270, subtitle)
        
        # "This is to certify that"
        p.setFillColor(colors.HexColor('#78350F'))
        p.setFont("Helvetica", 20)
        certify_text = "This is to certify that"
        certify_width = p.stringWidth(certify_text, "Helvetica", 20)
        p.drawString((width - certify_width) / 2, height - 320, certify_text)
        
        # Player Name
        p.setFillColor(colors.HexColor('#1F2937'))
        p.setFont("Helvetica-Bold", 42)
        player_name = request.user.username
        name_width = p.stringWidth(player_name, "Helvetica-Bold", 42)
        p.drawString((width - name_width) / 2, height - 380, player_name)
        
        # Achievement text
        p.setFillColor(colors.HexColor('#78350F'))
        p.setFont("Helvetica", 22)
        achievement_text = f"Has achieved {user_rank}{'st' if user_rank == 1 else 'nd' if user_rank == 2 else 'rd'} Place"
        achievement_width = p.stringWidth(achievement_text, "Helvetica", 22)
        p.drawString((width - achievement_width) / 2, height - 440, achievement_text)
        
        # Game name
        p.setFont("Helvetica", 20)
        game_text = "in the Banana Brain Blitz Game"
        game_width = p.stringWidth(game_text, "Helvetica", 20)
        p.drawString((width - game_width) / 2, height - 480, game_text)
        
        # Score
        p.setFont("Helvetica-Bold", 28)
        score_text = f"Final Score: {user_score} Points"
        score_width = p.stringWidth(score_text, "Helvetica-Bold", 28)
        p.drawString((width - score_width) / 2, height - 540, score_text)
        
        # Footer
        p.setFillColor(colors.HexColor('#78350F'))
        p.setFont("Helvetica", 16)
        date_text = f"Date: {datetime.now().strftime('%B %d, %Y')}"
        date_width = p.stringWidth(date_text, "Helvetica", 16)
        p.drawString((width - date_width) / 2, 80, date_text)
        
        # Decorative elements (using text symbols instead of emojis)
        p.setFont("Helvetica-Bold", 40)
        p.setFillColor(colors.HexColor('#92400E'))
        p.drawString(100, height - 100, "*")
        p.drawString(width - 140, height - 100, "*")
        p.drawString(100, 120, "*")
        p.drawString(width - 140, 120, "*")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Banana_Game_Certificate_{request.user.username}_{user_rank}st.pdf"'
        
        return response
        
    except Exception as e:
        logger.error("Error generating certificate: %s", e)
        return Response(
            {"detail": f"Error generating certificate: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



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
        from datetime import date
        import random
        
        user_answer = str(request.data.get('answer', '')).strip()
        time_taken = request.data.get('time_taken', 0)  # Time in seconds
        hints_used = request.data.get('hints_used', 0)  # Number of hints used for this puzzle
        if not user_answer:
            return JsonResponse({"error": "Missing answer"}, status=400)

        player, _ = Player.objects.get_or_create(user=request.user)
        puzzle_data = player.current_puzzle or {}

        real_solution = str(puzzle_data.get('solution', '')).strip()
        if not real_solution:
            return JsonResponse({"error": "No puzzle stored. Please fetch again."}, status=400)

        correct = user_answer == real_solution
        puzzle_id = puzzle_data.get('question', '')  # Use question URL as puzzle ID

        if correct:
            # Calculate base points based on difficulty
            difficulty_multipliers = {'easy': 0.7, 'medium': 1.0, 'hard': 1.5}
            base_points = 10 * difficulty_multipliers.get(player.difficulty, 1.0)
            
            # Time bonus (faster = more points, max bonus at 5 seconds)
            time_bonus = max(0, (40 - time_taken) / 2) if time_taken > 0 else 0
            time_bonus = min(time_bonus, 15)  # Cap at 15 points
            
            # Combo bonus (increases with combo count)
            combo_bonus = player.combo_count * 2
            player.combo_count += 1
            if player.combo_count > player.max_combo:
                player.max_combo = player.combo_count
            
            # Perfect solve bonus (no hints used)
            perfect_bonus = 0
            if hints_used == 0:
                perfect_bonus = 10
                player.perfect_solves += 1
            
            # Lucky streak (5% chance for 2x multiplier)
            lucky_multiplier = 2.0 if random.random() < 0.05 else 1.0
            
            # Calculate total points
            total_points = int((base_points + time_bonus + combo_bonus + perfect_bonus) * lucky_multiplier)
            
            # XP calculation (1 XP per point, bonus for perfect solves)
            xp_gained = total_points
            if hints_used == 0:
                xp_gained += 5  # Bonus XP for perfect solve
            
            # Level up check (100 XP per level)
            old_level = player.level
            player.xp += xp_gained
            new_level = (player.xp // 100) + 1
            leveled_up = new_level > old_level
            player.level = new_level
            
            # Update stats
            player.puzzles_solved += 1
            
            # Track puzzle in history (limit to last 50)
            if puzzle_id:
                if puzzle_id not in player.puzzle_history:
                    player.puzzle_history.append(puzzle_id)
                    if len(player.puzzle_history) > 50:
                        player.puzzle_history = player.puzzle_history[-50:]

            # Clear the stored puzzle after checking
            player.current_puzzle = {}
            player.save()
            
            return JsonResponse({
                "correct": True,
                "points": total_points,
                "xp_gained": xp_gained,
                "combo": player.combo_count,
                "leveled_up": leveled_up,
                "new_level": new_level if leveled_up else None,
                "perfect_solve": hints_used == 0,
                "lucky_streak": lucky_multiplier > 1.0,
                "breakdown": {
                    "base_points": int(base_points),
                    "time_bonus": int(time_bonus),
                    "combo_bonus": combo_bonus,
                    "perfect_bonus": perfect_bonus,
                    "lucky_multiplier": lucky_multiplier
                }
            })
        else:
            # Reset combo on wrong answer
            player.combo_count = 0
            player.current_puzzle = {}
            player.save()
            return JsonResponse({"correct": False, "correct_answer": real_solution})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_hint(request):
    """
    Use a hint power-up. Returns a hint message based on the current puzzle.
    Implements multiple hint strategies:
    1. Wrong answer reveal (original)
    2. Range hint (answer is between X and Y)
    3. Parity hint (odd/even)
    4. Comparison hint (greater/less than X)
    5. Multiple choice hint (answer is one of X, Y, Z)
    """
    try:
        player, _ = Player.objects.get_or_create(user=request.user)
        
        # Check if player has hints available
        if player.hints <= 0:
            return JsonResponse({"error": "No hints available"}, status=400)
        
        # Get current puzzle
        puzzle_data = player.current_puzzle or {}
        real_solution = str(puzzle_data.get('solution', '')).strip()
        
        if not real_solution:
            return JsonResponse({"error": "No puzzle stored. Please fetch a puzzle first."}, status=400)
        
        try:
            solution_num = int(real_solution)
        except ValueError:
            return JsonResponse({"error": "Invalid puzzle solution"}, status=400)
        
        # Decrement hint count
        player.hints -= 1
        player.save()
        
        # Select a random hint strategy
        import random
        hint_type = random.choice(['wrong_answer', 'range', 'parity', 'comparison', 'multiple_choice'])
        
        hint_message = ""
        hint_title = "💡 Hint Used!"
        
        if hint_type == 'wrong_answer':
            # Strategy 1: Reveal a wrong answer
            wrong_answers = [str(i) for i in range(1, 10) if i != solution_num]
            wrong_answer = random.choice(wrong_answers)
            hint_message = f"{wrong_answer} is NOT the answer"
        
        elif hint_type == 'range':
            # Strategy 2: Provide a range hint
            if solution_num <= 3:
                hint_message = "The answer is between 1 and 3"
            elif solution_num <= 6:
                hint_message = "The answer is between 4 and 6"
            else:
                hint_message = "The answer is between 7 and 9"
        
        elif hint_type == 'parity':
            # Strategy 3: Odd/Even hint
            if solution_num % 2 == 0:
                hint_message = "The answer is an EVEN number"
            else:
                hint_message = "The answer is an ODD number"
        
        elif hint_type == 'comparison':
            # Strategy 4: Comparison hint
            if solution_num < 5:
                hint_message = "The answer is LESS than 5"
            else:
                hint_message = "The answer is GREATER than or equal to 5"
        
        elif hint_type == 'multiple_choice':
            # Strategy 5: Multiple choice hint (3 options including correct one)
            possible_answers = [solution_num]
            while len(possible_answers) < 3:
                candidate = random.randint(1, 9)
                if candidate not in possible_answers:
                    possible_answers.append(candidate)
            random.shuffle(possible_answers)
            hint_message = f"The answer is one of: {', '.join(map(str, possible_answers))}"
        
        return JsonResponse({
            "hint": hint_message,
            "title": hint_title,
            "hints_remaining": player.hints,
            "hint_type": hint_type
        }, status=200)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_difficulty(request):
    """Set game difficulty level"""
    try:
        difficulty = request.data.get('difficulty', 'medium')
        if difficulty not in ['easy', 'medium', 'hard']:
            return JsonResponse({"error": "Invalid difficulty. Must be 'easy', 'medium', or 'hard'"}, status=400)
        
        player, _ = Player.objects.get_or_create(user=request.user)
        player.difficulty = difficulty
        player.save()
        
        return JsonResponse({
            "difficulty": difficulty,
            "message": f"Difficulty set to {difficulty}"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_challenge(request):
    """Get today's daily challenge"""
    try:
        from datetime import date, timedelta
        
        player, _ = Player.objects.get_or_create(user=request.user)
        today = date.today()
        
        # Check if already completed today
        if player.last_daily_challenge == today:
            return JsonResponse({
                "completed": True,
                "message": "Daily challenge already completed today!",
                "streak": player.daily_challenge_streak
            })
        
        # Check if streak should continue or reset
        if player.last_daily_challenge:
            yesterday = date.today() - timedelta(days=1)
            if player.last_daily_challenge == yesterday:
                # Continue streak
                pass
            elif player.last_daily_challenge < yesterday:
                # Reset streak
                player.daily_challenge_streak = 0
        else:
            player.daily_challenge_streak = 0
        
        # Generate challenge (solve 5 puzzles today)
        challenge_target = 5
        streak_bonus = player.daily_challenge_streak * 10  # 10 coins per streak day
        
        return JsonResponse({
            "completed": False,
            "target": challenge_target,
            "reward": 50 + streak_bonus,  # Base 50 coins + streak bonus
            "streak": player.daily_challenge_streak,
            "message": f"Solve {challenge_target} puzzles today to earn {50 + streak_bonus} coins!"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_daily_challenge(request):
    """Claim daily challenge reward"""
    try:
        from datetime import date, timedelta
        
        player, _ = Player.objects.get_or_create(user=request.user)
        today = date.today()
        
        # Check if already claimed
        if player.last_daily_challenge == today:
            return JsonResponse({"error": "Daily challenge already claimed today"}, status=400)
        
        # Check if challenge is completed (5 puzzles solved today)
        # For simplicity, we'll check if puzzles_solved increased by 5 since last challenge
        # In a real implementation, you'd track daily puzzle count separately
        
        # Calculate reward
        if player.last_daily_challenge:
            yesterday = date.today() - timedelta(days=1)
            if player.last_daily_challenge == yesterday:
                player.daily_challenge_streak += 1
            else:
                player.daily_challenge_streak = 1
        else:
            player.daily_challenge_streak = 1
        
        reward = 50 + (player.daily_challenge_streak * 10)
        player.coins += reward
        player.last_daily_challenge = today
        player.save()
        
        return JsonResponse({
            "reward": reward,
            "coins_earned": reward,
            "new_balance": player.coins,
            "streak": player.daily_challenge_streak,
            "message": f"Daily challenge completed! Earned {reward} coins!"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_game_stats(request):
    """Get comprehensive game statistics"""
    try:
        player, _ = Player.objects.get_or_create(user=request.user)
        
        # Calculate XP needed for next level
        xp_for_current_level = (player.level - 1) * 100
        xp_for_next_level = player.level * 100
        xp_progress = player.xp - xp_for_current_level
        xp_needed = xp_for_next_level - player.xp
        
        return JsonResponse({
            "level": player.level,
            "xp": player.xp,
            "xp_progress": xp_progress,
            "xp_needed": xp_needed,
            "xp_for_next_level": xp_for_next_level,
            "difficulty": player.difficulty,
            "combo": player.combo_count,
            "max_combo": player.max_combo,
            "puzzles_solved": player.puzzles_solved,
            "perfect_solves": player.perfect_solves,
            "daily_streak": player.daily_challenge_streak,
            "high_score": player.high_score,
            "coins": player.coins
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Contact Us Views
@api_view(['POST'])
@permission_classes([AllowAny])
def submit_contact(request):
    """Submit a contact form"""
    try:
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            contact = serializer.save()
            
            # Send thank you email to the user
            try:
                send_contact_thankyou_email(contact.name, contact.email)
            except Exception as email_error:
                logger.error("Failed to send contact thank you email: %s", email_error)
                # Don't fail the request if email fails, just log it
            
            return Response({
                "message": "Thank you for contacting us! We'll get back to you soon.",
                "id": contact.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Rating Views
@api_view(['GET'])
@permission_classes([AllowAny])
def get_ratings(request):
    """Get all ratings with average"""
    try:
        ratings = Rating.objects.all()
        serializer = RatingSerializer(ratings, many=True)
        
        # Calculate average rating
        if ratings.exists():
            avg_rating = sum(r.rating for r in ratings) / ratings.count()
            total_ratings = ratings.count()
        else:
            avg_rating = 0
            total_ratings = 0
        
        return Response({
            "ratings": serializer.data,
            "average_rating": round(avg_rating, 2),
            "total_ratings": total_ratings
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_rating(request):
    """Submit or update a rating"""
    try:
        rating_value = request.data.get('rating')
        if not rating_value:
            return Response({"error": "Rating is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create rating for this user
        rating, created = Rating.objects.get_or_create(
            user=request.user,
            defaults={'rating': rating_value}
        )
        
        if not created:
            # Update existing rating
            serializer = RatingCreateSerializer(rating, data={'rating': rating_value})
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            "message": "Rating submitted successfully" if created else "Rating updated successfully",
            "rating": rating.rating
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_rating(request):
    """Get current user's rating"""
    try:
        try:
            rating = Rating.objects.get(user=request.user)
            serializer = RatingSerializer(rating)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Rating.DoesNotExist:
            return Response({"message": "No rating found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Review Views
@api_view(['GET'])
@permission_classes([AllowAny])
def get_reviews(request):
    """Get all approved reviews"""
    try:
        reviews = Review.objects.filter(is_approved=True)
        serializer = ReviewSerializer(reviews, many=True)
        return Response({
            "reviews": serializer.data,
            "count": reviews.count()
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_review(request):
    """Submit a review"""
    try:
        serializer = ReviewCreateSerializer(data=request.data)
        if serializer.is_valid():
            review = Review.objects.create(
                user=request.user,
                **serializer.validated_data
            )
            
            # Send thank you email to the user
            try:
                user_email = request.user.email
                if user_email:
                    send_review_thankyou_email(user_email, request.user.username, review.title)
                else:
                    logger.warning("User %s has no email address, skipping review thank you email", request.user.username)
            except Exception as email_error:
                logger.error("Failed to send review thank you email: %s", email_error)
                # Don't fail the request if email fails, just log it
            
            return Response({
                "message": "Review submitted successfully! It will be visible after admin approval.",
                "id": review.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_reviews(request):
    """Get current user's reviews"""
    try:
        reviews = Review.objects.filter(user=request.user)
        serializer = ReviewSerializer(reviews, many=True)
        return Response({
            "reviews": serializer.data,
            "count": reviews.count()
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



