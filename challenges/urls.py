from django.urls import path

from . import views

urlpatterns = [
    # public Api
    path("", views.challenges, name="challenge-list"),
    path("<uuid:challenge_slug>/", views.particular_challenge, name="particular-challenge"),

    # assets
    path("<uuid:challenge_slug>/assets/", views.challenge_assets, name="challenge-assets"),
    path("<uuid:challenge_slug>/assets/<slug:asset_slug>/", views.challenge_asset_detail, name="challenge-asset-detail"),

    # submission
    path("<uuid:challenge_slug>/submissions/", views.challenge_submissions, name="challenge-submissions"),
    path("<uuid:challenge_slug>/submissions/<slug:submission_slug>/", views.challenge_submission_detail, name="challenge-submission-detail"),
]