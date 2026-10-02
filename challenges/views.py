from pathlib import PurePosixPath
from django.db.models import Q
from core.utils import response, get_paginated_queryset
from core.authentication import get_anonymous_id
from rest_framework.decorators import api_view
from rest_framework import status

from .models import Challenge, ChallengeAsset
from . import serializers
from core.storage.utils import upload_a_file, delete_file

# Create your views here.

def validate_asset_path(path):
    path = path.replace("\\", "/")
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute():
        return False
    if ".." in pure_path.parts:
        return False
    if not path or path.endswith("/"):
        return False
    return True

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

@api_view(["GET", "POST"])
def challenge_assets(request, challenge_slug):
    try:
        challenge_obj = Challenge.objects.get(slug=challenge_slug)
    except Challenge.DoesNotExist:
        return response(
            message="Challenge not found.",
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    owner_id = get_anonymous_id(request)
    if request.method == "GET":
        assets = challenge_obj.assets.filter(asset_type=ChallengeAsset.AssetType.CHALLENGE).order_by("path")

        return response(
            message="Challenge assets fetched successfully.",
            content={
                "assets": serializers.ChallengeAssetSerializer(assets, many=True,).data
            },
            success=True,
            status_code=status.HTTP_200_OK,
        )

    # post request
    if request.method == "POST":
        if challenge_obj.owner_id != owner_id:
            return response(
                message="You are not the owner of this challenge.",
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        serializer = serializers.CreateChallengeAssetSerializer(data=request.data)

        if not serializer.is_valid():
            return response(
                message="Invalid asset data.",
                content=serializer.errors,
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        file = serializer.validated_data["file"]
        path = serializer.validated_data["path"].replace("\\", "/")

        if not validate_asset_path(path):
            return response(
                message="Invalid asset path.",
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate paths inside the same challenge.
        if challenge_obj.assets.filter(path=path).exists():
            return response(
                message="An asset already exists at this path.",
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        storage_path = f"challenges/{challenge_obj.id}/{path}"

        asset_url = upload_a_file(
            file=file,
            bucket="challenge-files",
            path=storage_path,
            content_type=file.content_type,
        )

        asset_obj = ChallengeAsset.objects.create(
            name=PurePosixPath(path).name,
            path=path,
            file_type=serializer.validated_data["file_type"],
            asset_url=asset_url,
            challenge=challenge_obj,
            asset_type=ChallengeAsset.AssetType.CHALLENGE,
            is_public=serializer.validated_data["is_public"],
            owner_id=owner_id,
            slug=path.replace("/", "-"),
        )

        return response(
            message="Challenge asset uploaded successfully.",
            content=serializers.ChallengeAssetSerializer(asset_obj).data,
            success=True,
            status_code=status.HTTP_201_CREATED,
        )

@api_view(["GET", "PATCH", "DELETE"])
def challenge_asset_detail(request, challenge_slug, asset_slug):
    try:
        challenge_obj = Challenge.objects.get(slug=challenge_slug)
    except Challenge.DoesNotExist:
        return response(
            message="Challenge not found.",
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        asset_obj = challenge_obj.assets.get(
            slug=asset_slug,
            asset_type=ChallengeAsset.AssetType.CHALLENGE,
        )
    except ChallengeAsset.DoesNotExist:
        return response(
            message="Asset not found.",
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    owner_id = get_anonymous_id(request)
    is_owner = challenge_obj.owner_id == owner_id
    if request.method == "GET":
        serializer = serializers.ChallengeAssetSerializer(
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
    
    if is_owner:
        return response(
            message="You are not the owner of this challenge.",
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if request.method == "PATCH":
        serializer = serializers.UpdateChallengeAssetSerializer(
            asset_obj,
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

        asset_obj = serializer.save()

        return response(
            message="Challenge updated successfully.",
            content=serializers.ChallengeAssetSerializer(
                asset_obj,
            ).data,
            success=True,
            status_code=status.HTTP_200_OK,
        )
    elif request.method == "DELETE":
        delete_file(asset_obj.asset_url)

        asset_obj.delete()

        return response(
            message="Challenge asset deleted successfully.",
            success=True,
            status_code=status.HTTP_200_OK,
        )

