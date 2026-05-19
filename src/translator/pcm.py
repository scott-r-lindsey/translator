from math import sqrt


def rms_s16le(chunk: bytes) -> float:
    sample_count = len(chunk) // 2
    if sample_count == 0:
        return 0.0

    total = 0
    for index in range(0, sample_count * 2, 2):
        sample = int.from_bytes(chunk[index : index + 2], byteorder="little", signed=True)
        total += sample * sample

    return sqrt(total / sample_count) / 32_768
