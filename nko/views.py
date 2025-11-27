from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from .models import City, Category, NKO, NKOVersion
from .forms import NKOForm, NKOEditForm, TransferOwnershipForm
from .email_utils import send_new_application_notification

User = get_user_model()


# Create your views here.
def index(request):
    cities = City.objects.all()
    categories = Category.objects.all()
    return render(request, "index.html", {"cities": cities, "categories": categories})


def index_tsx(request):
    """Alternative index page using the TSX-inspired template.

    Prepares a simplified `ngos` list where each item contains a single
    representative category (the first) for rendering in the sidebar cards.
    """
    import json

    # Optimize queries by selecting only needed fields and using select_related
    cities_qs = City.objects.select_related("region").only("id", "name", "region__name")
    categories_qs = Category.objects.only("id", "name", "icon", "color")

    # Prepare cities for JSON
    cities_json = json.dumps(
        [
            {"id": city.id, "name": city.name, "region": city.region.name}
            for city in cities_qs
        ]
    )

    # Select approved, active NKOs with optimized query
    nko_qs = (
        NKO.objects.filter(is_approved=True, is_active=True)
        .select_related("city", "city__region", "owner")
        .prefetch_related("categories")
        .only(
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "description",
            "volunteer_functions",
            "phone",
            "website",
            "vk_link",
            "telegram_link",
            "other_social",
            "city__id",
            "city__name",
            "city__region__id",
            "city__region__name",
            "owner__id",
        )
    )

    # Cache owner check for authenticated user
    user_id = request.user.id if request.user.is_authenticated else None

    ngos = []
    for nko in nko_qs:
        # Use prefetched categories to avoid additional queries
        categories_list = list(nko.categories.all())
        first_cat = categories_list[0] if categories_list else None
        is_owner = user_id and nko.owner_id == user_id
        ngos.append(
            {
                "id": nko.id,
                "name": nko.name,
                "address": nko.address,
                "lat": nko.latitude,
                "lng": nko.longitude,
                "description": nko.description,
                "volunteer_functions": nko.volunteer_functions,
                "phone": nko.phone,
                "website": nko.website,
                "vk_link": nko.vk_link,
                "telegram_link": nko.telegram_link,
                "other_social": nko.other_social,
                "city": {
                    "id": nko.city.id,
                    "name": nko.city.name,
                }
                if nko.city
                else None,
                "is_owner": is_owner,
                "category": {
                    "id": first_cat.id,
                    "name": first_cat.name,
                    "color": first_cat.color,
                    "icon": first_cat.icon,
                }
                if first_cat
                else None,
            }
        )

    user_has_ngo = False
    if request.user.is_authenticated:
        user_has_ngo = NKO.objects.filter(owner=request.user).exists()

    # Make JSON-serializable lists for template and client-side JS
    categories = [
        {"id": c.id, "name": c.name, "icon": c.icon, "color": c.color}
        for c in categories_qs
    ]
    cities = [
        {"id": ct.id, "name": ct.name, "region": ct.region.name} for ct in cities_qs
    ]

    context = {
        "cities": cities,
        "categories": categories,
        "ngos": ngos,
        "cities_json": cities_json,
        "is_authenticated": request.user.is_authenticated,
        "user_has_ngo": user_has_ngo,
    }

    return render(request, "index_tsx.html", context)


def nko_list_api(request):
    nko_list = NKO.objects.filter(is_approved=True, is_active=True).prefetch_related(
        "categories"
    )
    data = []
    for nko in nko_list:
        categories_data = []
        for category in nko.categories.all():
            categories_data.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": slugify(category.name, allow_unicode=True),
                    "icon": category.icon,
                    "color": category.color,
                }
            )

        data.append(
            {
                "id": nko.id,
                "name": nko.name,
                "categories": categories_data,
                "city": nko.city.name,
                "city_id": nko.city.id,
                "city_slug": slugify(nko.city.name, allow_unicode=True),
                "region": nko.region.name,
                "latitude": nko.latitude,
                "longitude": nko.longitude,
                "phone": nko.phone,
                "address": nko.address,
                "website": nko.website,
                "description": nko.description,
                "has_pending_changes": nko.has_pending_changes,
            }
        )

    return JsonResponse(data, safe=False)


def categories_api(request):
    categories = Category.objects.all()
    cats = []
    for category in categories:
        cats.append(
            {
                "id": category.id,
                "name": category.name,
                "slug": slugify(category.name, allow_unicode=True),
                "icon": category.icon,
                "color": category.color,
            }
        )
    return JsonResponse(cats, safe=False)


