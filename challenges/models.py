from django.db import models
import uuid

class Challenge(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration = models.PositiveIntegerField()  # seconds
    slug = models.SlugField(max_length=220, unique=True, editable=False, blank=False, null=False)
    is_public_solution = models.BooleanField(default=False)

    owner_id = models.UUIDField(db_index=True,)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)


    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "challenge"
        verbose_name = "Challenge"
        verbose_name_plural = "Challenges"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = str(uuid.uuid4())

        super().save(*args, **kwargs)

class ChallengeSubmission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="submissions")
    owner_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=255)
    is_editorial = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "challenge_submission"
        verbose_name = "Challenge submission"
        verbose_name_plural = "Challenge submissions"

class ChallengeAsset(models.Model):
    class FileType(models.TextChoices):
        CODE = "code", "Code"
        MEDIA = "media", "Media"

    class AssetType(models.TextChoices):
        CHALLENGE = "challenge", "Challenge Asset"
        SOLUTION = "solution", "Solution Code File"

    name = models.CharField(max_length=255)

    file_type = models.CharField(max_length=20, choices=FileType.choices)
    asset_url = models.CharField(max_length=500)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="assets", null=True, blank=True)
    submission = models.ForeignKey(ChallengeSubmission, on_delete=models.CASCADE, related_name="assets", null=True, blank=True)
    asset_type = models.CharField( max_length=20, choices=AssetType.choices)
    is_public = models.BooleanField(default=False)
    owner_id = models.UUIDField(db_index=True)
    slug = models.SlugField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "challenge_asset"
        verbose_name = "Challenge asset"
        verbose_name_plural = "Challenge assets"