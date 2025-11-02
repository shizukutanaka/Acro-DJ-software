# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Plugin Testing Framework for Acro DJ Mixer

Provides:
- Plugin unit testing framework
- Mock objects for testing
- Test fixtures and utilities
- Performance testing
- Integration testing
"""

import logging
import unittest
import time
from typing import Optional, Any, Callable, Dict, List
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a test."""
    test_name: str
    passed: bool
    duration_ms: float
    error_message: Optional[str] = None
    assertions: int = 0


class MockPlugin:
    """Mock plugin for testing."""

    def __init__(self, plugin_id: str = "mock_plugin"):
        """Initialize mock plugin.

        Args:
            plugin_id: Plugin identifier
        """
        self.plugin_id = plugin_id
        self.initialized = False
        self.parameters = {}
        self.process_count = 0
        self.error_on_process = False

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        self.initialized = True

    def shutdown(self) -> None:
        """Shutdown plugin."""
        self.initialized = False

    def process_audio(self, audio: np.ndarray) -> np.ndarray:
        """Process audio."""
        self.process_count += 1

        if self.error_on_process:
            raise RuntimeError("Intentional error")

        return audio

    def get_parameter(self, name: str) -> Any:
        """Get parameter."""
        return self.parameters.get(name)

    def set_parameter(self, name: str, value: Any) -> None:
        """Set parameter."""
        self.parameters[name] = value


class MockAudioBuffer:
    """Mock audio buffer for testing."""

    def __init__(
        self,
        sample_rate: int = 44100,
        duration_seconds: float = 1.0,
        channels: int = 2
    ):
        """Initialize mock buffer.

        Args:
            sample_rate: Sample rate in Hz
            duration_seconds: Duration in seconds
            channels: Number of channels
        """
        self.sample_rate = sample_rate
        self.duration_seconds = duration_seconds
        self.channels = channels
        self.samples = int(sample_rate * duration_seconds)

    def generate_silence(self) -> np.ndarray:
        """Generate silence."""
        return np.zeros((self.samples, self.channels), dtype=np.float32)

    def generate_sine(self, frequency: float = 1000.0) -> np.ndarray:
        """Generate sine wave.

        Args:
            frequency: Frequency in Hz

        Returns:
            Audio data
        """
        t = np.linspace(0, self.duration_seconds, self.samples, dtype=np.float32)
        sine = np.sin(2 * np.pi * frequency * t)

        if self.channels > 1:
            return np.column_stack([sine] * self.channels)
        else:
            return sine.reshape(-1, 1)

    def generate_white_noise(self) -> np.ndarray:
        """Generate white noise.

        Returns:
            Audio data
        """
        return np.random.randn(self.samples, self.channels).astype(np.float32) * 0.1


class PluginTestCase(unittest.TestCase):
    """Base test case for plugin testing."""

    def setUp(self) -> None:
        """Set up test."""
        self.plugin = None
        self.audio_buffer = MockAudioBuffer()

    def tearDown(self) -> None:
        """Tear down test."""
        if self.plugin and hasattr(self.plugin, 'shutdown'):
            self.plugin.shutdown()

    def create_test_audio(self, **kwargs) -> np.ndarray:
        """Create test audio.

        Args:
            **kwargs: Audio buffer parameters

        Returns:
            Audio data
        """
        buffer = MockAudioBuffer(**kwargs)
        return buffer.generate_silence()

    def assert_audio_shape(
        self,
        audio: np.ndarray,
        expected_shape: tuple
    ) -> None:
        """Assert audio shape.

        Args:
            audio: Audio data
            expected_shape: Expected shape
        """
        self.assertEqual(audio.shape, expected_shape)

    def assert_audio_valid(self, audio: np.ndarray) -> None:
        """Assert audio is valid.

        Args:
            audio: Audio data
        """
        self.assertTrue(np.isfinite(audio).all())
        self.assertFalse(np.isnan(audio).any())
        self.assertFalse(np.isinf(audio).any())

    def assert_audio_amplitude(
        self,
        audio: np.ndarray,
        max_amplitude: float = 1.0
    ) -> None:
        """Assert audio amplitude is within limits.

        Args:
            audio: Audio data
            max_amplitude: Maximum amplitude
        """
        self.assertLessEqual(np.max(np.abs(audio)), max_amplitude)

    def assert_audio_silent(self, audio: np.ndarray, threshold: float = 1e-10) -> None:
        """Assert audio is silent.

        Args:
            audio: Audio data
            threshold: Silence threshold
        """
        self.assertLess(np.max(np.abs(audio)), threshold)


