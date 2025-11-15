from django import forms
from django.db.models import Case, When, IntegerField
from .models import NKO, Category, NKOVersion


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

        # Style file input for logo separately (Tailwind file: utilities)
        if "logo" in self.fields:
            file_classes = (
                "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 text-gray-800 "
                "file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold "
                "file:bg-[#4495D1] file:text-white hover:file:bg-[#2e7bb8] transition duration-200 shadow-md"
            )
            self.fields["logo"].widget.attrs.update({"class": file_classes})

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

        if "logo" in self.fields:
            file_classes = (
                "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 text-gray-800 "
                "file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold "
                "file:bg-[#4495D1] file:text-white hover:file:bg-[#2e7bb8] transition duration-200 shadow-md"
            )
            self.fields["logo"].widget.attrs.update({"class": file_classes})

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
