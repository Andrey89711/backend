from django.urls import path
from . import views

urlpatterns = [
    path('register/',                                       views.register_user,             name='admin-register'),
    path('users/',                                          views.list_users,                name='admin-users'),
    path('personnel/<str:role>/<int:pk>/',                  views.update_personnel,          name='admin-personnel-update'),
    path('personnel/<str:role>/<int:pk>/change-password/',  views.change_personnel_password, name='admin-personnel-password'),
    path('personnel/<str:role>/<int:pk>/user/',             views.get_personnel_user,        name='admin-personnel-user'),

    path('admins/',          views.list_admins,   name='admin-list'),
    path('admins/create/',   views.create_admin,  name='admin-create'),
    path('admins/<int:pk>/', views.delete_admin,  name='admin-delete'),
]
