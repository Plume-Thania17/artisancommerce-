# views.py - Version complète avec intégration Wave
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from .models import (Categorie, Product, Commande, UserProfile, 
                    Favorite, ShippingAddress, ProductReview, ContactMessage)
from django.core.paginator import Paginator
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
import json
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Avg
import hashlib
import hmac
from django.db import models
from django.db.models import Sum


# ==================== UTILITAIRES ====================
@login_required
def checkout(request):
    if request.method == "POST":
        data = json.loads(request.body)
        panier = data.get("panier", {})

        commande = Commande.objects.create(
            user=request.user,
            payment_status="pending"
        )

        total = 0
        for product_id, item in panier.items():
            product = Product.objects.get(id=product_id)
            total += item["quantity"] * item["price"]

        commande.total = total
        commande.save()

        return JsonResponse({"success": True})

def generate_wave_payment_link(amount, phone_number, order_id):
    """
    Génère un lien de paiement Wave simplifié
    Note: Pour un vrai déploiement, utilisez l'API officielle Wave
    """
    # Pour le moment, génération d'un lien de paiement simple
    # En production, remplacer par l'API Wave officielle
    base_url = "https://pay.wave.com"
    
    # Paramètres de paiement
    params = {
        'amount': int(amount),
        'currency': 'XOF',
        'phone': phone_number,
        'reference': f'CMD-{order_id}',
        'callback_url': f"{settings.SITE_URL}/payment/wave/callback/"
    }
    
    # Construction du lien (simplifié pour démo)
    payment_link = f"{base_url}/pay?amount={params['amount']}&phone={params['phone']}&ref={params['reference']}"
    
    return payment_link

# ==================== VUES PUBLIQUES ====================

def index(request):
    """Page d'accueil avec produits vedettes"""
    # Récupérer les produits avec pagination
    product_list = Product.objects.filter(is_active=True).select_related('Categorie')
    
    # Recherche par nom
    search_query = request.GET.get('search', '')
    if search_query:
        product_list = product_list.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(product_list, 8)
    page_number = request.GET.get('page')
    product_object = paginator.get_page(page_number)
    
    # Récupérer toutes les catégories pour le menu
    categories = Categorie.objects.all()
    
    context = {
        'product_object': product_object,
        'categories': categories,
        'search_query': search_query
    }
    
    return render(request, 'index.html', context)

def detail(request, myid):
    """Page détail d'un produit avec avis"""
    product = get_object_or_404(Product, id=myid)
    
    # Vérifier si favori
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(
            user=request.user, 
            product=product
        ).exists()
    
    # Calculer le pourcentage de réduction
    discount_percent = product.get_discount_percent()
    
    # Récupérer les avis
    reviews = ProductReview.objects.filter(product=product).select_related('user')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Produits similaires
    related_products = Product.objects.filter(
        Categorie=product.Categorie,
        is_active=True
    ).exclude(id=myid)[:4]
    
    context = {
        'product': product,
        'is_favorite': is_favorite,
        'discount_percent': discount_percent,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'related_products': related_products
    }
    
    return render(request, 'detail.html', context)

def products(request):
    """Page liste des produits avec filtres"""
    # Base queryset
    product_list = Product.objects.filter(is_active=True).select_related('Categorie')
    
    # Filtrage par catégorie
    category_id = request.GET.get('category')
    if category_id:
        product_list = product_list.filter(Categorie_id=category_id)
    
    # Filtrage par recherche
    search = request.GET.get('search', '')
    if search:
        product_list = product_list.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Tri
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price-asc':
        product_list = product_list.order_by('price')
    elif sort_by == 'price-desc':
        product_list = product_list.order_by('-price')
    elif sort_by == 'name':
        product_list = product_list.order_by('title')
    else:  # newest
        product_list = product_list.order_by('-date_ajout')
    
    # Pagination
    paginator = Paginator(product_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Marquer les favoris
    if request.user.is_authenticated:
        favorite_ids = Favorite.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)
        
        for product in page_obj:
            product.is_favorite = product.id in favorite_ids
    
    # Catégories pour la sidebar
    categories = Categorie.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category_id,
        'search_query': search
    }
    
    return render(request, 'products.html', context)

