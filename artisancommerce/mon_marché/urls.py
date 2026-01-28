# urls.py - Routes complètes pour l'application
from django.urls import path
from . import views

urlpatterns = [
    # ==================== PAGES PUBLIQUES ====================
    path('', views.index, name='home'),
    path('products/', views.products, name='products'),
    path('detail/<int:myid>/', views.detail, name='detail'),
    
    # ==================== AUTHENTIFICATION ====================
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # ==================== PROFIL UTILISATEUR ====================
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/settings/', views.setting, name='setting'),
    
    # ==================== ADRESSES ====================
    path('profile/addresses/', views.adresse, name='adresse'),
    path('profile/addresses/add/', views.add_address, name='add_address'),
    path('profile/addresses/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('profile/addresses/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),
    
    # ==================== FAVORIS ====================
    path('favorites/', views.favorites, name='favorites'),
    path('favorites/add/<int:product_id>/', views.add_favorite, name='add_favorite'),
    path('favorites/remove/<int:product_id>/', views.remove_favorite, name='remove_favorite'),
    
    # ==================== COMMANDES ====================
    path('orders/', views.order, name='order'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # ==================== CHECKOUT & PAIEMENT ====================
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/confirmation/', views.confirmation, name='confirmation'),
    path('checkout/process/', views.process_order, name='process_order'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    
    # ==================== CALLBACKS PAIEMENT ====================
    path('payment/wave/callback/', views.wave_callback, name='wave_callback'),
    
    # ==================== AVIS PRODUITS ====================
    path('review/add/<int:product_id>/', views.add_review, name='add_review'),
       # Pages statiques
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('search/', views.search, name='search'),
]