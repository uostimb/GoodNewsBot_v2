from django.urls import path

from goodnewsbot_worker import views


urlpatterns = [
    path('', views.LandingView.as_view(), name='goodnewsbot_landing'),
]
