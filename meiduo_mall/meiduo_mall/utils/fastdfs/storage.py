from django.core.files.storage import Storage, FileSystemStorage
from django.utils.deconstruct import deconstructible
from fdfs_client.client import Fdfs_client
from django.conf import settings


@deconstructible
class FDFSStorage(Storage):
    """FDFS文件存储类"""
    def __init__(self, client_conf=None, base_url=None):
        """
        client_conf: 客户端配置文件的路径
        base_url: FDFS nginx地址
        """
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF

        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_NGINX_URL

        self.base_url = base_url

    def _save(self, name, content):
        """
        name: 上传文件的名称 1.jpg
        content: 包含上传文件内容的File对象，可以通过content.read()获取上传文件的内容
        """
        # 创建Fdfs_client对象
        # client = Fdfs_client(settings.FDFS_CLIENT_CONF)
        client = Fdfs_client(self.client_conf)

        # 将文件上传到FDFS系统
        ret = client.upload_by_buffer(content.read())

        if ret.get('Status') != 'Upload successed.':
            # 上传文件失败
            raise Exception('上传文件到FDFS失败')

        # 获取文件id
        file_id = ret.get('Remote file_id')
        return file_id

    def exists(self, name):
        """
        此方法是在_save调用之前被调用，判断上传文件的名称和文件系统中原有的文件名是否冲突
        name: 上传文件的名称 1.jpg
        """
        return False

    def url(self, name):
        """
        返回可访问到文件存储系统中文件的完整的url地址:
        name: 数据表中image字段存储的内容
        """
        # return settings.FDFS_NGINX_URL + name
        return self.base_url + name
