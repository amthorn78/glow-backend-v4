#!/usr/bin/env python3
"""Unit tests for backend.hd_config module"""
import os
import unittest
from unittest.mock import patch
from backend.hd_config import get_hd_config, REQUIRED, OPTIONAL


class TestHDConfig(unittest.TestCase):
    """Test HD configuration environment loader"""

    def test_all_vars_set(self):
        """Test when all environment variables are set"""
        with patch.dict(os.environ, {
            'HD_API_KEY': 'test_api_key',
            'HD_GEOCODE_KEY': 'test_geocode_key',
            'HD_SERVICE_TOKEN': 'test_service_token'
        }):
            result = get_hd_config(check_optional=True)
            self.assertEqual(result['status'], 'OK (hd_config)')
            self.assertEqual(result['vars']['HD_API_KEY'], 'set')
            self.assertEqual(result['vars']['HD_GEOCODE_KEY'], 'set')
            self.assertEqual(result['vars']['HD_SERVICE_TOKEN'], 'set')

    def test_required_vars_missing(self):
        """Test when required environment variables are missing"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_hd_config(check_optional=True)
            expected_status = 'OK (hd_config WARN: missing=HD_API_KEY,HD_GEOCODE_KEY)'
            self.assertEqual(result['status'], expected_status)
            self.assertEqual(result['vars']['HD_API_KEY'], 'unset')
            self.assertEqual(result['vars']['HD_GEOCODE_KEY'], 'unset')
            self.assertEqual(result['vars']['HD_SERVICE_TOKEN'], 'unset')

    def test_partial_vars_set(self):
        """Test when only some variables are set"""
        with patch.dict(os.environ, {'HD_API_KEY': 'test_key'}, clear=True):
            result = get_hd_config(check_optional=True)
            expected_status = 'OK (hd_config WARN: missing=HD_GEOCODE_KEY)'
            self.assertEqual(result['status'], expected_status)
            self.assertEqual(result['vars']['HD_API_KEY'], 'set')
            self.assertEqual(result['vars']['HD_GEOCODE_KEY'], 'unset')

    def test_empty_string_treated_as_unset(self):
        """Test that empty string environment variables are treated as unset"""
        with patch.dict(os.environ, {
            'HD_API_KEY': '',
            'HD_GEOCODE_KEY': 'valid_key'
        }, clear=True):
            result = get_hd_config(check_optional=True)
            expected_status = 'OK (hd_config WARN: missing=HD_API_KEY)'
            self.assertEqual(result['status'], expected_status)
            self.assertEqual(result['vars']['HD_API_KEY'], 'unset')
            self.assertEqual(result['vars']['HD_GEOCODE_KEY'], 'set')

    def test_no_secret_values_exposed(self):
        """Test that actual secret values are never returned"""
        with patch.dict(os.environ, {
            'HD_API_KEY': 'super_secret_key_123',
            'HD_GEOCODE_KEY': 'another_secret_456'
        }):
            result = get_hd_config(check_optional=True)
            # Ensure no actual secret values are in the result
            result_str = str(result)
            self.assertNotIn('super_secret_key_123', result_str)
            self.assertNotIn('another_secret_456', result_str)
            # Only 'set' or 'unset' should be present
            for var_status in result['vars'].values():
                self.assertIn(var_status, ['set', 'unset'])

    def test_deterministic_key_ordering(self):
        """Test that keys are returned in deterministic order for stable artifacts"""
        with patch.dict(os.environ, {
            'HD_SERVICE_TOKEN': 'token',
            'HD_API_KEY': 'api_key',
            'HD_GEOCODE_KEY': 'geocode_key'
        }):
            result = get_hd_config(check_optional=True)
            keys = list(result['vars'].keys())
            # Keys should be in the order they appear in REQUIRED + OPTIONAL tuples
            expected_keys = ['HD_API_KEY', 'HD_GEOCODE_KEY', 'HD_SERVICE_TOKEN']
            self.assertEqual(keys, expected_keys)


if __name__ == '__main__':
    unittest.main()
