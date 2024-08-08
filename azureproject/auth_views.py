from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info(f"User {username} logged in successfully.")
            return HttpResponseRedirect(reverse('session_upload'))
        else:
            logger.error("Failed login attempt.")
            return render(request, 'sessionData/login.html', {'error': 'Invalid username or password'})
    else:
        return render(request, 'sessionData/login.html')

def logout_view(request):
    logout(request)
    logger.info("User logged out successfully.")
    return HttpResponseRedirect(reverse('login'))

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            logger.info(f"New user {username} registered and logged in successfully.")
            return redirect('session_upload')
        else:
            logger.error("Failed registration attempt.")
            return render(request, 'sessionData/register.html', {'form': form})
    else:
        form = UserCreationForm()
        return render(request, 'sessionData/register.html', {'form': form})