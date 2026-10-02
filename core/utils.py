from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework.response import Response

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

def get_paginated_queryset(queryset, page, per_page_items):
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
