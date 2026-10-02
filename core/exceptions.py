import logging

from django.db import DatabaseError
from rest_framework import status
from rest_framework.views import exception_handler

from core.utils import response, db_error_response, storage_error_response, STORAGE_ERRORS

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
        Safety net for anything a view did not handle itself, so every error
        is returned in the same shape as `core.utils.response`.
    """
    drf_response = exception_handler(exc, context)

    # DRF exceptions (auth, parse errors, method not allowed, ...).
    if drf_response is not None:
        data = drf_response.data
        message = data.get("detail", "Request failed.") if isinstance(data, dict) else "Request failed."

        api_response = response(
            message=str(message),
            success=False,
            code=getattr(exc, "default_code", "error"),
            error=data,
            status_code=drf_response.status_code,
        )
        # Keep headers such as WWW-Authenticate / Retry-After.
        for header, value in drf_response.items():
            api_response[header] = value
        return api_response

    if isinstance(exc, DatabaseError):
        return db_error_response(exc, "complete the request")

    if isinstance(exc, STORAGE_ERRORS):
        return storage_error_response(exc, "complete the request")

    logger.exception("Unhandled error in %s.", context.get("view"))
    return response(
        message="Something went wrong. Please try again.",
        success=False,
        code="server-error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
