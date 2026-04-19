from django.urls import path

from . import views


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.student_list, name='student_list'),
    path('student/add/', views.student_add, name='student_add'),
    path('student/edit/<str:sno>/', views.student_edit, name='student_edit'),
    path('student/delete/<str:sno>/', views.student_delete, name='student_delete'),
    path('student/query/', views.student_query, name='student_query'),
    path('student/stat/', views.student_stat, name='student_stat'),
    path('student/score/<str:sno>/', views.student_score_manage, name='student_score_manage'),
    path('student/score/delete/<int:score_id>/', views.student_score_delete, name='student_score_delete'),
    path('student/reset-password/<str:sno>/', views.student_reset_password, name='student_reset_password'),
    path('student/user/login/', views.student_login, name='student_login'),
    path('student/user/center/', views.student_center, name='student_center'),
    path('student/user/ai/', views.student_ai, name='student_ai'),
    path('student/user/logout/', views.student_logout, name='student_logout'),
    path('student/user/change_pwd/', views.student_change_pwd, name='student_change_pwd'),
]
