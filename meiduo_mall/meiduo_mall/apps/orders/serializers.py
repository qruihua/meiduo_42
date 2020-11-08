from datetime import datetime

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

from goods.models import SKU
from goods.serializers import SKUSerializer
from orders.models import OrderInfo, OrderGoods


class OrderSKUSerializer(serializers.ModelSerializer):
    """订单结算商品序列化器类"""
    count = serializers.IntegerField(label='结算数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image', 'count')


class OrderSerializer(serializers.ModelSerializer):
    """订单序列化器类"""
    class Meta:
        model = OrderInfo
        fields = ('order_id', 'address', 'pay_method')

        extra_kwargs = {
            'order_id': {
                'read_only': True
            },
            'address': {
                'write_only': True
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        """创建订单并保存订单数据"""
        # 获取address和pay_method
        address = validated_data['address']
        pay_method = validated_data['pay_method']

        # 获取登录用户
        user = self.context['request'].user

        # 订单编号：年月日时分秒+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%010d' % user.id

        # 商品总数量和实付款
        total_count = 0
        total_amount = Decimal(0)

        # 运费: 10
        freight = Decimal(10.0)

        # 订单状态
        if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH']: # 货到付款
            status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] # 待发货
        else:
            status = OrderInfo.ORDER_STATUS_ENUM['UNPAID'] # 待支付

        # redis链接
        redis_conn = get_redis_connection('cart')

        # 从redis set中获取用户购物车中被勾选的商品sku_id(勾选就是要购买的)
        cart_selected_key = 'cart_selected_%s' % user.id

        # Set(b'<sku_id>', b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis hash中获取用户购物车中所有商品sku_id和对应的数量count
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_dict = redis_conn.hgetall(cart_key)

        with transaction.atomic():
            # with语句块中的代码，凡是涉及到数据库的操作，在进行数据库操作时会放在同一事务中

            # 设置一个事务的保存点
            sid = transaction.savepoint()

            try:
                # 1）向订单基本信息表添加一条记录
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=total_count,
                    total_amount=total_amount,
                    freight=freight,
                    pay_method=pay_method,
                    status=status
                )

                # 2）订单中包含几个商品，就向订单商品表中添加几条记录
                for sku_id in sku_ids:
                    # 获取购买的数量
                    count = cart_dict[sku_id]
                    count = int(count)

                    for i in range(3):
                        # 根据sku_id获取商品对象
                        # select * from tb_sku where id=<sku_id>;
                        sku = SKU.objects.get(id=sku_id)

                        # 判断库存
                        if count > sku.stock:
                            # 回滚事务到sid保存点，将sid保存点之后的sql语句的执行结果撤销
                            transaction.savepoint_rollback(sid)
                            raise serializers.ValidationError('商品库存不足')

                        # 记录查出的商品原始库存
                        origin_stock = sku.stock
                        new_stock = origin_stock - count
                        new_sales = sku.sales + count

                        # 模拟产生订单并发
                        # print('users: %s times: %s origin_stock: %s' % (user.id, i, origin_stock))
                        # import time
                        # time.sleep(10)

                        # 销量增加，库存减少
                        # update tb_sku
                        # set stock=<new_stock>, sales=<new_sales>
                        # where id=<sku_id>;
                        # sku.stock -= count
                        # sku.sales += count
                        # sku.save()

                        # update tb_sku
                        # set stock=<new_stock>, sales=<new_sales>
                        # where id=<sku_id> and stock=<origin_stock>;
                        # 返回是一个数字：代表被更新的行数
                        res = SKU.objects.filter(id=sku_id, stock=origin_stock).\
                            update(stock=new_stock, sales=new_sales)

                        if res == 0:
                            if i == 2:
                                # 连续更新了3次，仍然失败，直接下单失败
                                # 回滚事务到sid保存点，将sid保存点之后的sql语句的执行结果撤销
                                transaction.savepoint_rollback(sid)
                                raise serializers.ValidationError('下单失败2')
                            # 更新失败，商品的库存发生了变化，需要重新进行查询和更新
                            continue

                        # 向订单商品表中添加一条记录
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=count,
                            price=sku.price
                        )

                        # 累加计算订单商品的总数量和总金额
                        total_count += count
                        total_amount += count*sku.price

                        # 跳出循环
                        break

                # 实付款
                total_amount += freight
                order.total_count = total_count
                order.total_amount = total_amount
                order.save()
            except serializers.ValidationError:
                # 继续向外抛出
                raise
            except Exception:
                # 下单失败，回滚事务到sid保存点，将sid保存点之后的sql语句的执行结果撤销
                transaction.savepoint_rollback(sid)
                raise serializers.ValidationError('下单失败1')

        # 3）清除购物车对应的购物车记录
        pl = redis_conn.pipeline()
        pl.hdel(cart_key, *sku_ids)
        pl.srem(cart_selected_key, *sku_ids)
        pl.execute()

        return order

    def create_1(self, validated_data):
        """创建订单并保存订单数据"""
        # 获取address和pay_method
        address = validated_data['address']
        pay_method = validated_data['pay_method']

        # 获取登录用户
        user = self.context['request'].user

        # 订单编号：年月日时分秒+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%010d' % user.id

        # 商品总数量和实付款
        total_count = 0
        total_amount = Decimal(0)

        # 运费: 10
        freight = Decimal(10.0)

        # 订单状态
        if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH']: # 货到付款
            status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] # 待发货
        else:
            status = OrderInfo.ORDER_STATUS_ENUM['UNPAID'] # 待支付

        # redis链接
        redis_conn = get_redis_connection('cart')

        # 从redis set中获取用户购物车中被勾选的商品sku_id(勾选就是要购买的)
        cart_selected_key = 'cart_selected_%s' % user.id

        # Set(b'<sku_id>', b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis hash中获取用户购物车中所有商品sku_id和对应的数量count
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_dict = redis_conn.hgetall(cart_key)

        with transaction.atomic():
            # with语句块中的代码，凡是涉及到数据库的操作，在进行数据库操作时会放在同一事务中

            # 设置一个事务的保存点
            sid = transaction.savepoint()

            try:
                # 1）向订单基本信息表添加一条记录
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=total_count,
                    total_amount=total_amount,
                    freight=freight,
                    pay_method=pay_method,
                    status=status
                )

                # 2）订单中包含几个商品，就向订单商品表中添加几条记录
                for sku_id in sku_ids:
                    # 获取购买的数量
                    count = cart_dict[sku_id]
                    count = int(count)

                    # 根据sku_id获取商品对象
                    # select * from tb_sku where id=<sku_id>;
                    # sku = SKU.objects.get(id=sku_id)

                    # select * from tb_sku where id=<sku_id> for update;
                    print('users: %s try get lock' % user.id)
                    sku = SKU.objects.select_for_update().get(id=sku_id) # 悲观锁(互斥锁)
                    print('users: %s get locked' % user.id)

                    # 判断库存
                    if count > sku.stock:
                        # 回滚事务到sid保存点，将sid保存点之后的sql语句的执行结果撤销
                        transaction.savepoint_rollback(sid)
                        raise serializers.ValidationError('商品库存不足')

                    # 模拟产生订单并发
                    # print('users: %s' % user.id)
                    import time
                    time.sleep(10)

                    # 销量增加，库存减少
                    sku.stock -= count
                    sku.sales += count
                    sku.save()

                    # 向订单商品表中添加一条记录
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )

                    # 累加计算订单商品的总数量和总金额
                    total_count += count
                    total_amount += count*sku.price

                # 实付款
                total_amount += freight
                order.total_count = total_count
                order.total_amount = total_amount
                order.save()
            except serializers.ValidationError:
                # 继续向外抛出
                raise
            except Exception:
                # 下单失败，回滚事务到sid保存点，将sid保存点之后的sql语句的执行结果撤销
                transaction.savepoint_rollback(sid)
                raise serializers.ValidationError('下单失败1')

        # 3）清除购物车对应的购物车记录
        pl = redis_conn.pipeline()
        pl.hdel(cart_key, *sku_ids)
        pl.srem(cart_selected_key, *sku_ids)
        pl.execute()

        return order


