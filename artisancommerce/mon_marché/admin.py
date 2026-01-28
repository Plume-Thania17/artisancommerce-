from django.contrib import admin
from.models import Categorie,Product, Commande,UserProfile, User
from django.contrib.auth.admin import UserAdmin
# Register your models here.
# Register your models here.
admin.site.site_header = "E-commerce"
admin.site.site_title = "Mynia"
admin.site.index_title = "Manageur"

class AdminCategorie(admin.ModelAdmin):
      list_display = ('name', 'date_ajout')
class AdminProduct(admin.ModelAdmin):     
      list_display = ('title', 'price', 'Categorie', 'date_ajout')
      search_fields = ('title',) 
      list_editable = ('price',)
class AdminCommande(admin.ModelAdmin):
  list_display = ('id', 'user', 'nom', 'email', 'items', 'total', 'ville', 'pays', 'date_commande')
  search_fields = ('nom', 'email', 'ville')  

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 1

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    
admin.site.register(Product,AdminProduct)
admin.site.register(Categorie,AdminCategorie)
admin.site.register(Commande, AdminCommande)
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'sujet', 'date_envoi', 'is_read', 'is_replied']
    list_filter = ['is_read', 'is_replied', 'date_envoi']
    search_fields = ['nom', 'email', 'sujet', 'message']
    readonly_fields = ['date_envoi']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Marquer comme lu"
    
    actions = [mark_as_read]