from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    path('add-event/', views.AddEventView.as_view(), name='add-event'),
    path('get-events/', views.GetEventsView.as_view(), name='get-events'),
    path('events/<int:event_id>/', views.EventDetailView.as_view(), name='event-detail'),
    path('settings/',      views.UserSettingsView.as_view(),  name='settings'),
    path('modify-event/',  views.ModifyEventView.as_view(),   name='modify-event'),
    path('command/',       views.CommandView.as_view(),        name='command'),
]