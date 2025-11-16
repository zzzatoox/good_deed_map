from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


UserModel = get_user_model()
 

class EmailOnlyBackend(ModelBackend):
    """Authenticate users strictly by email (case-insensitive)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # 'username' param is what Django passes from authentication forms;
        # we treat it as email here.
        email = username or kwargs.get(UserModel.USERNAME_FIELD)
        if email is None:
            return None
        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
