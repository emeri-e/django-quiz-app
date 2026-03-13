from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import UserRegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('quiz:quiz_list')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('quiz:quiz_list')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    # Get the user's completed sittings
    from apps.quiz.models import Sitting
    sittings = Sitting.objects.filter(
        user=request.user,
        complete=True
    ).select_related('quiz').order_by('-end')

    return render(request, 'accounts/profile.html', {
        'sittings': sittings,
    })
