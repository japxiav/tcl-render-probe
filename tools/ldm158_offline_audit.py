#!/usr/bin/env python3
"""Offline V643 LDM 158 audit. Reads two ELF files; never connects to TV."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

HASH = {
    "render": "7daa84de2d0b306fa0704498d0b8f10ddff51d812de34225c9598b9c1655ec7c",
    "hal": "608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500",
}
CHECKS = {
    "render": {
        0x2e83c: ("vmov.i32", "q8, #0x0"),
        0x2e846: ("vst1.64", "{d16, d17}, [r0]"),
        0x2e854: ("ldr", "r1, [r5, #0x10]"),
        0x2e86a: ("str", "r0, [sp, #0x14]"),
        0x2e8b0: ("str", "r0, [sp, #0x10]"),
        0x2e8c8: ("blx", "r7"),
        0x2e926: ("ldr.w", "r0, [r8, #0xc]"),
        0x2e92a: ("ldr", "r2, [r5, #0x10]"),
        0x2e92c: ("blx", "0x3d130"),
    },
    "hal": {
        0x784ea: ("ldrd", "r0, r1, [r4, #8]"),
        0x785e6: ("ldr", "r1, [r7, #0x2c]"),
        0x785e8: ("ldrd", "r0, r2, [r4, #4]"),
        0x785ec: ("blx", "0xbd0cc"),
    },
}
INSTRUCTION = re.compile(r"^\\s*([0-9a-f]+):\\s+(?:[0-9a-f]{4}(?:\\s+[0-9a-f]{4})?|[0-9a-f]{8})\\s+([\\w.]+)\\s*(.*)$")

def digest(file):
    h = hashlib.sha256()
    with file.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def disasm(file, first, last, tool):
    cmd = [tool, "-d", "--triple=thumbv7-none-linux-gnueabi", f"--start-address={first}", f"--stop-address={last}", str(file)]
    stdout = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30).stdout
    found = {}
    for line in stdout.splitlines():
        match = INSTRUCTION.match(line)
        if match:
            found[int(match[1], 16)] = (match[2], match[3].split("@", 1)[0].strip())
    return found

def model(requested):
    if not isinstance(requested, int) or requested < 0 or requested > 65536:
        raise ValueError("length must be an integer in [0,65536]")
    return "NO_DATA" if requested == 0 else "BLOCKED_UNVERIFIED_DESTINATION"

def audit(render, hal, tool="llvm-objdump"):
    files = {"render": Path(render), "hal": Path(hal)}
    for name, path in files.items():
        if not path.is_file() or digest(path) != HASH[name]:
            raise ValueError(f"unverified or wrong V643 ELF: {name}")
    if not shutil.which(tool):
        raise ValueError("llvm-objdump is required")
    asm = {
        "render": disasm(files["render"], 0x2e814, 0x2e940, tool),
        "hal": disasm(files["hal"], 0x78440, 0x785f4, tool),
    }
    evidence = []
    for name, checks in CHECKS.items():
        for address, expected in checks.items():
            value = asm[name].get(address)
            if value is None or value[0] != expected[0] or expected[1] not in value[1]:
                raise AssertionError(f"{name}@{address:#x}: expected {expected}, found {value}")
            evidence.append(f"{name}@{address:#x}: {value[0]} {value[1]}")
    direct_length_stores = [
        f"{address:#x}" for address, (op, args) in asm["render"].items()
        if 0x2e846 < address < 0x2e8c8 and op.startswith(("str", "vst")) and "[sp, #0x18]" in args
    ]
    return {
        "firmware": "TCL C6K V643",
        "verified_elf_sha256": HASH,
        "verified_instruction_count": len(evidence),
        "direct_stores_to_native_length": direct_length_stores,
        "evidence": evidence,
        "conclusion": "Zero-initialized native struct; no direct length store visible before HAL; HAL reads native+8, later service copy uses input+16. Indirect writes and buffer ownership remain unresolved.",
        "limit": "Static evidence is NOT proof of a reachable crash, zeros, or safety.",
        "gate": "BLOCK_TRANSACTION_158",
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render", type=Path, required=True)
    ap.add_argument("--hal", type=Path, required=True)
    ap.add_argument("--objdump", default="llvm-objdump")
    options = ap.parse_args()
    try:
        output = audit(options.render, options.hal, options.objdump)
    except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as exc:
        print(json.dumps({"gate": "FAILED_CLOSED", "reason": str(exc)}, indent=2))
        return 2
    print(json.dumps(output, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
