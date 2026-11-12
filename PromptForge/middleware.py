from django.utils import timezone
from workflows.models import Profile

class ActiveStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            Profile.objects.filter(user=request.user).update(last_active=timezone.now())
        return self.get_response(request)