"""
Unit tests for cloud queue adapters.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.wildlife_pipeline.cloud.queue import (
    NoQueueAdapter, RedisQueueAdapter, SQSAdapter, PubSubAdapter, create_queue_adapter
)


class TestNoQueueAdapter:
    """Test no-op queue adapter."""
    
    def test_adapter_creation(self):
        """Test adapter creation."""
        adapter = NoQueueAdapter()
        assert adapter is not None
    
    def test_send_message(self):
        """Test send message (no-op)."""
        adapter = NoQueueAdapter()
        # Should not raise any exceptions
        adapter.send_message("test-queue", {"message": "test"})
    
    def test_receive_messages(self):
        """Test receive messages (returns empty list)."""
        adapter = NoQueueAdapter()
        messages = adapter.receive_messages("test-queue", max_messages=10)
        assert messages == []
    
    def test_delete_message(self):
        """Test delete message (no-op)."""
        adapter = NoQueueAdapter()
        # Should not raise any exceptions
        adapter.delete_message("test-queue", "message-id")


class TestRedisQueueAdapter:
    """Test Redis queue adapter."""
    
    def test_adapter_creation(self):
        """Test adapter creation."""
        with patch('src.wildlife_pipeline.cloud.queue.redis.Redis') as mock_redis:
            adapter = RedisQueueAdapter(host="localhost", port=6379, db=0)
            assert adapter is not None
            mock_redis.assert_called_once_with(host="localhost", port=6379, db=0, decode_responses=True)
    
    def test_adapter_creation_missing_redis(self):
        """Test adapter creation when redis is not available."""
        with patch('src.wildlife_pipeline.cloud.queue.redis', None):
            with pytest.raises(ImportError, match="redis package required"):
                RedisQueueAdapter()
    
    @patch('src.wildlife_pipeline.cloud.queue.redis.Redis')
    def test_send_message(self, mock_redis):
        """Test send message."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        
        adapter = RedisQueueAdapter()
        message = {"test": "data"}
        
        adapter.send_message("test-queue", message)
        
        # Verify redis was called
        mock_redis_instance.lpush.assert_called_once_with("test-queue", json.dumps(message))
    
    @patch('src.wildlife_pipeline.cloud.queue.redis.Redis')
    def test_receive_messages(self, mock_redis):
        """Test receive messages."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        
        # Mock brpop to return messages
        mock_redis_instance.brpop.side_effect = [
            ("test-queue", json.dumps({"message": "1"})),
            ("test-queue", json.dumps({"message": "2"})),
            None  # No more messages
        ]
        
        adapter = RedisQueueAdapter()
        messages = adapter.receive_messages("test-queue", max_messages=10)
        
        # Verify messages were received
        assert len(messages) == 2
        assert messages[0]["message"] == "1"
        assert messages[1]["message"] == "2"
    
    @patch('src.wildlife_pipeline.cloud.queue.redis.Redis')
    def test_delete_message(self, mock_redis):
        """Test delete message (no-op for Redis)."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        
        adapter = RedisQueueAdapter()
        adapter.delete_message("test-queue", "message-id")
        
        # Redis doesn't need explicit deletion, so no calls should be made
        mock_redis_instance.assert_not_called()


