from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView, TemplateView
from users.views import LoginPage, RegisterPage

urlpatterns = [
    # ページルート: / → /login/ にリダイレクト
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('login/', LoginPage.as_view(), name='login'),
    path('register/', RegisterPage.as_view(), name='register'),
    # 新3画面 (認証不要)
    path('home/',   TemplateView.as_view(template_name='home.html'),   name='home'),
    path('input/',  TemplateView.as_view(template_name='input.html'),  name='input'),
    path('result/', TemplateView.as_view(template_name='result.html'), name='result'),

    path('admin/', admin.site.urls),
    path('api/schedule/', include('schedule.urls')),
    path('api/auth/', include('users.urls')),
]
