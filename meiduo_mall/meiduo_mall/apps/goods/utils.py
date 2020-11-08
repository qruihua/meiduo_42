from collections import OrderedDict

from goods.models import GoodsChannel


def get_categories():
    """返回商品分类数据"""
    categories = OrderedDict()  # 有序字典

    # 获取`频道`数据
    channels = GoodsChannel.objects.order_by('group_id', 'sequence')

    for channel in channels:
        # 获取频道组id
        group_id = channel.group_id

        if group_id not in categories:
            categories[group_id] = {'channels': [], 'sub_cats': []}

        # 获取频道关联一级分类
        cat1 = channel.category

        categories[group_id]['channels'].append({
            'id': cat1.id,
            'name': cat1.name,
            'url': channel.url
        })

        # 获取和一级分类关联的二级分类
        for cat2 in cat1.goodscategory_set.all():
            cat2.sub_cats = []
            # 获取和二级分类关联的三级分类
            for cat3 in cat2.goodscategory_set.all():
                cat2.sub_cats.append(cat3)

            categories[group_id]['sub_cats'].append(cat2)

    return categories
