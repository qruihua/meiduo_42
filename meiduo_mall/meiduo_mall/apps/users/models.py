from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

from itsdangerous import TimedJSONWebSignatureSerializer as TJWSSerializer, BadData

# Create your models here.
from meiduo_mall.utils.models import BaseModel
from users import constants
from areas.models import Area


class User(AbstractUser):
    """用户模型类"""
    mobile = models.CharField(max_length=11, verbose_name='手机号')
    email_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')
    default_address = models.OneToOneField('Address', related_name='addr_user', null=True, blank=True,
                                           on_delete=models.SET_NULL, verbose_name='默认地址')

    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def generate_verify_email_url(self):
        """生成用户的邮箱验证链接地址"""
        data = {
            'id': self.id,
            'email': self.email
        }

        # 对应用户的数据进行加密
        serializer = TJWSSerializer(secret_key=settings.SECRET_KEY, expires_in=constants.VERIFY_EMAIL_TOKEN_EXPIRES)
        token = serializer.dumps(data) # bytes
        # bytes->str
        token = token.decode()

        # 生成验证链接地址
        verify_url = 'http://www.meiduo.site:8080/succes_verify_email.html?token=' + token
        return verify_url

    @staticmethod
    def check_verify_email_token(token):
        """
        token: 加密用户的信息
        """
        serializer = TJWSSerializer(secret_key=settings.SECRET_KEY)

        try:
            data = serializer.loads(token)
        except BadData:
            # 解密失败
            return None
        else:
            # 解密成功
            id = data['id']
            email = data['email']

            # 查找对应的用户
            try:
                user = User.objects.get(id=id, email=email)
            except User.DoesNotExist:
                return None
            else:
                return user


class Address(BaseModel):
    """
    用户地址
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses', verbose_name='用户')
    title = models.CharField(max_length=20, verbose_name='地址名称')
    receiver = models.CharField(max_length=20, verbose_name='收货人')
    province = models.ForeignKey(Area, related_name='province_address', on_delete=models.PROTECT, verbose_name='省')
    city = models.ForeignKey(Area, related_name='city_address', on_delete=models.PROTECT, verbose_name='市')
    district = models.ForeignKey(Area, related_name='district_address', on_delete=models.PROTECT, verbose_name='区')
    place = models.CharField(max_length=50, verbose_name='地址')
    mobile = models.CharField(max_length=11, verbose_name='手机')
    phone = models.CharField(max_length=20, null=True, blank=True, default='', verbose_name='固定电话')
    email = models.CharField(max_length=30, null=True, blank=True, default='', verbose_name='电子邮箱')
    is_delete = models.BooleanField(default=False, verbose_name='逻辑删除')
    # is_default = models.BooleanField(default=False, verbose_name='是否默认')

    class Meta:
        db_table = 'tb_addresses'
        verbose_name = '用户地址'
        verbose_name_plural = verbose_name
        ordering = ['-update_time']

