"""Custom authentication backend allowing sign-in by email and password."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticate a user using case-insensitive email and password."""

    def authenticate(self, request, username=None, email=None, password=None, **kwargs):
        lookup_email = (email or username or '').strip().lower()
        if not lookup_email or password is None:
            return None

        user = User.objects.filter(email__iexact=lookup_email).first()
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
