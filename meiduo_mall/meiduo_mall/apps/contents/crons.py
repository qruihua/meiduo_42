# 定义函数生成首页的静态页面
import os
import time

from django.conf import settings
from django.template import loader

from contents.models import ContentCategory
from goods.models import GoodsChannel
from collections import OrderedDict


def generate_static_index_html():
    """生成首页的静态页面index.html"""
    # 1. 查数据：从数据库中查询出首页所需`商品分类`和`首页广告`数据
    # {
    #     '<group_id>': {
    #         'channels': [{'id': '一级分类id', 'name': '一类分类名称', 'url': '频道页面地址'}, {}, ...],
    #         'sub_cats': [{'id': '二级分类id', 'name': '二级分类名称',
    #                       'sub_cats': [{'id': '三级分类id', 'name': '三级分类名称'}, {}, ...]},
    #                      {},
    #                      ...]
    #     },
    #     ...
    # }
    print('generate_static_index_html: %s' % time.ctime())

    categories = OrderedDict() # 有序字典

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

    # 首页广告
    # {
    #     '<key>': '<该分类下所有广告>',
    #     '<key>': '<该分类下所有广告>',
    #     ...
    # }
    contents = {}

    # 获取广告分类的数据
    content_categories = ContentCategory.objects.all()

    for cat in content_categories:
        # 获取和cat分类关联的广告数据
        contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

    # 2. 调模板：调用`index.html`模板文件，给模板文件传递数据，进行模板渲染，将模板文件中的变量进行替换，获取替换之后完整html内容
    context = {
        'categories': categories,
        'contents': contents
    }

    # 加载模板：指定使用模板文件，获取模板对象
    temp = loader.get_template('index.html')

    # 模板渲染：给模板文传数据，将模板文件中变量进行替换，获取替换之后html页面
    res_html = temp.render(context)

    # 3. 保存静态页面：将渲染之后的html内容保存成一个静态文件
    save_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'index.html')

    with open(save_path, 'w', encoding='utf8') as f:
        f.write(res_html)