# ==================== AUTHENTIFICATION ====================

def register(request):
    """Inscription utilisateur"""
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, "Bienvenue sur Mynia Boutique !")
                return redirect('home')
            except Exception as e:
                messages.error(request, f"Erreur lors de l'inscription: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = RegisterForm()
    
    return render(request, 'register.html', {'form': form})

def user_login(request):
    """Connexion utilisateur"""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Redirection
                next_url = request.POST.get('next', '') or request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                
                messages.success(request, f"Bienvenue {user.first_name or user.username} !")
                return redirect('home')
            else:
                messages.error(request, "Identifiants incorrects")
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    """Déconnexion"""
    logout(request)
    messages.info(request, "Vous êtes déconnecté")
    return redirect('home')

# ==================== PROFIL ====================

@login_required
def profile(request):
    """Page profil utilisateur"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Statistiques
    total_orders = Commande.objects.filter(user=request.user).count()
    total_spent = Commande.objects.filter(
        user=request.user, 
        payment_status='paid'
    ).aggregate(total=models.Sum('total'))['total'] or 0
    
    context = {
        'profile': profile,
        'total_orders': total_orders,
        'total_spent': total_spent
    }
    
    return render(request, 'profile.html', context)

@login_required
def edit_profile(request):
    """Édition du profil"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            # Mise à jour User
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name = request.POST.get('last_name', '')
            request.user.email = request.POST.get('email', '')
            request.user.save()
            
            # Mise à jour Profile
            profile.phone = request.POST.get('phone', '')
            profile.address = request.POST.get('address', '')
            profile.ville = request.POST.get('ville', '')
            profile.zipcode = request.POST.get('zipcode', '')
            profile.date_naissance = request.POST.get('date_naissance') or None
            
            if 'profile_pic' in request.FILES:
                profile.profile_pic = request.FILES['profile_pic']
            
            profile.save()
            
            messages.success(request, "Profil mis à jour avec succès !")
            return redirect('profile')
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
    
    return render(request, 'edit_profile.html', {'profile': profile})

# ==================== ADRESSES ====================

@login_required
def adresse(request):
    """Page liste des adresses de livraison"""
    addresses = ShippingAddress.objects.filter(user=request.user).order_by('-is_default', '-id')
    
    context = {
        'addresses': addresses
    }
    
    return render(request, 'adresse.html', context)

@login_required
def add_address(request):
    if request.method == "POST":
        # Définir par défaut si coché
        if request.POST.get('is_default'):
            ShippingAddress.objects.filter(
                user=request.user,
                is_default=True
            ).update(is_default=False)

        ShippingAddress.objects.create(
            user=request.user,
            nom_complet=request.POST['nom_complet'],
            phone=request.POST['phone'],
            address=request.POST['address'],
            ville=request.POST['ville'],
            address_type=request.POST['address_type'],
            is_default=bool(request.POST.get('is_default'))
        )

        messages.success(request, "Adresse ajoutée avec succès !")
        return redirect('adresse')

    return render(request, 'add_address.html')

@login_required
def delete_address(request, address_id):
    """Supprimer une adresse"""
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Adresse supprimée")
    return redirect('adresse')

@login_required
def set_default_address(request, address_id):
    ShippingAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
    
    address = get_object_or_404(
        ShippingAddress,
        id=address_id,
        user=request.user
    )
    address.is_default = True
    address.save()

    messages.success(request, "Adresse définie par défaut")
    return redirect('adresse')

# ==================== FAVORIS ====================

@login_required
def favorites(request):
    """Page favoris"""
    user_favorites = Favorite.objects.filter(
        user=request.user
    ).select_related('product', 'product__Categorie')
    
    return render(request, 'favorites.html', {'favorites': user_favorites})

@login_required
def add_favorite(request, product_id):
    """Ajouter aux favoris"""
    product = get_object_or_404(Product, id=product_id)
    Favorite.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f"{product.title} ajouté aux favoris")
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def remove_favorite(request, product_id):
    """Retirer des favoris"""
    Favorite.objects.filter(
        user=request.user, 
        product_id=product_id
    ).delete()
    messages.info(request, "Produit retiré des favoris")
    return redirect(request.META.get('HTTP_REFERER', 'favorites'))

