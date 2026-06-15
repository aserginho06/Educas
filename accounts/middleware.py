from django.core.exceptions import PermissionDenied


class RoleContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.role = getattr(request.user, "role", None)
        if getattr(request.user, "is_authenticated", False) and not request.user.is_active:
            raise PermissionDenied("Conta inativa.")
        return self.get_response(request)


class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
