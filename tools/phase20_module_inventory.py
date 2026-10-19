#!/usr/bin/env python3
"""Offline inventory of local TCL/MediaTek kernel modules, no ADB or kernel calls.

Usage: python3 tools/phase20_module_inventory.py mediatek-drm-tv.ko mtk-tvpqu.ko
The script reads existing ELF files only. Never publishes binaries/logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ELF_MACHINE = {40: 'ARM32', 183: 'AArch64'}
TOPICS = {
    'ldm': re.compile(r'ldm|local.?dimm|mini.?led|led.?zone|backlight', re.I),
    'transport': re.compile(r'spi|pwm|i2c|mcu|mailbox|rpmsg', re.I),
    'drm_dma': re.compile(r'drm|dma.?heap|dma.?buf|ioctl|memory', re.I),
}
ASCII = re.compile(rb'[\x20-\x7e]{5,256}')

def inspect_file(path: Path):
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b'\x7fELF':
        raise ValueError(f'{path.name}: not an ELF file')
    if data[5] != 1:
        raise ValueError(f'{path.name}: unsupported endian')
    machine = int.from_bytes(data[18:20], 'little')
    if machine not in ELF_MACHINE:
        raise ValueError(f'{path.name}: unsupported machine {machine}')
    topics = {topic: [] for topic in TOPICS}
    seen = set()
    for match in ASCII.finditer(data):
        value = match.group().decode('ascii', errors='replace').strip()
        if value in seen:
            continue
        seen.add(value)
        for topic, rx in TOPICS.items():
            if rx.search(value) and len(topics[topic]) < 100:
                topics[topic].append({'file_offset': hex(match.start()), 'text': value[:160]})
    info = [m.group().decode('ascii', errors='replace') for m in ASCII.finditer(data)
            if m.group().startswith((b'vermagic=', b'depends=', b'name='))]
    return {'filename': path.name, 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'elf_arch': ELF_MACHINE[machine],
            'module_metadata': info[:20], 'indicators': topics,
            'note': 'Keywords alone do not demonstrate LDM access; disassembly and call graph required.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modules', type=Path, nargs='+')
    parser.add_argument('--out', type=Path)
    options = parser.parse_args()
    try:
        report = [inspect_file(path) for path in options.modules]
    except (OSError, ValueError) as exc:
        parser.exit(2, f'OFFLINE_SCAN_FAILED: {exc}\n')
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if options.out:
        options.out.write_text(payload + '\n', encoding='utf-8')
        print(f'Saved {options.out}, {len(report)} module(s)')
    else:
        print(payload)

if __name__ == '__main__':
    main()
