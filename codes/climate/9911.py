"""Commands encoder for Zanussi air conditioners (Midea-style 6 byte IR frame).

Frame: 4D B2 b2 ~b2 b4 ~b4 where b2 carries the fan speed and b4 the operation
mode (high nibble) and the temperature (low nibble, reversed Gray code of
temperature - 17). Bytes are transmitted least significant bit first and the whole
frame is repeated twice.

Preset and swing modes are not reverse engineered yet and are ignored.
"""

from custom_components.smartir.smartir_helpers import (
    bytes_to_pulses,
    pulses_to_broadlink,
)

# Pulse timings in microseconds.
HEADER_MARK = 4400
HEADER_SPACE = 4400
BIT_MARK = 540
ONE_SPACE = 1600
ZERO_SPACE = 540
FOOTER_MARK = 540
FOOTER_SPACE = 5100

MIN_TEMPERATURE = 17
MAX_TEMPERATURE = 30

FAN = {
    "auto": 0x05,
    "low": 0x01,
    "medium": 0x02,
    "high": 0x04,
}

MODE = {
    "cool": 0x0,
    "heat_cool": 0x1,
    "dry": 0x2,
    "heat": 0x3,
}

# Operation modes that don't use a selectable fan speed.
FIXED_FAN_MODES = ("heat_cool", "dry")

OFF_FRAME = bytes([0x4D, 0xB2, 0xDE, 0x21, 0x07, 0xF8])


def reverse4(x):
    return ((x & 0x1) << 3) | ((x & 0x2) << 1) | ((x & 0x4) >> 1) | ((x & 0x8) >> 3)


def frame(state, hvac_mode, fan_mode, temperature):
    if state == "off":
        return OFF_FRAME

    if hvac_mode in FIXED_FAN_MODES:
        b2 = 0xF8
    else:
        b2 = 0xF8 | FAN[fan_mode]

    if hvac_mode == "fan_only":
        b4 = 0x27
    else:
        temperature = int(temperature)
        if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
            raise ValueError(f"unsupported temperature {temperature}")
        n = temperature - MIN_TEMPERATURE
        gray = n ^ (n >> 1)
        b4 = (MODE[hvac_mode] << 4) | reverse4(gray)

    return bytes([0x4D, 0xB2, b2, b2 ^ 0xFF, b4, b4 ^ 0xFF])


def encode(state, hvac_mode, preset_mode, fan_mode, swing_mode, temperature):
    pulses = bytes_to_pulses(
        frame(state, hvac_mode, fan_mode, temperature),
        header_mark=HEADER_MARK,
        header_space=HEADER_SPACE,
        bit_mark=BIT_MARK,
        one_space=ONE_SPACE,
        zero_space=ZERO_SPACE,
        footer_mark=FOOTER_MARK,
        footer_space=FOOTER_SPACE,
        lsb_first=True,
    )
    return pulses_to_broadlink(pulses * 2)
