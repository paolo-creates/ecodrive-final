"""
Custom authentication backend for Staff login with email or username
"""
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import Staff


class EmailOrUsernameBackend(ModelBackend):
    """
    Allows staff to login using either username or email
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate staff using username or email
        """
        try:
            # Try to find staff by username or email
            staff = Staff.objects.get(
                Q(username=username) | Q(email=username)
            )
        except Staff.DoesNotExist:
            return None
        
        # Check if account is active
        if not staff.is_active:
            return None
        
        # Verify password
        if staff.check_password(password):
            return staff
        
        return None
    
    def get_user(self, user_id):
        """
        Get staff user by ID
        """
        try:
            return Staff.objects.get(pk=user_id)
        except Staff.DoesNotExist:
            return None