# ==================== COMMANDES ====================

@login_required
def order(request):
    commandes = Commande.objects.filter(user=request.user).order_by('-date_commande')
    return render(request, 'order.html', {'commandes': commandes})

@login_required
def order_detail(request, order_id):
    """Détail d'une commande"""
    order = get_object_or_404(Commande, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'order_number': order.order_number,
        'items': order.items if isinstance(order.items, list) else []
    }
    
    return render(request, 'order_detail.html', context)

# ==================== CHECKOUT & PAIEMENT ====================

@login_required
def checkout(request):
    """Page panier"""
    return render(request, 'checkout.html')

@login_required
def confirmation(request):
    """Page sélection adresse et paiement"""
    # Récupérer les adresses de l'utilisateur
    addresses = ShippingAddress.objects.filter(user=request.user)
    
    # Adresse par défaut
    default_address = addresses.filter(is_default=True).first()
    
    context = {
        'addresses': addresses,
        'default_address': default_address
    }
    
    return render(request, 'confirmation.html', context)

@login_required
def process_order(request):
    """Traitement de la commande et création"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)
    
    try:
        # Parser les données JSON
        data = json.loads(request.body)
        
        # Validation
        if not data.get('items'):
            return JsonResponse({'success': False, 'message': 'Panier vide'}, status=400)
        
        if not data.get('payment_method'):
            return JsonResponse({'success': False, 'message': 'Méthode de paiement requise'}, status=400)
        
        # Calculer le total
        items = data.get('items', [])
        subtotal = Decimal(0)
        
        for item in items:
            subtotal += Decimal(str(item.get('total', 0)))
        
        shipping_cost = Decimal('2000')  # Frais de livraison fixes
        total = subtotal + shipping_cost
        
        # Créer la commande
        commande = Commande.objects.create(
            user=request.user,
            items=items,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            total=total,
            nom=data.get('name', f"{request.user.first_name} {request.user.last_name}"),
            email=request.user.email,
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            ville=data.get('ville', ''),
            pays=data.get('pays', "Côte d'Ivoire"),
            zipcode=data.get('zipcode', ''),
            payment_method=data.get('payment_method'),
            payment_status='pending'
        )
        
        # Générer lien de paiement selon la méthode
        payment_url = None
        
        if data.get('payment_method') == 'wave':
            # Générer le lien Wave avec VOTRE numéro
            payment_url = generate_wave_payment_link(
                amount=float(total),
                phone_number='22707687487',  # VOTRE NUMÉRO
                order_id=commande.id
            )
        
        elif data.get('payment_method') == 'orange':
            # Lien Orange Money (à implémenter selon vos besoins)
            payment_url = f"/payment/orange/{commande.id}/"
        
        # Réponse de succès
        response_data = {
            'success': True,
            'order_id': commande.id,
            'order_number': commande.order_number,
            'total': str(total),
            'redirect_url': reverse('order_success', args=[commande.id])
        }
        
        if payment_url:
            response_data['payment_url'] = payment_url
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Données invalides'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def order_success(request, order_id):
    """Page de succès de commande"""
    order = get_object_or_404(Commande, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'order_number': order.order_number,
        'items': order.items if isinstance(order.items, list) else [],
        'total': order.total,
        'shipping_cost': order.shipping_cost
    }
    
    return render(request, 'order_success.html', context)

# ==================== CALLBACKS PAIEMENT ====================

def wave_callback(request):
    """Callback Wave pour confirmation de paiement"""
    if request.method == 'POST':
        try:
            # Récupérer les données de Wave
            data = json.loads(request.body)
            
            # Valider la signature (en production)
            # validate_wave_signature(data)
            
            # Mettre à jour la commande
            order_number = data.get('reference', '')
            if order_number.startswith('CMD-'):
                order_id = int(order_number.split('-')[1])
                commande = Commande.objects.get(id=order_id)
                
                if data.get('status') == 'success':
                    commande.payment_status = 'paid'
                    commande.date_paiement = timezone.now()
                    commande.payment_reference = data.get('transaction_id', '')
                    commande.save()
                    
                    return JsonResponse({'status': 'success'})
            
            return JsonResponse({'status': 'error', 'message': 'Commande non trouvée'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error'}, status=405)

# ==================== PARAMÈTRES ====================

@login_required
def setting(request):
    """Page paramètres"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Mise à jour des préférences
        profile.newsletter = request.POST.get('newsletter') == 'on'
        profile.notifications_email = request.POST.get('notifications_email') == 'on'
        profile.notifications_sms = request.POST.get('notifications_sms') == 'on'
        profile.save()
        
        messages.success(request, "Paramètres mis à jour")
        return redirect('setting')
    
    return render(request, 'setting.html', {'profile': profile})

