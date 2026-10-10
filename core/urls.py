from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('services/<slug:slug>/', views.service_detail, name='service_detail'),
    path('counsellors/', views.counsellors, name='counsellors'),
    path('about/', views.about, name='about'),
    path('book/', views.book, name='book'),
    path('book/availability/', views.booking_availability, name='booking_availability'),
    path('book/<int:booking_id>/confirmed/', views.book_confirmed, name='book_confirmed'),
]
