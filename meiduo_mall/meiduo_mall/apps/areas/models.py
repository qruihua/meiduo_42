from django.db import models

# Create your models here.


class Area(models.Model):
    """地区模型类"""
    name = models.CharField(max_length=20, verbose_name='地区名称')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='subs', null=True, verbose_name='父级地区')

    def __str__(self):
        """返回地区的名称"""
        return self.name

    class Meta:
        db_table = 'tb_areas'
        verbose_name = '地区表'
        verbose_name_plural = verbose_name
