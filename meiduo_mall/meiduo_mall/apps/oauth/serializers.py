import base64
import os

from django_redis import get_redis_connection
from rest_framework import serializers

from oauth.models import OAuthQQUser
from oauth.utils import OAuthQQ
from users.models import User


class QQAuthUserSerializer(serializers.ModelSerializer):
    """QQ绑定数据序列化器类"""
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    access_token = serializers.CharField(label='加密OpenID', write_only=True)
    token = serializers.CharField(label='JWT Token', read_only=True)
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$', write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'password', 'sms_code', 'access_token', 'token')

        extra_kwargs = {
            'username': {
                'read_only': True
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '最小长度为8',
                    'max_length': '最大长度为20'
                }

            }
        }

    # 手机号格式，短信验证码是否正确，access_token是否有效，如果手机已注册，校验密码是否正确
    def validate(self, attrs):
        # access_token是否有效
        access_token = attrs['access_token'] # 加密的openid

        openid = OAuthQQ.check_save_user_token(access_token)

        if openid is None:
            # 解密失败
            raise serializers.ValidationError('无效的access_token')

        attrs['openid'] = openid

        # 短信验证码是否正确
        # 从redis中获取真实的短信验证码内容
        redis_conn = get_redis_connection('verify_codes')

        mobile = attrs['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile)  # bytes

        if real_sms_code is None:
            raise serializers.ValidationError('短信验证码已过期')

        # 获取客户端传递短信验证码内容
        sms_code = attrs['sms_code']  # str

        # 对比短信验证码内容
        if real_sms_code.decode() != sms_code:
            raise serializers.ValidationError('短信验证码错误')

        # 如果手机已注册，校验密码是否正确
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 用户不存在，mobile未注册
            user = None
        else:
            # 用户存在，mobile已注册，校验密码是否正确
            password = attrs['password']
            if not user.check_password(password):
                # 密码不正确
                raise serializers.ValidationError('密码错误')

        attrs['user'] = user

        return attrs

    def create(self, validated_data):
        """保存QQ登录绑定的数据"""
        # 如果mobile未注册，先创建新用户
        user = validated_data['user']

        if user is None:
            mobile = validated_data['mobile']
            password = validated_data['password']
            # 随机生成用户名
            username = base64.b64encode(os.urandom(9)).decode()
            user = User.objects.create_user(username=username,
                                            password=password,
                                            mobile=mobile)
        # 保存绑定的数据
        openid = validated_data['openid']
        OAuthQQUser.objects.create(user=user,
                                   openid=openid)

        # 生成jwt token
        from rest_framework_jwt.settings import api_settings

        # 生成载荷的内容
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        # 生成jwt token
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        # 给user对象增加属性token，保存jwt token的数据
        user.token = token

        return user
















