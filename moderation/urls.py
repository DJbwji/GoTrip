from django.urls import path
from . import views
app_name = 'moderation'
urlpatterns = [path('',views.queue,name='queue'),path('complain/<int:pk>/',views.complain,name='complain'),path('<str:kind>/<int:pk>/',views.decision,name='decision')]
