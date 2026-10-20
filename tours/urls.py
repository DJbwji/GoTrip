from django.urls import path
from . import views
app_name = 'tours'
urlpatterns = [path('',views.Catalog.as_view(),name='catalog'), path('new/',views.edit,name='create'),
    path('<int:pk>/',views.detail,name='detail'), path('<int:pk>/edit/',views.edit,name='edit'),
    path('<int:pk>/delete/',views.delete,name='delete'), path('<int:pk>/submit/',views.submit,name='submit'),
    path('<int:pk>/favorite/',views.favorite,name='favorite'), path('<int:pk>/review/',views.review,name='review')]
