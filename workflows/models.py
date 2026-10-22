from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# --- MAIN MODELS ---

class Workflow(models.Model):
    AI_MODELS = (
        ('ChatGPT', 'ChatGPT'), ('Midjourney', 'Midjourney'), ('Claude', 'Claude'),
        ('Gemini', 'Gemini'), ('Grok', 'Grok'), ('Kimi', 'Kimi'), ('Qwen', 'Qwen'), ('Other', 'Other')
    )

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflows')
    title = models.CharField(max_length=250)
    description = models.TextField(help_text="Describe the prompt output")
    prompt_text = models.TextField(help_text="The actual prompt text")
    ai_model = models.CharField(max_length=60, choices=AI_MODELS)
    
    # Existing image field
    output_image = models.ImageField(upload_to='outputs/', blank=True, null=True)
    
    # NEW: Video field added here
    output_video = models.FileField(upload_to='outputs/videos/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def total_upvotes(self):
        return self.upvotes.count()


class Upvote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='upvotes')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='upvotes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'workflow')

    def __str__(self):
        return f"{self.user.username} upvoted {self.workflow.title}" 


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself!")
    profile_picture = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField() 

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Comment(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.workflow.title}"


class LoveReaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='love_reactions')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='love_reactions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'workflow')

    def __str__(self):
        return f"{self.user.username} loved {self.workflow.title}"


# --- NEW: BOOKMARK MODEL ---
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'workflow')

    def __str__(self):
        return f"{self.user.username} bookmarked {self.workflow.title}"


# --- NOTIFICATION MODEL ---
class Notification(models.Model):
    recipient = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    actor = models.ForeignKey(User, related_name='actor_notifications', on_delete=models.CASCADE)
    verb = models.CharField(max_length=255) 
    target = models.ForeignKey(Workflow, null=True, blank=True, on_delete=models.CASCADE) 
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.actor.username} {self.verb}"


# --- MAGIC SIGNALS ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, date_of_birth='2000-01-01')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    Profile.objects.get_or_create(user=instance)