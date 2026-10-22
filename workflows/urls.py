from django.urls import path
from . import views

urlpatterns = [
    path('', views.feed_view, name='feed'),
    path('workflow/<int:pk>/', views.detail_view, name='detail'),
    path('create/', views.create_workflow_view, name='create'),
    path('upvote/<int:pk>/', views.upvote_view, name='upvote'),
    
    path('profile/<str:username>/', views.user_profile_view, name='profile'),
    path('profile/<str:username>/network/', views.network_view, name='network'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('update-picture/', views.update_profile_picture_view, name='update_profile_picture'),
    
    path('toggle-follow/<str:username>/', views.toggle_follow_view, name='toggle_follow'),
    
    path('workflow/<int:pk>/update/', views.update_workflow_view, name='update'),
    path('workflow/<int:pk>/delete/', views.delete_workflow_view, name='delete'),
    
    path('workflow/<int:pk>/comment/', views.add_comment_view, name='add_comment'),
    path('workflow/<int:pk>/love/', views.toggle_love_view, name='toggle_love'),
    
    path('notifications/', views.notifications_view, name='notifications'),
    path('trending/', views.trending_view, name='trending'),

    path('saved/', views.saved_view, name='saved'),
    path('bookmark/<int:pk>/', views.toggle_bookmark_view, name='toggle_bookmark'),
]