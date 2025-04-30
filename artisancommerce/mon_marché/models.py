from django.db import models
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

class Categorie(models.Model):
    name = models.CharField(max_length=200)
    date_ajout = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_ajout']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=200)
    price = models.FloatField()
    description = models.TextField()
    Categorie = ForeignKey(Categorie, related_name='category', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', blank=True, null=True) 
    image_url = models.URLField(blank=True, null=True)
    date_ajout = models.DateTimeField(auto_now=True)
    is_new = models.BooleanField(default=False)  # Ajouté
    old_price = models.FloatField(null=True, blank=True)  # Ajouté
    
     # Méthode utilitaire pour obtenir l'image (fichier ou URL)
    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        elif self.image_url:
            return self.image_url
        return ''  # URL d'image par défaut si nécessaire



    def is_favorite(self, user):
        if not user.is_authenticated:
            return False
        return Favorite.objects.filter(user=user, product=self).exists()
    class Meta:
        ordering = ['-date_ajout'] 
    
    def __str__(self):
        return self.title

class Commande(models.Model):
    # Remplacer le champ items par une structure JSON
    items = models.JSONField(default=list)  # Stocke les articles sous forme de liste de dictionnaires
    total = models.DecimalField(max_digits=10, decimal_places=2)  # Meilleur type pour les montants
    nom = models.CharField(max_length=150)
    email = models.EmailField()
    address = models.CharField(max_length=200)
    ville = models.CharField(max_length=200)
    pays = models.CharField(max_length=300)
    zipcode = models.CharField(max_length=300)
    date_commande = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Options de paiement
    PAYMENT_METHODS = [
        ('orange', 'Orange Money'),
        ('wave', 'Wave'),
        ('cash', 'Paiement à la livraison'),
    ]
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    
    # Statuts de paiement
    PAYMENT_STATUS = [
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('failed', 'Échoué'),
        ('refunded', 'Remboursé'),
    ]
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default='pending')
    
    class Meta:
        ordering = ['-date_commande']
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
    
    def __str__(self):
        return f"Commande #{self.id} - {self.nom}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    zipcode = models.CharField(max_length=10, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    def __str__(self):
        return f"Profil de {self.user.username}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:  # Nouveau Meta
        unique_together = ('user', 'product')  # Empêche les doublons

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:  # Nouveau Meta
        ordering = ['-date_added']