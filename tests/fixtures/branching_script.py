import tester
import log


def verify_firmware_version(device, expected_ver):
    response = tester.send_cmd("GET_VERSION", device)
    if response.status != 0:
        log.error("Command failed")
        return False
    if device.type == "TypeA":
        version = response.data[:8]
    elif device.type == "TypeB":
        version = response.data[:16]
    else:
        raise ValueError(f"Unknown device: {device.type}")
    if version == expected_ver:
        return True
    else:
        log.warning(f"Mismatch: {version} != {expected_ver}")
        return False
