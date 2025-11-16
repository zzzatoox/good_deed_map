import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils import timezone


class Command(BaseCommand):
    help = "Load initial data from CSV files in `initial_data/` into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            dest="dir",
            default=str(Path(settings.BASE_DIR) / "initial_data"),
            help="Directory containing CSV files (default: <BASE_DIR>/initial_data)",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["dir"])
        if not data_dir.exists():
            self.stderr.write(f"Directory not found: {data_dir}")
            return

        from nko.models import Region, City, Category, NKO
        from users.models import Profile
        from django.contrib.auth import get_user_model

        User = get_user_model()

        def read_csv(name):
            path = data_dir / name
            if not path.exists():
                self.stdout.write(f"Skipping missing file: {path}")
                return []
            with path.open("r", encoding="utf-8") as fh:
                return list(csv.DictReader(fh))

        # Users (must be loaded before NKOs)
        users_csv = read_csv("user.csv")
        for row in users_csv:
            try:
                uid = int(row.get("id") or 0)
            except Exception:
                uid = None
            username = row.get("username") or ""
            password = row.get("password") or ""
            first_name = row.get("first_name") or ""
            last_name = row.get("last_name") or ""
            email = row.get("email") or ""
            try:
                is_superuser = bool(int(row.get("is_superuser") or 0))
            except Exception:
                is_superuser = False
            try:
                is_staff = bool(int(row.get("is_staff") or 0))
            except Exception:
                is_staff = False
            try:
                is_active = bool(int(row.get("is_active") or 1))
            except Exception:
                is_active = True

            last_login = None
            if row.get("last_login") and row.get("last_login") != "NULL":
                last_login = parse_datetime(row.get("last_login"))
            date_joined = None
            if row.get("date_joined") and row.get("date_joined") != "NULL":
                date_joined = parse_datetime(row.get("date_joined"))

            if uid:
                defaults = {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "is_superuser": is_superuser,
                    "is_staff": is_staff,
                    "is_active": is_active,
                }
                user_obj, created = User.objects.update_or_create(
                    id=uid, defaults=defaults
                )
                # set hashed password directly (CSV contains hashed passwords)
                if password:
                    user_obj.password = password
                    user_obj.save(update_fields=["password"])
                # set optional datetimes
                    if last_login:
                        # make timezone-aware if required
                        if timezone.is_naive(last_login) and settings.USE_TZ:
                            last_login = timezone.make_aware(last_login, timezone.get_current_timezone())
                        User.objects.filter(pk=user_obj.pk).update(last_login=last_login)
                    if date_joined:
                        if timezone.is_naive(date_joined) and settings.USE_TZ:
                            date_joined = timezone.make_aware(date_joined, timezone.get_current_timezone())
                        User.objects.filter(pk=user_obj.pk).update(date_joined=date_joined)

        # Regions
        regions = read_csv("region.csv")
        for row in regions:
            try:
                rid = int(row.get("id") or 0)
            except ValueError:
                rid = None
            name = row.get("name")
            if not name:
                continue
            if rid:
                Region.objects.update_or_create(id=rid, defaults={"name": name})
            else:
                Region.objects.get_or_create(name=name)

        # Cities
        cities = read_csv("cities.csv")
        for row in cities:
            try:
                cid = int(row.get("id") or 0)
            except ValueError:
                cid = None
            name = row.get("name")
            region_id = row.get("region_id")
            if not name or not region_id:
                continue
            try:
                region = Region.objects.get(id=int(region_id))
            except Region.DoesNotExist:
                self.stderr.write(f"Region id {region_id} not found for city {name}")
                continue
            defaults = {"name": name, "region": region}
            if cid:
                City.objects.update_or_create(id=cid, defaults=defaults)
            else:
                City.objects.get_or_create(name=name, region=region)

        # Categories
        categories = read_csv("category.csv")
        for row in categories:
            try:
                catid = int(row.get("id") or 0)
            except ValueError:
                catid = None
            name = row.get("name")
            description = row.get("description") or ""
            icon = row.get("icon") or ""
            if not name:
                continue
            defaults = {"name": name, "description": description, "icon": icon}
            if catid:
                Category.objects.update_or_create(id=catid, defaults=defaults)
            else:
                Category.objects.get_or_create(name=name, defaults=defaults)

        # NKOs
        nkos = read_csv("nko.csv")
        for row in nkos:
            try:
                nkid = int(row.get("id") or 0)
            except ValueError:
                nkid = None

            name = row.get("name")
            if not name:
                continue

            description = row.get("description") or ""
            volunteer_functions = row.get("volunteer_functions") or ""
            phone = row.get("phone") or ""
            address = row.get("address") or ""

            def parse_float(val):
                if not val or val.strip().upper() == "NULL":
                    return None
                try:
                    return float(val)
                except Exception:
                    return None

            latitude = parse_float(row.get("latitude"))
            longitude = parse_float(row.get("longitude"))

            logo = row.get("logo")
            if logo and logo.strip().upper() == "NULL":
                logo = None

            website = row.get("website") or ""
            vk_link = row.get("vk_link") or ""
            telegram_link = row.get("telegram_link") or ""
            other_social = row.get("other_social") or ""

            created_at = row.get("created_at")
            updated_at = row.get("updated_at")
            try:
                is_approved = bool(int(row.get("is_approved")))
            except Exception:
                is_approved = False
            try:
                is_active = bool(int(row.get("is_active")))
            except Exception:
                is_active = True

            city_id = row.get("city_id")
            owner_id = row.get("owner_id")

            city = None
            if city_id:
                try:
                    city = City.objects.get(id=int(city_id))
                except City.DoesNotExist:
                    self.stderr.write(f"City id {city_id} not found for NKO {name}")

            owner = None
            if owner_id:
                try:
                    owner = User.objects.get(id=int(owner_id))
                except User.DoesNotExist:
                    self.stderr.write(
                        f"User id {owner_id} not found as owner for NKO {name}"
                    )

            # If required foreign keys are missing, skip this NKO to avoid integrity errors.
            if not city:
                self.stderr.write(f"Skipping NKO '{name}': missing city (id={city_id})")
                continue
            if not owner:
                self.stderr.write(
                    f"Skipping NKO '{name}': missing owner (id={owner_id})"
                )
                continue

            defaults = {
                "description": description,
                "volunteer_functions": volunteer_functions,
                "phone": phone,
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
                "website": website,
                "vk_link": vk_link,
                "telegram_link": telegram_link,
                "other_social": other_social,
                "is_approved": is_approved,
                "is_active": is_active,
            }

            if city:
                defaults["city"] = city
            if owner:
                defaults["owner"] = owner

            if nkid:
                obj, created = NKO.objects.update_or_create(
                    id=nkid, defaults={"name": name, **defaults}
                )
            else:
                obj, created = NKO.objects.get_or_create(
                    name=name, defaults={**defaults}
                )

            # Try to set created_at/updated_at if provided (best-effort)
            if created_at:
                dt = parse_datetime(created_at)
                if dt:
                    if timezone.is_naive(dt) and settings.USE_TZ:
                        dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    NKO.objects.filter(pk=obj.pk).update(created_at=dt)
            if updated_at:
                dt2 = parse_datetime(updated_at)
                if dt2:
                    if timezone.is_naive(dt2) and settings.USE_TZ:
                        dt2 = timezone.make_aware(dt2, timezone.get_current_timezone())
                    NKO.objects.filter(pk=obj.pk).update(updated_at=dt2)

        # NKO <-> Category mapping
        mappings = read_csv("nko_category.csv")
        for row in mappings:
            nko_id = row.get("nko_id")
            cat_id = row.get("category_id")
            if not nko_id or not cat_id:
                continue
            try:
                nko = NKO.objects.get(id=int(nko_id))
                cat = Category.objects.get(id=int(cat_id))
                nko.categories.add(cat)
            except Exception as exc:
                self.stderr.write(f"Error adding category mapping {row}: {exc}")

        # Profiles
        profiles = read_csv("profile.csv")
        for row in profiles:
            user_id = row.get("user_id")
            if not user_id:
                continue
            try:
                user = User.objects.get(id=int(user_id))
            except User.DoesNotExist:
                self.stderr.write(f"User id {user_id} for profile not found")
                continue

            email_confirmed = row.get("email_confirmed")
            try:
                email_confirmed = bool(int(email_confirmed))
            except Exception:
                email_confirmed = False
            patronymic = row.get("patronymic") or ""

            Profile.objects.update_or_create(
                user=user,
                defaults={"email_confirmed": email_confirmed, "patronymic": patronymic},
            )

        self.stdout.write(self.style.SUCCESS("Initial data import completed."))
