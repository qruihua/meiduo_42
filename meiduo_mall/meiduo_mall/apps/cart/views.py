import base64
import pickle

from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cart import constants
from cart.serializers import CartSerializer, CartSKUSerializer, CartDelSerializer, CartSelectSerializer

from goods.models import SKU


# /cart/ jwt token
class CartView(APIView):
    def perform_authentication(self, request):
        """重写父类方法，让当前视图跳过DRF框架的认证机制"""
        pass

    # DELETE /cart/
    def delete(self, request):
        """
        删除购物车记录:
        1. 获取sku_id并进行校验(sku_id必传，sku_id对应商品是否存在)
        2. 删除用户的购物车记录
            2.1 如果用户已登录，删除redis中对应的购物车记录
            2.2 如果用户未登录，删除cookie中对应的购物车记录
        3. 返回应答，购物车记录删除成功
        """
        # 1. 获取sku_id并进行校验(sku_id必传，sku_id对应商品是否存在)
        serializer = CartDelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的数据
        sku_id = serializer.validated_data['sku_id']

        try:
            # 触发DRF认证机制
            user = request.user
        except Exception:
            user = None

        # 2. 删除用户的购物车记录
        if user and user.is_authenticated:
            # 2.1 如果用户已登录，删除redis中对应的购物车记录
            # redis链接
            redis_conn = get_redis_connection('cart')

            # 删除hash中sku_id属性和对应的值
            cart_key = 'cart_%s' % user.id
            redis_conn.hdel(cart_key, sku_id)

            # 删除set中勾选状态
            cart_selected_key = 'cart_selected_%s' % user.id
            redis_conn.srem(cart_selected_key, sku_id)

            # 返回应答
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # 2.2 如果用户未登录，删除cookie中对应的购物车记录
            response = Response(status=status.HTTP_204_NO_CONTENT)
            # 获取cookie购物车记录
            cookie_cart = request.COOKIES.get('cart')  # None

            if cookie_cart is None:
                # cookie购物车无数据，不需要删除
                return response

            # 解析cookie购物车数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))  # {}

            if not cart_dict:
                # 字典为空，购物车无数据，不需要删除
                return response

            # 删除对应记录
            if sku_id in cart_dict:
                del cart_dict[sku_id]
                # 设置cookie购物车数据
                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)

            # 3. 返回应答，购物车记录删除成功
            return response

    # PUT /cart/
    def put(self, request):
        """
        修改购物车记录:
        1. 获取参数并进行校验(参数完整性，sku_id对应的商品是否存在，count是否大于库存)
        2. 修改用户的购物车记录
            2.1 如果用户已登录，修改redis中对应的购物车记录
            2.2 如果用户未登录，修改cookie中对应的购物车记录
        3. 返回应答，购物车记录修改成功
        """
        # 1. 获取参数并进行校验(参数完整性，sku_id对应的商品是否存在，count是否大于库存)
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的参数
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count'] # 修改数量
        selected = serializer.validated_data['selected'] # 修改勾选状态

        try:
            # 触发DRF认证机制
            user = request.user
        except Exception:
            user = None

        # 2. 修改用户的购物车记录
        if user and user.is_authenticated:
            # 2.1 如果用户已登录，修改redis中对应的购物车记录
            # redis链接
            redis_conn = get_redis_connection('cart')

            # 修改hash中sku_id属性对应值
            cart_key = 'cart_%s' % user.id
            redis_conn.hset(cart_key, sku_id, count)

            # 修改勾选状态
            cart_selected_key = 'cart_selected_%s' % user.id

            if selected:
                # 将sku_id添加到set中
                redis_conn.sadd(cart_selected_key, sku_id)
            else:
                # 将sku_id从set中移除
                redis_conn.srem(cart_selected_key, sku_id)

            return Response(serializer.validated_data)
        else:
            # 2.2 如果用户未登录，修改cookie中对应的购物车记录
            response = Response(serializer.validated_data)

            # 获取cookie购物车记录
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart is None:
                # cookie购物车无数据，不需要修改
                return response

            # 解析cookie购物车数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode())) # {}

            if not cart_dict:
                # 字典为空，购物车无数据，不需要修改
                return response

            # 保存修改的数据
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 3. 返回应答，购物车记录修改成功
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)
            return response

    # GET /cart/
    def get(self, request):
        """
        购物车记录获取:
        1. 获取用户购物车的记录
            1.1 如果用户已登录，从redis中获取用户的购物车记录
            1.2 如果用户未登录，从cookie中获取用户的购物车记录
        2. 根据用户购物车中商品的id获取对应商品的数据
        3. 将购物车数据序列化并返回
        """
        try:
            # 触发认证机制
            user = request.user
        except Exception:
            user = None

        # 1. 获取用户购物车的记录
        if user and user.is_authenticated:
            # 1.1 如果用户已登录，从redis中获取用户的购物车记录
            # redis链接
            redis_conn = get_redis_connection('cart')

            # 从redis hash中获取用户购物车中添加的商品的id和对应的数量count
            cart_key = 'cart_%s' % user.id

            # {
            #     b'<sku_id>': b'<count>',
            #     ...
            # }
            cart_redis = redis_conn.hgetall(cart_key)

            # 从redis set中获取用户购物车被勾选的商品的id
            cart_selected_key = 'cart_selected_%s' % user.id

            # Set(b'<sku_id>', b'<sku_id>', ...)
            sku_ids = redis_conn.smembers(cart_selected_key)

            # 组织数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = {}

            for sku_id, count in cart_redis.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in sku_ids
                }
        else:
            # 1.2 如果用户未登录，从cookie中获取用户的购物车记录
            # 获取cookie中购物车数据
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart:
                # 解析cookie中的购物车数据
                # {
                #     '<sku_id>': {
                #         'count': '<count>',
                #         'selected': '<selected>'
                #     },
                #     ...
                # }
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

        # 2. 根据用户购物车中商品的id获取对应商品的数据
        cart_sku_ids = cart_dict.keys() # (1, 3, 5)

        # select * from tb_sku where id in (1, 3, 5);
        skus = SKU.objects.filter(id__in=cart_sku_ids)

        for sku in skus:
            # 给sku对象增加属性count和selected
            # 分别保存该对象在用户购物车中添加的商品的数量和勾选状态
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']

        # 3. 将购物车数据序列化并返回
        serializer = CartSKUSerializer(skus, many=True)
        return Response(serializer.data)

    # POST /cart/
    def post(self, request):
        """
        购物车记录保存:
        1. 获取参数并进行校验(参数完整性，sku_id是否存在，商品库存是否足够)
        2. 保存用户的购物车记录
            2.1 如果用户已登录，在redis中存储用户的购物车记录
            2.2 如果用户未登录，在cookie中存储用户的购物车记录
        3. 返回应答，购物车记录添加成功
        """
        # 1. 获取参数并进行校验(参数完整性，sku_id是否存在，商品库存是否足够)
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取检验之后的数据
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # 获取user
        try:
            # 只有使用request.user，就会触发DRF框架认证机制
            user = request.user
        except Exception:
            user = None

        # 2. 保存用户的购物车记录
        if user and user.is_authenticated:
            # 2.1 如果用户已登录，在redis中存储用户的购物车记录
            # 获取redis链接
            redis_conn = get_redis_connection('cart')

            # hash: 存储登录用户购物车添加的商品id和对应数量count
            # 如果该商品已经添加过，购物车记录中商品的数量需要进行累加
            cart_key = 'cart_%s' % user.id
            redis_conn.hincrby(cart_key, sku_id, count)

            # set: 存储登录用户购物车中被勾选的商品的id
            cart_selected_key = 'cart_selected_%s' % user.id

            if selected:
                redis_conn.sadd(cart_selected_key, sku_id)

            return Response(serializer.validated_data, status=status.HTTP_201_CREATED)
        else:
            # 2.2 如果用户未登录，在cookie中存储用户的购物车记录
            # 获取cookie中原有的购物车记录
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart:
                # 解析cookie中的购物车数据
                # {
                #     '<sku_id>': {
                #         'count': '<count>',
                #         'selected': '<selected>'
                #     },
                #     ...
                # }
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

            # 保存购物车记录
            if sku_id in cart_dict:
                # 数据累加
                count += cart_dict[sku_id]['count']

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 3. 返回应答，购物车记录添加成功
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            # 设置cookie购物车数据
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)
            return response


