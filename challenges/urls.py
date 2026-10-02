from django.urls import path

from .views import *

urlpatterns = [
    # public Api
    path("", views.challenges, name="challenge-list"),
    path("<uuid:challenge_slug>/", views.particular_challenge, name="particular-challenge"),

]