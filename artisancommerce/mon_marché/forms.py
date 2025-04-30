from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User  # Import manquant
from .models import UserProfile
from django.core.exceptions import ValidationError

class RegisterForm(UserCreationForm):
    phone = forms.CharField(max_length=20, required=True)
    profile_pic = forms.ImageField(required=False)  # Uniformisez ce nom
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'last_name']

    def save(self, commit=True):
        user = super().save(commit=commit)  # Modification cruciale
        UserProfile.objects.create(
            user=user,
            phone=self.cleaned_data['phone'],
            profile_pic=self.cleaned_data.get('profile_pic', None)
        )
        return user
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Cet email est déjà utilisé.")
        return email
class LoginForm(forms.Form):
    username = forms.CharField(label='Nom d\'utilisateur')
    password = forms.CharField(widget=forms.PasswordInput)