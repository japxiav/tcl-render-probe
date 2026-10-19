#!/usr/bin/env python3
"""Offline-only guard for the V643 LDM158 output-vector hypothesis.

No device calls, no ADB, no Binder, no DRM. The byte-length model is
conditional and is NOT a statement about the vendor API's unit conventions.
"""

def classify_copy(begin, end, capacity, length):
    if type(length) is not int or length < 0 or length > 65536:
        raise ValueError("length is invalid")
    if length == 0:
        return "NO_PAYLOAD"
    if any(v is None for v in (begin, end, capacity)):
        return "BLOCK_UNVERIFIED_VECTOR_STATE"
    if any(type(v) is not int or v < 0 for v in (begin, end, capacity)):
        raise ValueError("address is invalid")
    if not begin <= end <= capacity:
        return "BLOCK_INVALID_VECTOR_LAYOUT"
    if capacity - end < length:
        return "BLOCK_INSUFFICIENT_TAIL_CAPACITY"
    return "BLOCK_SEMANTICALLY_WRONG_END_POINTER"


# Evidenced by the exact hashes and disassembly in FASE17 report:
# MediaTek AIDL serializes return vector from object+8.
# Render implementation reads memcpy destination from return object+12.
# On usual ARM32 libc++ std::vector layout, +12 is its end pointer.
AIDL_RETURN_VECTOR_OFFSET = 8
RENDER_COPY_DESTINATION_OFFSET = 12
TV_TRANSACTION_158_ALLOWED = False
