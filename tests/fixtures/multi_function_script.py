import tester


def init_device(device):
    resp = tester.send_cmd("INIT", device)
    if resp.status != 0:
        raise RuntimeError("Init failed")
    return resp.data


def read_register(device, addr):
    if addr < 0 or addr > 0xFFFF:
        raise ValueError(f"Invalid address: {addr}")
    resp = tester.send_cmd("READ_REG", device, addr=addr)
    return resp.data
