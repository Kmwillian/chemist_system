from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth import logout
from django.shortcuts import redirect


app_name = 'accounts'
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    #path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    #path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('logout/', logout_view, name='logout'),
]