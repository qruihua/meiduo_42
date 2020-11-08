from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from areas.models import Area
from areas.serializers import AreaSerializer, SubAreaSerializer


class AreasViewSet(CacheResponseMixin, ReadOnlyModelViewSet):
    """地区视图集"""
    # 关闭分页
    pagination_class = None

    def get_serializer_class(self):
        """根据不同的操作返回不同的序列化器类"""
        if self.action == 'list':
            return AreaSerializer
        else:
            return SubAreaSerializer

    def get_queryset(self):
        """根据不同的操作返回不同的查询集"""
        if self.action == 'list':
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()


# GET /areas/
class AreasView(ListAPIView):
    serializer_class = AreaSerializer
    # 指定当前视图所使用的查询集
    queryset = Area.objects.filter(parent=None)

    # def get(self, request):
    #     """
    #     获取所有省级地区的信息：
    #     1. 查询出所有省级地区的数据
    #     2. 将省级地区的数据序列化并返回
    #     """
    #     # 1. 查询出所有省级地区的数据
    #     areas = self.get_queryset()  # QuerySet
    #
    #     # 2. 将省级地区的数据序列化并返回
    #     serializer = self.get_serializer(areas, many=True)
    #     return Response(serializer.data)


# GET /areas/(?P<pk>\d+)/
class SubAreasView(RetrieveAPIView):
    serializer_class = SubAreaSerializer
    queryset = Area.objects.all()

    # def get(self, request, pk):
    #     """
    #     获取指定地区的数据(关联对象嵌套序列化操作):
    #     1. 根据pk获取指定地区数据
    #     2. 将指定地区的数据序列化并返回(地区下级地区进行嵌套序列化)
    #     """
    #     # 1. 根据pk获取指定地区数据
    #     area = self.get_object()
    #
    #     # 2. 将指定地区的数据序列化并返回(地区下级地区进行嵌套序列化)
    #     serializer = self.get_serializer(area)
    #     return Response(serializer.data)
