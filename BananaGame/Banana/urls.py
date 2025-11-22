from django.urls import path
from .import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('login/request-otp/', views.request_email_otp, name='request-email-otp'),
    path('login/verify-otp/', views.verify_email_otp_login, name='verify-email-otp'),
    path('logout/', views.logout, name='logout'),
    path('logout-all/', views.logout_all, name='logout-all'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('player/', views.player_detail, name='player-detail'),
    path('submit-score/', views.submit_score, name='submit-score'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('puzzle/', views.fetch_puzzle, name='fetch-puzzle'),
    path('check-puzzle/', views.check_puzzle_answer, name='check-puzzle'),
    path('use-hint/', views.use_hint, name='use-hint'),
    path('set-difficulty/', views.set_difficulty, name='set-difficulty'),
    path('daily-challenge/', views.get_daily_challenge, name='get-daily-challenge'),
    path('claim-daily-challenge/', views.claim_daily_challenge, name='claim-daily-challenge'),
    path('game-stats/', views.get_game_stats, name='get-game-stats'),
    
    # Contact Us
    path('contact/', views.submit_contact, name='submit-contact'),
    
    # Ratings
    path('ratings/', views.get_ratings, name='get-ratings'),
    path('ratings/submit/', views.submit_rating, name='submit-rating'),
    path('ratings/my-rating/', views.get_user_rating, name='get-user-rating'),
    
    # Reviews
    path('reviews/', views.get_reviews, name='get-reviews'),
    path('reviews/submit/', views.submit_review, name='submit-review'),
    path('reviews/my-reviews/', views.get_user_reviews, name='get-user-reviews'),

]