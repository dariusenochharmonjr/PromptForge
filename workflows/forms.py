from django import forms
from .models import Workflow, Comment, Profile
from django.contrib.auth.models import User

class WorkflowForm(forms.ModelForm):
    class Meta:
        model = Workflow
        # Added 'output_video' to the fields list
        fields = ['title', 'description', 'prompt_text', 'ai_model', 'output_image', 'output_video']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control modern-input', 
                'placeholder': 'Give your prompt a catchy title...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control modern-input', 
                'rows': 3, 
                'placeholder': 'Briefly describe what this prompt does...'
            }),
            'prompt_text': forms.Textarea(attrs={
                'class': 'form-control modern-input code-editor', 
                'rows': 10, 
                'placeholder': 'Paste or write your actual AI prompt here...'
            }),
            'ai_model': forms.Select(attrs={
                'class': 'form-control modern-input'
            }),
            'output_image': forms.ClearableFileInput(attrs={
                'class': 'form-control modern-input'
            }),
            # NEW: Modern widget for video
            'output_video': forms.ClearableFileInput(attrs={
                'class': 'form-control modern-input', 
                'accept': 'video/mp4,video/x-m4v,video/*'
            }),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control modern-input', 
                'rows': 3, 
                'placeholder': 'Write a comment...'
            }),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control modern-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control modern-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control modern-input'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'date_of_birth', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control modern-input', 'rows': 4}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control modern-input', 'type': 'date'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control modern-input'}),
        }