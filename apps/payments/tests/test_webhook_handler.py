"""
Tests for the WebhookHandler class.

Tests the comprehensive webhook handling including:
- IP whitelisting
- Signature verification
- Logging
- Error handling
"""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory

from apps.payments.webhooks.handler import WebhookHandler
from apps.payments.models import WebhookLog


class WebhookHandlerIPWhitelistTests(TestCase):
    """Test IP whitelisting functionality."""
    
    def setUp(self):
        self.handler = WebhookHandler()
    
    def test_verify_ip_rukassa_valid_single_ip(self):
        """Test that a single whitelisted IP is accepted."""
        # RUkassa whitelist includes 185.71.76.0/27
        result = self.handler._verify_ip("185.71.76.5", "rukassa")
        self.assertTrue(result)
    
    def test_verify_ip_rukassa_invalid_ip(self):
        """Test that a non-whitelisted IP is rejected."""
        result = self.handler._verify_ip("192.168.1.1", "rukassa")
        self.assertFalse(result)
    
    def test_verify_ip_nowpayments_valid_ip(self):
        """Test NOWpayments whitelisted IP."""
        result = self.handler._verify_ip("18.209.98.55", "nowpayments")
        self.assertTrue(result)
    
    def test_verify_ip_nowpayments_invalid_ip(self):
        """Test NOWpayments non-whitelisted IP."""
        result = self.handler._verify_ip("10.0.0.1", "nowpayments")
        self.assertFalse(result)
    
    def test_verify_ip_no_whitelist_configured(self):
        """Test that unknown providers with no whitelist allow all IPs."""
        result = self.handler._verify_ip("1.2.3.4", "unknown_provider")
        self.assertTrue(result)


class WebhookHandlerSignatureExtractionTests(TestCase):
    """Test signature extraction from headers and payload."""
    
    def setUp(self):
        self.handler = WebhookHandler()
    
    def test_extract_signature_rukassa(self):
        """Test RUkassa signature extraction from payload."""
        payload = {"sign": "abc123def456"}
        headers = {}
        signature = self.handler._extract_signature(headers, payload, "rukassa")
        self.assertEqual(signature, "abc123def456")
    
    def test_extract_signature_nowpayments(self):
        """Test NOWpayments signature extraction from headers."""
        payload = {}
        headers = {"X-Nowpayments-Sig": "xyz789"}
        signature = self.handler._extract_signature(headers, payload, "nowpayments")
        self.assertEqual(signature, "xyz789")
    
    def test_extract_signature_nowpayments_lowercase_header(self):
        """Test NOWpayments signature with lowercase header."""
        payload = {}
        headers = {"x-nowpayments-sig": "xyz789"}
        signature = self.handler._extract_signature(headers, payload, "nowpayments")
        self.assertEqual(signature, "xyz789")


class WebhookHandlerClientIPTests(TestCase):
    """Test client IP extraction."""
    
    def setUp(self):
        self.handler = WebhookHandler()
        self.factory = RequestFactory()
    
    def test_get_client_ip_direct(self):
        """Test getting IP from REMOTE_ADDR."""
        request = self.factory.post('/webhook/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        ip = self.handler._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')
    
    def test_get_client_ip_forwarded(self):
        """Test getting IP from X-Forwarded-For header."""
        request = self.factory.post('/webhook/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 198.51.100.1'
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        ip = self.handler._get_client_ip(request)
        # Should return the first IP in X-Forwarded-For
        self.assertEqual(ip, '203.0.113.1')


class WebhookHandlerLoggingTests(TestCase):
    """Test webhook logging functionality."""
    
    fixtures = ["payments_providers_methods.json"]
    
    def setUp(self):
        self.handler = WebhookHandler()
        self.factory = RequestFactory()
    
    def test_webhook_creates_log_entry(self):
        """Test that webhook processing creates a WebhookLog entry."""
        initial_count = WebhookLog.objects.count()
        
        request = self.factory.post(
            '/webhook/',
            data=json.dumps({"order_id": "DEP-123", "sign": "invalid"}),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '185.71.76.5'
        
        response = self.handler.handle_deposit_webhook(request, "rukassa")
        
        # Should create a log entry even for invalid signature
        self.assertEqual(WebhookLog.objects.count(), initial_count + 1)
        
        log = WebhookLog.objects.latest('created_at')
        self.assertEqual(log.provider, "rukassa")
        self.assertEqual(log.event_type, "deposit")
        self.assertEqual(log.ip_address, "185.71.76.5")
    
    def test_webhook_logs_processing_time(self):
        """Test that webhook logs include processing time."""
        request = self.factory.post(
            '/webhook/',
            data=json.dumps({"order_id": "DEP-123", "sign": "invalid"}),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '185.71.76.5'
        
        response = self.handler.handle_deposit_webhook(request, "rukassa")
        
        log = WebhookLog.objects.latest('created_at')
        self.assertIsNotNone(log.processing_time_ms)
        self.assertGreater(log.processing_time_ms, 0)


class WebhookHandlerErrorHandlingTests(TestCase):
    """Test error handling in webhook processing."""
    
    fixtures = ["payments_providers_methods.json"]
    
    def setUp(self):
        self.handler = WebhookHandler()
        self.factory = RequestFactory()
    
    def test_invalid_json_returns_400(self):
        """Test that invalid JSON returns 400 Bad Request."""
        request = self.factory.post(
            '/webhook/',
            data='invalid json{',
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '185.71.76.5'
        
        response = self.handler.handle_deposit_webhook(request, "rukassa")
        self.assertEqual(response.status_code, 400)
    
    def test_non_whitelisted_ip_returns_403(self):
        """Test that non-whitelisted IP returns 403 Forbidden."""
        request = self.factory.post(
            '/webhook/',
            data=json.dumps({"order_id": "DEP-123"}),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '192.168.1.1'  # Not whitelisted
        
        response = self.handler.handle_deposit_webhook(request, "rukassa")
        self.assertEqual(response.status_code, 403)
        
        # Check log entry
        log = WebhookLog.objects.latest('created_at')
        self.assertEqual(log.processing_result, "ip_rejected")
        self.assertEqual(log.response_code, 403)
    
    def test_invalid_signature_returns_401(self):
        """Test that invalid signature returns 401 Unauthorized."""
        request = self.factory.post(
            '/webhook/',
            data=json.dumps({"order_id": "DEP-123", "sign": "invalid_signature"}),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '185.71.76.5'  # Whitelisted
        
        response = self.handler.handle_deposit_webhook(request, "rukassa")
        self.assertEqual(response.status_code, 401)
        
        # Check log entry
        log = WebhookLog.objects.latest('created_at')
        self.assertEqual(log.processing_result, "signature_invalid")
        self.assertEqual(log.response_code, 401)
        self.assertFalse(log.is_valid_signature)
    
    def test_unknown_provider_returns_404(self):
        """Test that unknown provider returns 404 Not Found."""
        request = self.factory.post(
            '/webhook/',
            data=json.dumps({"order_id": "DEP-123"}),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = self.handler.handle_deposit_webhook(request, "unknown_provider")
        self.assertEqual(response.status_code, 404)
        
        # Check log entry
        log = WebhookLog.objects.latest('created_at')
        self.assertEqual(log.processing_result, "provider_not_found")
        self.assertEqual(log.response_code, 404)