# ==================== AVIS PRODUITS ====================

@login_required
def add_review(request, product_id):
    """Ajouter un avis sur un produit"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        # Vérifier si l'utilisateur a déjà laissé un avis
        existing_review = ProductReview.objects.filter(
            user=request.user, 
            product=product
        ).first()
        
        rating = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '')
        
        if existing_review:
            existing_review.rating = rating
            existing_review.comment = comment
            existing_review.save()
            messages.success(request, "Avis mis à jour")
        else:
            ProductReview.objects.create(
                user=request.user,
                product=product,
                rating=rating,
                comment=comment
            )
            messages.success(request, "Avis ajouté avec succès")
        
        return redirect('detail', myid=product_id)
    
    return redirect('home')
# ==================== PAGES STATIQUES ====================

def about(request):
    """Page À propos / Notre Histoire"""
    categories = Categorie.objects.all()
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'about.html', context)

def contact(request):
    """Page de contact avec formulaire"""
    categories = Categorie.objects.all()
    
    if request.method == 'POST':
        try:
            # Créer le message de contact
            ContactMessage.objects.create(
                nom=request.POST.get('nom'),
                email=request.POST.get('email'),
                sujet=request.POST.get('sujet'),
                message=request.POST.get('message')
            )
            
            messages.success(request, "Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.")
            return redirect('contact')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de l'envoi du message : {str(e)}")
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'contact.html', context)
# Ajoutez cette vue dans votre fichier views.py

def search(request):
    """Vue de recherche de produits"""
    query = request.GET.get('q', '').strip()
    categories = Categorie.objects.all()
    
    # Initialiser les résultats
    products = Product.objects.filter(is_active=True).select_related('Categorie')
    
    # Filtrage par recherche
    if query:
        products = products.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(Categorie__name__icontains=query)
        )
    
    # Filtrage par catégories
    selected_categories = request.GET.get('categories', '').split(',')
    selected_categories = [cat for cat in selected_categories if cat]
    
    if selected_categories:
        products = products.filter(Categorie_id__in=selected_categories)
    
    # Tri
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price-asc':
        products = products.order_by('price')
    elif sort_by == 'price-desc':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('title')
    else:  # newest
        products = products.order_by('-date_ajout')
    
    context = {
        'query': query,
        'products': products,
        'products_count': products.count(),
        'categories': categories,
        'selected_categories': selected_categories,
        'sort_by': sort_by,
    }
    
    return render(request, 'search_results.html', context)