from celery import Celery

# 设置Django运行所需的环境变量
import os
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")

# 1. 创建Celery类的对象
celery_app = Celery('celery_tasks')

# 2. 加载配置
celery_app.config_from_object('celery_tasks.config')

# 3. 让celery worker在启动时自动加载任务函数
celery_app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email', 'celery_tasks.html'])