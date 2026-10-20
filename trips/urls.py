from django.urls import path
from . import views
app_name = 'trips'
urlpatterns = [path('',views.TripList.as_view(),name='list'), path('new/',views.edit,name='create'),
    path('<int:pk>/',views.TripDetail.as_view(),name='detail'), path('<int:pk>/edit/',views.edit,name='edit'),
    path('<int:pk>/delete/',views.delete,name='delete'), path('<int:pk>/join/',views.join,name='join')]
