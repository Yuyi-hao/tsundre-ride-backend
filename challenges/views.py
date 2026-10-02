from django.shortcuts import render
from django.db.models import Q
from core.utils import response, get_paginated_queryset
from core.authentication import get_anonymous_id
from rest_framework.decorators import api_view
from rest_framework import status

from .models import Challenge
from . import serializers

# Create your views here.

@api_view(['GET', 'POST'])
def challenges(request):
    if request.method == "GET":
        challenge_objs = Challenge.objects.all()

        owner_id = request.GET.get("owner_id")

        if owner_id:
            challenge_objs = challenge_objs.filter(
                owner_id=owner_id
            )

        status_filter = request.GET.get("status")

        if status_filter:
            challenge_objs = challenge_objs.filter(
                status=status_filter
            )

        search = request.GET.get("search")

        if search:
            challenge_objs = challenge_objs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
            )


        challenge_objs , pre_page, next_page, current_page = get_paginated_queryset(
            challenge_objs,
            request.GET.get("page", 1),
            request.GET.get("per_page_items", 10),
        )

        content = {
            "challenges": serializers.ListChallengeSerializer(challenge_objs, many=True).data,
            "count": challenge_objs.paginator.count,
            "total_pages": challenge_objs.paginator.num_pages,
            "current_page": current_page,
            "previous_page": pre_page,
            "next_page": next_page,

        }
        return response(message='Challenge list fetched successfully.', 
                        content=content,
                        success=True,
                        status_code=status.HTTP_200_OK)
    
    elif request.method == "POST":
        owner_id = get_anonymous_id(request)
        serializer = serializers.ChallengeCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return response(
                message="Invalid challenge data.",
                success=False,
                code='invalid-data',
                error=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        
        challenge_obj = serializer.save(owner_id=owner_id)

        content = {'challenge': serializers.ChallengeDetailSerializer(challenge_obj).data}

        return response(
            message="Challenge created successfully!!",
            content=content,
            success=True,
            status_code=status.HTTP_201_CREATED
        )

@api_view(["GET", "PATCH", "DELETE"])
def particular_challenge(request, challenge_slug):
    try:
        challenge_obj = Challenge.objects.get(slug=challenge_slug)
    except Challenge.DoesNotExist:
        return response(
            message="Challenge not found.",
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    owner_id = get_anonymous_id(request)
    is_owner = challenge_obj.owner_id == owner_id

    if request.method == "GET":
        serializer = serializers.DetailChallengeSerializer(
            challenge_obj,
            context={
                "is_owner": is_owner,
            },
        )

        return response(
            message="Challenge fetched successfully.",
            content=serializer.data,
            success=True,
            status_code=status.HTTP_200_OK,
        )

    elif request.method == "PATCH":
        if not is_owner:
            return response(
                message="You do not own this challenge.",
                content={},
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = serializers.UpdateChallengeSerializer(
            challenge_obj,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return response(
                message="Invalid challenge data.",
                error=serializer.errors,
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        challenge_obj = serializer.save()

        return response(
            message="Challenge updated successfully.",
            content=serializers.DetailChallengeSerializer(
                challenge_obj,
            ).data,
            success=True,
            status_code=status.HTTP_200_OK,
        )

    elif request.method == "DELETE":
        if not is_owner:
            return response(
                message="You do not own this challenge.",
                content={},
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        challenge_obj.status = Challenge.Status.CANCELED
        challenge_obj.save(
            update_fields=[
                "status",
                "modified_at",
            ]
        )

        return response(
            message="Challenge canceled successfully.",
            content={},
            success=True,
            status_code=status.HTTP_200_OK,
        )