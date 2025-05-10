import json
from typing import Dict, Any, Callable, Awaitable
import uuid
import aio_pika
from aio_pika import ExchangeType, Message, IncomingMessage

from app.core.config import settings
from app.core.logging import app_logger


class RabbitMQClient:
    """RabbitMQのクライアントクラス"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.user_events_exchange = None
        self.auth_events_exchange = None
        self.logger = app_logger
        self.is_initialized = False
        self.consumer_tags = []
    
    async def initialize(self):
        """RabbitMQへの接続を初期化"""
        if self.is_initialized:
            return
        
        try:
            # RabbitMQ接続文字列の構築
            rabbitmq_url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
            
            # 接続の確立
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            
            # チャネルの開設
            self.channel = await self.connection.channel()
            
            # exchangeの宣言
            self.user_events_exchange = await self.channel.declare_exchange(
                "user_events",
                ExchangeType.TOPIC,
                durable=True
            )
            
            self.auth_events_exchange = await self.channel.declare_exchange(
                "auth_events",
                ExchangeType.TOPIC,
                durable=True
            )
            
            self.is_initialized = True
            self.logger.info("RabbitMQ接続が確立されました")
        except Exception as e:
            self.logger.error(f"RabbitMQ接続エラー: {str(e)}", exc_info=True)
            raise
    
    async def close(self):
        """接続のクローズ"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self.is_initialized = False
            self.logger.info("RabbitMQ接続がクローズされました")
    
    async def publish_user_event(self, event_type: str, user_data: Dict[str, Any]):
        """ユーザーイベントの発行"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # メッセージのJSONシリアライズ
            message_body = {
                "event_type": event_type,
                "user_data": self._serialize_user_data(user_data)
            }
            
            # メッセージの発行
            await self.auth_events_exchange.publish(
                Message(
                    body=json.dumps(message_body).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="user.created"
            )
            
            self.logger.info(f"ユーザーイベントを発行しました: {event_type}, ユーザーID={user_data.get('id', 'unknown')}")
        except Exception as e:
            self.logger.error(f"メッセージ発行エラー: {str(e)}", exc_info=True)
            # エラーはログに記録するが例外は再送出しない
            # メッセージングがサービスの主要機能を妨げるべきではない
    
    async def setup_user_creation_consumer(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """ユーザー作成リクエストのコンシューマーをセットアップ"""
        if not self.is_initialized:
            await self.initialize()
        
        # キューの宣言
        queue = await self.channel.declare_queue(
            "user_creation_queue",
            durable=True
        )
        
        # exchangeとキューのバインド
        await queue.bind(
            exchange=self.user_events_exchange,
            routing_key="user.sync"
        )
        
        # コンシューマーの設定
        async def process_message(message: IncomingMessage):
            async with message.process():
                try:
                    # メッセージボディの解析
                    body = json.loads(message.body.decode())
                    
                    # イベントタイプの確認
                    event_type = body.get("event_type")
                    if event_type == "user.created":
                        user_data = body.get("user_data", {})
                        self.logger.info(f"ユーザー作成リクエストを受信: {user_data}")
                        
                        # コールバック関数の呼び出し
                        await callback(user_data)
                    else:
                        self.logger.warning(f"未知のイベントタイプ: {event_type}")
                
                except json.JSONDecodeError:
                    self.logger.error("JSONデコードエラー", exc_info=True)
                except Exception as e:
                    self.logger.error(f"メッセージ処理エラー: {str(e)}", exc_info=True)
        
        # コンシューマーの開始
        consumer_tag = await queue.consume(process_message)
        self.consumer_tags.append(consumer_tag)
        self.logger.info("ユーザー作成リクエストのコンシューマーを開始しました")
    
    def _serialize_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """ユーザーデータのシリアライズ"""
        serialized = {}
        for key, value in user_data.items():
            if isinstance(value, uuid.UUID):
                serialized[key] = str(value)
            else:
                serialized[key] = value
        return serialized


# シングルトンインスタンス
rabbitmq_client = RabbitMQClient()


# ユーザーイベントタイプの定義
class UserEventTypes:
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"


# ヘルパー関数
async def publish_user_created(user_data: Dict[str, Any]):
    """ユーザー作成イベントの発行"""
    await rabbitmq_client.publish_user_event(UserEventTypes.USER_CREATED, user_data)


async def publish_user_updated(user_data: Dict[str, Any]):
    """ユーザー更新イベントの発行"""
    await rabbitmq_client.publish_user_event(UserEventTypes.USER_UPDATED, user_data)


async def publish_user_deleted(user_data: Dict[str, Any]):
    """ユーザー削除イベントの発行"""
    await rabbitmq_client.publish_user_event(UserEventTypes.USER_DELETED, user_data)
