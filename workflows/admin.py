from django.contrib import admin
from .models import Workflow, Upvote, Follow, Profile

# 1. Register Workflow
@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'ai_model', 'created_at')
    list_filter = ('ai_model', 'created_at', 'author') # Adds a sidebar filter
    search_fields = ('title', 'prompt_text', 'author__username') # Lets you search by username
    readonly_fields = ('created_at',) # Prevents accidental date changes
    ordering = ('-created_at',) # Shows newest workflows at the top

# 2. Register Upvote
@admin.register(Upvote)
class UpvoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'workflow', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'workflow__title') # Search by user or workflow name
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

# 3. Register Profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
    search_fields = ('user__username', 'bio') # Crucial for finding specific users
    # If you have a profile picture field, you can add it to list_display: ('user', 'bio', 'profile_picture')

# 4. Register Follow
@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower__username', 'following__username') # Search by either username
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)