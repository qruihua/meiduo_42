from django.test import TestCase
from urllib.parse import urlencode, parse_qs
from urllib.request import urlopen

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import BadData

# Create your tests here.

if __name__ == "__main__":
    # 解密
    req_data = 'eyJleHAiOjE1NTQ1MzY2MTgsImlhdCI6MTU1NDUzMzAxOCwiYWxnIjoiSFMyNTYifQ.' \
               'eyJvcGVuaWQiOiJLREtLRDkxOTI5a0RLSURJRExMOTE5MyJ9.nbqQdpkseTuq5bIX0-g8H-LzvK4E93PsUAur2u4ADAU'

    serializer = Serializer(secret_key='abc123')

    try:
        res = serializer.loads(req_data)
    except BadData:
        print('解密失败')
    else:
        print(res)

# if __name__ == "__main__":
#     # 签名加密
#     req_dict = {
#         'openid': 'KDKKD91929kDKIDIDLL9193'
#     }
#
#     serializer = Serializer(secret_key='abc123', expires_in=3600)
#
#     res = serializer.dumps(req_dict) # bytes
#     # bytes->str
#     res = res.decode()
#     print(res)


# if __name__ == "__main__":
#     # urlopen(req_url): 发起http网络请求
#
#     req_url = 'http://api.meiduo.site:8000/mobiles/13155667788/count/'
#
#     # 向req_url发起http网络请求
#     response = urlopen(req_url)
#
#     # 获取响应数据
#     res_data = response.read() # bytes类型
#     # bytes->str
#     res_data = res_data.decode()
#     print(res_data)


# if __name__ == "__main__":
#     # parse_qs('查询字符串'): 将查询字符串转换为字典
#
#     req_str = 'a=1&b=2&c=3'
#
#     res = parse_qs(req_str) # 字典键对应value类型时list
#     print(res)

# if __name__ == "__main__":
#     # urlencode(dict): 将字典转换为查询字符串
#
#     req_dict = {
#         'a': 1,
#         'b': 2,
#         'c': 3
#     }
#
#     # a=1&b=2&c=3
#
#     res = urlencode(req_dict)
#     print(res)
