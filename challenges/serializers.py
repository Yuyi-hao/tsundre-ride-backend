import logging

from rest_framework import serializers

from core.storage.utils import get_presigned_url
from core.utils import STORAGE_ERRORS

from .models import Challenge, ChallengeAsset, ChallengeSubmission

logger = logging.getLogger(__name__)

# Seconds a download URL stays valid. Pages fetch files right after loading, so this can be short.
ASSET_DOWNLOAD_URL_EXPIRY = 60 * 60


class ChallengeAssetSerializer(serializers.ModelSerializer):
    # The bucket is private, so clients download through a short-lived signed URL
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ChallengeAsset
        fields = ["id", "name", "path", "file_type", "asset_url", "download_url", "asset_type",
                  "is_public", "slug", "created_at", "modified_at",
        ]
        read_only_fields = ["id", "asset_url", "created_at", "modified_at",]

    def get_download_url(self, obj):
        try:
            return get_presigned_url(obj.asset_url, expires_in=ASSET_DOWNLOAD_URL_EXPIRY)
        except (*STORAGE_ERRORS, ValueError):
            logger.exception("Could not sign download URL for asset %s.", obj.pk)
            return None


class SubmissionSerializer(serializers.ModelSerializer):
    assets = ChallengeAssetSerializer(many=True, read_only=True)

    class Meta:
        model = ChallengeSubmission
        fields = [ "id", "challenge", "owner_id", "status", "description",
                  "slug", "is_editorial", "created_at", "modified_at", "assets",]
        read_only_fields = [ "id", "challenge", "owner_id", "created_at", "modified_at", "assets"]


class ChallengeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = ["name", "description", "duration", "is_public_solution"]


class ListChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = ["id", "name", "description", "duration", "slug", 
                  "is_public_solution", "status", "created_at", "modified_at",]


class ChallengeDetailSerializer(serializers.ModelSerializer):
    assets = ChallengeAssetSerializer(many=True, read_only=True)
    editorial_submission = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = ["id", "name", "description", "duration", "slug", "is_public_solution", "owner_id",
                  "status", "created_at", "modified_at", "assets", "editorial_submission"]
        read_only_fields = [
            "id", "owner_id", "status", "created_at", "modified_at", "assets", "editorial_submission"
        ]

    def get_editorial_submission(self, obj):
        submission = obj.submissions.filter(
            is_editorial=True,
        ).prefetch_related(
            "assets",
        ).first()

        if not submission:
            return None

        return SubmissionSerializer(submission).data


class SubmissionSerializer(serializers.ModelSerializer):
    assets = ChallengeAssetSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ChallengeSubmission
        fields = [
            "id",
            "status",
            "description",
            "slug",
            "is_editorial",
            "created_at",
            "modified_at",
            "assets",
        ]


class ListChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = [
            "id",
            "name",
            "description",
            "duration",
            "slug",
            "is_public_solution",
            "status",
            "created_at",
            "modified_at",
        ]


class CreateChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = [
            "name",
            "description",
            "duration",
            "slug",
            "is_public_solution",
        ]


class UpdateChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = [
            "name",
            "description",
            "duration",
            "is_public_solution",
        ]


class DetailChallengeSerializer(serializers.ModelSerializer):
    assets = ChallengeAssetSerializer(
        many=True,
        read_only=True,
    )

    editorial_submission = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            "id",
            "name",
            "description",
            "duration",
            "slug",
            "is_public_solution",
            "owner_id",
            "status",
            "created_at",
            "modified_at",
            "assets",
            "editorial_submission",
        ]

    def get_editorial_submission(self, obj):
        submission = obj.submissions.filter(
            is_editorial=True,
        ).prefetch_related(
            "assets",
        ).first()

        if not submission:
            return None

        return SubmissionSerializer(submission).data

# assets 
class CreateChallengeAssetSerializer(serializers.Serializer):
    # Starter files created in the editor are often still empty
    file = serializers.FileField(allow_empty_file=True)
    path = serializers.CharField(max_length=1024)
    file_type = serializers.ChoiceField(
        choices=ChallengeAsset.FileType.choices
    )
    is_public = serializers.BooleanField(default=False)

class UpdateChallengeAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeAsset
        fields = [
            "name",
            "is_public",
        ]

class ChallengeSubmissionSerializer(serializers.ModelSerializer):
    assets = ChallengeAssetSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ChallengeSubmission
        fields = ["id", "status", "description", "slug", "is_public",
            "is_editorial", "created_at", "modified_at", "assets"]
        read_only_fields = [
            "id", "slug", "is_editorial", "created_at", "modified_at", "assets",
        ]

class CreateChallengeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeSubmission
        fields = [
            "description",
        ]

class UpdateChallengeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeSubmission
        fields = [
            "description",
            "is_public",
            # draft <-> submitted
            "status",
        ]

class CreateSubmissionAssetSerializer(serializers.Serializer):
    # Files created in the editor are often still empty
    file = serializers.FileField(allow_empty_file=True)
    path = serializers.CharField(max_length=1024)
    file_type = serializers.ChoiceField(
        choices=ChallengeAsset.FileType.choices
    )