@login_required
def add_nko(request):
    from django.contrib import messages
    from .models import Region

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
        messages.warning(
            request,
            f"У вас есть ожидающая заявка на передачу прав НКО '{pending_transfer.nko.name}'. "
            f"Дождитесь её рассмотрения перед созданием нового НКО.",
        )
        return redirect("index")

    if request.method == "POST":
        # Debug: log phone field value
        phone_value = request.POST.get("phone", "")
        print(
            f"[DEBUG add_nko] phone from POST: '{phone_value}' (type: {type(phone_value)}, len: {len(phone_value)})"
        )

        form = NKOForm(request.POST, request.FILES)

        # Handle city_name field
        city_name = request.POST.get("city_name", "").strip()
        city_id = request.POST.get("city")

        # Debug logging
        print(f"[DEBUG add_nko] city_name from POST: '{city_name}'")
        print(f"[DEBUG add_nko] city_id from POST: '{city_id}'")

        if city_id:
            # User selected existing city from dropdown
            try:
                city = City.objects.get(id=city_id)
            except City.DoesNotExist:
                messages.error(request, "Выбранный город не найден.")
                return redirect("index")
        elif city_name:
            # User entered custom city name - will be created after moderation
            # For now, use a default/placeholder city or handle in moderation
            # We'll store city_name in NKOVersion and create city on approval
            city = None  # Will be handled in moderation
        else:
            messages.error(request, "Пожалуйста, укажите город.")
            return redirect("index")

        if form.is_valid():
            nko = form.save(commit=False)
            nko.owner = request.user
            nko.is_approved = False

            # If no city selected, use first available as placeholder
            if not city:
                city = City.objects.first()
                if not city:
                    messages.error(request, "Ошибка: нет доступных городов в базе.")
                    return redirect("index")

            nko.city = city
            nko.save()
            form.save_m2m()

            # Create initial version with city_name if custom
            if city_name and not city_id:
                print(
                    f"[DEBUG add_nko] Creating NKOVersion with city_name: '{city_name}'"
                )
                version = NKOVersion.objects.create(
                    nko=nko,
                    name=nko.name,
                    description=nko.description,
                    volunteer_functions=nko.volunteer_functions,
                    phone=nko.phone,
                    address=nko.address,
                    latitude=nko.latitude,
                    longitude=nko.longitude,
                    website=nko.website,
                    vk_link=nko.vk_link,
                    telegram_link=nko.telegram_link,
                    other_social=nko.other_social,
                    city_name=city_name,
                    created_by=request.user,
                    is_approved=False,
                )
                version.categories.set(nko.categories.all())
                print(
                    f"[DEBUG add_nko] Created NKOVersion id={version.id}, city_name='{version.city_name}'"
                )

                # Отправляем уведомление администраторам о новой заявке
                send_new_application_notification(version)
            else:
                print(
                    f"[DEBUG add_nko] Skipping NKOVersion creation. city_name='{city_name}', city_id='{city_id}'"
                )

            messages.success(
                request,
                f"Заявка на создание НКО '{nko.name}' отправлена на модерацию. "
                f"После одобрения администратором НКО появится на карте.",
            )

            return redirect("index")
        else:
            # Form validation failed
            error_messages = []
            for field, errors in form.errors.items():
                field_label = (
                    form.fields.get(field).label if field in form.fields else field
                )
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")

            if error_messages:
                messages.error(request, "Ошибки в форме: " + "; ".join(error_messages))
            else:
                messages.error(
                    request, "Пожалуйста, проверьте правильность заполнения формы."
                )

            return redirect("index")
    else:
        form = NKOForm()

    return render(request, "nko/add_nko.html", {"form": form})


@login_required
def edit_nko(request, pk):
    from django.contrib import messages

    nko = get_object_or_404(NKO, pk=pk, owner=request.user)

    pending_version = nko.get_pending_version()
    if pending_version:
        return redirect("index")

    if request.method == "POST":
        form = NKOEditForm(request.POST, request.FILES)

        # Handle city_name field (same logic as add_nko)
        city_name = request.POST.get("city_name", "").strip()
        city_id = request.POST.get("city")

        # Debug logging
        print(f"[DEBUG edit_nko] city_name from POST: '{city_name}'")
        print(f"[DEBUG edit_nko] city_id from POST: '{city_id}'")
        print(f"[DEBUG edit_nko] nko_id: {pk}")

        if form.is_valid():
            version = form.save(commit=False)
            version.nko = nko
            version.created_by = request.user
            if version.latitude is None:
                version.latitude = nko.latitude
            if version.longitude is None:
                version.longitude = nko.longitude

            # Store city_name if custom city entered
            if city_name and not city_id:
                print(f"[DEBUG edit_nko] Setting city_name on version: '{city_name}'")
                version.city_name = city_name
            else:
                print(f"[DEBUG edit_nko] No custom city. city_id='{city_id}'")

            version.save()
            form.save_m2m()

            nko.has_pending_changes = True
            nko.save()

            print(
                f"[DEBUG edit_nko] Saved NKOVersion id={version.id}, city_name='{version.city_name}'"
            )

            # Отправляем уведомление администраторам о новой заявке
            send_new_application_notification(version)

            messages.success(
                request,
                f"Изменения в НКО '{nko.name}' отправлены на модерацию. "
                f"После одобрения администратором изменения будут применены.",
            )

            return redirect("index")
        else:
            # Form validation failed
            error_messages = []
            for field, errors in form.errors.items():
                field_label = (
                    form.fields.get(field).label if field in form.fields else field
                )
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")

            if error_messages:
                messages.error(request, "Ошибки в форме: " + "; ".join(error_messages))
            else:
                messages.error(
                    request, "Пожалуйста, проверьте правильность заполнения формы."
                )

            return redirect("index")
    else:
        initial_data = {
            "name": nko.name,
            "description": nko.description,
            "volunteer_functions": nko.volunteer_functions,
            "phone": nko.phone,
            "address": nko.address,
            "latitude": nko.latitude,
            "longitude": nko.longitude,
            "website": nko.website,
            "vk_link": nko.vk_link,
            "telegram_link": nko.telegram_link,
            "other_social": nko.other_social,
        }
        form = NKOEditForm(initial=initial_data)
        form.fields["categories"].initial = nko.categories.all()
        # Ensure hidden latitude/longitude inputs show current values
        if "latitude" in form.fields:
            form.fields["latitude"].initial = nko.latitude
        if "longitude" in form.fields:
            form.fields["longitude"].initial = nko.longitude

    return render(request, "nko/edit_nko.html", {"form": form, "nko": nko})


