from django.utils import timezone
from workflows.models import Profile

class ActiveStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            Profile.objects.filter(user=request.user).update(last_active=timezone.now())
        return self.get_response(request)

from django.middleware.csrf import get_token


class EnsureCsrfCookieMiddleware:
    """Guarantees every GET response sets a fresh csrftoken cookie."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'GET':
            get_token(request)
        return self.get_response(request)