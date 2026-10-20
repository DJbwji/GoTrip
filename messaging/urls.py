from django.urls import path
from . import views
app_name = 'messaging'
urlpatterns = [path('',views.inbox,name='inbox'),path('start/<int:pk>/',views.start,name='start'),path('<int:pk>/',views.chat,name='chat')]
