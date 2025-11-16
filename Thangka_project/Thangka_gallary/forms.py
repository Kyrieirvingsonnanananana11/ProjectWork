from django import forms
from django.contrib.auth.models import User
from .models import Artwork, Artist, ContactMessage

class RegisterForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    full_name = forms.CharField(required=False, max_length=140)
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean(self):
        cleaned = super().clean()
        # if user provided only one password field, copy it to the other to avoid validation blocking
        pw = cleaned.get('password1')
        if pw and not cleaned.get('password2'):
            cleaned['password2'] = pw
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data.get('password1', ''))
        if commit:
            user.save()
        return user

class ArtistForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ('name', 'bio', 'avatar', 'website', 'twitter', 'instagram')

class ArtworkForm(forms.ModelForm):
    class Meta:
        model = Artwork
        fields = ('title', 'description', 'category', 'tags', 'materials', 'year_created', 'price', 'is_featured', 'is_published')
        # DO NOT add a FileField here for multiple images!

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ('name', 'email', 'subject', 'message')
