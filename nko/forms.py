from django import forms
from .models import NKO, Category, NKOVersion


class NKOForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Направления деятельности",
    )

    class Meta:
        model = NKO
        fields = [
            "name",
            "categories",
            "city",
            "description",
            "volunteer_functions",
            "phone",
            "address",
            "logo",
            "website",
            "vk_link",
            "telegram_link",
            "other_social",
        ]
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Чем занимается ваша организация?"}
            ),
            "volunteer_functions": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Чем могут помочь волонтеры?"}
            ),
            "address": forms.Textarea(attrs={"rows": 2}),
        }


class NKOEditForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Направления деятельности",
    )

    change_description = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 2, "placeholder": "Опишите, что вы изменили"}
        ),
        required=False,
        label="Описание изменений",
    )

    class Meta:
        model = NKOVersion
        fields = [
            "name",
            "categories",
            "description",
            "volunteer_functions",
            "phone",
            "address",
            "logo",
            "website",
            "vk_link",
            "telegram_link",
            "other_social",
            "change_description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "volunteer_functions": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }


class TransferOwnershipForm(forms.ModelForm):
    new_owner_email = forms.EmailField(
        label="Email нового владельца",
        help_text="Введите email пользователя, которому хотите передать управление НКО",
    )

    change_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=True,
        label="Причина передачи",
        help_text="Объясните, почему вы передаете управление этой НКО",
    )

    class Meta:
        model = NKOVersion
        fields = ["new_owner_email", "change_description"]

    def clean_new_owner_email(self):
        email = self.cleaned_data["new_owner_email"]
        from django.contrib.auth.models import User

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Пользователь с таким email не найден.")
        return user
