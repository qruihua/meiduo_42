from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.utils import merge_cookie_cart_to_redis
from oauth.exceptions import QQAPIError
from oauth.models import OAuthQQUser
from oauth.serializers import QQAuthUserSerializer
from oauth.utils import OAuthQQ


# GET /oauth/qq/authorization/?next=<登录之后访问页面地址>
class QQAuthURLView(APIView):
    def get(self, request):
        """
        获取QQ登录网址:
        1. 获取next
        2. 组织QQ登录网址和参数
        3. 返回QQ登录网址
        """
        # 1. 获取next
        next = request.query_params.get('next', '/')

        # 2. 组织QQ登录网址和参数
        oauth = OAuthQQ(state=next)
        login_url = oauth.get_login_url()

        # 3. 返回QQ登录网址
        return Response({'login_url': login_url})


class QQAuthUserView(GenericAPIView):
    serializer_class = QQAuthUserSerializer

    # POST /oauth/qq/user/
    def post(self, request):
        """
        保存绑定的数据:
        1. 获取参数并进行校验(参数的完整性，手机号格式，短信验证码是否正确，access_token是否有效，如果手机已注册，校验密码是否正确)
        2. 保存QQ登录绑定的数据
        3. 返回应答，登录成功
        """
        # 1. 获取参数并进行校验(参数的完整性，手机号格式，短信验证码是否正确，access_token是否有效，如果手机已注册，校验密码是否正确)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. 保存QQ登录绑定的数据(create)
        user = serializer.save()

        # 3. 返回应答，登录成功
        # 调用合并购物车记录函数
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        merge_cookie_cart_to_redis(request, user, response)
        return response

    # GET /oauth/qq/user/?code=<code>
    def get(self, request):
        """
        获取QQ登录用户的openid并处理：
        1. 获取code并校验(code必传)
        2. 获取QQ登录用户openid
            2.1 根据code请求qq服务器获取access_token
            2.2 根据access_token请求qq服务器获取openid
        3. 根据openid判断是否绑定过本网站用户
            3.1 如果已绑定，直接生成jwt token并返回
            3.2 如果未绑定，将openid加密并返回
        """
        # 1. 获取code并校验(code必传)
        code = request.query_params.get('code')

        if code is None:
            return Response({'message': '缺少code参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 获取QQ登录用户openid
        oauth = OAuthQQ()
        try:
            # 2.1 根据code请求qq服务器获取access_token
            access_token = oauth.get_access_token(code)
            # 2.2 根据access_token请求qq服务器获取openid
            openid = oauth.get_openid(access_token)
        except QQAPIError:
            return Response({'message': 'QQ登录异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 3. 根据openid判断是否绑定过本网站用户
        try:
            qq_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 3.2 如果未绑定，将openid加密并返回
            secret_openid = oauth.generate_save_user_token(openid)
            return Response({'access_token': secret_openid})
        else:
            # 3.1 如果已绑定，直接生成jwt token并返回
            from rest_framework_jwt.settings import api_settings

            user = qq_user.user
            # 生成载荷的内容
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            # 生成jwt token
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            # 返回响应
            response_data = {
                'user_id': user.id,
                'username': user.username,
                'token': token
            }

            # 调用合并购物车记录函数
            response = Response(response_data)
            merge_cookie_cart_to_redis(request, user, response)
            return response

