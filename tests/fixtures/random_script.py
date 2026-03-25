import random
import tester


def write_random_blocks(device, count):
    for i in range(count):
        addr = random.randint(0x0000, 0xFFFF)
        size = random.choice([512, 1024, 4096])
        resp = tester.send_cmd("WRITE", device, addr=addr, size=size)
        if resp.status != 0:
            if addr > 0xFFF0:
                continue
            else:
                raise RuntimeError(f"Write failed at {addr:#x}")
    return True
