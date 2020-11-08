# 封装合并购物车记录函数
import base64
import pickle

from django_redis import get_redis_connection


def merge_cookie_cart_to_redis(request, user, response):
    """
    将cookie中购物车数据合并到登录用户的redis购物车记录中:
    request: 请求对象
    user: 登录用户对象
    response: 响应对象
    """
    # 1. 获取cookie中的购物车数据
    cookie_cart = request.COOKIES.get('cart') # None

    if cookie_cart is None:
        # cookie购物车中无数据，不需要合并
        return

    # 解析cookie中购物车数据
    # {
    #     '<sku_id>': {
    #         'count': '<count>',
    #         'selected': '<selected>'
    #     },
    #     ...
    # }
    cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode())) # {}
    if not cart_dict:
        # 字典为空，cookie购物车中无数据，不需要合并
        return

    # 2. 将cookie中购物车数据合并对应redis购物车记录中
    # 组织数据
    # 保存cookie购物车数据中添加的商品id和对应的数量count，
    # 在进行合并时将cart的key和value作为属性和值设置到redis hash中
    # {
    #     '<sku_id>': '<count>',
    #     ...
    # }
    cart = {}

    # 保存cookie购物车数据中被勾选的商品id，
    # 在进行合并时将cart_selected_add商品id添加到redis set中
    cart_selected_add = []

    # 保存cookie购物车数据中未被勾选的商品id，
    # 在进行合并时将cart_selected_remove商品id从redis set中移除
    cart_selected_remove = []

    for sku_id, count_selected in cart_dict.items():
        cart[sku_id] = count_selected['count']

        if count_selected['selected']:
            # 勾选
            cart_selected_add.append(sku_id)
        else:
            # 未勾选
            cart_selected_remove.append(sku_id)

    # 进行合并
    redis_conn = get_redis_connection('cart')

    # 在进行合并时将cart的key和value作为属性和值设置到redis hash中
    cart_key = 'cart_%s' % user.id
    redis_conn.hmset(cart_key, cart)

    # 在进行合并时将cart_selected_add商品id添加到redis set中
    cart_selected_key = 'cart_selected_%s' % user.id
    if cart_selected_add:
        redis_conn.sadd(cart_selected_key, *cart_selected_add)

    # 在进行合并时将cart_selected_remove商品id从redis set中移除
    if cart_selected_remove:
        redis_conn.srem(cart_selected_key, *cart_selected_remove)

    # 3. 删除cookie中的购物车数据
    response.delete_cookie('cart')
