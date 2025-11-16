from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('gallery/', views.gallery, name='gallery'),
    path('gallery/json/', views.gallery_json, name='gallery_json'),
    path('artwork/<int:pk>/', views.artwork_detail, name='artwork_detail'),
    path('about_thangka/', views.about_thangka, name='about_thangka'),
    path('about_team/', views.about_team, name='about_team'),
    path('contact/', views.contact, name='contact'),
    path('register/', views.user_register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('upload/', views.upload_artwork, name='upload'),
    path('profile/', views.profile, name='profile'),
    path('password-reset/', views.password_reset, name='password_reset'),
    path('artist/', views.artist_dashboard, name='artist_dashboard'),
    path('artist/artworks_json/', views.artist_artworks_json, name='artist_artworks_json'),
    path('chat/', views.chat_page, name='chat_page'),
    path('api/toggle_like/', views.toggle_like, name='toggle_like'),
    path('api/toggle_bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('api/toggle_follow/', views.toggle_follow, name='toggle_follow'),
    path('notifications/', views.notifications_page, name='notifications_page'),
    path('notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notif_read'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
]
