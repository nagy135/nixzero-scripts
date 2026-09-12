import unittest
from unittest.mock import Mock, call

from servo import release_servo


class GpioError(Exception):
    def __str__(self):
        return repr(self.args[0])


class ReleaseServoTests(unittest.TestCase):
    def setUp(self):
        self.gpio = Mock(TX_PWM=0, BAD_PWM_MICROS=-86, error=GpioError)
        self.gpio.error_text.return_value = "bad PWM micros"

    def assert_released(self):
        self.assertEqual(self.gpio.mock_calls[-2:], [
            call.gpio_write(1, 18, 0), call.gpio_free(1, 18)])

    def test_finished_train_needs_no_stop(self):
        self.gpio.tx_busy.return_value = 0
        release_servo(self.gpio, 1)
        self.gpio.tx_servo.assert_not_called()
        self.assert_released()

    def test_active_train_is_stopped(self):
        self.gpio.tx_busy.return_value = 1
        release_servo(self.gpio, 1)
        self.gpio.tx_servo.assert_called_once_with(1, 18, 0)
        self.assert_released()

    def test_train_finishing_during_stop_is_harmless(self):
        self.gpio.tx_busy.side_effect = [1, 0]
        self.gpio.tx_servo.side_effect = GpioError("bad PWM micros")
        release_servo(self.gpio, 1)
        self.assert_released()

    def test_unexpected_stop_error_is_reported_after_release(self):
        self.gpio.tx_busy.return_value = 1
        self.gpio.tx_servo.side_effect = GpioError("bad handle")
        with self.assertRaisesRegex(GpioError, "bad handle"):
            release_servo(self.gpio, 1)
        self.assert_released()

    def test_pwm_error_with_active_train_is_not_hidden(self):
        self.gpio.tx_busy.return_value = 1
        self.gpio.tx_servo.side_effect = GpioError("bad PWM micros")
        with self.assertRaisesRegex(GpioError, "bad PWM micros"):
            release_servo(self.gpio, 1)
        self.assert_released()

    def test_failed_write_still_frees_line(self):
        self.gpio.tx_busy.return_value = 0
        self.gpio.gpio_write.side_effect = GpioError("bad write")
        with self.assertRaisesRegex(GpioError, "bad write"):
            release_servo(self.gpio, 1)
        self.gpio.gpio_free.assert_called_once_with(1, 18)


if __name__ == "__main__":
    unittest.main()
