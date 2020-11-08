from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_haystack.viewsets import HaystackViewSet

from goods.models import SKU, GoodsCategory, GoodsChannel
from goods.serializers import SKUSerializer, SKUIndexSerializer


# GET /categories/(?P<category_id>\d+)/
class BreadCrumbView(APIView):
    def get(self, request, category_id):
        # 获取对应的三级分类数据
        cat3 = GoodsCategory.objects.get(id=category_id)
        cat2 = cat3.parent
        cat1 = GoodsChannel.objects.get(id=cat2.parent_id)

        # 组织相应数据
        response_data = {
            'cat1': {
                'name': cat1.category.name,
                'url': cat1.url
            },
            'cat2': {
                'name': cat2.name
            },
            'cat3': {
                'name': cat3.name
            }
        }

        return Response(response_data)


# GET /categories/(?P<category_id>\d+)/skus/
class SKUListView(ListAPIView):
    # 指定视图所使用的序列化器类
    serializer_class = SKUSerializer
    # 指定视图所使用的查询集
    # queryset = SKU.objects.filter(category_id=category_id, is_launched=True)

    def get_queryset(self):
        """返回视图所使用的查询集"""
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True)

    # 设置排序
    filter_backends = [OrderingFilter]
    # 设置排序字段
    ordering_fields = ('update_time', 'price', 'sales')

    # def get(self, request, category_id):
    #     """
    #     self.kwargs: 字典，保存从url地址中提取的所有命名参数
    #     获取分类SKU商品的数据:
    #     1. 根据`category_id`获取分类SKU商品的数据
    #     2. 将商品的数据序列化并返回
    #     """
    #     # 1. 根据`category_id`获取分类SKU商品的数据
    #     # skus = SKU.objects.filter(category_id=category_id, is_launched=True)
    #     skus = self.get_queryset()
    #
    #     # 2. 将商品的数据序列化并返回
    #     serializer = self.get_serializer(skus, many=True)
    #     return Response(serializer.data)


# GET /skus/search/?text=<搜索关键字>
class SKUSearchViewSet(HaystackViewSet):
    # 指定索引类对应的模型类
    index_models = [SKU]

    # 指定搜索结果序列化器采用的序列化器类
    # haystack搜索出中每个结果对象中都包含两个属性
    # text: 索引字段的内容
    # object: 搜索出的模型对象(sku模型对象)
    serializer_class = SKUIndexSerializer


# GET /skus/hot/
class SKUHotView(ListAPIView):
    queryset = SKU.objects.order_by('sales')[:2]
    serializer_class = SKUSerializer

    # 关闭分页
    pagination_class = None