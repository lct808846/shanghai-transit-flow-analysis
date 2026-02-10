from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change-password'),
    # 管理员接口
    path('users/', views.user_list, name='user-list'),
    path('users/<int:user_id>/role/', views.update_user_role, name='update-user-role'),
    path('users/<int:user_id>/toggle/', views.toggle_user_active, name='toggle-user-active'),
]