# PUT /cart/selection/
class CartSelectView(APIView):
    def perform_authentication(self, request):
        """让当前视图跳过DRF框架认证过程"""
        pass

    def put(self, request):
        """
        购物车记录的全选和取消全选:
        1. 获取selected并进行校验(selected必传)
        2. 设置购物车记录的勾选状态 True: 全选 False: 取消全选
            2.1 如果用户已登录，操作redis中对应的购物车记录
            2.2 如果用户未登录，操作cookie中对应的购物车记录
        3. 返回应答
        """
        # 1. 获取selected并进行校验(selected必传)
        serializer = CartSelectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取selected
        selected = serializer.validated_data['selected']

        try:
            # 触发认证机制
            user = request.user
        except Exception:
            user = None

        # 2. 设置购物车记录的勾选状态 True: 全选 False: 取消全选
        if user and user.is_authenticated:
            # 2.1 如果用户已登录，操作redis中对应的购物车记录
            # 获取redis链接
            redis_conn = get_redis_connection('cart')

            # 从redis hash中获取用户购物车中所有商品的id
            cart_key = 'cart_%s' % user.id
            sku_ids = redis_conn.hkeys(cart_key)

            cart_selected_key = 'cart_selected_%s' % user.id
            if selected:
                # 全选：将用户购物车中所有商品sku_id添加到redis set中
                redis_conn.sadd(cart_selected_key, *sku_ids)
            else:
                # 全不选：将用户购物车中所有商品sku_id从redis set中移除
                redis_conn.srem(cart_selected_key, *sku_ids)

            # 返回应答
            return Response({'message': 'OK'})
        else:
            # 2.2 如果用户未登录，操作cookie中对应的购物车记录
            # 获取cookie购物车记录
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart:
                # 解析cookie购物车记录
                # {
                #     '<sku_id>': {
                #         'count': '<count>',
                #         'selected': '<selected>'
                #     },
                #     ...
                # }
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

            # 设置cookie购物车记录勾选状态
            for sku_id, count_selected in cart_dict.items():
                count_selected['selected'] = selected

            # 3. 返回应答
            response = Response({'message': 'OK'})
            # 设置cookie购物车记录
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)
            return response




