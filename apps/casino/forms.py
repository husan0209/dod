from django import forms
from .models import UserSeed


class ChangeClientSeedForm(forms.ModelForm):
    class Meta:
        model = UserSeed
        fields = ['client_seed']
        widgets = {
            'client_seed': forms.TextInput(attrs={'placeholder': 'Ваш новый client seed'}),
        }


class VerifyGameForm(forms.Form):
    server_seed = forms.CharField(max_length=64, label="Server Seed")
    client_seed = forms.CharField(max_length=64, label="Client Seed")
    nonce = forms.IntegerField(label="Nonce")
    game_type = forms.ChoiceField(choices=[
        ('crash', 'Crash'),
        ('dice', 'Dice'),
        ('roulette', 'Roulette'),
        ('slots', 'Slots'),
        ('mines', 'Mines'),
        ('plinko', 'Plinko'),
    ], label="Тип игры")
    game_data = forms.JSONField(label="Данные игры")
