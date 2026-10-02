import uuid

from rest_framework.exceptions import AuthenticationFailed

def get_anonymous_id(request):
    anonymous_id = request.headers.get("X-Anonymous-ID")

    if not anonymous_id:
        raise AuthenticationFailed("X-Anonymous-ID header is required.")
    try:
        return uuid.UUID(anonymous_id)
    except(ValueError, AttributeError, TypeError):
        raise AuthenticationFailed("Invalid anonymous ID.")