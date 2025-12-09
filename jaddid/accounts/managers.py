from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    """ Custom user model manager where email is the unique identifier
    for authentication instead of username."""

    def create_user(self, email, password, **args):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("Email field is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **args)
        user.set_password(password)
        user.save()
        return user
    
    
