from base64 import b64encode
import binascii
import struct


# round to given precision
@staticmethod
def precision_round(number, precision):
    if precision == 0.1:
        return round(float(number), 1)
    if precision == 0.5:
        return round((float(number) * 2) / 2.0, 1)
    elif precision == 1:
        return round(float(number))
    elif precision > 1:
        return round(float(number) / int(precision)) * int(precision)
    else:
        return None


@staticmethod
def closest_match_index(value, list):
    prev_val = None
    for index, entry in enumerate(list):
        if entry > (value or 0):
            if prev_val is None:
                return index
            diff_lo = value - prev_val
            diff_hi = entry - value
            if diff_lo < diff_hi:
                return index - 1
            return index
        prev_val = entry

    return len(list) - 1


@staticmethod
def closest_match_value(value, list):
    if value is None or not len(list):
        return None

    temp = sorted(
        list,
        key=lambda entry: abs(float(entry) - value),
    )
    if len(temp):
        return temp[0]
    else:
        return None


def pronto2lirc(pronto):
    """Convert Pronto hex bytes into a list of pulse lengths in microseconds."""
    codes = [
        int(binascii.hexlify(pronto[i : i + 2]), 16) for i in range(0, len(pronto), 2)
    ]

    if codes[0]:
        raise ValueError("Pronto code should start with 0000")
    if len(codes) != 4 + 2 * (codes[2] + codes[3]):
        raise ValueError("Number of pulse widths does not match the preamble")

    frequency = 1 / (codes[1] * 0.241246)
    return [int(round(code / frequency)) for code in codes[4:]]


def lirc2broadlink(pulses):
    """Convert a list of pulse lengths in microseconds into a Broadlink IR packet."""
    array = bytearray()

    for pulse in pulses:
        pulse = int(pulse * 269 / 8192)

        if pulse < 256:
            array += bytearray(struct.pack(">B", pulse))
        else:
            array += bytearray([0x00])
            array += bytearray(struct.pack(">H", pulse))

    packet = bytearray([0x26, 0x00])
    packet += bytearray(struct.pack("<H", len(array)))
    packet += array
    packet += bytearray([0x0D, 0x05])

    # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
    remainder = (len(packet) + 4) % 16
    if remainder:
        packet += bytearray(16 - remainder)
    return packet


def pulses_to_broadlink(pulses):
    """Convert a list of pulse lengths in microseconds into a Broadlink Base64 command.

    The returned string is what a device file with `"supportedController": "Broadlink"`
    and `"commandsEncoding": "Base64"` expects as a command value.
    """
    return b64encode(lirc2broadlink(pulses)).decode("utf-8")


def bytes_to_pulses(
    data,
    *,
    header_mark,
    header_space,
    bit_mark,
    one_space,
    zero_space,
    footer_mark=None,
    footer_space=None,
    lsb_first=False,
):
    """Convert a byte frame into IR pulse lengths (microseconds) using pulse distance encoding.

    The result alternates mark, space, mark, space... starting with the header mark.
    Each bit is a `bit_mark` followed by `one_space` or `zero_space`. Bits of each byte
    are sent most significant first unless `lsb_first` is set. An optional footer
    (stop mark and inter-frame gap) is appended.
    """
    pulses = [header_mark, header_space]
    bit_order = range(8) if lsb_first else range(7, -1, -1)
    for byte in data:
        for bit in bit_order:
            pulses.append(bit_mark)
            pulses.append(one_space if (byte >> bit) & 1 else zero_space)
    if footer_mark is not None:
        pulses.append(footer_mark)
    if footer_space is not None:
        pulses.append(footer_space)
    return pulses
