from decimal import Decimal
from django_redis import get_redis_connection
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from goods.models import SKU
from orders.models import OrderInfo, OrderGoods
from orders.serializers import OrderSKUSerializer, OrderSerializer, OrderGoodsSerializer, SaveOrderCommentSerializer, \
    OrderInfoSerializer


class OrdersSettlementView(APIView):
    permission_classes = [IsAuthenticated]

    # GET /orders/settlement/
    def get(self, request):
        """
        获取订单结算商品的数据:
        1. 从redis中获取用户所要结算商品的sku_id和结算数量count
        2. 根据商品sku_id获取对应商品的数据&组织运费
        3. 将结算数据序列化并返回
        """
        # 1. 从redis中获取用户所要结算商品的sku_id和结算数量count
        # redis链接
        redis_conn = get_redis_connection('cart')

        # 从redis set中获取用户购物车中被勾选的商品的sku_id
        user = request.user
        cart_selected_key = 'cart_selected_%s' % user.id

        # Set(b'<sku_id>', b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis hash中获取用户购物车中所有商品的id和对应的数量count
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_redis = redis_conn.hgetall(cart_key)

        # 转换数据
        # {
        #     '<sku_id>': '<count>',
        #     ...
        # }
        cart_dict = {}

        for sku_id, count in cart_redis.items():
            cart_dict[int(sku_id)] = int(count)

        # 2. 根据商品sku_id获取对应商品的数据&组织运费
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count，保存该商品所要结算的数量count
            sku.count = cart_dict[sku.id]

        # 运费
        freight = Decimal(10.0)

        # 3. 将结算数据序列化并返回
        serializer = OrderSKUSerializer(skus, many=True)

        response_data = {
            'freight': freight,
            'skus': serializer.data
        }
        return Response(response_data)


# /orders/
class OrdersViewSet(CreateModelMixin,
                    ListModelMixin,
                    GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderSerializer
        else:
            return OrderInfoSerializer

    def get_queryset(self):
        """返回当前登录用户的订单数据"""
        user = self.request.user
        return OrderInfo.objects.filter(user=user).order_by('-create_time')


class UncommentOrderGoodsView(ListAPIView):
    """
    待评论的订单商品
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderGoodsSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        order_id = self.kwargs['order_id']
        try:
            OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            raise PermissionDenied

        return OrderGoods.objects.filter(order_id=order_id, is_commented=False)


class OrderCommentView(CreateAPIView):
    """
    订单评论
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SaveOrderCommentSerializer
