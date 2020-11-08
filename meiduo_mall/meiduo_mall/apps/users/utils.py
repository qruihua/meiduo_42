from users.models import User


def jwt_response_payload_handler(token, user=None, request=None):
    """
    自定义jwt认证成功返回数据
    """
    return {
        'token': token,
        'user_id': user.id,
        'username': user.username
    }


# 自定义Django的认证后端类，继承于ModelBackend，
# 重写authenticate方法，让账户既可以是用户名，也可以手机号
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UserNameMobileBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        username: 接收账户名，此处账户名可以是`用户名`，也可以是`手机号`
        password: 接收密码
        """
        # 1. 根据用户名或手机号查询用户的信息
        try:
            user = User.objects.get(Q(username=username) | Q(mobile=username))
        except User.DoesNotExist:
            return None

        # 2. 校验密码是否正确
        if user.check_password(password):
            # 密码正确
            return user
