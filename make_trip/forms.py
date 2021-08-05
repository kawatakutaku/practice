from django import forms
from django.db.models import fields
from django.forms import widgets
from django.forms.widgets import EmailInput, Widget
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Budget, Group, Memo, Transport, Trip, Spot, Other
from django.contrib.auth import get_user_model, authenticate
from django.core.validators import EmailValidator
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst

User = get_user_model()

class SignUp(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 新規登録の際に必要な項目を書き出す    <=  UserCreationFormに含まれているフィールド全てにクラス名を書き出す処理
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.help_text = None

        # フィールドに属性を追加する => labelはMetaで登録しても上手くいかないからこっちでやった方が良いかも
        self.fields['last_name'].widget.attrs['placeholder'] = '例：山田'
        self.fields['first_name'].widget.attrs['placeholder'] = '例：太郎'
        self.fields['username'].widget.attrs['placeholder'] = 'ユーザーネーム'
        self.fields['password1'].widget.attrs['placeholder'] = 'パスワード'
        self.fields['password2'].widget.attrs['placeholder'] = 'パスワード(確認)'
        self.fields['email'].widget.attrs['placeholder'] = 'メールアドレス'
        self.fields['password1'].label = 'パスワード(8文字以上)'
        self.fields['password2'].label = 'パスワード(確認)'
        self.fields['username'].label = 'ユーザーネーム'
        self.fields['email'].label = 'メールアドレス'
        self.fields['last_name'].label = '苗字'
        self.fields['first_name'].label = '名前'

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']

    def clean_email(self):
        email = self.cleaned_data['email']
        # 仮登録までしかしてないメールアドレスを消去する
        User.objects.filter(email=email, is_active=False).delete()
        return email

class GroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Group
        fields = ('title',)
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'グループ名'})
        }

class TripForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Trip
        fields = ('trip_name', 'start', 'end')
        widgets = {
            'trip_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '旅行タイトル', 'name': 'trip_name'}),
            'start': forms.DateInput(attrs={'class': 'form-control bigDate', 'placeholder': '出発日', 'autocomplete': 'off', 'name': 'start'}),
            'end': forms.DateInput(attrs={'class': 'form-control bigDate', 'placeholder': '帰宅日', 'autocomplete': 'off', 'name': 'end'})
        }

class SpotForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Spot
        fields = ('spot_name', 'spot_time', 'spot_cost')
        widgets = {
            'spot_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '観光地', 'name': 'spot_name'}),
            'spot_time': forms.DateTimeInput(attrs={'class': 'form-control smallDate', 'placeholder': '到着時間', 'autocomplete': 'off', 'name': 'spot_time'}),
            'spot_cost': forms.NumberInput(attrs={'class': 'form-control costs', 'placeholder': '滞在料金', 'name': 'spot_cost'})
        }

class OtherForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Other
        fields = ('extra_name', 'extra_cost')
        widgets = {
            'extra_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '追加の費用の項目', 'name': 'extra_menu'}),
            'extra_cost': forms.NumberInput(attrs={'class': 'form-control costs', 'placeholder': '追加の費用', 'name': 'extra_cost'})
        }

class BudgetForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Budget
        fields = ('predict_money',)
        widgets = { 'predict_money': forms.NumberInput(attrs={'class': 'form-control costs', 'placeholder': '予算'}) }

class MemoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['memo'].label = ''

    class Meta:
        model = Memo
        fields = ('memo',)
        widgets = { 'memo': forms.Textarea(attrs={'class': 'form-control'}) }

class TransportForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transport_name'].required = False
        self.fields['transport_fee'].required = False
        self.fields['transport_time'].required = False

    class Meta:
        model = Transport
        fields = ('transport_name', 'transport_time', 'transport_fee')
        widgets = {
            'transport_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '移動手段'}),
            'transport_time': forms.DateTimeInput(attrs={'class': 'form-control smallDate', 'placeholder': '乗る時間', 'autocomplete': 'off'}),
            'transport_fee': forms.NumberInput(attrs={'class': 'form-control costs', 'placeholder': '料金'})
        }

class Login(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['username'].widget.attrs['placeholder'] = 'メールアドレス'
        self.fields['password'].widget.attrs['placeholder'] = 'パスワード'
        self.fields['username'].label = 'メールアドレス'
        self.fields['password'].label = 'パスワード'

class AddGroup(forms.Form):
    input_url = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control'}))


'''
class School(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Test
        fields = ('test_name', 'test_score')
        widgets = {
            'test_name': forms.TextInput(attrs={'class': 'form-control'}),
            'test_score': forms.NumberInput(attrs={'class': 'form-control'})
        }
        label = {
            'test_name': 'テスト名',
            'test_score': '点数'
        }
class Sport(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Sports
        fields = ('sport_name', 'sport_rank')
        widgets = {
            'sport_name': forms.TextInput(attrs={'class': 'form-control'}),
            'sport_rank': forms.NumberInput(attrs={'class': 'form-control'})
        }
        label = {
            'sport_name': 'スポーツ名',
            'sport_rank': 'ランク'
        }
'''