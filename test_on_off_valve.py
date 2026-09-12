import unittest
from unittest.mock import Mock, patch

from on_off_valve import valve_angles
from run import run


class ValveTests(unittest.TestCase):
    def driver(self):
        driver = Mock(TX_WAVE=1)
        driver.gpiochip_open.return_value = 5
        driver.gpio_get_chip_info.return_value = (0, 54, "", "pinctrl-bcm2835")
        driver.tx_busy.return_value = 0
        driver.pulse.side_effect = lambda bits, mask, delay: (bits, mask, delay)
        return driver

    def test_closes_before_first_prompt_and_enter_toggles(self):
        driver = self.driver()
        commands = iter(["", "", "q"])
        prompts = []

        def answer(_):
            # Each command has finished before the next prompt appears.
            prompts.append(driver.tx_wave.call_count)
            return next(commands)

        with patch("builtins.print"), patch("builtins.input", side_effect=answer):
            run(driver, valve_angles())
        waves = [args.args[2] for args in driver.tx_wave.call_args_list]
        self.assertEqual(prompts, [1, 2, 3])
        self.assertEqual(waves[0], [(1, 1, 2000), (0, 1, 18000)] * 100)
        self.assertEqual(waves[1], [(1, 1, 1000), (0, 1, 19000)] * 100)
        self.assertEqual(waves[2], waves[0])
        driver.gpio_free.assert_called_once_with(5, 23)
        driver.gpiochip_close.assert_called_once_with(5)

    def test_text_does_not_toggle(self):
        with patch("builtins.print"), patch("builtins.input", side_effect=["hello", "q"]):
            self.assertEqual(list(valve_angles()), [180])

    def test_eof_or_ctrl_c_releases_gpio_after_startup(self):
        for interruption in (EOFError, KeyboardInterrupt):
            with self.subTest(interruption=interruption):
                driver = self.driver()
                with patch("builtins.print"), patch("builtins.input", side_effect=interruption):
                    if interruption is KeyboardInterrupt:
                        with self.assertRaises(KeyboardInterrupt):
                            run(driver, valve_angles())
                    else:
                        run(driver, valve_angles())
                driver.tx_wave.assert_called_once()
                driver.gpio_free.assert_called_once_with(5, 23)
                driver.gpiochip_close.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
