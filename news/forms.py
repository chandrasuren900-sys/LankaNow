from django import forms
from .models import ContactMessage
class ContactForm(forms.ModelForm):
    class Meta:
        model=ContactMessage
        fields=['name','email','message']
        widgets={'message':forms.Textarea(attrs={'rows':6})}
class SubscribeForm(forms.Form):
    email=forms.EmailField(max_length=254)
    consent=forms.BooleanField()
