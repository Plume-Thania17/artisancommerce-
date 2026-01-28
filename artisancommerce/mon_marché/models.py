# models.py - Version complète et améliorée
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid

# ==================== CATÉGORIES ====================
class Categorie(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nom de la catégorie")
    description = models.TextField(blank=True, verbose_name="Description")
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
    
    def __str__(self):
        return self.name
    
    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        elif self.image_url:
            return self.image_url
        return 'https://via.placeholder.com/300x200?text=No+Image'

# ==================== PRODUITS ====================
class Product(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(verbose_name="Description")
    Categorie = models.ForeignKey(Categorie, related_name='products', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', blank=True, null=True) 
    image_url = models.URLField(blank=True, null=True)
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock disponible")
    is_new = models.BooleanField(default=False, verbose_name="Nouveau produit")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    date_ajout = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_ajout'] 
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
    
    def __str__(self):
        return self.title
    
    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        elif self.image_url:
            return self.image_url
        return 'https://via.placeholder.com/400x400?text=No+Image'
    
    def get_discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0
    
    def is_in_stock(self):
        return self.stock > 0
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

# ==================== PROFIL UTILISATEUR ====================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    address = models.CharField(max_length=200, blank=True, verbose_name="Adresse")
    ville = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    pays = models.CharField(max_length=100, default="Côte d'Ivoire")
    zipcode = models.CharField(max_length=10, blank=True, verbose_name="Code postal")
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_naissance = models.DateField(null=True, blank=True)
    
    # Préférences
    newsletter = models.BooleanField(default=False)
    notifications_email = models.BooleanField(default=True)
    notifications_sms = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"
    
    def __str__(self):
        return f"Profil de {self.user.username}"
    
    def get_full_address(self):
        parts = [self.address, self.ville, self.pays, self.zipcode]
        return ", ".join([p for p in parts if p])

# ==================== ADRESSES DE LIVRAISON ====================
class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipping_addresses')
    nom_complet = models.CharField(max_length=200, verbose_name="Nom complet")
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    address = models.CharField(max_length=200, verbose_name="Adresse")
    ville = models.CharField(max_length=100, verbose_name="Ville")
    pays = models.CharField(max_length=100, default="Côte d'Ivoire")
    zipcode = models.CharField(max_length=10, blank=True, verbose_name="Code postal")
    
    TYPE_CHOICES = [
        ('domicile', 'Domicile'),
        ('bureau', 'Bureau'),
        ('autre', 'Autre'),
    ]
    address_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='domicile')
    is_default = models.BooleanField(default=False, verbose_name="Adresse par défaut")
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-date_ajout']
        verbose_name = "Adresse de livraison"
        verbose_name_plural = "Adresses de livraison"
    
    def __str__(self):
        return f"{self.nom_complet} - {self.address_type}"
    
    def save(self, *args, **kwargs):
        # Si c'est la première adresse ou marquée par défaut
        if self.is_default:
            # Retirer le statut par défaut des autres adresses
            ShippingAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

# ==================== COMMANDES ====================
class Commande(models.Model):
    # Identifiant unique
    order_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    
    # Articles (JSON pour flexibilité)
    items = models.JSONField(default=list)
    
    # Montants
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=2000)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Informations client
    nom = models.CharField(max_length=150, verbose_name="Nom complet")
    email = models.EmailField()
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    address = models.CharField(max_length=200, verbose_name="Adresse")
    ville = models.CharField(max_length=200, verbose_name="Ville")
    pays = models.CharField(max_length=300, default="Côte d'Ivoire")
    zipcode = models.CharField(max_length=300, blank=True)
    
    # Paiement
    PAYMENT_METHODS = [
        ('wave', 'Wave'),
        ('orange', 'Orange Money'),
        ('cash', 'Paiement à la livraison'),
    ]
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    
    PAYMENT_STATUS = [
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('failed', 'Échoué'),
        ('refunded', 'Remboursé'),
    ]
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default='pending')
    payment_reference = models.CharField(max_length=200, blank=True)
    
    # Statut de livraison
    ORDER_STATUS = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('processing', 'En préparation'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
    ]
    order_status = models.CharField(max_length=50, choices=ORDER_STATUS, default='pending')
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes de commande")
    
    # Dates
    date_commande = models.DateTimeField(auto_now_add=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_commande']
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
    
    def __str__(self):
        return f"{self.order_number} - {self.nom}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Générer un numéro de commande unique
            self.order_number = f"CMD-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    def get_items_count(self):
        return sum(item.get('quantity', 0) for item in self.items)

# ==================== FAVORIS ====================
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-date_added']
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
    
    def __str__(self):
        return f"{self.user.username} - {self.product.title}"

# ==================== AVIS PRODUITS ====================
class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1)])  # 1-5 étoiles
    comment = models.TextField(verbose_name="Commentaire")
    date_added = models.DateTimeField(auto_now_add=True)
    is_verified_purchase = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-date_added']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
    
    def __str__(self):
        return f"{self.user.username} - {self.product.title} ({self.rating}★)"

# ==================== NEWSLETTER ====================
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    date_subscribed = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Abonné Newsletter"
        verbose_name_plural = "Abonnés Newsletter"
    
    def __str__(self):
        return self.email
# ==================== MESSAGES DE CONTACT ====================
class ContactMessage(models.Model):
    nom = models.CharField(max_length=200, verbose_name="Nom complet")
    email = models.EmailField(verbose_name="Email")
    sujet = models.CharField(max_length=200, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    date_envoi = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    is_replied = models.BooleanField(default=False, verbose_name="Répondu")
    
    class Meta:
        ordering = ['-date_envoi']
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
    
    def __str__(self):
        return f"{self.nom} - {self.sujet} ({self.date_envoi.strftime('%d/%m/%Y')})"