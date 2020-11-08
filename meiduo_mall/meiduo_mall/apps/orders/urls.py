from django.conf.urls import url
from orders import views

urlpatterns = [
    url(r'^orders/settlement/$', views.OrdersSettlementView.as_view()),
    # url(r'^orders/$', views.OrdersView.as_view()),
    url(r'^orders/(?P<order_id>\d+)/uncommentgoods/$', views.UncommentOrderGoodsView.as_view()),  # 未评论商品
    url(r'^orders/(?P<order_id>\d+)/comments/$', views.OrderCommentView.as_view()),  # 商品评论
]

from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register('orders', views.OrdersViewSet, base_name='orders')
urlpatterns += router.urls