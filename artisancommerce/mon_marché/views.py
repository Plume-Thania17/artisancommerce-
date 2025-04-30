from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from .models import Categorie, Product, Commande, UserProfile, Favorite
from django.core.paginator import Paginator
import requests  
import random
import string
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm  # Import des nouveaux formulaires
# Fonction pour générer un ID de commande aléatoire
import json
from decimal import Decimal
from django.http import JsonResponse
from django.urls import reverse





def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

# Fonction pour générer une référence client
def generate_client_reference():
    return 'CLIENT-' + ''.join(random.choices(string.digits, k=8))

def index(request):
    Product_object = Product.objects.all()
    item_name = request.GET.get('item-name')
    if item_name != '' and item_name is not None:
        Product_object = Product.objects.filter(title__icontains=item_name)
    paginator = Paginator(Product_object, 4)
    page = request.GET.get('page')
    Product_object = paginator.get_page(page)
    return render(request, 'index.html', {'product_object': Product_object})

def detail(request, myid):
    product_object = Product.objects.get(id=myid)
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product_object).exists()
    return render(request, 'detail.html', {
        'product': product_object,
        'is_favorite': is_favorite
    })
# Nouvelle version de checkout avec gestion authentifiée
def checkout(request):
    if not request.user.is_authenticated:
        return redirect(f'/login/?next={request.path}')
    
    if request.method == "POST":
        items = request.POST.get('items')
        total = request.POST.get('total')
        
        # Utilisation des infos du profil connecté
        com = Commande(
            items=items,
            total=total,
            nom=request.user.get_full_name(),
            email=request.user.email,
            address=request.POST.get('address'),
            ville=request.POST.get('ville'),
            pays=request.POST.get('pays'),
            zipcode=request.POST.get('zipcode'),
            user=request.user  # Lier la commande à l'utilisateur
        )
        com.save()
        return redirect('confirmation')
    
    # Pré-remplir avec les infos utilisateur si disponible
    try:
        profile = request.user.profile
        initial_data = {
            'nom': request.user.get_full_name(),
            'email': request.user.email,
            'phone': profile.phone
        }
    except UserProfile.DoesNotExist:
        initial_data = {}
    
    return render(request, 'checkout.html', {'initial_data': initial_data})



def confirmation(request, order_id=None):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Si order_id est fourni, récupérer cette commande spécifique
    if order_id:
        commande = get_object_or_404(Commande, id=order_id, user=request.user)
    else:
        # Sinon, récupérer la dernière commande de l'utilisateur
        commande = Commande.objects.filter(user=request.user).order_by('-date_commande').first()
        if not commande:
            return redirect('home')
    
    context = {
        'commande': commande,
        'order_number': f"CMD-{commande.id:06d}",
        'items': commande.items if isinstance(commande.items, list) else [],
        'total': float(commande.total) + 2000,  # Ajout des frais de livraison
        'shipping_cost': 2000,
        'payment_method': dict(Commande.PAYMENT_METHODS).get(commande.payment_method, ''),
        'payment_status': dict(Commande.PAYMENT_STATUS).get(commande.payment_status, '')
    }
    
    return render(request, 'confirmation.html', context)

@login_required
def initiate_payment(request, method, order_id):
    """
    Vue unifiée pour initier les paiements Orange Money et Wave
    """
    commande = get_object_or_404(Commande, id=order_id, user=request.user)
    
    if method == 'orange':
        return initiate_orange_payment(request, order_id)
    elif method == 'wave':
        return initiate_wave_payment(request, order_id)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Méthode de paiement non supportée'
        }, status=400)



