from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth import logout
from .forms import CustomLoginForm, CustomSignupForm


def signup_view(request):
    if request.method == 'POST':
        # IMPORTANT: We must add request.FILES to handle the image upload!
        form = CustomSignupForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Save the User
            user = form.save()
            
            # 2. Save the Date of Birth to their Profile
            user.profile.date_of_birth = form.cleaned_data.get('date_of_birth')
            
            # 3. Save the Profile Picture (if they uploaded one)
            if form.cleaned_data.get('profile_picture'):
                user.profile.profile_picture = form.cleaned_data.get('profile_picture')
                
            user.profile.save()
            
            # 4. Log them in
            login(request, user)
            
            # 5. Redirect them to their NEW Profile Page!
            return redirect('profile', username=user.username)
    else:
        form = CustomSignupForm()
        
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        # Use the new CustomLoginForm instead of AuthenticationForm
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('feed')
    else:
        # Use the new CustomLoginForm here too
        form = CustomLoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('feed')
# Create your views here.
