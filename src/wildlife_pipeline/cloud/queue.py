"""
Queue adapters for event-driven processing.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import json
import time
from .interfaces import QueueAdapter


class NoQueueAdapter(QueueAdapter):
    """No-op queue adapter for batch processing."""
    
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> None:
        """No-op for batch processing."""
        pass
    
    def receive_messages(self, queue_name: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """No-op for batch processing."""
        return []
    
    def delete_message(self, queue_name: str, message_id: str) -> None:
        """No-op for batch processing."""
        pass


class RedisQueueAdapter(QueueAdapter):
    """Redis queue adapter for local event-driven processing."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        try:
            import redis
            self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        except ImportError:
            raise ImportError("redis package required for RedisQueueAdapter")
    
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> None:
        """Send message to Redis queue."""
        self.redis.lpush(queue_name, json.dumps(message))
    
    def receive_messages(self, queue_name: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Receive messages from Redis queue."""
        messages = []
        for _ in range(max_messages):
            result = self.redis.brpop(queue_name, timeout=1)
            if result:
                queue, message_data = result
                messages.append(json.loads(message_data))
            else:
                break
        return messages
    
    def delete_message(self, queue_name: str, message_id: str) -> None:
        """Delete message from Redis queue (Redis doesn't need explicit deletion)."""
        pass


class SQSAdapter(QueueAdapter):
    """AWS SQS queue adapter."""
    
    def __init__(self, region: str = "eu-north-1"):
        try:
            import boto3
            self.sqs = boto3.client('sqs', region_name=region)
        except ImportError:
            raise ImportError("boto3 package required for SQSAdapter")
        self.region = region
    
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> None:
        """Send message to SQS queue."""
        try:
            queue_url = self.sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
            self.sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
        except Exception as e:
            print(f"Error sending message to SQS: {e}")
    
    def receive_messages(self, queue_name: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Receive messages from SQS queue."""
        try:
            queue_url = self.sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=1
            )
            
            messages = []
            for msg in response.get('Messages', []):
                message_data = json.loads(msg['Body'])
                message_data['_sqs_receipt_handle'] = msg['ReceiptHandle']
                messages.append(message_data)
            
            return messages
        except Exception as e:
            print(f"Error receiving messages from SQS: {e}")
            return []
    
    def delete_message(self, queue_name: str, message_id: str) -> None:
        """Delete message from SQS queue."""
        try:
            queue_url = self.sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
            self.sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message_id
            )
        except Exception as e:
            print(f"Error deleting message from SQS: {e}")


class PubSubAdapter(QueueAdapter):
    """Google Cloud Pub/Sub queue adapter."""
    
    def __init__(self, project_id: str):
        try:
            from google.cloud import pubsub_v1
            self.publisher = pubsub_v1.PublisherClient()
            self.subscriber = pubsub_v1.SubscriberClient()
        except ImportError:
            raise ImportError("google-cloud-pubsub package required for PubSubAdapter")
        self.project_id = project_id
    
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> None:
        """Send message to Pub/Sub topic."""
        try:
            topic_path = self.publisher.topic_path(self.project_id, queue_name)
            self.publisher.publish(
                topic_path,
                json.dumps(message).encode('utf-8')
            )
        except Exception as e:
            print(f"Error sending message to Pub/Sub: {e}")
    
    def receive_messages(self, queue_name: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Receive messages from Pub/Sub subscription."""
        try:
            subscription_path = self.subscriber.subscription_path(self.project_id, f"{queue_name}-sub")
            
            messages = []
            def callback(message):
                try:
                    message_data = json.loads(message.data.decode('utf-8'))
                    message_data['_pubsub_ack_id'] = message.ack_id
                    messages.append(message_data)
                    message.ack()
                except Exception as e:
                    print(f"Error processing Pub/Sub message: {e}")
                    message.nack()
            
            # Pull messages synchronously
            response = self.subscriber.pull(
                request={"subscription": subscription_path, "max_messages": max_messages}
            )
            
            for message in response.received_messages:
                try:
                    message_data = json.loads(message.message.data.decode('utf-8'))
                    message_data['_pubsub_ack_id'] = message.ack_id
                    messages.append(message_data)
                except Exception as e:
                    print(f"Error processing Pub/Sub message: {e}")
            
            return messages
        except Exception as e:
            print(f"Error receiving messages from Pub/Sub: {e}")
            return []
    
    def delete_message(self, queue_name: str, message_id: str) -> None:
        """Delete message from Pub/Sub (handled by ack)."""
        pass


def create_queue_adapter(adapter_type: str, **kwargs) -> QueueAdapter:
    """Factory function to create queue adapters."""
    if adapter_type == "none":
        return NoQueueAdapter()
    elif adapter_type == "redis":
        return RedisQueueAdapter(**kwargs)
    elif adapter_type == "sqs":
        return SQSAdapter(**kwargs)
    elif adapter_type == "pubsub":
        return PubSubAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown queue adapter type: {adapter_type}")
