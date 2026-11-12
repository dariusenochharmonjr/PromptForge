from django import forms
from django.core.exceptions import ValidationError
from .models import Workflow, Comment, Profile
from django.contrib.auth.models import User


class WorkflowForm(forms.ModelForm):
    class Meta:
        model = Workflow
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
            'output_video': forms.ClearableFileInput(attrs={
                'class': 'form-control modern-input', 
                'accept': 'video/mp4,video/x-m4v,video/*'
            }),
        }

    def clean_output_image(self):
        image = self.cleaned_data.get('output_image')
        if image:
            # 1. Check file size (10MB limit)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError('Image is too large. Maximum size is 10MB.')
            
            # 2. Check file extension
            if not image.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                raise ValidationError('Unsupported image type. Please upload JPG, PNG, WEBP, GIF or BMP.')
            
            # 3. Verify the file is not corrupted
            try:
                from PIL import Image
                image.seek(0)
                Image.open(image).verify()
                image.seek(0)  # Reset pointer so Cloudinary can read it
            except ImportError:
                image.seek(0)
            except Exception:
                raise ValidationError('This image file appears corrupted or unreadable. Please re-save it and try again.')
        return image

    def clean_output_video(self):
        video = self.cleaned_data.get('output_video')
        if video:
            # 1. Check file size (60MB limit)
            if video.size > 60 * 1024 * 1024:
                raise ValidationError('Video is too large. Maximum size is 60MB.')
            
            # 2. Check file extension
            if not video.name.lower().endswith(('.mp4', '.webm', '.ogg', '.mov')):
                raise ValidationError('Unsupported video type. Please upload MP4, WEBM, OGG or MOV.')
        return video


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