@login_required
def transfer_ownership(request, pk):
    from django.contrib import messages

    nko = get_object_or_404(NKO, pk=pk, owner=request.user)

    if nko.get_pending_version() or nko.has_pending_changes:
        return redirect("index")

    if request.method == "POST":
        form = TransferOwnershipForm(request.POST)
        if form.is_valid():
            new_owner = form.cleaned_data["new_owner_email"]

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

            # Отправляем уведомление администраторам о заявке на передачу прав
            send_new_application_notification(version)

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
    # If fragment requested (for modal), render the compact fragment matching React layout
    if request.GET.get("fragment") == "1":
        return render(request, "partials/my_applications_fragment.html", context)

    return render(request, "nko/my_requests.html", context)


@login_required
def my_requests_tsx(request):
    """Render the TSX-styled My Applications page (full-page view)."""
    user_nko = NKO.objects.filter(owner=request.user).first()

    approved_versions = []
    pending_versions = []
    rejected_versions = []

    has_pending_transfer = False
    if user_nko:
        approved_versions = NKOVersion.objects.filter(
            nko=user_nko, is_approved=True
        ).order_by("-created_at")

        pending_versions = NKOVersion.objects.filter(
            nko=user_nko, is_approved=False, is_rejected=False
        ).order_by("-created_at")

        rejected_versions = NKOVersion.objects.filter(
            nko=user_nko, is_rejected=True
        ).order_by("-created_at")

        # Check if there's a pending ownership transfer
        has_pending_transfer = pending_versions.filter(new_owner__isnull=False).exists()

    context = {
        "user_nko": user_nko,
        "approved_versions": approved_versions,
        "pending_versions": pending_versions,
        "rejected_versions": rejected_versions,
        "has_pending_transfer": has_pending_transfer,
    }

    return render(request, "nko/my_requests_tsx.html", context)


@login_required
def transfer_ownership_tsx(request):
    """Handle ownership transfer from TSX page (automatically finds user's NKO)."""
    nko = NKO.objects.filter(owner=request.user).first()

    if not nko:
        messages.error(request, "У вас нет НКО для передачи прав.")
        return redirect("my_requests_tsx")

    if nko.get_pending_version() or nko.has_pending_changes:
        messages.warning(
            request, "Невозможно передать права: есть ожидающие изменения на модерации."
        )
        return redirect("my_requests_tsx")

    if request.method == "POST":
        try:
            new_owner_email = request.POST.get("new_owner_email")
            transfer_reason = request.POST.get("transfer_reason")

            if not new_owner_email or not transfer_reason:
                messages.error(request, "Необходимо заполнить все поля.")
                return redirect("my_requests_tsx")

            # Find user by email
            try:
                new_owner = User.objects.get(email=new_owner_email)
            except User.DoesNotExist:
                messages.error(
                    request, f"Пользователь с email {new_owner_email} не найден."
                )
                return redirect("my_requests_tsx")

            # Check if new owner already has an NKO
            existing_nko = NKO.objects.filter(owner=new_owner).first()
            if existing_nko:
                messages.error(
                    request,
                    f"Невозможно передать права: пользователь {new_owner.get_full_name() or new_owner.username} "
                    f"уже владеет НКО '{existing_nko.name}'. Один пользователь может владеть только одним НКО.",
                )
                return redirect("my_requests_tsx")

            # Check for pending transfer requests to this user
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
                return redirect("my_requests_tsx")

            # Check if new owner has pending NKO application
            pending_nko = NKO.objects.filter(owner=new_owner, is_approved=False).first()
            if pending_nko:
                messages.warning(
                    request,
                    f"У пользователя {new_owner.get_full_name() or new_owner.username} есть ожидающая заявка "
                    f"на создание НКО '{pending_nko.name}'. "
                    f"Дождитесь её рассмотрения перед передачей прав.",
                )
                return redirect("my_requests_tsx")

            # Create transfer version
            version = NKOVersion.objects.create(
                nko=nko,
                created_by=request.user,
                new_owner=new_owner,
                change_description=transfer_reason,
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

        except Exception as e:
            messages.error(request, f"Произошла ошибка при передаче прав: {str(e)}")

    return redirect("my_requests_tsx")