class TestSQSAdapter:
    """Test SQS queue adapter."""
    
    def test_adapter_creation(self):
        """Test adapter creation."""
        with patch('src.wildlife_pipeline.cloud.queue.boto3.client') as mock_boto3:
            adapter = SQSAdapter(region="eu-north-1")
            assert adapter is not None
            mock_boto3.assert_called_once_with('sqs', region_name="eu-north-1")
    
    def test_adapter_creation_missing_boto3(self):
        """Test adapter creation when boto3 is not available."""
        with patch('src.wildlife_pipeline.cloud.queue.boto3', None):
            with pytest.raises(ImportError, match="boto3 package required"):
                SQSAdapter()
    
    @patch('src.wildlife_pipeline.cloud.queue.boto3.client')
    def test_send_message(self, mock_boto3):
        """Test send message."""
        mock_sqs = MagicMock()
        mock_boto3.return_value = mock_sqs
        
        adapter = SQSAdapter()
        message = {"test": "data"}
        
        adapter.send_message("test-queue", message)
        
        # Verify SQS was called
        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args
        assert call_args[1]['MessageBody'] == json.dumps(message)
    
    @patch('src.wildlife_pipeline.cloud.queue.boto3.client')
    def test_send_message_error(self, mock_boto3):
        """Test send message with error."""
        mock_sqs = MagicMock()
        mock_sqs.send_message.side_effect = Exception("SQS error")
        mock_boto3.return_value = mock_sqs
        
        adapter = SQSAdapter()
        message = {"test": "data"}
        
        # Should not raise exception, just print error
        adapter.send_message("test-queue", message)
    
    @patch('src.wildlife_pipeline.cloud.queue.boto3.client')
    def test_receive_messages(self, mock_boto3):
        """Test receive messages."""
        mock_sqs = MagicMock()
        mock_boto3.return_value = mock_sqs
        
        # Mock SQS response
        mock_sqs.get_queue_url.return_value = {'QueueUrl': 'https://sqs.eu-north-1.amazonaws.com/123456789012/test-queue'}
        mock_sqs.receive_message.return_value = {
            'Messages': [
                {
                    'Body': json.dumps({"message": "1"}),
                    'ReceiptHandle': 'receipt-handle-1'
                },
                {
                    'Body': json.dumps({"message": "2"}),
                    'ReceiptHandle': 'receipt-handle-2'
                }
            ]
        }
        
        adapter = SQSAdapter()
        messages = adapter.receive_messages("test-queue", max_messages=10)
        
        # Verify messages were received
        assert len(messages) == 2
        assert messages[0]["message"] == "1"
        assert messages[0]["_sqs_receipt_handle"] == "receipt-handle-1"
        assert messages[1]["message"] == "2"
        assert messages[1]["_sqs_receipt_handle"] == "receipt-handle-2"
    
    @patch('src.wildlife_pipeline.cloud.queue.boto3.client')
    def test_receive_messages_error(self, mock_boto3):
        """Test receive messages with error."""
        mock_sqs = MagicMock()
        mock_sqs.get_queue_url.side_effect = Exception("SQS error")
        mock_boto3.return_value = mock_sqs
        
        adapter = SQSAdapter()
        messages = adapter.receive_messages("test-queue", max_messages=10)
        
        # Should return empty list on error
        assert messages == []
    
    @patch('src.wildlife_pipeline.cloud.queue.boto3.client')
    def test_delete_message(self, mock_boto3):
        """Test delete message."""
        mock_sqs = MagicMock()
        mock_boto3.return_value = mock_sqs
        
        adapter = SQSAdapter()
        adapter.delete_message("test-queue", "receipt-handle")
        
        # Verify SQS was called
        mock_sqs.delete_message.assert_called_once()
        call_args = mock_sqs.delete_message.call_args
        assert call_args[1]['ReceiptHandle'] == "receipt-handle"
    
    @patch('src.wildlife_pipeline.cloud.queue.boto3.client')
    def test_delete_message_error(self, mock_boto3):
        """Test delete message with error."""
        mock_sqs = MagicMock()
        mock_sqs.delete_message.side_effect = Exception("SQS error")
        mock_boto3.return_value = mock_sqs
        
        adapter = SQSAdapter()
        # Should not raise exception, just print error
        adapter.delete_message("test-queue", "receipt-handle")


class TestPubSubAdapter:
    """Test Google Cloud Pub/Sub adapter."""
    
    def test_adapter_creation(self):
        """Test adapter creation."""
        with patch('src.wildlife_pipeline.cloud.queue.pubsub_v1') as mock_pubsub:
            adapter = PubSubAdapter(project_id="test-project")
            assert adapter is not None
            assert adapter.project_id == "test-project"
    
    def test_adapter_creation_missing_pubsub(self):
        """Test adapter creation when pubsub is not available."""
        with patch('src.wildlife_pipeline.cloud.queue.pubsub_v1', None):
            with pytest.raises(ImportError, match="google-cloud-pubsub package required"):
                PubSubAdapter(project_id="test-project")
    
    @patch('src.wildlife_pipeline.cloud.queue.pubsub_v1')
    def test_send_message(self, mock_pubsub):
        """Test send message."""
        mock_publisher = MagicMock()
        mock_pubsub.PublisherClient.return_value = mock_publisher
        
        adapter = PubSubAdapter(project_id="test-project")
        message = {"test": "data"}
        
        adapter.send_message("test-topic", message)
        
        # Verify publisher was called
        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args[0][0] == "projects/test-project/topics/test-topic"
        assert call_args[0][1] == json.dumps(message).encode('utf-8')
    
    @patch('src.wildlife_pipeline.cloud.queue.pubsub_v1')
    def test_send_message_error(self, mock_pubsub):
        """Test send message with error."""
        mock_publisher = MagicMock()
        mock_publisher.publish.side_effect = Exception("Pub/Sub error")
        mock_pubsub.PublisherClient.return_value = mock_publisher
        
        adapter = PubSubAdapter(project_id="test-project")
        message = {"test": "data"}
        
        # Should not raise exception, just print error
        adapter.send_message("test-topic", message)
    
    @patch('src.wildlife_pipeline.cloud.queue.pubsub_v1')
    def test_receive_messages(self, mock_pubsub):
        """Test receive messages."""
        mock_subscriber = MagicMock()
        mock_pubsub.SubscriberClient.return_value = mock_subscriber
        
        # Mock subscription path
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-topic-sub"
        
        # Mock pull response
        mock_response = MagicMock()
        mock_response.received_messages = [
            MagicMock(
                message=MagicMock(data=json.dumps({"message": "1"}).encode('utf-8')),
                ack_id="ack-1"
            ),
            MagicMock(
                message=MagicMock(data=json.dumps({"message": "2"}).encode('utf-8')),
                ack_id="ack-2"
            )
        ]
        mock_subscriber.pull.return_value = mock_response
        
        adapter = PubSubAdapter(project_id="test-project")
        messages = adapter.receive_messages("test-topic", max_messages=10)
        
        # Verify messages were received
        assert len(messages) == 2
        assert messages[0]["message"] == "1"
        assert messages[0]["_pubsub_ack_id"] == "ack-1"
        assert messages[1]["message"] == "2"
        assert messages[1]["_pubsub_ack_id"] == "ack-2"
    
    @patch('src.wildlife_pipeline.cloud.queue.pubsub_v1')
    def test_receive_messages_error(self, mock_pubsub):
        """Test receive messages with error."""
        mock_subscriber = MagicMock()
        mock_subscriber.pull.side_effect = Exception("Pub/Sub error")
        mock_pubsub.SubscriberClient.return_value = mock_subscriber
        
        adapter = PubSubAdapter(project_id="test-project")
        messages = adapter.receive_messages("test-topic", max_messages=10)
        
        # Should return empty list on error
        assert messages == []
    
    @patch('src.wildlife_pipeline.cloud.queue.pubsub_v1')
    def test_delete_message(self, mock_pubsub):
        """Test delete message (no-op for Pub/Sub)."""
        mock_subscriber = MagicMock()
        mock_pubsub.SubscriberClient.return_value = mock_subscriber
        
        adapter = PubSubAdapter(project_id="test-project")
        adapter.delete_message("test-topic", "ack-id")
        
        # Pub/Sub handles deletion via ack, so no explicit calls needed
        mock_subscriber.assert_not_called()


