from django.urls import path
from .import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('player/', views.player_detail, name='player-detail'),
    path('submit-score/', views.submit_score, name='submit-score'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('puzzle/', views.fetch_puzzle, name='fetch-puzzle'),
    path('check-puzzle/', views.check_puzzle_answer, name='check-puzzle'),

]