def initiate_orange_payment(request, commande_id=None):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Vérification que les settings sont bien configurés
        if not all([hasattr(settings, 'ORANGE_MERCHANT_KEY'), 
                   hasattr(settings, 'ORANGE_API_TOKEN')]):
            return JsonResponse({'status': 'error', 'message': 'Configuration Orange Money manquante'}, status=500)
            
        payload = {
            'merchant_key': settings.ORANGE_MERCHANT_KEY,
            'currency': 'XOF',
            'order_id': generate_order_id(),
            'amount': amount,
            'return_url': getattr(settings, 'ORANGE_CALLBACK_URL', ''),
            'cancel_url': getattr(settings, 'ORANGE_CANCEL_URL', ''),
            'notif_url': getattr(settings, 'ORANGE_NOTIF_URL', ''),
            'lang': 'fr'
        }
        
        try:
            response = requests.post(
                'https://api.orange.com/orange-money-webpay/dev/v1/webpayment',
                json=payload,
                headers={'Authorization': f'Bearer {settings.ORANGE_API_TOKEN}'},
                timeout=30
            )
            response.raise_for_status()  # Lève une exception pour les codes 4XX/5XX
            return JsonResponse(response.json())
        except requests.exceptions.RequestException as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

def initiate_wave_payment(request, commande_id=None):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Vérification de la configuration Wave
        if not all([hasattr(settings, 'WAVE_API_KEY'), 
                   hasattr(settings, 'WAVE_MERCHANT_ID')]):
            return JsonResponse({'status': 'error', 'message': 'Configuration Wave manquante'}, status=500)
            
        payload = {
            'amount': amount,
            'currency': 'XOF',
            'client_reference': generate_client_reference(),
            'error_url': getattr(settings, 'WAVE_ERROR_URL', ''),
            'success_url': getattr(settings, 'WAVE_SUCCESS_URL', '')
        }
        
        try:
            response = requests.post(
                'https://api.wave.com/v1/checkout/sessions',
                json=payload,
                headers={
                    'Authorization': f'Bearer {settings.WAVE_API_KEY}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            response.raise_for_status()
            return JsonResponse(response.json())
        except requests.exceptions.RequestException as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)
# Nouvelles vues d'authentification
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # Création automatique du profil
            UserProfile.objects.create(
                user=user,
                phone=form.cleaned_data['phone'],
                profile_picture=form.cleaned_data['profile_pic']
            )
            # Connexion automatique
            login(request, user)
            messages.success(request, "Inscription réussie !")
            return redirect('home')
    
        else:
            print(form.errors)  # Debug
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Récupérer le paramètre next du formulaire ou de l'URL
                next_url = request.POST.get('next', '') or request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('home')
            else:
                messages.error(request, "Identifiants incorrects")
        else:
            # Afficher les erreurs de formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('home')
@login_required
def profile(request):
    try:
        # Essayez d'obtenir ou de créer le profil
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        return render(request, 'profile.html', {'user': request.user, 'profile': profile})
    except Exception as e:
        messages.error(request, f"Erreur lors de l'accès au profil: {str(e)}")
        return redirect('home')
@login_required
def favorites(request):
    # Récupérer les favoris de l'utilisateur connecté
    user_favorites = Favorite.objects.filter(user=request.user).select_related('product')
    return render(request, 'favorites.html', {'favorites': user_favorites})
@login_required
def add_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Favorite.objects.get_or_create(user=request.user, product=product)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def remove_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Favorite.objects.filter(user=request.user, product=product).delete()
    return redirect('favorites')


@login_required
def checkout(request):
    if request.method == "POST":
        try:
            # Récupérer et valider les données du formulaire
            payment_method = request.POST.get('payment_method')
            if not payment_method or payment_method not in dict(Commande.PAYMENT_METHODS):
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Veuillez sélectionner un mode de paiement valide'
                }, status=400)

            # Récupérer le panier depuis localStorage via AJAX
            try:
                panier = json.loads(request.POST.get('items', '[]'))
                if not panier:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Votre panier est vide'
                    }, status=400)
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Format de panier invalide'
                }, status=400)

            # Convertir le panier en format structuré
            items_list = []
            total = Decimal(0)
            
            for item in panier:
                try:
                    item_total = Decimal(str(item.get('total', 0)))
                    items_list.append({
                        'id': str(item.get('id', '')),
                        'product_id': int(item.get('id', 0)),  # Pour référence produit
                        'name': str(item.get('name', '')),
                        'quantity': int(item.get('quantity', 1)),
                        'price': str(Decimal(str(item.get('price', 0)))),
                        'total': str(item_total)
                    })
                    total += item_total
                except (ValueError, TypeError) as e:
                    continue  # Ignorer les items invalides

            # Validation des données de livraison
            required_fields = ['address', 'ville', 'zipcode']
            missing_fields = [field for field in required_fields if not request.POST.get(field)]
            if missing_fields:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Champs obligatoires manquants: {", ".join(missing_fields)}'
                }, status=400)

            # Créer la commande
            commande = Commande(
                items=items_list,
                total=total,
                nom=f"{request.user.first_name} {request.user.last_name}".strip(),
                email=request.user.email,
                address=request.POST.get('address'),
                ville=request.POST.get('ville'),
                pays=request.POST.get('pays', 'Côte d\'Ivoire'),
                zipcode=request.POST.get('zipcode'),
                user=request.user,
                payment_method=payment_method,
                payment_status='pending'
            )
            commande.full_clean()  # Validation du modèle
            commande.save()

            # Réponse JSON standardisée
            response_data = {
                'status': 'success',
                'order_id': commande.id,
                'order_number': f"CMD-{commande.id:06d}",
                'total': str(total + Decimal(2000))  # Inclut les frais de livraison
            }

            # Gestion des différents modes de paiement
            if payment_method in ['orange', 'wave']:
                response_data['payment_url'] = reverse('initiate_payment', kwargs={
                    'method': payment_method,
                    'order_id': commande.id
                })
            else:
                response_data['redirect_url'] = reverse('confirmation', args=[commande.id])

            return JsonResponse(response_data)

        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f"Erreur lors du traitement de la commande: {str(e)}"
            }, status=500)

    # GET request - afficher le formulaire
    context = {}
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            context['initial_data'] = {
                'nom': f"{request.user.first_name} {request.user.last_name}",
                'email': request.user.email,
                'address': profile.address,
                'ville': profile.ville,
                'pays': getattr(profile, 'pays', 'Côte d\'Ivoire'),
                'zipcode': profile.zipcode,
                'phone': profile.phone
            }
        except UserProfile.DoesNotExist:
            context['initial_data'] = {
                'nom': f"{request.user.first_name} {request.user.last_name}",
                'email': request.user.email
            }
    
    return render(request, 'checkout.html', context)

