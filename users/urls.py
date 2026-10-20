from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth
from . import views
from .forms import EmailLoginForm
app_name = 'users'
urlpatterns = [
    path('signup/',views.signup,name='signup'),
    path('login/',auth.LoginView.as_view(authentication_form=EmailLoginForm),name='login'),
    path('logout/',auth.LogoutView.as_view(),name='logout'),
    path('',views.dashboard,name='dashboard'),
    path('profile/',views.profile_edit,name='profile'),
    path('become-guide/',views.guide_apply,name='guide_apply'),
    path('guides/',views.GuideList.as_view(),name='guides'),
    path('guides/<int:pk>/',views.GuideDetail.as_view(),name='guide'),
    path('password/reset/',auth.PasswordResetView.as_view(success_url=reverse_lazy('users:password_reset_done')),name='password_reset'),
    path('password/sent/',auth.PasswordResetDoneView.as_view(),name='password_reset_done'),
    path('password/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(success_url=reverse_lazy('users:password_reset_complete')),name='password_reset_confirm'),
    path('password/complete/',auth.PasswordResetCompleteView.as_view(),name='password_reset_complete'),
]
