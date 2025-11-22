from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.text import slugify
from .models import City, Category, NKO, NKOVersion
from .forms import NKOForm, NKOEditForm, TransferOwnershipForm


# Create your views here.
def index(request):
    cities = City.objects.all()
    categories = Category.objects.all()
    return render(request, "index.html", {"cities": cities, "categories": categories})


def nko_list_api(request):
    nko_list = NKO.objects.filter(is_approved=True, is_active=True).prefetch_related(
        "categories"
    )
    data = []
    for nko in nko_list:
        category_list = [category.name for category in nko.categories.all()]
        category_ids = [category.id for category in nko.categories.all()]

        def map_category_to_key(name):
            s = (name or "").lower()
            if "живот" in s:
                return "animals"
            if "эколог" in s or "устойчив" in s:
                return "ecology"
            if "спорт" in s or "здоровье" in s:
                return "sport"
            if "социал" in s or "помощ" in s:
                return "social"
            if "территор" in s or "местн" in s:
                return "territory"
            return "other"

        category_keys = [map_category_to_key(c) for c in category_list]
        category_slugs = [slugify(c) for c in category_list]
        primary_category = category_keys[0] if category_keys else "other"
        data.append(
            {
                "id": nko.id,
                "name": nko.name,
                "categories": category_list,
                "category_ids": category_ids,
                "category_slugs": category_slugs,
                "category_keys": category_keys,
                "primary_category": primary_category,
                "city": nko.city.name,
                "city_id": nko.city.id,
                "city_slug": slugify(nko.city.name),
                "region": nko.region.name,
                "latitude": nko.latitude,
                "longitude": nko.longitude,
                "phone": nko.phone,
                "address": nko.address,
                "website": nko.website,
                "description": nko.description,
                "logo_url": nko.logo.url if nko.logo else None,
                "has_pending_changes": nko.has_pending_changes,
            }
        )

    return JsonResponse(data, safe=False)


def categories_api(request):
    cats = Category.objects.all().values("id", "name")
    return JsonResponse(list(cats), safe=False)


@login_required
def add_nko(request):
    existing = NKO.objects.filter(owner=request.user).first()
    if existing:
        if existing.has_pending_changes or not existing.is_approved:
            return redirect("index")

        return redirect("edit_nko", pk=existing.pk)

    # Проверяем, нет ли ожидающих заявок на передачу прав этому пользователю
    pending_transfer = NKOVersion.objects.filter(
        new_owner=request.user, is_approved=False, is_rejected=False
    ).first()

    if pending_transfer:
        from django.contrib import messages

        messages.warning(
            request,
            f"У вас есть ожидающая заявка на передачу прав НКО '{pending_transfer.nko.name}'. "
            f"Дождитесь её рассмотрения перед созданием нового НКО.",
        )
        return redirect("index")

    if request.method == "POST":
        form = NKOForm(request.POST, request.FILES)
        if form.is_valid():
            from django.contrib import messages

            nko = form.save(commit=False)
            nko.owner = request.user
            nko.is_approved = False
            nko.save()
            form.save_m2m()

            messages.success(
                request,
                f"Заявка на создание НКО '{nko.name}' отправлена на модерацию. "
                f"После одобрения администратором НКО появится на карте.",
            )

            return redirect("index")
    else:
        form = NKOForm()

    return render(request, "nko/add_nko.html", {"form": form})


@login_required
def edit_nko(request, pk):
    nko = get_object_or_404(NKO, pk=pk, owner=request.user)

    pending_version = nko.get_pending_version()
    if pending_version:
        return redirect("index")

    if request.method == "POST":
        form = NKOEditForm(request.POST, request.FILES)
        if form.is_valid():
            from django.contrib import messages

            version = form.save(commit=False)
            version.nko = nko
            version.created_by = request.user
            if version.latitude is None:
                version.latitude = nko.latitude
            if version.longitude is None:
                version.longitude = nko.longitude
            version.save()
            form.save_m2m()

            nko.has_pending_changes = True
            nko.save()

            messages.success(
                request,
                f"Изменения в НКО '{nko.name}' отправлены на модерацию. "
                f"После одобрения администратором изменения будут применены.",
            )

            return redirect("index")
    else:
        initial_data = {
            "name": nko.name,
            "description": nko.description,
            "volunteer_functions": nko.volunteer_functions,
            "phone": nko.phone,
            "address": nko.address,
            "website": nko.website,
            "vk_link": nko.vk_link,
            "telegram_link": nko.telegram_link,
            "other_social": nko.other_social,
        }
        form = NKOEditForm(initial=initial_data)
        form.fields["categories"].initial = nko.categories.all()

    return render(request, "nko/edit_nko.html", {"form": form, "nko": nko})


