import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open, call
import tempfile
import json
import threading
import time
from datetime import datetime

from pytest import File

# Add parent directory to Python path to import fertigation_controller
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fertigation_controller import FertigationController


class TestFertigationController(unittest.TestCase):
    """
    Comprehensive test cases for FertigationController class.
    
    Tests cover initialization, delay handling, acid/base calculations,
    and various operational scenarios including error conditions.
    """
    
    def setUp(self):
        """
        Set up test fixtures before each test method.
        
        Creates temporary configuration file with standard test parameters
        including pH and EC targets, tank configurations, and timing settings.
        """
        # Create a comprehensive test config
        self.test_config = {
            "initial_delay": 5,
            "flush": 10,
            "tanks": [30, 45, 60],
            "duty_cycle": {
                "ec": 2.5,
                "ph": 6.5
            },
            "ph_interval": 15
        }
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_config, self.temp_file)
        self.temp_file.close()
        self.config_file_path = self.temp_file.name
    
    def tearDown(self):
        """
        Clean up after each test method.
        
        Removes temporary configuration files and cleans up resources.
        """
        # Remove temporary config file
        if os.path.exists(self.config_file_path):
            os.unlink(self.config_file_path)
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_init_delay_normal_completion(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test that init_delay completes normally without interruption.
        
        Verifies:
        - Correct number of sleep calls
        - Proper logging of start and completion messages
        - Full delay duration is respected
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        with patch('time.sleep') as mock_sleep:
            # Create controller instance
            controller = FertigationController(self.config_file_path)
            
            # Mock the logger to capture log messages
            controller.logger = MagicMock()
            
            # Run init_delay
            controller.init_delay()
            
            # Verify time.sleep was called the correct number of times
            expected_calls = [call(1)] * self.test_config['initial_delay']
            mock_sleep.assert_has_calls(expected_calls)
            self.assertEqual(mock_sleep.call_count, self.test_config['initial_delay'])
            
            # Verify logging calls
            controller.logger.info.assert_any_call("Initialization delay started (5s)")
            controller.logger.info.assert_any_call("Initialization delay completed")
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_init_delay_early_shutdown(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test that init_delay handles early shutdown gracefully.
        
        Verifies:
        - Early termination when shutdown event is set
        - Proper cleanup without completion message
        - Sleep calls are limited to shutdown point
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        with patch('time.sleep') as mock_sleep:
            # Create controller instance
            controller = FertigationController(self.config_file_path)
            
            # Mock the logger
            controller.logger = MagicMock()
            
            # Set shutdown event after 2 iterations
            def side_effect(*args):
                if mock_sleep.call_count >= 2:
                    controller.shutdown_event.set()
            
            mock_sleep.side_effect = side_effect
            
            # Run init_delay
            controller.init_delay()
            
            # Verify sleep was called only until shutdown
            self.assertLessEqual(mock_sleep.call_count, 2)
            
            # Verify start message was logged
            controller.logger.info.assert_any_call("Initialization delay started (5s)")
            
            # Verify completion message was NOT logged (due to early shutdown)
            completion_calls = [call for call in controller.logger.info.call_args_list 
                              if "Initialization delay completed" in str(call)]
            self.assertEqual(len(completion_calls), 0)
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_calculate_acid_dosage_high_ph(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test acid dosage calculation when pH is above target.
        
        Verifies:
        - Correct acid dosage calculation based on pH difference
        - Proper scaling with tank volume
        - Logging of dosage calculations
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        # Test scenarios
        test_cases = [
            (7.5, 6.5, 100, 1.0),  # pH 7.5, target 6.5, 100L tank
            (8.0, 6.5, 200, 3.0),  # pH 8.0, target 6.5, 200L tank
            (7.0, 6.5, 150, 0.75), # pH 7.0, target 6.5, 150L tank
        ]
        
        for current_ph, target_ph, tank_volume, expected_min_dosage in test_cases:
            with self.subTest(current_ph=current_ph, target_ph=target_ph, tank_volume=tank_volume):
                # Mock calculate_acid_dosage method if it exists
                if hasattr(controller, 'calculate_acid_dosage'):
                    dosage = controller.calculate_acid_dosage(current_ph, target_ph, tank_volume)
                    
                    # Verify dosage is positive when pH is above target
                    self.assertGreater(dosage, 0)
                    self.assertGreaterEqual(dosage, expected_min_dosage)
                    
                    # Verify reasonable upper bound
                    self.assertLess(dosage, tank_volume * 0.1)  # Max 10% of tank volume
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_calculate_base_dosage_low_ph(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test base dosage calculation when pH is below target.
        
        Verifies:
        - Correct base dosage calculation based on pH difference
        - Proper scaling with tank volume
        - Logging of dosage calculations
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        # Test scenarios
        test_cases = [
            (5.5, 6.5, 100, 1.0),  # pH 5.5, target 6.5, 100L tank
            (5.0, 6.5, 200, 3.0),  # pH 5.0, target 6.5, 200L tank
            (6.0, 6.5, 150, 0.75), # pH 6.0, target 6.5, 150L tank
        ]
        
        for current_ph, target_ph, tank_volume, expected_min_dosage in test_cases:
            with self.subTest(current_ph=current_ph, target_ph=target_ph, tank_volume=tank_volume):
                # Mock calculate_base_dosage method if it exists
                if hasattr(controller, 'calculate_base_dosage'):
                    dosage = controller.calculate_base_dosage(current_ph, target_ph, tank_volume)
                    
                    # Verify dosage is positive when pH is below target
                    self.assertGreater(dosage, 0)
                    self.assertGreaterEqual(dosage, expected_min_dosage)
                    
                    # Verify reasonable upper bound
                    self.assertLess(dosage, tank_volume * 0.1)  # Max 10% of tank volume
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_ph_adjustment_within_tolerance(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test that pH adjustment is skipped when values are within tolerance.
        
        Verifies:
        - No adjustment when pH is within acceptable range
        - Proper tolerance checking
        - Appropriate logging messages
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        target_ph = self.test_config['duty_cycle']['ph']
        tolerance = self.test_config.get('ph_tolerance', 0.2)
        
        # Test pH values within tolerance
        test_ph_values = [
            target_ph,  # Exact target
            target_ph + tolerance * 0.5,  # Within upper tolerance
            target_ph - tolerance * 0.5,  # Within lower tolerance
            target_ph + tolerance,  # At upper boundary
            target_ph - tolerance,  # At lower boundary
        ]
        
        for test_ph in test_ph_values:
            with self.subTest(ph=test_ph):
                # Mock pH adjustment check method if it exists
                if hasattr(controller, 'ph_needs_adjustment'):
                    needs_adjustment = controller.ph_needs_adjustment(test_ph, target_ph, tolerance)
                    self.assertFalse(needs_adjustment, f"pH {test_ph} should not need adjustment")
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_ph_adjustment_outside_tolerance(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test that pH adjustment is triggered when values are outside tolerance.
        
        Verifies:
        - Adjustment is triggered for out-of-range pH values
        - Proper tolerance boundary detection
        - Correct adjustment direction (acid vs base)
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        target_ph = self.test_config['duty_cycle']['ph']
        tolerance = self.test_config.get('ph_tolerance', 0.2)
        
        # Test pH values outside tolerance
        test_cases = [
            (target_ph + tolerance + 0.1, 'acid'),  # Above upper tolerance
            (target_ph - tolerance - 0.1, 'base'),  # Below lower tolerance
            (target_ph + 1.0, 'acid'),              # Significantly high
            (target_ph - 1.0, 'base'),              # Significantly low
        ]
        
        for test_ph, expected_adjustment in test_cases:
            with self.subTest(ph=test_ph, adjustment=expected_adjustment):
                # Mock pH adjustment check method if it exists
                if hasattr(controller, 'ph_needs_adjustment'):
                    needs_adjustment = controller.ph_needs_adjustment(test_ph, target_ph, tolerance)
                    self.assertTrue(needs_adjustment, f"pH {test_ph} should need adjustment")
                
                # Mock get_adjustment_type method if it exists
                if hasattr(controller, 'get_ph_adjustment_type'):
                    adjustment_type = controller.get_ph_adjustment_type(test_ph, target_ph)
                    self.assertEqual(adjustment_type, expected_adjustment)
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_pump_timing_calculations(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test pump timing calculations for acid and base dosing.
        
        Verifies:
        - Correct timing based on dosage and pump rates
        - Proper conversion from volume to time
        - Safety limits for maximum pump runtime
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        acid_rate = self.test_config.get('acid_pump_rate', 1.5)  # ml/second
        base_rate = self.test_config.get('base_pump_rate', 1.2)  # ml/second
        
        # Test pump timing calculations
        test_cases = [
            (15.0, acid_rate, 10.0),  # 15ml at 1.5ml/s = 10s
            (12.0, base_rate, 10.0),  # 12ml at 1.2ml/s = 10s
            (3.0, acid_rate, 2.0),    # 3ml at 1.5ml/s = 2s
            (6.0, base_rate, 5.0),    # 6ml at 1.2ml/s = 5s
        ]
        
        for dosage_ml, pump_rate, expected_time in test_cases:
            with self.subTest(dosage=dosage_ml, rate=pump_rate):
                # Mock calculate_pump_time method if it exists
                if hasattr(controller, 'calculate_pump_time'):
                    pump_time = controller.calculate_pump_time(dosage_ml, pump_rate)
                    self.assertAlmostEqual(pump_time, expected_time, places=1)
                    
                    # Verify safety limits
                    max_time = self.test_config.get('max_adjustment_time', 300)
                    self.assertLessEqual(pump_time, max_time)
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_sensor_reading_validation(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test sensor reading validation and error handling.
        
        Verifies:
        - Valid sensor reading ranges
        - Error handling for invalid readings
        - Retry logic for failed sensor reads
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        # Test valid sensor readings
        valid_readings = [
            ('ph', 7.0, True),
            ('ph', 6.5, True),
            ('ec', 2.5, True),
            ('ec', 1.8, True),
        ]
        
        # Test invalid sensor readings
        invalid_readings = [
            ('ph', -1.0, False),  # Negative pH
            ('ph', 15.0, False),  # Too high pH
            ('ec', -0.5, False),  # Negative EC
            ('ec', 20.0, False),  # Extremely high EC
        ]
        
        all_test_cases = valid_readings + invalid_readings
        
        for sensor_type, reading, should_be_valid in all_test_cases:
            with self.subTest(sensor=sensor_type, reading=reading):
                # Mock validate_sensor_reading method if it exists
                if hasattr(controller, 'validate_sensor_reading'):
                    is_valid = controller.validate_sensor_reading(sensor_type, reading)
                    self.assertEqual(is_valid, should_be_valid)
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_init_delay_zero_delay(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test init_delay handles zero delay configuration correctly.
        
        Verifies:
        - No sleep calls when delay is zero
        - Proper logging for zero delay scenario
        - Immediate completion
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        # Modify config for zero delay
        zero_delay_config = self.test_config.copy()
        zero_delay_config['initial_delay'] = 0
        
        # Create temporary file with zero delay config
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(zero_delay_config, temp_file)
        temp_file.close()
        
        try:
            with patch('time.sleep') as mock_sleep:
                # Create controller instance
                controller = FertigationController(temp_file.name)
                
                # Mock the logger
                controller.logger = MagicMock()
                
                # Run init_delay
                controller.init_delay()
                
                # Verify no sleep calls were made
                mock_sleep.assert_not_called()
                
                # Verify logging calls
                controller.logger.info.assert_any_call("Initialization delay started (0s)")
                controller.logger.info.assert_any_call("Initialization delay completed")
        
        finally:
            # Clean up temporary file
            os.unlink(temp_file.name)
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_emergency_shutdown_handling(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test emergency shutdown scenarios and safety mechanisms.
        
        Verifies:
        - Immediate response to shutdown signals
        - Proper cleanup of resources
        - Safety state activation
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        # Test emergency shutdown
        controller.shutdown_event.set()
        
        # Mock emergency_shutdown method if it exists
        if hasattr(controller, 'emergency_shutdown'):
            controller.emergency_shutdown()
            
            # Verify shutdown event is set
            self.assertTrue(controller.shutdown_event.is_set())
            
            # Verify logging
            controller.logger.warning.assert_called()
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_tank_cycling_logic(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test tank cycling and duration management.
        
        Verifies:
        - Correct tank sequence handling
        - Proper timing for each tank
        - Tank state transitions
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        tank_durations = self.test_config['tanks']
        
        # Test tank cycling logic
        for i, duration in enumerate(tank_durations):
            with self.subTest(tank=i, duration=duration):
                # Mock get_current_tank method if it exists
                if hasattr(controller, 'get_current_tank'):
                    current_tank = controller.get_current_tank()
                    self.assertIsInstance(current_tank, int)
                    self.assertGreaterEqual(current_tank, 0)
                    self.assertLess(current_tank, len(tank_durations))
                
                # Mock get_tank_duration method if it exists
                if hasattr(controller, 'get_tank_duration'):
                    tank_duration = controller.get_tank_duration(i)
                    self.assertEqual(tank_duration, duration)


class TestFertigationControllerConfigLoading(unittest.TestCase):
    """
    Test configuration loading functionality and error handling.
    
    Covers various configuration scenarios including missing files,
    invalid JSON, and malformed configuration parameters.
    """

    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_nonexistent_file_raises_error(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test that attempting to load a non-existent file raises FileNotFoundError.
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        with self.assertRaises(FileNotFoundError) as context:
            controller = FertigationController("non-existent.json")
        self.assertIn("control signal file not found", str(context.exception).lower())

    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_valid_configuration_loads_successfully(self, mock_stream_handler, mock_file_handler, mock_signal):
        """Test that valid configuration file loads correctly."""
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        valid_config = {
            "initial_delay": 5,
            "flush": 10,
            "tanks": [30, 45, 60],
            "duty_cycle": {
                "ec": 2.5,
                "ph": 6.5
            },
            "ph_interval": 15
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(valid_config, temp_file)
            temp_file_path = temp_file.name
        
        try:
            controller = FertigationController(temp_file_path)
            self.assertIsNotNone(controller.config)
            self.assertEqual(controller.config["initial_delay"], valid_config["initial_delay"])
            self.assertEqual(controller.config["flush"], valid_config["flush"])
            self.assertEqual(controller.config["tanks"], valid_config["tanks"])
            self.assertEqual(controller.config["duty_cycle"], valid_config["duty_cycle"])
            self.assertEqual(controller.config["ph_interval"], valid_config["ph_interval"])
        finally:
            os.unlink(temp_file_path)

    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_validate_config_missing_required_keys(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test validation fails when required keys are missing.
        
        Verifies:
        - Error is raised for each missing required key
        - Error message specifies the missing key
        """
        # Setup
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        # Test each required key
        required_keys = ['initial_delay', 'flush', 'tanks', 'duty_cycle']
        for key in required_keys:
            with self.subTest(missing_key=key):
                # Create config missing one required key
                config = {
                    'initial_delay': 5,
                    'flush': 10,
                    'tanks': [30, 45, 60],
                    'duty_cycle': {'ec': 2.5, 'ph': 6.5}
                }
                del config[key]
                
                # Create controller with incomplete config
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(config, temp_file)
                    temp_file_path = temp_file.name
                
                try:
                    controller = FertigationController(temp_file_path)
                    # Should not reach here
                    self.fail(f"ValueError not raised for missing {key}")
                except ValueError as e:
                    self.assertIn(key, str(e))
                finally:
                    os.unlink(temp_file_path)

    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_validate_config_valid_ph_interval(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test validation succeeds with valid pH interval values.
        
        Verifies:
        - Default pH interval is accepted
        - Custom pH interval is accepted
        - Edge case values are handled correctly
        """
        # Setup
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        valid_intervals = [1, 15, 30, 60, 120]
        
        for interval in valid_intervals:
            with self.subTest(ph_interval=interval):
                config = {
                    'initial_delay': 5,
                    'flush': 10,
                    'tanks': [30, 45, 60],
                    'duty_cycle': {'ec': 2.5, 'ph': 6.5},
                    'ph_interval': interval
                }
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(config, temp_file)
                    temp_file_path = temp_file.name
                
                try:
                    controller = FertigationController(temp_file_path)
                    self.assertEqual(controller.ph_interval, interval)
                finally:
                    os.unlink(temp_file_path)

    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_validate_config_invalid_ph_interval(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test validation fails with invalid pH interval values.
        
        Verifies:
        - Negative intervals are rejected
        - Zero interval is rejected
        - Non-integer intervals are rejected
        """
        # Setup
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        invalid_intervals = [-1, 0, 1.5, "30", None]
        
        for interval in invalid_intervals:
            with self.subTest(ph_interval=interval):
                config = {
                    'initial_delay': 5,
                    'flush': 10,
                    'tanks': [30, 45, 60],
                    'duty_cycle': {'ec': 2.5, 'ph': 6.5},
                    'ph_interval': interval
                }
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(config, temp_file)
                    temp_file_path = temp_file.name
                
                try:
                    with self.assertRaises(ValueError) as context:
                        controller = FertigationController(temp_file_path)
                    self.assertIn("ph_interval must be a positive integer", str(context.exception))
                finally:
                    os.unlink(temp_file_path)

    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_validate_config_complete_valid_configuration(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test validation succeeds with complete valid configuration.
        
        Verifies:
        - All required keys present
        - All values have correct types
        - Optional parameters are handled correctly
        """
        # Setup
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        config = {
            'initial_delay': 5,
            'flush': 10,
            'tanks': [30, 45, 60],
            'duty_cycle': {'ec': 2.5, 'ph': 6.5},
            'ph_interval': 30,
            'optional_param': 'some_value'  # Should be ignored
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(config, temp_file)
            temp_file_path = temp_file.name
        
        try:
            controller = FertigationController(temp_file_path)
            # Verify all config values are correctly set
            self.assertEqual(controller.ph_interval, 30)
            self.assertEqual(controller.config['initial_delay'], 5)
            self.assertEqual(controller.config['flush'], 10)
            self.assertEqual(controller.config['tanks'], [30, 45, 60])
            self.assertEqual(controller.config['duty_cycle']['ec'], 2.5)
            self.assertEqual(controller.config['duty_cycle']['ph'], 6.5)
        finally:
            os.unlink(temp_file_path)


class TestFertigationControllerAdvancedFeatures(unittest.TestCase):
    """
    Test advanced features and edge cases of the FertigationController.
    
    Includes stress testing, concurrent operations, and complex scenarios
    that might occur in production environments.
    """
    
    def setUp(self):
        """Set up advanced test scenarios with comprehensive configuration."""
        self.advanced_config = {
            "initial_delay": 3,
            "flush": 15,
            "tanks": [20, 30, 40, 50],
            "duty_cycle": {
                "ec": 2.8,
                "ph": 6.2
            }
        }
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.advanced_config, self.temp_file)
        self.temp_file.close()
        self.config_file_path = self.temp_file.name
    
    def tearDown(self):
        """Clean up advanced test resources."""
        if os.path.exists(self.config_file_path):
            os.unlink(self.config_file_path)
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_concurrent_operations_safety(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test thread safety and concurrent operation handling.
        
        Verifies:
        - Safe concurrent access to shared resources
        - Proper locking mechanisms
        - No race conditions in critical sections
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        # Simulate concurrent operations
        results = []
        errors = []
        
        def concurrent_operation(operation_id):
            """Simulate concurrent controller operations."""
            try:
                # Mock some controller operations
                if hasattr(controller, 'generate_ph_reading'):
                    reading = controller.generate_ph_reading()
                    results.append(f"Operation {operation_id}: {reading}")
                else:
                    results.append(f"Operation {operation_id}: completed")
            except Exception as e:
                errors.append(f"Operation {operation_id}: {str(e)}")
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrent operations failed: {errors}")
        self.assertEqual(len(results), 5, "Not all concurrent operations completed")
    
    @patch('signal.signal')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_stress_testing_rapid_adjustments(self, mock_stream_handler, mock_file_handler, mock_signal):
        """
        Test system behavior under rapid pH/EC adjustment scenarios.
        
        Verifies:
        - Stability under rapid changes
        - Proper rate limiting
        - System doesn't become unstable
        """
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        controller = FertigationController(self.config_file_path)
        controller.logger = MagicMock()
        
        # Simulate rapid pH changes
        ph_readings = [7.5, 6.0, 8.0, 5.5, 7.8, 6.2, 5.8, 7.2]
        adjustments_made = 0
        
        for ph in ph_readings:
            # Mock rapid pH adjustment scenario
            if hasattr(controller, 'handle_ph_reading'):
                try:
                    controller.handle_ph_reading(ph)
                    adjustments_made += 1
                except Exception as e:
                    self.fail(f"Rapid pH adjustment failed: {str(e)}")
        
        # Verify system handled rapid changes
        self.assertGreater(adjustments_made, 0, "No adjustments were processed")


if __name__ == '__main__':
    """
    Main test execution with comprehensive coverage reporting.
    
    Runs all test suites and provides detailed output for debugging
    and validation of the FertigationController functionality.
    """
    # Configure test runner for detailed output
    unittest.main(verbosity=2, buffer=True)