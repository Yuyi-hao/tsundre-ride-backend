import logging
import uuid
from pathlib import PurePosixPath
from django.db import DatabaseError, transaction
from django.db.models import Q
from core.utils import (
    response,
    get_paginated_queryset,
    db_error_response,
    storage_error_response,
    STORAGE_ERRORS,
)
from core.authentication import get_anonymous_id
from rest_framework.decorators import api_view
from rest_framework import status
from django.db.models import Case, When, Value, IntegerField

from .models import Challenge, ChallengeAsset, ChallengeSubmission
from . import serializers
from core.storage.utils import upload_a_file, delete_file

logger = logging.getLogger(__name__)

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


def safe_delete_file(file_url):
    """
        Best-effort file removal. Used when the DB row is already gone (or was
        never created), so a storage failure must not fail the request — it only
        leaves an orphan file, which we log.
    """
    try:
        delete_file(file_url)
    except (*STORAGE_ERRORS, ValueError):
        logger.exception("Could not delete file %s from storage.", file_url)


@api_view(['GET', 'POST'])
def challenges(request):
    if request.method == "GET":
        challenge_objs = Challenge.objects.all()

        owner_id = request.GET.get("owner_id")

        if owner_id:
            try:
                owner_id = uuid.UUID(owner_id)
            except ValueError:
                return response(
                    message="Invalid owner_id.",
                    success=False,
                    code='invalid-data',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
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

        challenge_objs = challenge_objs.order_by("-created_at")

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

        try:
            challenge_obj = serializer.save(owner_id=owner_id)
        except DatabaseError as exc:
            return db_error_response(exc, "create the challenge")

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
            code='not-found',
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
                success=False,
                code='forbidden',
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
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            challenge_obj = serializer.save()
        except DatabaseError as exc:
            return db_error_response(exc, "update the challenge")

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
                success=False,
                code='forbidden',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        challenge_obj.status = Challenge.Status.CANCELED
        try:
            challenge_obj.save(
                update_fields=[
                    "status",
                    "modified_at",
                ]
            )
        except DatabaseError as exc:
            return db_error_response(exc, "cancel the challenge")

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
            code='not-found',
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
                code='forbidden',
                status_code=status.HTTP_403_FORBIDDEN,
            )
        serializer = serializers.CreateChallengeAssetSerializer(data=request.data)

        if not serializer.is_valid():
            return response(
                message="Invalid asset data.",
                error=serializer.errors,
                success=False,
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        file = serializer.validated_data["file"]
        path = serializer.validated_data["path"].replace("\\", "/")

        if not validate_asset_path(path):
            return response(
                message="Invalid asset path.",
                success=False,
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate paths inside the same challenge.
        if challenge_obj.assets.filter(path=path).exists():
            return response(
                message="An asset already exists at this path.",
                success=False,
                code='conflict',
                status_code=status.HTTP_409_CONFLICT,
            )

        storage_path = f"challenges/{challenge_obj.id}/{path}"

        try:
            asset_url = upload_a_file(
                file=file,
                bucket="challenge-files",
                path=storage_path,
                content_type=file.content_type,
            )
        except STORAGE_ERRORS as exc:
            return storage_error_response(exc, "upload the asset")

        try:
            # slug is left to the model (uuid): it must be globally unique and
            # URL-safe, which a path like "src/index.html" is not.
            asset_obj = ChallengeAsset.objects.create(
                name=PurePosixPath(path).name,
                path=path,
                file_type=serializer.validated_data["file_type"],
                asset_url=asset_url,
                challenge=challenge_obj,
                asset_type=ChallengeAsset.AssetType.CHALLENGE,
                is_public=serializer.validated_data["is_public"],
                owner_id=owner_id,
            )
        except DatabaseError as exc:
            # Don't leave the uploaded file orphaned in storage.
            safe_delete_file(asset_url)
            return db_error_response(exc, "save the asset")

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
            code='not-found',
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
            code='not-found',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    owner_id = get_anonymous_id(request)
    if request.method == "GET":
        return response(
            message="Challenge asset fetched successfully.",
            content=serializers.ChallengeAssetSerializer(asset_obj).data,
            success=True,
            status_code=status.HTTP_200_OK,
        )

    if challenge_obj.owner_id != owner_id:
        return response(
            message="You are not the owner of this challenge.",
            success=False,
            code='forbidden',
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
                message="Invalid asset data.",
                error=serializer.errors,
                success=False,
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            asset_obj = serializer.save()
        except DatabaseError as exc:
            return db_error_response(exc, "update the asset")

        return response(
            message="Challenge asset updated successfully.",
            content=serializers.ChallengeAssetSerializer(
                asset_obj,
            ).data,
            success=True,
            status_code=status.HTTP_200_OK,
        )
    elif request.method == "DELETE":
        asset_url = asset_obj.asset_url

        # Delete the row first: if that fails nothing has changed. If the file
        # delete fails afterwards we only leave an orphan file, not a broken row.
        try:
            asset_obj.delete()
        except DatabaseError as exc:
            return db_error_response(exc, "delete the asset")

        safe_delete_file(asset_url)

        return response(
            message="Challenge asset deleted successfully.",
            success=True,
            status_code=status.HTTP_200_OK,
        )

@api_view(["GET", "POST"])
def challenge_submissions(request, challenge_slug):
    try:
        challenge_obj = Challenge.objects.get(
            slug=challenge_slug
        )
    except Challenge.DoesNotExist:
        return response(
            message="Challenge not found.",
            success=False,
            code='not-found',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    owner_id = get_anonymous_id(request)

    is_challenge_owner = challenge_obj.owner_id == owner_id

    if request.method == "GET":

        if is_challenge_owner:
            submissions = challenge_obj.submissions.filter(
                Q(status=ChallengeSubmission.Status.SUBMITTED) |
                Q(owner_id=owner_id)
            )
        else:
            submissions = challenge_obj.submissions.filter(
                Q(owner_id=owner_id) |
                Q(
                    is_public=True,
                    status=ChallengeSubmission.Status.SUBMITTED,
                )
            )

        submissions = submissions.annotate(
            is_mine=Case(
                When(owner_id=owner_id, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_mine", "-is_editorial", "-created_at")

        submissions = submissions.order_by("-created_at")

        return response(
            message="Challenge submissions fetched successfully.",
            content={
                "submissions": serializers.ChallengeSubmissionSerializer(
                    submissions,
                    many=True,
                ).data,
            },
            success=True,
            status_code=status.HTTP_200_OK,
        )

    if request.method == "POST":
        serializer = serializers.CreateChallengeSubmissionSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return response(
                message="Invalid submission data.",
                error=serializer.errors,
                success=False,
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Editorial submission is only allowed for challenge owner.
        is_editorial = is_challenge_owner

        try:
            submission_obj = serializer.save(
                challenge=challenge_obj,
                owner_id=owner_id,
                is_editorial=is_editorial,
                is_public=False,
            )
        except DatabaseError as exc:
            return db_error_response(exc, "create the submission")

        return response(
            message="Submission created successfully.",
            content=serializers.ChallengeSubmissionSerializer(
                submission_obj
            ).data,
            success=True,
            status_code=status.HTTP_201_CREATED,
        )

@api_view(["GET", "PATCH", "DELETE"])
def challenge_submission_detail(request, challenge_slug, submission_slug):
    try:
        challenge_obj = Challenge.objects.get(
            slug=challenge_slug
        )
    except Challenge.DoesNotExist:
        return response(
            message="Challenge not found.",
            success=False,
            code='not-found',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        submission_obj = challenge_obj.submissions.get(
            slug=submission_slug
        )
    except ChallengeSubmission.DoesNotExist:
        return response(
            message="Submission not found.",
            success=False,
            code='not-found',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    owner_id = get_anonymous_id(request)

    is_challenge_owner = challenge_obj.owner_id == owner_id
    is_submission_owner = submission_obj.owner_id == owner_id


    if request.method == "GET":

        can_view = (
            is_challenge_owner
            or is_submission_owner
            or submission_obj.is_public
        )

        if not can_view:
            return response(
                message="You do not have permission to view this submission.",
                success=False,
                code='forbidden',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return response(
            message="Submission fetched successfully.",
            content=serializers.ChallengeSubmissionSerializer(
                submission_obj
            ).data,
            success=True,
            status_code=status.HTTP_200_OK,
        )

    if not is_submission_owner:
        return response(
            message="You are not the owner of this submission.",
            success=False,
            code='forbidden',
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "PATCH":
        serializer = serializers.UpdateChallengeSubmissionSerializer(
            submission_obj,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return response(
                message="Invalid submission data.",
                error=serializer.errors,
                success=False,
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        is_submitting = (
            serializer.validated_data.get("status") == ChallengeSubmission.Status.SUBMITTED
            and submission_obj.status != ChallengeSubmission.Status.SUBMITTED
        )
        if is_submitting and challenge_obj.status != Challenge.Status.ACTIVE:
            return response(
                message="This challenge is no longer accepting submissions.",
                success=False,
                code='challenge-closed',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            submission_obj = serializer.save()
        except DatabaseError as exc:
            return db_error_response(exc, "update the submission")

        return response(
            message="Submission updated successfully.",
            content=serializers.ChallengeSubmissionSerializer(
                submission_obj
            ).data,
            success=True,
            status_code=status.HTTP_200_OK,
        )

    if request.method == "DELETE":
        try:
            with transaction.atomic():
                asset_urls = list(submission_obj.assets.values_list("asset_url", flat=True))
                submission_obj.delete()
        except DatabaseError as exc:
            return db_error_response(exc, "delete the submission")

        # Assets rows are cascade-deleted; clean up their files too.
        for asset_url in asset_urls:
            safe_delete_file(asset_url)

        return response(
            message="Submission deleted successfully.",
            success=True,
            status_code=status.HTTP_200_OK,
        )

def get_challenge_and_submission(challenge_slug, submission_slug):
    """
        Returns (challenge, submission, None), or (None, None, error_response)
        when either one doesn't exist.
    """
    try:
        challenge_obj = Challenge.objects.get(slug=challenge_slug)
    except Challenge.DoesNotExist:
        return None, None, response(
            message="Challenge not found.",
            success=False,
            code='not-found',
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        submission_obj = challenge_obj.submissions.get(slug=submission_slug)
    except ChallengeSubmission.DoesNotExist:
        return None, None, response(
            message="Submission not found.",
            success=False,
            code='not-found',
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return challenge_obj, submission_obj, None


def check_can_edit_submission_files(submission_obj, owner_id):
    """
        Only the submission owner can change its files, and only while it is a draft.
        Returns an error response, or None when allowed.
    """
    if submission_obj.owner_id != owner_id:
        return response(
            message="You are not the owner of this submission.",
            success=False,
            code='forbidden',
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if submission_obj.status != ChallengeSubmission.Status.DRAFT:
        return response(
            message="Unsubmit this submission before changing its files.",
            success=False,
            code='not-draft',
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return None


@api_view(["GET", "POST"])
def submission_assets(request, challenge_slug, submission_slug):
    challenge_obj, submission_obj, error = get_challenge_and_submission(challenge_slug, submission_slug)
    if error:
        return error

    owner_id = get_anonymous_id(request)

    if request.method == "GET":
        can_view = (
            challenge_obj.owner_id == owner_id
            or submission_obj.owner_id == owner_id
            or submission_obj.is_public
        )
        if not can_view:
            return response(
                message="You do not have permission to view this submission.",
                success=False,
                code='forbidden',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        assets = submission_obj.assets.order_by("path")
        return response(
            message="Submission files fetched successfully.",
            content={
                "assets": serializers.ChallengeAssetSerializer(assets, many=True).data
            },
            success=True,
            status_code=status.HTTP_200_OK,
        )

    if request.method == "POST":
        error = check_can_edit_submission_files(submission_obj, owner_id)
        if error:
            return error

        serializer = serializers.CreateSubmissionAssetSerializer(data=request.data)
        if not serializer.is_valid():
            return response(
                message="Invalid file data.",
                error=serializer.errors,
                success=False,
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        file = serializer.validated_data["file"]
        path = serializer.validated_data["path"].replace("\\", "/")

        if not validate_asset_path(path):
            return response(
                message="Invalid file path.",
                success=False,
                code='invalid-data',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if submission_obj.assets.filter(path=path).exists():
            return response(
                message="A file already exists at this path.",
                success=False,
                code='conflict',
                status_code=status.HTTP_409_CONFLICT,
            )

        storage_path = f"submissions/{submission_obj.id}/{path}"

        try:
            asset_url = upload_a_file(
                file=file,
                bucket="challenge-files",
                path=storage_path,
                content_type=file.content_type,
            )
        except STORAGE_ERRORS as exc:
            return storage_error_response(exc, "upload the file")

        try:
            asset_obj = ChallengeAsset.objects.create(
                name=PurePosixPath(path).name,
                path=path,
                file_type=serializer.validated_data["file_type"],
                asset_url=asset_url,
                submission=submission_obj,
                asset_type=ChallengeAsset.AssetType.SOLUTION,
                owner_id=owner_id,
            )
        except DatabaseError as exc:
            safe_delete_file(asset_url)
            return db_error_response(exc, "save the file")

        return response(
            message="Submission file uploaded successfully.",
            content=serializers.ChallengeAssetSerializer(asset_obj).data,
            success=True,
            status_code=status.HTTP_201_CREATED,
        )


@api_view(["DELETE"])
def submission_asset_detail(request, challenge_slug, submission_slug, asset_slug):
    _, submission_obj, error = get_challenge_and_submission(challenge_slug, submission_slug)
    if error:
        return error

    try:
        asset_obj = submission_obj.assets.get(slug=asset_slug)
    except ChallengeAsset.DoesNotExist:
        return response(
            message="File not found.",
            success=False,
            code='not-found',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    error = check_can_edit_submission_files(submission_obj, get_anonymous_id(request))
    if error:
        return error

    asset_url = asset_obj.asset_url
    try:
        asset_obj.delete()
    except DatabaseError as exc:
        return db_error_response(exc, "delete the file")

    safe_delete_file(asset_url)

    return response(
        message="Submission file deleted successfully.",
        success=True,
        status_code=status.HTTP_200_OK,
    )
