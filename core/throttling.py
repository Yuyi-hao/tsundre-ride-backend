from rest_framework.throttling import SimpleRateThrottle

class AnonymousIDThrottle(SimpleRateThrottle):
    scope = "anonymous"

    def get_cache_key(self, request, view):
        anonymous_id = request.headers.get('X-Anonymous-ID')
        if not anonymous_id:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": anonymous_id
        }

class IPThrottle(SimpleRateThrottle):
    scope = "ip"

    def get_cache_key(self, request, view):
        return self.cache_format%{
            "scope": self.scope,
            "ident": self.get_ident(request)
        }

