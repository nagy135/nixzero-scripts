import argparse
import unittest
from unittest.mock import Mock, call, patch

from servo_wave import angle_argument, angle_sequence, angle_to_pulse, choreography, play


class WaveTests(unittest.TestCase):
    def test_angle_conversion_preserves_endpoints_and_centre(self):
        self.assertEqual([angle_to_pulse(a) for a in (0, 45, 90, 180)],
                         [1000, 1250, 1500, 2000])

    def test_invalid_angles_are_rejected(self):
        for value in ("-1", "181", "nan", "inf", "text"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                angle_argument(value)

    def test_custom_angles_preserve_order_and_duration(self):
        sequence = angle_sequence([90, 30, 150, 90], duration=0.5)
        self.assertEqual([label for label, _, _ in sequence], ["90°", "30°", "150°", "90°"])
        self.assertEqual([w for _, w, _ in sequence],
                         [[1500] * 25, [1167] * 25, [1833] * 25, [1500] * 25])

    def driver(self):
        driver = Mock(TX_WAVE=1)
        driver.gpiochip_open.return_value = 5
        driver.gpio_get_chip_info.return_value = (0, 54, "", "pinctrl-bcm2835")
        driver.tx_busy.return_value = 0
        driver.pulse.side_effect = lambda bits, mask, delay: (bits, mask, delay)
        return driver

    def test_dance_is_bounded_varied_and_returns_to_centre(self):
        sequence = choreography("dance")
        widths = sequence[0][1]
        self.assertEqual(widths[0], 1500)
        self.assertEqual(widths[-1], 1500)
        self.assertGreaterEqual(min(widths), 1000)
        self.assertLessEqual(max(widths), 2000)
        self.assertGreater(len(set(widths)), 20)
        self.assertLessEqual(sum(len(w) / 50 + p for _, w, p in sequence), 10)

    def test_demo_preserves_original_sequence(self):
        sequence = choreography("demo")
        self.assertEqual([widths for _, widths, _ in sequence],
                         [[1500] * 100, [1000] * 100, [2000] * 100])
        self.assertEqual([pause for _, _, pause in sequence], [1, 1, 1])

    def test_wave_uses_20ms_frames_and_releases_selected_gpio(self):
        driver = self.driver()
        with patch("builtins.print"):
            play(driver, [("test", [1000, 1500, 2000], 0)])
        driver.tx_wave.assert_called_once_with(5, 23, [
            (1, 1, 1000), (0, 1, 19000), (1, 1, 1500),
            (0, 1, 18500), (1, 1, 2000), (0, 1, 18000)])
        self.assertEqual(driver.mock_calls[-2:],
                         [call.gpio_free(5, 23), call.gpiochip_close(5)])

    def test_interruption_releases_gpio_and_closes_chip(self):
        driver = self.driver()
        driver.tx_busy.side_effect = KeyboardInterrupt
        with patch("builtins.print"), self.assertRaises(KeyboardInterrupt):
            play(driver, [("test", [1500], 0)])
        driver.gpio_free.assert_called_once_with(5, 23)
        driver.gpiochip_close.assert_called_once_with(5)

    def test_stuck_wave_times_out_and_releases_gpio(self):
        driver = self.driver()
        driver.tx_busy.return_value = 1
        with (patch("builtins.print"),
              patch("servo_wave.time.monotonic", side_effect=[0, 2]),
              self.assertRaisesRegex(RuntimeError, "deadline")):
            play(driver, [("test", [1500], 0)])
        driver.gpio_free.assert_called_once_with(5, 23)
        driver.gpiochip_close.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
