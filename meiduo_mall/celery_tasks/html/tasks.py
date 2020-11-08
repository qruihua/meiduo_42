# 封装生成静态详情页面和列表页面的任务函数
import os

from django.conf import settings
from django.template import loader

from goods.models import SKU
from goods.utils import get_categories

from celery_tasks.main import celery_app


@celery_app.task(name='generate_static_sku_detail_html')
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


@celery_app.task(name='generate_static_sku_list_html')
def generate_static_sku_list_html():
    """生成商品的静态列表页面"""
    # 1. 查数据
    # 商品分类菜单
    categories = get_categories()

    # 2. 调模板：list.html，进行模板渲染
    context = {
        'categories': categories,
    }

    # 加载模板
    temp = loader.get_template('list.html')

    # 模板渲染
    res_html = temp.render(context)

    # 3. 保存静态页面
    save_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'list.html')

    with open(save_path, 'w') as f:
        f.write(res_html)


@celery_app.task(name='generate_static_sku_search_html')
def generate_static_sku_search_html():
    """生成商品的搜索结果静态页面"""
    # 1. 查数据
    # 商品分类菜单
    categories = get_categories()

    # 2. 调模板：search.html，进行模板渲染
    context = {
        'categories': categories,
    }

    # 加载模板
    temp = loader.get_template('search.html')

    # 模板渲染
    res_html = temp.render(context)

    # 3. 保存静态页面
    save_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'search.html')

    with open(save_path, 'w') as f:
        f.write(res_html)