"""Commands encoder for Mesto Hero Room air conditioners (TCL112 protocol)."""

from custom_components.smartir.smartir_helpers import (
    bytes_to_pulses,
    pulses_to_broadlink,
)

# Timings measured from the supplied captures, in microseconds.
HEADER_MARK = 3000
HEADER_SPACE = 1740
BIT_MARK = 435
ONE_SPACE = 1110
ZERO_SPACE = 390
FOOTER_MARK = 435

MIN_TEMPERATURE = 16
MAX_TEMPERATURE = 30

FAN = {
    "auto": 0x00,
    "low": 0x02,
    "medium": 0x03,
    "high": 0x05,
}


def frame(state, hvac_mode, fan_mode, swing_mode, temperature):
    """Build the 14-byte TCL112 state frame."""
    if hvac_mode != "cool":
        raise ValueError(f"unsupported operation mode {hvac_mode!r}")
    if fan_mode not in FAN:
        raise ValueError(f"unsupported fan mode {fan_mode!r}")
    if swing_mode not in ("off", "on"):
        raise ValueError(f"unsupported swing mode {swing_mode!r}")
    if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
        raise ValueError(f"unsupported temperature {temperature}")

    data = bytearray(
        [
            0x23,
            0xCB,
            0x26,
            0x01,
            0x00,
            0x24 if state == "on" else 0x20,
            0x03,  # Cool
            31 - int(temperature),
            FAN[fan_mode] | (0x38 if swing_mode == "on" else 0x00),
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    )
    data[13] = sum(data[:13]) & 0xFF
    return bytes(data)


def encode(state, hvac_mode, preset_mode, fan_mode, swing_mode, temperature):
    """Return one Broadlink Base64 command for the requested AC state."""
    if state not in ("on", "off"):
        raise ValueError(f"unsupported power state {state!r}")
    if preset_mode is not None:
        raise ValueError(f"unsupported preset mode {preset_mode!r}")

    pulses = bytes_to_pulses(
        frame(state, hvac_mode, fan_mode, swing_mode, temperature),
        header_mark=HEADER_MARK,
        header_space=HEADER_SPACE,
        bit_mark=BIT_MARK,
        one_space=ONE_SPACE,
        zero_space=ZERO_SPACE,
        footer_mark=FOOTER_MARK,
        lsb_first=True,
    )
    return pulses_to_broadlink(pulses)
