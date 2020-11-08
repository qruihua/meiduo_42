# 封装任务函数
from celery_tasks.main import celery_app
from celery_tasks.sms.yuntongxun.sms import CCP

# 发送短信模板ID
SEND_SMS_TEMP_ID = 1

# 获取日志器
import logging
logger = logging.getLogger('django')


@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, sms_code, expires):
    """发送短信的任务函数"""
    try:
        res = CCP().send_template_sms(mobile, [sms_code, expires], SEND_SMS_TEMP_ID)
    except Exception:
        # 发送短信异常
        logger.error('发送短信异常：[mobile: %s] [sms_code_%s]' % (mobile, sms_code))
    else:
        if res != 0:
            # 发送短信失败
            logger.error('发送短信失败：[mobile: %s] [sms_code_%s]' % (mobile, sms_code))
        else:
            # 发送短信成功
            logger.info('发送短信成功：[mobile: %s] [sms_code_%s]' % (mobile, sms_code))

