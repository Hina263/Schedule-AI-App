from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    path('add-event/', views.AddEventView.as_view(), name='add-event'),
    path('get-events/', views.GetEventsView.as_view(), name='get-events'),
    path('events/<int:event_id>/', views.DeleteEventView.as_view(), name='delete-event'),
]