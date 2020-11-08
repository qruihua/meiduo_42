from datetime import datetime

from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import ObtainJSONWebToken, jwt_response_payload_handler

from cart.utils import merge_cookie_cart_to_redis
from goods.models import SKU
from goods.serializers import SKUSerializer
from users import constants
from users.models import User
from users.serializers import UserSerializer, UserDetailSerializer, EmailSerializer, AddressSerializer, \
    AddressTitleSerializer, HistorySerializer


# Create your views here.


# GET /usernames/(?P<username>\w{5,20})/count/
class UserNameCountView(APIView):
    def get(self, request, username):
        """
        获取用户名的数量:
        1. 根据username查询用户的数量
        2. 返回应答
        """
        # 1. 根据username查询用户的数量
        count = User.objects.filter(username=username).count()

        # 2. 返回应答
        response_data = {
            'username': username,
            'count': count
        }
        return Response(response_data)


# GET /mobiles/(?P<mobile>1[3-9]\d{9})/count/
class MobileCountView(APIView):
    def get(self, request, mobile):
        """
        获取手机号的数量:
        1. 根据mobile查询用户的数量
        2. 返回应答
        """
        # 1. 根据mobile查询用户的数量
        count = User.objects.filter(mobile=mobile).count()

        # 2. 返回应答
        response_data = {
            'mobile': mobile,
            'count': count
        }
        return Response(response_data)


# POST /users/
class UserView(CreateAPIView):
    # 指定视图所使用的序列化器类
    serializer_class = UserSerializer

    # def post(self, request):
    #     """
    #     注册用户信息的保存(用户创建):
    #     1. 获取参数并进行校验(参数完整性，手机号格式，手机号是否注册，是否同意协议，两次密码是否一致，短信验证码是否正确）
    #     2. 创建新用户并保存注册用户的信息
    #     3. 将新用户数据序列化返回
    #     """
    #     # 1. 获取参数并进行校验(参数完整性，手机号格式，手机号是否注册，是否同意协议，两次密码是否一致，短信验证码是否正确）
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     # 2. 创建新用户并保存注册用户的信息(create)
    #     serializer.save()
    #
    #     # 3. 将新用户数据序列化返回
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


# GET /user/
class UserDetailView(RetrieveAPIView):
    # 指定当前视图的权限控制类，此处是仅认证的用户才能进行访问
    permission_classes = [IsAuthenticated]

    serializer_class = UserDetailSerializer
    # queryset = <'指定视图所使用的查询集'>

    def get_object(self):
        # 返回当前登录的用户对象
        # self.request: request请求对象
        return self.request.user

    # def get(self, request):
    #     """
    #     self.request: request请求对象
    #     request.user:
    #         1. 如果用户已认证，request.user就是登录的用户的对象
    #         2. 如果用户未认证，request.user是一个匿名用户类的对象
    #     获取登录用户个人信息:
    #     1. 获取登录用户对象
    #     2. 将登录用户对象序列化并返回
    #     """
    #     # 1. 获取登录用户对象
    #     user = self.get_object() # user = request.user
    #
    #     # 2. 将登录用户对象序列化并返回
    #     serializer = self.get_serializer(user)
    #     return Response(serializer.data)


# PUT /email/
class EmailView(APIView):
    # 指定当前视图的权限控制类，此处是仅认证的用户才能进行访问
    permission_classes = [IsAuthenticated]

    def put(self, request):
        """
        登录用户的邮箱设置:
        1. 获取登录用户
        2. 获取email参数并进行校验(email必传，email格式)
        3. 设置登录用户的邮箱并给邮箱发送验证邮件
        4. 返回应答，邮箱设置成功
        """
        # 1. 获取登录用户
        user = request.user

        # 2. 获取email参数并进行校验(email必传，email格式)
        serializer = EmailSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)

        # 3. 设置登录用户的邮箱并给邮箱发送验证邮件(update)
        serializer.save()

        # 4. 返回应答，邮箱设置成功
        return Response(serializer.data)


