from django.urls import path

from .views import *

urlpatterns = [
    # public Api
    path("", challenge, name="challenge-list"),
    path("<uuid:challenge_slug>/", particular_challenge, name="particular-challenge"),

]