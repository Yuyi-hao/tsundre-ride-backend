import logging

from botocore.exceptions import BotoCoreError, ClientError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import DatabaseError, IntegrityError
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# Errors raised by the storage layer (boto3).
STORAGE_ERRORS = (BotoCoreError, ClientError)

MAX_PER_PAGE_ITEMS = 100

def response(message, content=False, success=True, code=False, error=False, status_code=200):
    """
        Summary or Description of the Function
        Parameters:
            message (string):
            content (any):
            success (bool):
            code    (string):
            error   (dict):
            status_code (int): default 200
        Returns:
            dict : Returning response object
    """
    response = {}
    response['message'] = message
    response['success'] = success

    if not success:
        response['code'] = code
    if content or content == []:
        response['content'] = content
    if type(error) is not bool:
        response['success'] = False
        response['code'] = code
        response['error'] = error
    return Response(response,status_code)

def db_error_response(exc, action):
    """
        Build a response for a failed database operation.
        Parameters:
            exc (DatabaseError): the exception that was raised
            action (string): what we were trying to do, e.g. "create the challenge"
    """
    logger.exception("Database error while trying to %s.", action)

    if isinstance(exc, IntegrityError):
        return response(
            message=f"Could not {action}: it conflicts with existing data.",
            success=False,
            code="conflict",
            status_code=status.HTTP_409_CONFLICT,
        )

    return response(
        message=f"Could not {action} due to a database error. Please try again.",
        success=False,
        code="database-error",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def storage_error_response(exc, action):
    """
        Build a response for a failed file storage operation.
    """
    logger.exception("Storage error while trying to %s.", action)

    return response(
        message=f"Could not {action} due to a storage error. Please try again.",
        success=False,
        code="storage-error",
        status_code=status.HTTP_502_BAD_GATEWAY,
    )


def _to_positive_int(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def get_paginated_queryset(queryset, page, per_page_items):
    per_page_items = min(_to_positive_int(per_page_items, 10), MAX_PER_PAGE_ITEMS)
    paginator = Paginator(queryset, per_page_items)
    try:
        required_list = paginator.page(page)
    except PageNotAnInteger:
        required_list = paginator.page(1)
    except EmptyPage:
        required_list = paginator.page(paginator.num_pages)

    # Has previous
    if required_list.has_previous():
        pre_page = required_list.previous_page_number()
    else:
        pre_page = None

    # Has next
    if required_list.has_next():
        next_page = required_list.next_page_number()
    else:
        next_page = None
    return required_list,pre_page,next_page, required_list.number
