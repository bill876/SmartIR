import importlib.util
import itertools
import logging
import os.path

from .smartir_helpers import precision_round

_LOGGER = logging.getLogger(__name__)

ENCODE_FUNCTION = "encode"

# Same values as homeassistant.const STATE_ON / STATE_OFF; kept literal so this
# module (like device_data.py) can be used by test_device_data.py without HA.
STATE_ON = "on"
STATE_OFF = "off"


def load_encoder_module(file_path: str):
    """Import a device commands encoder module from the given file path.

    Returns the module, or None (after logging) if it can't be imported or
    doesn't define a callable `encode` function.
    """
    file_name = os.path.basename(file_path)
    module_name = "smartir_encoder_" + os.path.splitext(file_name)[0]
    try:
        _LOGGER.debug("Loading device encoder file '%s'.", file_path)
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        _LOGGER.error("Error loading device encoder file '%s': '%s'.", file_path, e)
        return None

    if not callable(getattr(module, ENCODE_FUNCTION, None)):
        _LOGGER.error(
            "Invalid device encoder file '%s': missing '%s' function.",
            file_name,
            ENCODE_FUNCTION,
        )
        return None

    _LOGGER.debug("Loaded device encoder file '%s'.", file_path)
    return module


def encode_command(encoder, **kwargs):
    """Call the encoder and return a list of command strings.

    The encoder may return a single command string or a list of them. Raises
    ValueError if the encoder returns anything else.
    """
    commands = getattr(encoder, ENCODE_FUNCTION)(**kwargs)
    if isinstance(commands, str):
        commands = [commands]
    if not (
        isinstance(commands, list)
        and len(commands)
        and all(isinstance(command, str) and command for command in commands)
    ):
        raise ValueError(
            f"encoder returned '{commands!r}' instead of a command string or list of command strings"
        )
    return commands


def check_encoder_climate(file_name, encoder, device_data):
    """Exercise a climate encoder for every declared mode/temperature combination.

    Mirrors the JSON commands validation: every combination of declared operation,
    preset, fan and swing modes and every supported temperature must encode into a
    command, as must the 'off' command for each operation mode.
    """
    precision = device_data["precision"]
    temperatures = []
    temperature = precision_round(device_data["minTemperature"], precision)
    while temperature <= device_data["maxTemperature"]:
        temperatures.append(temperature)
        temperature = precision_round(temperature + precision, precision)

    def modes(attr):
        return device_data.get(attr) or [None]

    combinations = itertools.chain(
        (
            (STATE_OFF, hvac_mode, preset_mode, fan_mode, swing_mode, temperatures[0])
            for hvac_mode in device_data["operationModes"]
            for preset_mode in modes("presetModes")[:1]
            for fan_mode in modes("fanModes")[:1]
            for swing_mode in modes("swingModes")[:1]
        ),
        itertools.product(
            [STATE_ON],
            device_data["operationModes"],
            modes("presetModes"),
            modes("fanModes"),
            modes("swingModes"),
            temperatures,
        ),
    )

    for (
        state,
        hvac_mode,
        preset_mode,
        fan_mode,
        swing_mode,
        temperature,
    ) in combinations:
        try:
            encode_command(
                encoder,
                state=state,
                hvac_mode=hvac_mode,
                preset_mode=preset_mode,
                fan_mode=fan_mode,
                swing_mode=swing_mode,
                temperature=temperature,
            )
        except Exception as e:
            _LOGGER.error(
                "Invalid device encoder file '%s': failed to encode state '%s', operation mode '%s', preset mode '%s', fan mode '%s', swing mode '%s', temperature '%s': '%s'.",
                file_name,
                state,
                hvac_mode,
                preset_mode,
                fan_mode,
                swing_mode,
                temperature,
                e,
            )
            return False

    return True
