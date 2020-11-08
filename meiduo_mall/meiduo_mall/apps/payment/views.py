import os

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from orders.models import OrderInfo
from alipay import AliPay


# GET /orders/(?<order_id>\d+)/payment/
from payment.models import Payment


class PaymentURLView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """
        获取支付宝支付网址:
        1. 获取order_id并校验订单是否有效
        2. 组织支付宝的支付网址和参数
        3. 返回支付宝的支付网址
        """
        # 1. 获取order_id并校验订单是否有效
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=request.user,
                                          pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'],
                                          status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return Response({'message': '无效的订单id'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 组织支付宝的支付网址和参数
        # 初始化
        alipay = AliPay(
            appid=settings.ALIPAY_APPID, # 开发者应用APPID
            app_notify_url=None,  # 默认回调url
            # 网站的私钥文件路径
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/payment/keys/app_private_key.pem'),
            # 支付宝公钥文件路径
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/payment/keys/alipay_public_key.pem'),
            sign_type="RSA2",  # 签名算法
            debug=settings.ALIPAY_DEBUG  # 是否使用沙箱
        )

        # 组织参数
        total_pay = order.total_amount # Decimal
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id, # 订单编号
            total_amount=str(total_pay), # 支付总金额
            subject='美多商城%s' % order_id, # 订单标题
            return_url="http://www.meiduo.site:8080/pay_success.html"
        )

        # 3. 返回支付宝的支付网址
        pay_url = settings.ALIPAY_URL + '?' + order_string
        return Response({'alipay_url': pay_url})

# charset=utf-8&
# out_trade_no=201904180856190000000002& # 订单编号
# method=alipay.trade.page.pay.return&
# total_amount=7998.00&
# 签名字符串
# sign=ZYTFHZBO5XURFdiO7iZmh3k5GNWSXZUq%2BenprKkcKSjOPlp0CoZcD5XyGCxiUQaEIsSmjtv3vJLzDvs8LIE2R5k0L%2FmuH%2BvtfXxQ6%2B%2F3esoydOnfpokKJUL1scU0YTbsDtHfoQGMk%2BcTVa0UwiIH4H5yJpbbtVoyS0GQzDZP4bbf9%2ByqCn7yGqPC6u6Lptp%2BCaP00MQ8%2BCkFjP0lyiGyusyjxqhgJNHcceZwx67mbYVQxwvSyNdnx0Ji2JiOFxx3OgNnck2f9nKf399qyhxe%2BAz041CJnyuQxgdg8SkI3j7uhCggRBZVn3lfA1a6wR34oX0yt2Lv6Kc23RyFdpH6fQ%3D%3D&
# trade_no=2019041822001485921000010092& # 支付交易编号
# auth_app_id=2016090800464054&
# version=1.0&
# app_id=2016090800464054&
# sign_type=RSA2&
# seller_id=2088102174694091&
# timestamp=2019-04-18+09%3A23%3A38


# PUT /payment/status/?<支付结果数据>
class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        """
        保存支付结果信息:
        1. 获取参数并进行签名校验
        2. 校验订单是否有效
        3. 保存支付结果并修改订单状态
        4. 返回应答，支付完成
        """
        # 1. 获取参数并进行签名校验
        data = request.query_params.dict() # QueryDict->dict

        signature = data.pop('sign') # 原始签名字符串

        # 初始化
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,  # 开发者应用APPID
            app_notify_url=None,  # 默认回调url
            # 网站的私钥文件路径
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/payment/keys/app_private_key.pem'),
            # 支付宝公钥文件路径
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/payment/keys/alipay_public_key.pem'),
            sign_type="RSA2",  # 签名算法
            debug=settings.ALIPAY_DEBUG  # 是否使用沙箱
        )

        # 验证签名
        success = alipay.verify(data, signature)

        if not success:
            # 验证失败
            return Response({'message': '非法操作'}, status=status.HTTP_403_FORBIDDEN)

        # 2. 校验订单是否有效
        order_id = data.get('out_trade_no')

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=request.user,
                                          pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'],
                                          status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return Response({'message': '无效的订单id'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 保存支付结果并修改订单状态
        trade_id = data.get('trade_no')
        Payment.objects.create(
            order=order,
            trade_id=trade_id
        )

        # 修改订单状态
        order.status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] # 待发货
        order.save()

        # 4. 返回应答，支付完成
        return Response({'trade_id': trade_id})