@login_required
def transfer_ownership(request, pk):
    nko = get_object_or_404(NKO, pk=pk, owner=request.user)

    if nko.get_pending_version() or nko.has_pending_changes:
        return redirect("index")

    if request.method == "POST":
        form = TransferOwnershipForm(request.POST)
        if form.is_valid():
            new_owner = form.cleaned_data["new_owner_email"]
            from django.contrib import messages

            # Проверяем, нет ли у нового владельца уже НКО
            existing_nko = NKO.objects.filter(owner=new_owner).first()
            if existing_nko:
                messages.error(
                    request,
                    f"Невозможно передать права: пользователь {new_owner.get_full_name() or new_owner.username} "
                    f"уже владеет НКО '{existing_nko.name}'. Один пользователь может владеть только одним НКО.",
                )
                return render(
                    request, "nko/transfer_ownership.html", {"form": form, "nko": nko}
                )

            # Проверяем, нет ли ожидающих заявок на передачу прав этому пользователю
            pending_transfer = NKOVersion.objects.filter(
                new_owner=new_owner, is_approved=False, is_rejected=False
            ).first()

            if pending_transfer:
                messages.warning(
                    request,
                    f"У пользователя {new_owner.get_full_name() or new_owner.username} уже есть ожидающая заявка "
                    f"на передачу прав НКО '{pending_transfer.nko.name}'. "
                    f"Дождитесь её рассмотрения перед отправкой новой заявки.",
                )
                return render(
                    request, "nko/transfer_ownership.html", {"form": form, "nko": nko}
                )

            # Проверяем, нет ли неодобренного НКО у этого пользователя
            pending_nko = NKO.objects.filter(owner=new_owner, is_approved=False).first()
            if pending_nko:
                messages.warning(
                    request,
                    f"У пользователя {new_owner.get_full_name() or new_owner.username} есть ожидающая заявка "
                    f"на создание НКО '{pending_nko.name}'. "
                    f"Дождитесь её рассмотрения перед передачей прав.",
                )
                return render(
                    request, "nko/transfer_ownership.html", {"form": form, "nko": nko}
                )

            version = NKOVersion.objects.create(
                nko=nko,
                created_by=request.user,
                new_owner=new_owner,
                change_description=form.cleaned_data["change_description"],
                name=nko.name,
                description=nko.description,
                volunteer_functions=nko.volunteer_functions,
                latitude=nko.latitude,
                longitude=nko.longitude,
                phone=nko.phone,
                address=nko.address,
                website=nko.website,
                vk_link=nko.vk_link,
                telegram_link=nko.telegram_link,
                other_social=nko.other_social,
            )
            version.categories.set(nko.categories.all())

            nko.has_pending_changes = True
            nko.save()

            messages.success(
                request,
                f"Заявка на передачу прав НКО '{nko.name}' пользователю "
                f"{new_owner.get_full_name() or new_owner.username} отправлена на модерацию.",
            )

            return redirect("index")
    else:
        form = TransferOwnershipForm()

    return render(request, "nko/transfer_ownership.html", {"form": form, "nko": nko})


@login_required
def my_requests(request):
    """Просмотр заявок пользователя (ожидающих и отклоненных)"""
    user_nko = NKO.objects.filter(owner=request.user).first()

    pending_versions = []
    rejected_versions = []

    if user_nko:
        pending_versions = NKOVersion.objects.filter(
            nko=user_nko, is_approved=False, is_rejected=False
        ).order_by("-created_at")

        rejected_versions = NKOVersion.objects.filter(
            nko=user_nko, is_rejected=True
        ).order_by("-created_at")

    context = {
        "user_nko": user_nko,
        "pending_versions": pending_versions,
        "rejected_versions": rejected_versions,
    }

    return render(request, "nko/my_requests.html", context)
