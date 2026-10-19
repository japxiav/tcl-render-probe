#!/usr/bin/env python3
"""TCL C6K V643 Phase 18: static audit of AIDL transaction 158.

Offline analysis only. No ADB, Binder IPC, DRM, root, patching, or TV access.
The exact expected ELF hashes and instruction patterns are intentional gates.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path

SHA256 = {
    "aidl": "de7d548884f7fadd141e9bce9a075039367ccb6a3065cfc23bdba09350254ed0",
    "render": "7daa84de2d0b306fa0704498d0b8f10ddff51d812de34225c9598b9c1655ec7c",
}
TEXT_FILE_BIAS = 0x1000  # Specific to the *verified* V643 AIDL ELF.
TABLE_BASE = 0x27964
TRANSACTION = 158
EXPECTED_TARGET = 0x2A90A
# Addresses selected by direct inspection of the hash-pinned binaries.
CHECKS = {
    "aidl": {
        0x27960: "tbh [pc, r0, lsl #1]",
        0x2a90a: "vmov.i32 q8, #0x0",
        0x2a912: "add.w r9, sp, #0x48",
        0x2a924: "vst1.64 {d16, d17}, [r0]!",
        0x2a928: "vst1.64 {d16, d17}, [r0]",
        0x2a954: "ldr r0, [r6]",
        0x2a956: "ldr.w r7, [r0, #0x28c]",
        0x2a95c: "str.w r9, [sp]",
        0x2a960: "blx r7",
        0x2a97e: "add r1, sp, #0x48",
        0x2a982: "bl 0x3ed78",
        0x45682: "add.w r0, r6, #0x8",
        0x45688: "blx 0x51d80",
    },
    "render": {
        0x2e842: "ldr.w r8, [sp, #0x40]",
        0x2e91e: "movs r0, #0x0",
        0x2e922: "str.w r0, [r8]",
        0x2e926: "ldr.w r0, [r8, #0xc]",
        0x2e92a: "ldr r2, [r5, #0x10]",
        0x2e92c: "blx 0x3d130",
    },
}

def sha256(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def jump_target(aidl_data, transaction=TRANSACTION):
    if type(transaction) is not int or not 1 <= transaction <= 169:
        raise ValueError("transaction outside verified jump table")
    loc = TABLE_BASE + 2 * (transaction - 1) - TEXT_FILE_BIAS
    if loc < 0 or loc + 2 > len(aidl_data):
        raise ValueError("truncated jump table")
    # Thumb TBH uses address of next instruction as base; this is TABLE_BASE.
    displacement = struct.unpack_from("<H", aidl_data, loc)[0]
    return TABLE_BASE + 2 * displacement

def capture_disassembly(binary, start, end, llvm):
    proc = subprocess.run(
        [llvm, "-d", "--triple=thumbv7-none-linux-gnueabi",
         f"--start-address={start:#x}", f"--stop-address={end:#x}", str(binary)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    result = {}
    for line in proc.stdout.splitlines():
        match = re.match(r"^\s*([0-9a-f]+):\s+", line)
        if match:
            result[int(match.group(1), 16)] = re.sub(r"\s+", " ", line).strip()
    return result

def audit(aidl, render, llvm="llvm-objdump"):
    files = {"aidl": Path(aidl), "render": Path(render)}
    for role, path in files.items():
        if not path.is_file() or sha256(path) != SHA256[role]:
            raise ValueError(f"Unverified ELF: {role}; audit fails closed")
    if not shutil.which(llvm):
        raise ValueError("llvm-objdump not found")
    data = files["aidl"].read_bytes()
    expected_tbh = bytes.fromhex("df e8 10 f0")
    if data[0x27960 - TEXT_FILE_BIAS:0x27964 - TEXT_FILE_BIAS] != expected_tbh:
        raise AssertionError("AIDL TBH instruction changed")
    dest = jump_target(data)
    if dest != EXPECTED_TARGET:
        raise AssertionError(f"158 dispatch moved to {dest:#x}")
    maps = {
        "aidl": {
            **capture_disassembly(files["aidl"], 0x27960, 0x27964, llvm),
            **capture_disassembly(files["aidl"], 0x2a90a, 0x2a990, llvm),
            **capture_disassembly(files["aidl"], 0x45682, 0x4568c, llvm),
        },
        "render": capture_disassembly(files["render"], 0x2e814, 0x2e940, llvm),
    }
    verified = []
    for role, points in CHECKS.items():
        for address, expectation in points.items():
            observed = maps[role].get(address, "")
            if expectation not in observed:
                raise AssertionError(f"{role}@{address:#x}: expected {expectation!r}, observed {observed!r}")
            verified.append(f"{role}@{address:#x}: {expectation}")

    return {
        "status": "PHASE18_EVIDENCE_VERIFIED",
        "firmware": "TCL C6K 55 V643",
        "read_only": True,
        "sha256": SHA256,
        "transaction": TRANSACTION,
        "jump_target": hex(dest),
        "assembly_checks": len(verified),
        "instructions": verified,
        "analysis": [
            "BnRender's 158 dispatcher zero-initializes a 32-byte result object at sp+0x48.",
            "It passes the same result object as the virtual method's output parameter.",
            "AIDL serializes a vector at return+8; Render::GetLdmBlockData reads memcpy destination at return+12.",
            "Under 32-bit libc++ std::vector ABI return+12 is end, not begin.",
            "No result-vector resize was observed before the virtual call; no resizing inside Render implementation was identified.",
        ],
        "limitations": "Static evidence. No runtime reachability, crash, or driver behavior established. Other aliases and ABI assumptions require independent review.",
        "decision": "DO_NOT_CALL_AIDL_158_ON_TV",
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aidl", required=True, type=Path)
    p.add_argument("--render", required=True, type=Path)
    p.add_argument("--objdump", default="llvm-objdump")
    args = p.parse_args()
    try:
        result = audit(args.aidl, args.render, args.objdump)
    except (AssertionError, ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "FAILED_CLOSED", "reason": str(error)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