class TestCreateQueueAdapter:
    """Test queue adapter factory function."""
    
    def test_create_no_queue_adapter(self):
        """Test creating no queue adapter."""
        adapter = create_queue_adapter("none")
        assert isinstance(adapter, NoQueueAdapter)
    
    def test_create_redis_adapter(self):
        """Test creating Redis adapter."""
        with patch('src.wildlife_pipeline.cloud.queue.redis.Redis'):
            adapter = create_queue_adapter("redis", host="localhost", port=6379, db=0)
            assert isinstance(adapter, RedisQueueAdapter)
    
    def test_create_sqs_adapter(self):
        """Test creating SQS adapter."""
        with patch('src.wildlife_pipeline.cloud.queue.boto3.client'):
            adapter = create_queue_adapter("sqs", region="eu-north-1")
            assert isinstance(adapter, SQSAdapter)
    
    def test_create_pubsub_adapter(self):
        """Test creating Pub/Sub adapter."""
        with patch('src.wildlife_pipeline.cloud.queue.pubsub_v1'):
            adapter = create_queue_adapter("pubsub", project_id="test-project")
            assert isinstance(adapter, PubSubAdapter)
    
    def test_create_invalid_adapter(self):
        """Test creating invalid adapter."""
        with pytest.raises(ValueError, match="Unknown queue adapter type"):
            create_queue_adapter("invalid")


class TestQueueAdapterIntegration:
    """Test queue adapter integration."""
    
    def test_no_queue_adapter_integration(self):
        """Test no queue adapter integration."""
        adapter = NoQueueAdapter()
        
        # Test complete workflow
        queue_name = "test-queue"
        message = {"test": "data"}
        
        # Send message
        adapter.send_message(queue_name, message)
        
        # Receive messages (should be empty)
        messages = adapter.receive_messages(queue_name, max_messages=10)
        assert messages == []
        
        # Delete message (no-op)
        adapter.delete_message(queue_name, "message-id")
    
    def test_queue_adapter_interface(self):
        """Test that all queue adapters implement the interface."""
        adapters = [
            NoQueueAdapter(),
        ]
        
        # Add mocked adapters
        with patch('src.wildlife_pipeline.cloud.queue.redis.Redis'):
            adapters.append(RedisQueueAdapter())
        
        with patch('src.wildlife_pipeline.cloud.queue.boto3.client'):
            adapters.append(SQSAdapter())
        
        with patch('src.wildlife_pipeline.cloud.queue.pubsub_v1'):
            adapters.append(PubSubAdapter(project_id="test"))
        
        for adapter in adapters:
            # Test that all adapters have required methods
            assert hasattr(adapter, 'send_message')
            assert hasattr(adapter, 'receive_messages')
            assert hasattr(adapter, 'delete_message')
            
            # Test that methods are callable
            assert callable(adapter.send_message)
            assert callable(adapter.receive_messages)
            assert callable(adapter.delete_message)


if __name__ == '__main__':
    pytest.main([__file__])