class PluginPerformanceTest:
    """Performance testing for plugins."""

    def __init__(self, plugin: Any, warmup_iterations: int = 10):
        """Initialize performance test.

        Args:
            plugin: Plugin to test
            warmup_iterations: Number of warmup iterations
        """
        self.plugin = plugin
        self.warmup_iterations = warmup_iterations
        self.results: List[float] = []

    def measure_latency(
        self,
        operation: Callable,
        iterations: int = 100
    ) -> Dict[str, float]:
        """Measure operation latency.

        Args:
            operation: Operation to measure
            iterations: Number of iterations

        Returns:
            Dictionary with latency statistics
        """
        # Warmup
        for _ in range(self.warmup_iterations):
            operation()

        # Measure
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            operation()
            end = time.perf_counter()

            times.append((end - start) * 1000)  # Convert to ms

        times.sort()

        return {
            'min': min(times),
            'max': max(times),
            'mean': sum(times) / len(times),
            'median': times[len(times) // 2],
            'p95': times[int(len(times) * 0.95)],
            'p99': times[int(len(times) * 0.99)],
        }

    def measure_throughput(
        self,
        operation: Callable,
        duration_seconds: float = 1.0
    ) -> float:
        """Measure operation throughput.

        Args:
            operation: Operation to measure
            duration_seconds: Measurement duration

        Returns:
            Operations per second
        """
        start = time.perf_counter()
        count = 0

        while time.perf_counter() - start < duration_seconds:
            operation()
            count += 1

        elapsed = time.perf_counter() - start

        return count / elapsed


class PluginIntegrationTest:
    """Integration testing utilities."""

    @staticmethod
    def test_plugin_lifecycle(plugin: Any) -> List[TestResult]:
        """Test complete plugin lifecycle.

        Args:
            plugin: Plugin to test

        Returns:
            List of test results
        """
        results = []

        # Test initialization
        start = time.perf_counter()

        try:
            if hasattr(plugin, 'initialize'):
                plugin.initialize({})

            duration = (time.perf_counter() - start) * 1000

            results.append(TestResult(
                test_name='initialize',
                passed=True,
                duration_ms=duration
            ))

        except Exception as e:
            results.append(TestResult(
                test_name='initialize',
                passed=False,
                duration_ms=0,
                error_message=str(e)
            ))

        # Test execution
        if hasattr(plugin, 'process_audio'):
            start = time.perf_counter()

            try:
                audio = np.zeros((44100, 2), dtype=np.float32)
                output = plugin.process_audio(audio)

                assert output is not None
                assert output.shape == audio.shape

                duration = (time.perf_counter() - start) * 1000

                results.append(TestResult(
                    test_name='process_audio',
                    passed=True,
                    duration_ms=duration
                ))

            except Exception as e:
                results.append(TestResult(
                    test_name='process_audio',
                    passed=False,
                    duration_ms=0,
                    error_message=str(e)
                ))

        # Test shutdown
        start = time.perf_counter()

        try:
            if hasattr(plugin, 'shutdown'):
                plugin.shutdown()

            duration = (time.perf_counter() - start) * 1000

            results.append(TestResult(
                test_name='shutdown',
                passed=True,
                duration_ms=duration
            ))

        except Exception as e:
            results.append(TestResult(
                test_name='shutdown',
                passed=False,
                duration_ms=0,
                error_message=str(e)
            ))

        return results

    @staticmethod
    def test_plugin_parameters(plugin: Any, parameters: Dict[str, Any]) -> List[TestResult]:
        """Test plugin parameters.

        Args:
            plugin: Plugin to test
            parameters: Parameters to test

        Returns:
            List of test results
        """
        results = []

        for param_name, param_value in parameters.items():
            try:
                if hasattr(plugin, 'set_parameter'):
                    plugin.set_parameter(param_name, param_value)

                if hasattr(plugin, 'get_parameter'):
                    retrieved = plugin.get_parameter(param_name)
                    assert retrieved == param_value

                results.append(TestResult(
                    test_name=f'parameter_{param_name}',
                    passed=True,
                    duration_ms=0
                ))

            except Exception as e:
                results.append(TestResult(
                    test_name=f'parameter_{param_name}',
                    passed=False,
                    duration_ms=0,
                    error_message=str(e)
                ))

        return results
