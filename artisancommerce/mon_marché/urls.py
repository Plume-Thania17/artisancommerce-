from django.urls import path
from mon_marché.views import (
    index,
    detail,
    checkout,
    confirmation,
    initiate_orange_payment,
    initiate_wave_payment,
    register,
    user_login,
    user_logout,
    profile,
    favorites,
    add_favorite,
    remove_favorite,
    edit_profile  ,# Ajouter edit_profile ici
    products,
    
)
from mon_marché.views import initiate_payment

urlpatterns = [
    # URLs existantes
    path('', index, name='home'),
    path('<int:myid>', detail, name="detail"),
    path('checkout/', checkout, name="checkout"),
    path('products/', products, name='products'),
    path('confirmation/<int:order_id>/', confirmation, name='confirmation'),  
    
    # Nouveaux endpoints de paiement
path('payment/<str:method>/<int:order_id>/', initiate_payment, name="initiate_payment"),
    
    # URLs d'authentification
    path('register/', register, name='register'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('profile/', profile, name='profile'),
    path('profile/edit/', edit_profile, name='edit_profile'),  # Utiliser la fonction importée
    path('favorites/', favorites, name='favorites'),
     
    path('favorites/add/<int:product_id>/', add_favorite, name='add_favorite'),
    path('favorites/remove/<int:product_id>/', remove_favorite, name='remove_favorite'),
]