#返回地圖功能寫在app.py

from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *

def Confirm_Template():

    message = TemplateSendMessage(
        alt_text='早安',
        template=ConfirmTemplate(
            text="是否使用",
            actions=[
                PostbackTemplateAction(
                    label="是",
                    text="是",
                    data="使用"
                ),
                MessageTemplateAction(
                    label="查詢其他功能",
                    text="查詢其他功能"
                )
            ]
        )
    )
    return message
