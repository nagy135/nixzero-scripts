import unittest
from unittest.mock import Mock, call, patch

from run import angle_to_pulse, run


class ServoTests(unittest.TestCase):
    def driver(self):
        driver = Mock(TX_WAVE=1)
        driver.gpiochip_open.return_value = 5
        driver.gpio_get_chip_info.return_value = (0, 54, "", "pinctrl-bcm2835")
        driver.tx_busy.return_value = 0
        driver.pulse.side_effect = lambda bits, mask, delay: (bits, mask, delay)
        return driver

    def test_angles_remain_in_established_pulse_range(self):
        self.assertEqual([angle_to_pulse(a) for a in (0, 90, 180)], [1000, 1500, 2000])
        for angle in (-1, 181, float("nan"), float("inf")):
            with self.subTest(angle=angle), self.assertRaises(ValueError):
                angle_to_pulse(angle)

    def test_moves_only_to_entered_angles_then_quits(self):
        driver = self.driver()
        with patch("builtins.print"), patch("builtins.input", side_effect=["0", "90", "45.5", "q"]):
            run(driver)
        waves = [args.args[2] for args in driver.tx_wave.call_args_list]
        self.assertEqual(waves[0], [(1, 1, 1000), (0, 1, 19000)] * 100)
        self.assertEqual(waves[1], [(1, 1, 1500), (0, 1, 18500)] * 100)
        self.assertEqual(waves[2], [(1, 1, 1253), (0, 1, 18747)] * 100)
        self.assertEqual(len(waves), 3)
        self.assertEqual(sum(p[2] for p in waves[0]), 2_000_000)
        self.assertEqual(driver.mock_calls[-2:],
                         [call.gpio_free(5, 23), call.gpiochip_close(5)])

    def test_interruption_during_wave_releases_gpio(self):
        driver = self.driver()
        driver.tx_busy.side_effect = KeyboardInterrupt
        with (patch("builtins.print"), patch("builtins.input", return_value="90"),
              self.assertRaises(KeyboardInterrupt)):
            run(driver)
        driver.gpio_free.assert_called_once_with(5, 23)
        driver.gpiochip_close.assert_called_once_with(5)

    def test_stuck_wave_times_out_and_releases_gpio(self):
        driver = self.driver()
        driver.tx_busy.return_value = 1
        with (patch("builtins.print"),
              patch("builtins.input", return_value="90"),
              patch("run.time.monotonic", side_effect=[0, 4]),
              self.assertRaisesRegex(RuntimeError, "deadline")):
            run(driver)
        driver.gpio_free.assert_called_once_with(5, 23)
        driver.gpiochip_close.assert_called_once_with(5)

    def test_invalid_input_does_not_send_pulses(self):
        driver = self.driver()
        values = ["", "hello", "-1", "181", "nan", "inf", "90", "q"]
        with patch("builtins.print"), patch("builtins.input", side_effect=values):
            run(driver)
        driver.tx_wave.assert_called_once()

    def test_eof_or_quit_before_angle_does_not_move(self):
        for value in (EOFError, "q"):
            with self.subTest(value=value):
                driver = self.driver()
                with patch("builtins.input", side_effect=[value]):
                    run(driver)
                driver.tx_wave.assert_not_called()
                driver.gpio_free.assert_called_once_with(5, 23)
                driver.gpiochip_close.assert_called_once_with(5)

    def test_wrong_controller_is_closed_without_driving(self):
        driver = self.driver()
        driver.gpio_get_chip_info.return_value = (0, 54, "", "other")
        with self.assertRaisesRegex(RuntimeError, "controller"):
            run(driver)
        driver.gpio_claim_output.assert_not_called()
        driver.gpiochip_close.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
