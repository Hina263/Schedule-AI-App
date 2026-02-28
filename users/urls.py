from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/',    views.LoginView.as_view(),    name='login'),
    path('logout/',   views.LogoutView.as_view(),   name='logout'),
    path('google/',   views.GoogleLoginView.as_view(), name='google'),
    path('me/',       views.MeView.as_view(),       name='me'),
]
