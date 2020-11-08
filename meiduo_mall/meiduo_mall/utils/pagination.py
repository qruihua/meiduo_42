from rest_framework.pagination import PageNumberPagination


# ?page=<页码>&page_size=<页容量>
class StandardResultPagination(PageNumberPagination):
    # 默认页容量
    page_size = 6
    # 最大页容量
    max_page_size = 20
    # 获取分页数据时，指定页容量参数的名称
    page_size_query_param = 'page_size'
