from django.shortcuts import redirect
from django.urls import reverse


class StaffAuthenticationMiddleware:
    """Middleware to check Staff authentication for protected views"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.protected_paths = [
            '/home/',
            '/loans/',
            '/payments/',
            '/borrowers/',
            '/staff/',
            '/ebike-models/',
            '/api/'
        ]
        # These paths don't require authentication
        self.public_paths = [
            '/api/login/',
            '/api/logout/',
            '/',
        ]

    def __call__(self, request):
        # Check if path is public (doesn't require authentication)
        if any(request.path == path for path in self.public_paths):
            return self.get_response(request)
        
        # Check if path requires authentication
        if any(request.path.startswith(path) for path in self.protected_paths):
            # Check if user is authenticated (either superuser or staff member)
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                if 'staff_id' not in request.session:
                    # API requests should return 401
                    if request.path.startswith('/api/'):
                        from django.http import JsonResponse
                        return JsonResponse({"error": "Unauthorized"}, status=401)
                    # Page requests should redirect to login
                    return redirect('/')

        response = self.get_response(request)
        return response
