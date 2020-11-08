from django.test import TestCase
import pickle
import base64


# pickle.dumps(obj|dict): 将传入的字典或对象转换为bytes字节流
# pickle.loads(bytes字节流): 将传入bytes字节流转换为字典或者对象
# base64.b64encode(bytes字节流): 将传入的bytes字节流进行base64编码，返回编码之后bytes内容
# base64.b64decode(编码之后bytes内容|str): 将传入的内容进行base64解码，返回解码之后bytes内容


# if __name__ == "__main__":
#     cookie_data = 'gAN9cQAoSwF9cQEoWAgAAABzZWxlY3RlZHECiFgFAAAAY291bnR' \
#                   'xA0sCdUsDfXEEKGgCiWgDSwF1SwV9cQUoaAKIaANLA3V1Lg=='
#
#     # res = cookie_data.encode() # bytes
#     # print(res)
#     #
#     # res = base64.b64decode(res)
#     # print(res)
#     #
#     # res = pickle.loads(res)
#     # print(res)
#
#     # res = pickle.loads(base64.b64decode(cookie_data.encode()))
#     res = pickle.loads(base64.b64decode(cookie_data))
#     print(res)


# if __name__ == "__main__":
#     cart_dict = {
#         1: {
#             'count': 2,
#             'selected': True
#         },
#         3: {
#             'count': 1,
#             'selected': False
#         },
#         5: {
#             'count': 3,
#             'selected': True
#         }
#     }
#
#     # res = pickle.dumps(cart_dict) # bytes
#     # print(res)
#     #
#     # res = base64.b64encode(res)
#     # print(res)
#     #
#     # res = res.decode()
#     # print(res)
#
#     res = base64.b64encode(pickle.dumps(cart_dict)).decode()
#     # response.set_cookie('cart', res, max_age='过期时间: s')
#     print(res)