class OrderGoodsSerializer(serializers.ModelSerializer):
    """
    订单商品数据序列化器
    """
    sku = SKUSerializer()

    class Meta:
        model = OrderGoods
        fields = ('id', 'sku', 'count', 'price')


class DateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        tz = timezone.get_default_timezone()
        value = timezone.localtime(value, timezone=tz)
        return super().to_representation(value)


class OrderInfoSerializer(serializers.ModelSerializer):
    """
    订单数据序列化器
    """
    skus = OrderGoodsSerializer(many=True)
    # create_time = DateTimeField(format='%Y-%m-%d %H:%M:%S')
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = OrderInfo
        fields = ('order_id', 'create_time', 'total_amount', 'freight', 'status', 'skus', 'pay_method')


class SaveOrderCommentSerializer(serializers.ModelSerializer):
    """
    保存订单评论数据序列化器
    """
    class Meta:
        model = OrderGoods
        fields = ('sku', 'comment', 'score', 'is_anonymous')
        extra_kwargs = {
            'comment': {
                'required': True
            },
            'score': {
                'required': True
            },
            'is_anonymous': {
                'required': True
            }
        }

    def validate(self, attrs):
        order_id = self.context['view'].kwargs['order_id']
        user = self.context['request'].user
        try:
            OrderInfo.objects.filter(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
        except OrderInfo.DoesNotExist:
            raise serializers.ValidationError('订单信息有误')

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        order_id = self.context['view'].kwargs['order_id']
        sku = validated_data['sku']

        # 保存评论数据
        OrderGoods.objects.filter(order_id=order_id, sku=sku, is_commented=False).update(
            comment=validated_data['comment'],
            score=validated_data['score'],
            is_anonymous=validated_data['is_anonymous'],
            is_commented=True
        )

        # 累计评论数据
        sku.comments += 1
        sku.save()
        sku.goods.comments += 1
        sku.goods.save()

        # 如果所有订单商品都已评价，则修改订单状态为已完成
        if OrderGoods.objects.filter(order_id=order_id, is_commented=False).count() == 0:
            OrderInfo.objects.filter(order_id=order_id).update(status=OrderInfo.ORDER_STATUS_ENUM['FINISHED'])

        return validated_data