@login_required
def edit_profile(request):
    try:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'POST':
            # Mettre à jour les informations de l'utilisateur
            user = request.user
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()
            
            # Mettre à jour les informations du profil
            profile.phone = request.POST.get('phone', '')
            profile.address = request.POST.get('address', '')
            profile.ville = request.POST.get('ville', '')
            profile.zipcode = request.POST.get('zipcode', '')
            
            # Traiter l'image de profil
            if 'profile_pic' in request.FILES:
                profile.profile_pic = request.FILES['profile_pic']
            
            profile.save()
            messages.success(request, "Profil mis à jour avec succès!")
            return redirect('profile')
        
        return render(request, 'edit_profile.html', {'user': request.user, 'profile': profile})
    except Exception as e:
        messages.error(request, f"Erreur lors de l'édition du profil: {str(e)}")
        return redirect('profile')
def products(request):
    product_list = Product.objects.all()
    categories = Categorie.objects.all()  # Récupérer toutes les catégories
    
    # Filtrage par catégorie si le paramètre 'category' existe
    category_id = request.GET.get('category')
    if category_id:
        product_list = product_list.filter(Categorie_id=category_id)
    
    # Pagination et gestion des favoris (votre code existant)
    paginator = Paginator(product_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.user.is_authenticated:
        favorite_product_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        for product in page_obj.object_list:
            product.is_favorite = product.id in favorite_product_ids
    
    return render(request, 'products.html', {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'categories': categories,  # Ajout des catégories au contexte
        'user': request.user
    })