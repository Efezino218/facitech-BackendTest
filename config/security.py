"""
Custom rate limit decorators for ISCOOA Facitech API.
Applied to sensitive endpoints.
"""
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from rest_framework.response import Response
from rest_framework import status
from functools import wraps


def rate_limit(key='ip', rate='10/m', method='POST'):
    """
    Decorator that applies rate limiting to a view method.
    Default: 10 requests per minute per IP.

    Usage:
        @rate_limit(rate='5/m')
        def post(self, request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Apply rate limit check
            from django_ratelimit.core import is_ratelimited
            limited = is_ratelimited(
                request  = request,
                group    = func.__qualname__,
                key      = key,
                rate     = rate,
                method   = method,
                increment = True,
            )
            if limited:
                return Response(
                    {
                        'detail': (
                            'Too many requests. '
                            'Please wait before trying again.'
                        )
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator