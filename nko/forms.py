from django import forms
from django.db.models import Case, When, IntegerField
from .models import NKO, Category, NKOVersion
import re


def validate_russian_phone(phone):
    """
    Валидация российского номера телефона.
    Принимаемые форматы:
    - +7 (XXX) XXX-XX-XX
    - +7XXXXXXXXXX
    - 8 (XXX) XXX-XX-XX
    - 8XXXXXXXXXX
    - 7XXXXXXXXXX
    """
    print(
        f"[DEBUG validate_russian_phone] called with phone: '{phone}' (type: {type(phone)}, len: {len(phone) if phone else 0})"
    )
    # Handle empty, None, or whitespace-only strings
    if not phone or not phone.strip():
        print(f"[DEBUG validate_russian_phone] phone is empty, returning empty string")
        return ""

    # Удаляем все нецифровые символы кроме +
    cleaned = re.sub(r"[^\d+]", "", phone)
    print(f"[DEBUG validate_russian_phone] cleaned: '{cleaned}'")

    # If cleaned value is just "+7" or "7" or empty, treat as empty phone
    if cleaned in ["", "+7", "7", "+", "8"]:
        print(
            f"[DEBUG validate_russian_phone] cleaned value is just prefix/empty, returning empty string"
        )
        return ""

    # Проверяем различные форматы
    patterns = [
        r"^\+7\d{10}$",  # +7XXXXXXXXXX
        r"^8\d{10}$",  # 8XXXXXXXXXX
        r"^7\d{10}$",  # 7XXXXXXXXXX
    ]

    for pattern in patterns:
        if re.match(pattern, cleaned):
            # Нормализуем к формату +7XXXXXXXXXX
            if cleaned.startswith("8"):
                cleaned = "+7" + cleaned[1:]
            elif cleaned.startswith("7"):
                cleaned = "+" + cleaned
            return cleaned

    raise forms.ValidationError(
        "Некорректный формат телефона. "
        "Используйте российский номер: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX"
    )


class StyledCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = "nko/widgets/checkbox_select.html"
    option_template_name = "nko/widgets/checkbox_option.html"


class NKOForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=StyledCheckboxSelectMultiple(attrs={"class": "grid gap-2"}),
        required=True,
        label="Направления деятельности",
    )

    city_name = forms.CharField(
        required=False, widget=forms.HiddenInput(), label="Название города"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make city field optional since we handle it via city_name
        if "city" in self.fields:
            self.fields["city"].required = False

        common_classes = (
            "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 "
            "text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 "
            "focus:ring-[#4495D1] transition duration-200 shadow-md text-base "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
        )

        for name in (
            "name",
            "city",
            "website",
            "vk_link",
            "telegram_link",
            "other_social",
            "phone",
        ):
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": common_classes})

        for textarea in ("description", "volunteer_functions", "address"):
            if textarea in self.fields:
                attrs = self.fields[textarea].widget.attrs
                attrs.update({"class": common_classes})

        if "categories" in self.fields:
            qs = Category.objects.annotate(
                is_other=Case(
                    When(name__iexact="Другое", then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            ).order_by("is_other", "name")
            self.fields["categories"].queryset = qs
            self.fields["categories"].widget.attrs.update({"class": "grid gap-2"})

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        print(
            f"[DEBUG NKOForm.clean_phone] phone value: '{phone}' (type: {type(phone)}, len: {len(phone)})"
        )
        if phone:
            result = validate_russian_phone(phone)
            print(f"[DEBUG NKOForm.clean_phone] validated result: '{result}'")
            return result
        print(f"[DEBUG NKOForm.clean_phone] returning empty string")
        return ""

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
            "latitude",
            "longitude",
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
            "latitude": forms.HiddenInput(attrs={"id": "id_lat"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_lon"}),
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "+7 (XXX) XXX-XX-XX",
                    "class": "phone-input",
                    "autocomplete": "tel",
                }
            ),
        }


class NKOEditForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=StyledCheckboxSelectMultiple(attrs={"class": "grid gap-2"}),
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
            "latitude",
            "longitude",
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
            "latitude": forms.HiddenInput(attrs={"id": "id_lat"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_lon"}),
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "+7 (XXX) XXX-XX-XX",
                    "class": "phone-input",
                    "autocomplete": "tel",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = (
            "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 "
            "text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 "
            "focus:ring-[#4495D1] transition duration-200 shadow-md text-base "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
        )

        for name in (
            "name",
            "website",
            "vk_link",
            "telegram_link",
            "other_social",
            "phone",
        ):
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": common_classes})

        for textarea in (
            "description",
            "volunteer_functions",
            "address",
            "change_description",
        ):
            if textarea in self.fields:
                self.fields[textarea].widget.attrs.update({"class": common_classes})

        if "categories" in self.fields:
            qs = Category.objects.annotate(
                is_other=Case(
                    When(name__iexact="Другое", then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            ).order_by("is_other", "name")
            self.fields["categories"].queryset = qs
            self.fields["categories"].widget.attrs.update({"class": "grid gap-2"})

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            return validate_russian_phone(phone)
        return ""


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = (
            "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 "
            "text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 "
            "focus:ring-[#4495D1] transition duration-200 shadow-md text-base "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
        )

        if "new_owner_email" in self.fields:
            self.fields["new_owner_email"].widget.attrs.update(
                {"class": common_classes}
            )

        if "change_description" in self.fields:
            self.fields["change_description"].widget.attrs.update(
                {"class": common_classes}
            )
