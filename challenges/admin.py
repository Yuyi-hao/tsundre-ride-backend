from django.contrib import admin

from .models import Challenge, ChallengeAsset, ChallengeSubmission


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner_id",
        "status",
        "duration",
        "created_at",
        "modified_at",
    )
    search_fields = (
        "name",
        "slug",
        "owner_id",
    )
    list_filter = (
        "status",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "modified_at",
    )


@admin.register(ChallengeSubmission)
class ChallengeSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "challenge",
        "owner_id",
        "status",
        "is_public",
        "is_editorial",
        "created_at",
        "modified_at",
    )
    search_fields = (
        "slug",
        "owner_id",
        "challenge__name",
    )
    list_filter = (
        "status",
        "is_public",
        "is_editorial",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "modified_at",
    )


@admin.register(ChallengeAsset)
class ChallengeAssetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "path",
        "file_type",
        "asset_type",
        "challenge",
        "submission",
        "is_public",
        "created_at",
    )
    search_fields = (
        "name",
        "path",
        "slug",
        "owner_id",
    )
    list_filter = (
        "file_type",
        "asset_type",
        "is_public",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "modified_at",
    )