# PUT /emails/verification/?token='<加密用户的信息>'
class EmailVerifyView(APIView):
    def put(self, request):
        """
        用户邮箱验证:
        1. 获取token参数并进行校验(token必传，对token解密)
        2. 将对应的用户邮箱验证标记email_active设置为True
        3. 返回应答
        """
        # 1. 获取token参数并进行校验(token必传，对token解密)
        token = request.query_params.get('token') # None

        if token is None:
            return Response({'message': '缺少token参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 对token解密
        user = User.check_verify_email_token(token)

        if user is None:
            # 解密失败
            return Response({'message': '无效的token数据'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 将对应的用户邮箱验证标记email_active设置为True
        user.email_active = True
        user.save()

        # 3. 返回应答
        return Response({'message': 'OK'})


class AddressViewSet(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    """地址视图集"""
    permission_classes = [IsAuthenticated]

    # 指定视图所使用的序列化器类
    serializer_class = AddressSerializer

    def get_queryset(self):
        """返回视图所使用的查询集"""
        return self.request.user.addresses.filter(is_delete=False)

    # POST /addresses/ -> create
    def create(self, request):
        """
        request.user: 获取登录用户
        新增地址数据的保存:
        0. 地址数量上限判断(用户的地址是否超过最大地址数量)
        1. 获取参数并进行校验(参数完整性，手机号格式，邮箱格式)
        2. 创建并保存新增地址的数据
        3. 将新增地址数据序列化并返回
        """
        # 0. 地址数量上限判断(用户的地址是否超过最大地址数量)
        count = request.user.addresses.filter(is_delete=False).count()

        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '地址数量超过上限'}, status=status.HTTP_403_FORBIDDEN)

        # # 1. 获取参数并进行校验(参数完整性，手机号格式，邮箱格式)
        # serializer = self.get_serializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        #
        # # 2. 创建并保存新增地址的数据(create)
        # serializer.save()
        #
        # # 3. 将新增地址数据序列化并返回
        # return Response(serializer.data, status=status.HTTP_201_CREATED)

        # 调用CreateModelMixin中的create方法
        return super().create(request)

    # GET /addresses/ -> list
    def list(self, request):
        """
        获取用户的收货地址数据:
        1. 查询用户的收货地址数据
        2. 将用户的收货地址数据序列化并返回
        """
        # 1. 查询用户的收货地址数据
        # addresses = request.user.addresses.filter(is_delete=False)
        addresses = self.get_queryset()

        # 2. 将用户的收货地址数据序列化并返回
        serializer = self.get_serializer(addresses, many=True)
        response_data = {
            'user_id': request.user.id,
            'default_address_id': request.user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data
        }

        return Response(response_data)

    # DELETE /addresses/(?P<pk>\d+)/ -> destroy
    def destroy(self, request, pk):
        """
        删除指定的地址数据:
        1. 根据pk获取指定地址数据
        2. 将指定地址进行删除(逻辑删除)
        3. 返回应答
        """
        # 1. 根据pk获取指定地址数据
        address = self.get_object()

        # 2. 将指定地址进行删除(逻辑删除)
        address.is_delete = True
        address.save()

        # 3. 返回应答
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT /addresses/(?P<pk>\d+)/ -> update
    # def update(self, request, pk):
    #     """
    #     修改指定的地址数据:
    #     1. 根据pk获取指定的地址数据
    #     2. 获取参数并进行校验
    #     3. 保存修改地址的数据
    #     4. 将修改地址数据序列化并返回
    #     """
    #     # 1. 根据pk获取指定的地址数据
    #     address = self.get_object()
    #
    #     # 2. 获取参数并进行校验
    #     serializer = self.get_serializer(address, data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     # 3. 保存修改地址的数据(update)
    #     serializer.save()
    #
    #     # 4. 将修改地址数据序列化并返回
    #     return Response(serializer.data)

    # PUT /addresses/(?P<pk>\d+)/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk):
        """
        设置用户的默认地址:
        1. 根据pk获取指定地址数据
        2. 设置用户的默认地址
        3. 返回应答
        """
        # 1. 根据pk获取指定地址数据
        address = self.get_object()

        # 2. 设置用户的默认地址
        # request.user.default_address = address
        request.user.default_address_id = address.id
        request.user.save()

        # 3. 返回应答
        return Response({'message': 'OK'})

    # PUT /addresses/(?P<pk>\d+)/title/
    @action(methods=['put'], detail=True)
    def title(self, request, pk):
        """
        修改指定的地址标题:
        1. 根据pk获取指定的地址数据
        2. 获取title并进行校验(title必传)
        3. 保存修改地址的标题
        4. 返回应答
        """
        # 1. 根据pk获取指定的地址数据
        address = self.get_object()

        # 2. 获取title并进行校验(title必传)
        serializer = AddressTitleSerializer(address, data=request.data)
        serializer.is_valid(raise_exception=True)

        # 3. 保存修改地址的标题(update)
        serializer.save()

        # 4. 返回应答
        return Response(serializer.data)


class BrowseHistoryView(CreateAPIView):
    permission_classes = [IsAuthenticated]

    serializer_class = HistorySerializer

    # GET /browse_histories/
    def get(self, request):
        """
        浏览记录获取:
        1. 从redis中获取登录用户浏览的商品的sku_id
        2. 根据商品的id获取对应商品的数据
        3. 将商品的数据序列化并返回
        """
        # 1. 从redis中获取登录用户浏览的商品的sku_id
        redis_conn = get_redis_connection('histories')

        history_key = 'history_%s' % request.user.id
        # [b'<sku_id>', b'<sku_id>', ...]
        sku_ids = redis_conn.lrange(history_key, 0, -1)

        # 2. 根据商品的id获取对应商品的数据
        skus = []

        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id) # SKU.objects.get(id=b'1')
            skus.append(sku)

        # 3. 将商品的数据序列化并返回
        serializer = SKUSerializer(skus, many=True)
        return Response(serializer.data)

    # POST /browse_histories/
    # def post(self, request):
    #     """
    #     浏览记录保存:
    #     1. 获取sku_id并进行校验(sku_id必传，sku_id对应的商品是否存在)
    #     2. 在redis中保存登录用户的浏览记录
    #     3. 返回应答，添加成功
    #     """
    #     # 1. 获取sku_id并进行校验(sku_id必传，sku_id对应的商品是否存在)
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     # 2. 在redis中保存登录用户的浏览记录(create)
    #     serializer.save()
    #
    #     # 3. 返回应答，添加成功
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


# POST /authorizations/
class UserAuthorizeView(ObtainJSONWebToken):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # 账户名和密码正确
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            # 调用合并购物车记录的函数
            merge_cookie_cart_to_redis(request, user, response)
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)














