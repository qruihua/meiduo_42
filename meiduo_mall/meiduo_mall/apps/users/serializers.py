import re

from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework.generics import CreateAPIView

from goods.models import SKU
from users import constants
from users.models import User, Address


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器类"""
    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='JWT token', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'password', 'password2', 'sms_code', 'allow', 'token')

        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '最小长度为5',
                    'max_length': '最大长度为20'
                }
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

    # 手机号格式，手机号是否注册，是否同意协议，两次密码是否一致，短信验证码是否正确
    def validate_mobile(self, value):
        """针对mobile字段的内容进行补充验证"""
        # 手机号格式
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式不正确')

        # 手机号是否注册
        count = User.objects.filter(mobile=value).count()

        if count != 0:
            raise serializers.ValidationError('手机号已注册')

        return value

    def validate_allow(self, value):
        """针对allow字段的内容进行补充验证"""
        if value != 'true':
            raise serializers.ValidationError('请同意协议')

        return value

    def validate(self, attrs):
        """
        attrs: 字典，创建序列化器对象时，传入的data数据
        """
        # 两次密码是否一致
        password = attrs['password']
        password2 = attrs['password2']

        if password != password2:
            raise serializers.ValidationError('两次密码不一致')

        # 短信验证码是否正确
        # 从redis中获取真实的短信验证码内容
        redis_conn = get_redis_connection('verify_codes')

        mobile = attrs['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile) # bytes

        if real_sms_code is None:
            raise serializers.ValidationError('短信验证码已过期')

        # 获取客户端传递短信验证码内容
        sms_code = attrs['sms_code'] # str

        # 对比短信验证码内容
        if real_sms_code.decode() != sms_code:
            raise serializers.ValidationError('短信验证码错误')

        return attrs

    def create(self, validated_data):
        """
        validated_data: 校验之后字典数据
        """
        # 清除无用的数据
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        # 创建新用户
        user = User.objects.create_user(**validated_data)

        # 生成一个jwt token，保存注册用户身份信息
        from rest_framework_jwt.settings import api_settings

        # 生成载荷的内容
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        # 生成jwt token
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        # 给user对象动态增加属性token，保存jwt token数据
        user.token = token

        # 返回user
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """用户序列化器类"""
    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    """邮箱设置序列化器类"""
    class Meta:
        model = User
        fields = ('id', 'email')

        extra_kwargs = {
            'email': {
                'required': True
            }
        }

    def update(self, instance, validated_data):
        """
        instance: 用户对象
        validated_data: 校验之后的数据
        """
        # 设置登录用户的邮箱
        email = validated_data['email']
        instance.email = email
        instance.save()

        # 生成验证链接：http://www.meiduo.site:8080/succes_verify_email.html?user_id=<username>&email=<email>
        # itsdangerous对用户的信息进行加密，将加密之后的内容放在验证链接中
        # http://www.meiduo.site:8080/succes_verify_email.html?token=<加密用户数据>
        verify_url = instance.generate_verify_email_url()

        # 发出发送邮件任务消息
        from celery_tasks.email.tasks import send_verify_email
        send_verify_email.delay(email, verify_url)

        return instance


# addr = Address.objects.get(id=1)
# addr.province 关联的省
# addr.city 关联的市
# addr.district 关联的区县

class AddressSerializer(serializers.ModelSerializer):
    """地址序列化器类"""
    province_id = serializers.IntegerField(label='省id')
    city_id = serializers.IntegerField(label='市id')
    district_id = serializers.IntegerField(label='区县id')
    # 将关联对象序列化为关联对象模型类__str__方法的返回值
    province = serializers.StringRelatedField(label='省名称')
    city = serializers.StringRelatedField(label='市名称')
    district = serializers.StringRelatedField(label='区县名称')

    class Meta:
        model = Address
        exclude = ('user', 'is_delete', 'create_time', 'update_time')

    # 手机号格式
    def validate_mobile(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号错误')

        return value

    def create(self, validated_data):
        """创建并保存新增地址的数据"""
        # 获取登录的用户
        user = self.context['request'].user
        validated_data['user'] = user

        # 调用ModelSerializer类中create方法新增地址
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """地址标题序列化器类"""
    class Meta:
        model = Address
        fields = ('title', )


class HistorySerializer(serializers.Serializer):
    """浏览记录序列化器类"""
    sku_id = serializers.IntegerField(label='sku商品id')

    def validate_sku_id(self, value):
        # 校验商品是否存在
        try:
            sku = SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('商品不存在')

        return value

    def create(self, validated_data):
        # 在redis中保存登录用户的浏览记录
        redis_conn = get_redis_connection('histories')

        # 获取登录用户
        user = self.context['request'].user

        # 1. 去重：如果用户已经浏览过该商品，那么商品的id需要先从redis列表中移除
        sku_id = validated_data['sku_id']
        history_key = 'history_%s' % user.id
        redis_conn.lrem(history_key, 0, sku_id)

        # 2. 左侧加入：把最新浏览的商品的id添加到列表的最左侧
        redis_conn.lpush(history_key, sku_id)

        # 3. 截取：只保留用户最新浏览的几个商品id
        redis_conn.ltrim(history_key, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)

        return validated_data








