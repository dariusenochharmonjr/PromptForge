from django.contrib import admin
from .models import Workflow, Upvote, Follow, Profile

# 1. Register Workflow
@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'ai_model', 'created_at')
    search_fields = ('title', 'prompt_text')

# 2. Register Upvote
@admin.register(Upvote)
class UpvoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'workflow', 'created_at')

# 3. Register Profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')

# 4. Register Follow
@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')