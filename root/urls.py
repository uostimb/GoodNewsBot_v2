from django.urls import path

from root import views


urlpatterns = [
    path('', views.RootView.as_view(), name='root'),
]
