from django.urls import path
from . import views
app_name = 'bookings'
urlpatterns = [path('create/<int:pk>/',views.create,name='create'),path('<int:pk>/payment/',views.payment,name='payment'),path('<int:pk>/cancel/',views.cancel,name='cancel')]
