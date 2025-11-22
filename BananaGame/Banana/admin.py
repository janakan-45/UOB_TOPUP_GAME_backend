from django.contrib import admin
from .models import Player, Score, OTP, Contact, Rating, Review


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'xp', 'coins', 'high_score', 'puzzles_solved']
    list_filter = ['level', 'difficulty']
    search_fields = ['user__username', 'user__email']


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ['user', 'score', 'date']
    list_filter = ['date']
    search_fields = ['user__username']


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp_type', 'contact_info', 'is_used', 'created_at', 'expires_at']
    list_filter = ['otp_type', 'is_used', 'created_at']
    search_fields = ['user__username', 'contact_info']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    )


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'created_at', 'updated_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['user__username', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'title', 'content', 'rating')
        }),
        ('Moderation', {
            'fields': ('is_approved', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['approve_reviews', 'disapprove_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} review(s) approved.")
    approve_reviews.short_description = "Approve selected reviews"
    
    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} review(s) disapproved.")
    disapprove_reviews.short_description = "Disapprove selected reviews"
