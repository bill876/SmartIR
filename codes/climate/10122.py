"""Commands encoder for the Mesto Cthulhu Room A air conditioner.

This is the ESPHome raw-command variant of encoder 10121.  The protocol is
documented there; raw commands use positive mark and negative space durations.
"""

import json

from custom_components.smartir.smartir_helpers import bytes_to_pulses

HEADER_MARK = 8440
HEADER_SPACE = 4665
BIT_MARK = 640
ONE_SPACE = 1855
ZERO_SPACE = 560
FOOTER_MARK = 640

SWING_HEADER_MARK = 8444
SWING_HEADER_SPACE = 4661
SWING_BIT_MARK = 635
SWING_ONE_SPACE = 1856
SWING_ZERO_SPACE = 578
SWING_FOOTER_MARK = 635

MIN_TEMPERATURE = 18
MAX_TEMPERATURE = 26

MODE = {"cool": 0x01}
FAN = {"auto": 0x00, "low": 0x10}
SWING_FRAME = bytes([0xD1, 0x2E])


def frame(state, hvac_mode, fan_mode, temperature):
    """Build the four-byte state frame from the captured protocol."""
    if hvac_mode not in MODE:
        raise ValueError(f"unsupported operation mode {hvac_mode!r}")
    if fan_mode not in FAN:
        raise ValueError(f"unsupported fan mode {fan_mode!r}")
    if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
        raise ValueError(f"unsupported temperature {temperature}")

    byte_1 = MODE[hvac_mode] | FAN[fan_mode]
    if state == "off":
        byte_1 |= 0x80
    checksum = (
        0xFF - ((0xC0 + byte_1 + int(temperature)) & 0xFF)
    ) & 0xFF
    return bytes([0xC0, byte_1, int(temperature), checksum])


def raw_command(
    data,
    *,
    header_mark,
    header_space,
    bit_mark,
    one_space,
    zero_space,
    footer_mark,
):
    """Serialize a byte frame as an ESPHome raw command JSON array."""
    pulses = bytes_to_pulses(
        data,
        header_mark=header_mark,
        header_space=header_space,
        bit_mark=bit_mark,
        one_space=one_space,
        zero_space=zero_space,
        footer_mark=footer_mark,
        lsb_first=True,
    )
    return json.dumps(
        [pulse if index % 2 == 0 else -pulse for index, pulse in enumerate(pulses)]
    )


def encode(state, hvac_mode, preset_mode, fan_mode, swing_mode, temperature):
    """Return ESPHome raw commands for the requested AC state."""
    if state not in ("on", "off"):
        raise ValueError(f"unsupported power state {state!r}")
    if preset_mode is not None:
        raise ValueError(f"unsupported preset mode {preset_mode!r}")
    if swing_mode not in ("off", "on"):
        raise ValueError(f"unsupported swing mode {swing_mode!r}")

    commands = [
        raw_command(
            frame(state, hvac_mode, fan_mode, temperature),
            header_mark=HEADER_MARK,
            header_space=HEADER_SPACE,
            bit_mark=BIT_MARK,
            one_space=ONE_SPACE,
            zero_space=ZERO_SPACE,
            footer_mark=FOOTER_MARK,
        )
    ]

    if state == "on" and swing_mode == "on":
        commands.append(
            raw_command(
                SWING_FRAME,
                header_mark=SWING_HEADER_MARK,
                header_space=SWING_HEADER_SPACE,
                bit_mark=SWING_BIT_MARK,
                one_space=SWING_ONE_SPACE,
                zero_space=SWING_ZERO_SPACE,
                footer_mark=SWING_FOOTER_MARK,
            )
        )

    return commands
