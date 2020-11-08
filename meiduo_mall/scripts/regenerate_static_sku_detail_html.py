#! /usr/bin/env python
import os

import sys
# 将scripts目录的上级目录添加到当前py程序搜索包目录列表中
sys.path.insert(0, '../')

# 设置django运行所依赖环境变量
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")

# 让django进行初始化
import django
django.setup()

from django.conf import settings
from django.template import loader

from goods.models import SKU
from goods.utils import get_categories


def generate_static_sku_detail_html(sku_id):
    """生成sku_id对应商品的静态详情页面"""
    # 1. 查数据
    # 商品分类菜单
    categories = get_categories()

    # 获取当前sku的信息
    sku = SKU.objects.get(id=sku_id)
    # 获取和商品关联的图片
    sku.images = sku.skuimage_set.all()

    # 面包屑导航信息中的频道
    # 获取和sku对象关联SPU对象
    goods = sku.spu
    # goods.category1：获取和SPU对象关联的一级分类
    # category1.goodschannel：获取和一级分类关联的频道对象
    goods.channel = goods.category1.goodschannel

    # 构建当前商品的规格键
    # sku_key = [规格1参数id， 规格2参数id， 规格3参数id, ...]
    sku_specs = sku.skuspecification_set.order_by('spec_id')
    sku_key = []
    for spec in sku_specs:
        sku_key.append(spec.option.id)

    # 获取当前商品的所有SKU
    skus = goods.sku_set.all()

    # 构建不同规格参数（选项）的sku字典
    # spec_sku_map = {
    #     (规格1参数id, 规格2参数id, 规格3参数id, ...): sku_id,
    #     (规格1参数id, 规格2参数id, 规格3参数id, ...): sku_id,
    #     ...
    # }
    spec_sku_map = {}
    for s in skus:
        # 获取sku的规格参数
        s_specs = s.skuspecification_set.order_by('spec_id')
        # 用于形成规格参数-sku字典的键
        key = []
        for spec in s_specs:
            key.append(spec.option.id)
        # 向规格参数-sku字典添加记录
        spec_sku_map[tuple(key)] = s.id

    # 获取当前商品的规格信息
    # specs = [
    #    {
    #        'name': '屏幕尺寸',
    #        'options': [
    #            {'value': '13.3寸', 'sku_id': xxx},
    #            {'value': '15.4寸', 'sku_id': xxx},
    #        ]
    #    },
    #    {
    #        'name': '颜色',
    #        'options': [
    #            {'value': '银色', 'sku_id': xxx},
    #            {'value': '黑色', 'sku_id': xxx}
    #        ]
    #    },
    #    ...
    # ]
    specs = goods.goodsspecification_set.order_by('id')
    # 若当前sku的规格信息不完整，则不再继续
    if len(sku_key) < len(specs):
        return
    for index, spec in enumerate(specs):
        # 复制当前sku的规格键
        key = sku_key[:]
        # 该规格的选项
        options = spec.specificationoption_set.all()
        for option in options:
            # 在规格参数sku字典中查找符合当前规格的sku
            key[index] = option.id
            option.sku_id = spec_sku_map.get(tuple(key))

        spec.options = options

    # 2. 调模板：detail.html，进行模板渲染
    context = {
        'categories': categories,
        'goods': goods,
        'specs': specs,
        'sku': sku
    }

    # 加载模板
    temp = loader.get_template('detail.html')

    # 模板渲染
    res_html = temp.render(context)

    # 3. 保存静态页面
    save_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'goods/%s.html' % sku_id)

    with open(save_path, 'w') as f:
        f.write(res_html)


if __name__ == "__main__":
    # 获取所有的商品
    skus = SKU.objects.all()

    for sku in skus:
        print(sku.id)
        generate_static_sku_detail_html(sku.id)
