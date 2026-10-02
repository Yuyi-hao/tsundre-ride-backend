from rest_framework import serializers

from .models import Challenge, ChallengeAsset, ChallengeSubmission


class ChallengeAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeAsset
        fields = ["id", "name", "file_type", "asset_url", "asset_type", "is_public",
            "slug", "created_at", "modified_at",
        ]
        read_only_fields = ["id", "created_at", "modified_at",]


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


class ChallengeAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeAsset
        fields = [
            "id",
            "name",
            "file_type",
            "asset_url",
            "asset_type",
            "is_public",
            "slug",
            "created_at",
            "modified_at",
        ]


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
class ChallengeAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeAsset
        fields = ["id", "name", "path", "file_type", "asset_url", "asset_type", "is_public", 
                  "slug", "created_at", "modified_at",
        ]
        read_only_fields = [
            "id",
            "asset_url",
            "created_at",
            "modified_at",
        ]


class CreateChallengeAssetSerializer(serializers.Serializer):
    file = serializers.FileField()
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
        ]