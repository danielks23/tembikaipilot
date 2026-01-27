#!/usr/bin/env python3
"""
SD Card Performance Testing Tool for openpilot/KOMMU
Tests read/write performance and provides recommendations.
"""

import os
import sys
import time
import ctypes
import subprocess
from pathlib import Path

# Test configuration
TEST_SIZE_MB = 500  # Size of test file in MB
MOUNT_POINT = "/data/media"
BLOCK_SIZE = 1024 * 1024  # 1MB blocks

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_result(test_name, value, unit, recommendation=None):
    print(f"{Colors.BOLD}{test_name}:{Colors.END} {value:.2f} {unit}")
    if recommendation:
        color = Colors.GREEN if "Good" in recommendation else Colors.YELLOW if "Acceptable" in recommendation else Colors.RED
        print(f"  → {color}{recommendation}{Colors.END}")

def check_mount():
    """Check if /data/media is mounted"""
    print_header("Storage Mount Check")
    try:
        result = subprocess.run(['mount'], capture_output=True, text=True)
        media_mount = [line for line in result.stdout.split('\n') if '/data/media' in line]

        if media_mount:
            print(f"{Colors.GREEN}✓ Storage is mounted:{Colors.END}")
            for line in media_mount:
                print(f"  {line}")
            return True
        else:
            print(f"{Colors.RED}✗ /data/media is NOT mounted!{Colors.END}")
            return False
    except Exception as e:
        print(f"{Colors.RED}Error checking mount: {e}{Colors.END}")
        return False

def get_storage_info():
    """Get storage capacity and usage information"""
    print_header("Storage Information")
    try:
        stat = os.statvfs(MOUNT_POINT)
        total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
        used_gb = ((stat.f_blocks - stat.f_bfree) * stat.f_frsize) / (1024**3)
        avail_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        used_percent = (used_gb / total_gb) * 100

        print(f"Total Size:     {total_gb:.2f} GB")
        print(f"Used:           {used_gb:.2f} GB ({used_percent:.1f}%)")
        print(f"Available:      {avail_gb:.2f} GB")

        if avail_gb < 10:
            print(f"{Colors.RED}⚠ Warning: Low storage space!{Colors.END}")

        # Check device info
        result = subprocess.run(['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT'],
                              capture_output=True, text=True)
        print(f"\n{Colors.BOLD}Block Devices:{Colors.END}")
        for line in result.stdout.split('\n'):
            if 'mmcblk1' in line or 'media' in line:
                print(f"  {line}")

        return True
    except Exception as e:
        print(f"{Colors.RED}Error getting storage info: {e}{Colors.END}")
        return False

def get_sd_card_speed_class():
    """Extract UHS Speed Class (U1, U3, etc.) and Video Speed Class (V30, V60, etc.)"""
    speed_classes = []
    try:
        # Try to read SCR register to get UHS speed class
        scr_file = "/sys/block/mmcblk1/device/scr"
        if os.path.exists(scr_file):
            with open(scr_file, 'rb') as f:
                scr_data = f.read()
                if len(scr_data) >= 8:
                    # SCR is 64-bit, speed class is in bits [415:409] (SCR version 4.0+)
                    # Byte 4 contains UHS speed class info
                    if len(scr_data) > 4:
                        byte4 = scr_data[4]
                        uhs_speed_class = (byte4 >> 4) & 0x0F
                        if uhs_speed_class == 0:
                            speed_classes.append("U1 (10 MB/s min)")
                        elif uhs_speed_class == 1:
                            speed_classes.append("U3 (30 MB/s min)")
                        elif uhs_speed_class == 2:
                            speed_classes.append("U60 (60 MB/s min)")
                        elif uhs_speed_class == 3:
                            speed_classes.append("U90 (90 MB/s min)")

        # If no speed class found from SCR, try mmc-utils
        if not speed_classes:
            try:
                result = subprocess.run(['mmc', 'extcsd', 'read', '/dev/mmcblk1'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Look for Video Speed Class in output
                    for line in result.stdout.split('\n'):
                        line_lower = line.lower()
                        if 'video speed class' in line_lower:
                            if 'v90' in line_lower or 'v 90' in line_lower:
                                speed_classes.append("V90 (90 MB/s min)")
                            elif 'v60' in line_lower or 'v 60' in line_lower:
                                speed_classes.append("V60 (60 MB/s min)")
                            elif 'v30' in line_lower or 'v 30' in line_lower:
                                speed_classes.append("V30 (30 MB/s min)")
            except Exception:
                pass

    except Exception:
        pass

    return speed_classes

def get_mmc_info_from_dmesg():
    """Extract MMC info from dmesg logs (fallback method)"""
    timing_mode = None
    clock_mhz = 0
    try:
        result = subprocess.run(['dmesg'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.split('\n')

        # Look for "mmc1: new ultra high speed SDR104" pattern
        for line in reversed(lines):  # Reverse to get latest info
            if 'mmc' in line and 'new' in line and 'speed' in line.lower():
                # Extract timing mode: "ultra high speed SDR104"
                if 'SDR104' in line:
                    timing_mode = "sd-uhs-SDR104"
                elif 'DDR50' in line:
                    timing_mode = "sd-uhs-DDR50"
                elif 'SDR50' in line:
                    timing_mode = "sd-uhs-SDR50"
                elif 'SDR25' in line:
                    timing_mode = "sd-uhs-SDR25"
                elif 'HS400' in line:
                    timing_mode = "mmc-hs400"
                elif 'high speed' in line.lower():
                    timing_mode = "sd-hs"
                if timing_mode:
                    break

        # Look for bus speed: "Bus speed (slot 0) = 148500000Hz"
        for line in reversed(lines):
            if 'mmc_host mmc' in line and 'Bus speed' in line and 'actual' in line:
                try:
                    # Extract frequency from "actual 148500000HZ"
                    parts = line.split('actual')
                    if len(parts) > 1:
                        freq_str = parts[1].split('HZ')[0].strip()
                        clock_hz = int(freq_str)
                        clock_mhz = clock_hz // 1000000
                        break
                except Exception:
                    pass

    except Exception:
        pass

    return timing_mode, clock_mhz

def find_mmc_device():
    """Find the correct mmc device for the SD card (mmc0, mmc1, mmc2, etc.)"""
    import glob
    mmc_hosts = glob.glob("/sys/class/mmc_host/mmc*")
    for mmc_path in sorted(mmc_hosts):
        mmc_name = mmc_path.split('/')[-1]
        try:
            clock_file = f"{mmc_path}/ios/clock"
            if os.path.exists(clock_file):
                with open(clock_file) as f:
                    clock = int(f.read().strip())
                    if clock > 0:  # Device is active
                        return mmc_name
        except Exception:
            pass
    return "mmc0"  # Default fallback

def get_sd_card_mode_and_speed():
    """Get SD card mode (UHS-I, etc.) and current speed"""
    print_header("SD Card Mode & Speed Detection")

    # Mapping of timing modes to theoretical speeds
    mode_speeds = {
        "sd": (25, "Standard Speed"),
        "sd-hs": (50, "High Speed"),
        "sd-uhs-sdr12": (25, "UHS-I SDR12"),
        "sd-uhs-sdr25": (50, "UHS-I SDR25"),
        "sd-uhs-sdr50": (104, "UHS-I SDR50"),
        "sd-uhs-sdr104": (208, "UHS-I SDR104"),
        "sd-uhs-ddr50": (104, "UHS-I DDR50"),
    }

    try:
        # Auto-detect the correct mmc device
        mmc_device = find_mmc_device()

        # Get timing mode (UHS-I, etc.)
        timing_file = f"/sys/class/mmc_host/{mmc_device}/ios/timing"
        clock_file = f"/sys/class/mmc_host/{mmc_device}/ios/clock"
        bus_width_file = f"/sys/class/mmc_host/{mmc_device}/ios/bus_width"
        card_name_file = "/sys/block/mmcblk1/device/name"

        timing_mode = "Unknown"
        clock_mhz = 0
        bus_width = "Unknown"
        card_name = "Unknown"
        theoretical_speed = "Unknown"

        # Get timing mode
        if os.path.exists(timing_file):
            with open(timing_file) as f:
                timing_mode = f.read().strip()

        # Get clock speed
        if os.path.exists(clock_file):
            with open(clock_file) as f:
                clock_hz = int(f.read().strip())
                clock_mhz = clock_hz // 1000000

        # Fallback to dmesg if sysfs files aren't available
        if (timing_mode == "Unknown" or clock_mhz == 0):
            dmesg_timing, dmesg_clock = get_mmc_info_from_dmesg()
            if dmesg_timing:
                timing_mode = dmesg_timing
            if dmesg_clock > 0:
                clock_mhz = dmesg_clock

        # Get bus width
        if os.path.exists(bus_width_file):
            with open(bus_width_file) as f:
                bus_width = f.read().strip()

        # Get card name
        if os.path.exists(card_name_file):
            with open(card_name_file) as f:
                card_name = f.read().strip()

        # Calculate theoretical speed based on timing mode
        mode_lower = timing_mode.lower()
        # Sort by length descending to match longest (most specific) patterns first
        for mode_key in sorted(mode_speeds.keys(), key=len, reverse=True):
            if mode_key in mode_lower:
                speed_mbps, mode_name = mode_speeds[mode_key]
                theoretical_speed = f"{speed_mbps} MB/s ({mode_name})"
                break

        print(f"{Colors.BOLD}Card Name:{Colors.END} {card_name}")
        print(f"{Colors.BOLD}Timing Mode:{Colors.END} {timing_mode}")
        print(f"{Colors.BOLD}Clock Speed:{Colors.END} {clock_mhz} MHz")
        print(f"{Colors.BOLD}Bus Width:{Colors.END} {bus_width} bits")
        print(f"{Colors.BOLD}Theoretical Speed:{Colors.END} {theoretical_speed}")

        # Get and display speed class (U1, U3, V30, etc.)
        speed_classes = get_sd_card_speed_class()
        if speed_classes:
            print(f"{Colors.BOLD}Speed Classes:{Colors.END} {', '.join(speed_classes)}")

        # Provide recommendation based on available information
        # Priority: Speed Class > Timing Mode (since timing may fail on some devices)
        assessment = None

        # Check speed class first (most reliable indicator)
        if speed_classes:
            speed_class_str = ' '.join(speed_classes).upper()
            if 'U90' in speed_class_str or 'V90' in speed_class_str:
                assessment = f"{Colors.GREEN}✓ Excellent: U90/V90 speed class - Premium card{Colors.END}"
            elif 'U60' in speed_class_str or 'V60' in speed_class_str:
                assessment = f"{Colors.GREEN}✓ Excellent: U60/V60 speed class - High performance{Colors.END}"
            elif 'U3' in speed_class_str or 'V30' in speed_class_str:
                assessment = f"{Colors.GREEN}✓ Good: U3/V30 speed class - Meets openpilot requirements{Colors.END}"
            elif 'U1' in speed_class_str:
                assessment = f"{Colors.YELLOW}⚠ Acceptable: U1 speed class - may struggle with sustained writes{Colors.END}"

        # Fallback to timing mode if speed class not detected
        if not assessment:
            if "SDR104" in timing_mode or "DDR50" in timing_mode:
                assessment = f"{Colors.GREEN}✓ Excellent: UHS-I capable mode detected{Colors.END}"
            elif "SDR50" in timing_mode:
                assessment = f"{Colors.YELLOW}⚠ Good: UHS-I SDR50 mode (could be faster){Colors.END}"
            elif "hs" in timing_mode.lower() or "50" in timing_mode:
                assessment = f"{Colors.YELLOW}⚠ Acceptable: High Speed mode detected{Colors.END}"
            elif timing_mode != "Unknown":
                assessment = f"{Colors.RED}✗ Poor: {timing_mode} mode - upgrade recommended{Colors.END}"
            else:
                assessment = f"{Colors.YELLOW}⚠ Unable to detect timing mode (sysfs unavailable). Check physical card markings.{Colors.END}"

        if assessment:
            print(assessment)

        return True
    except Exception as e:
        print(f"{Colors.RED}Error detecting SD card mode: {e}{Colors.END}")
        print(f"{Colors.YELLOW}(This is normal if not running on device){Colors.END}")
        return False

def test_sequential_write(test_file: str, size_mb: int) -> float | None:
    """Test sequential write speed"""
    print_header("Sequential Write Test")
    print("Write Method: Python file.write + fsync per 1MB block")
    print(f"Writing {size_mb} MB to test file...")

    try:
        start_time = time.time()

        # Write test
        with open(test_file, 'wb') as f:
            data = os.urandom(BLOCK_SIZE)  # 1MB of random data
            for _ in range(size_mb):
                f.write(data)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        elapsed = time.time() - start_time
        speed_mbps = size_mb / elapsed

        print_result("Write Speed", speed_mbps, "MB/s",
                    get_write_recommendation(speed_mbps))
        return speed_mbps
    except Exception as e:
        print(f"{Colors.RED}Write test failed: {e}{Colors.END}")
        return None

def test_buffered_write_openpilot_style(test_file: str, size_mb: int) -> float | None:
    """Test write speed using openpilot's exact method (C fwrite via ctypes)

    openpilot uses C's fwrite() with buffering, writing data without per-write
    flushes. This uses ctypes to call libc's fwrite directly, replicating
    openpilot's exact logging behavior.
    """
    print_header("Write Test (openpilot C fwrite method)")
    print("Write Method: C fwrite (stdio buffering, single flush at end)")
    print(f"Writing {size_mb} MB using C fwrite (buffered, no per-write flush)...")

    try:
        # Load C library for direct fwrite calls
        libc = ctypes.CDLL(None)
        fopen = libc.fopen
        fwrite = libc.fwrite
        fflush = libc.fflush
        fclose = libc.fclose
        fsync = libc.fsync

        fopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        fopen.restype = ctypes.c_void_p

        fwrite.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p]
        fwrite.restype = ctypes.c_size_t

        fflush.argtypes = [ctypes.c_void_p]
        fflush.restype = ctypes.c_int

        fclose.argtypes = [ctypes.c_void_p]
        fclose.restype = ctypes.c_int

        fsync.argtypes = [ctypes.c_int]
        fsync.restype = ctypes.c_int

        buffered_file = test_file + '.buffered'
        start_time = time.time()

        # Open file in write mode (exactly like openpilot)
        file_ptr = fopen(buffered_file.encode(), b'wb')
        if not file_ptr:
            raise OSError(f"Cannot open {buffered_file}")

        # Write data using C's fwrite (buffered, no per-write flush)
        data = os.urandom(BLOCK_SIZE)
        for _ in range(size_mb):
            written = fwrite(data, 1, BLOCK_SIZE, file_ptr)
            if written != BLOCK_SIZE:
                fclose(file_ptr)
                raise OSError(f"fwrite failed: wrote {written} bytes, expected {BLOCK_SIZE}")

        # Only flush once at the end (exactly like openpilot)
        fflush(file_ptr)

        # Get file descriptor and sync to disk
        fd = os.open(buffered_file, os.O_RDONLY)
        fsync(fd)
        os.close(fd)

        fclose(file_ptr)

        elapsed = time.time() - start_time
        speed_mbps = size_mb / elapsed

        print_result("openpilot C fwrite Speed", speed_mbps, "MB/s",
                    get_write_recommendation(speed_mbps))

        # Clean up
        if os.path.exists(buffered_file):
            os.remove(buffered_file)

        return speed_mbps
    except Exception as e:
        print(f"{Colors.RED}openpilot C fwrite test failed: {e}{Colors.END}")
        # Clean up on error
        try:
            if os.path.exists(buffered_file):
                os.remove(buffered_file)
        except Exception:
            pass
        return None

def test_sequential_read(test_file: str, size_mb: int) -> float | None:
    """Test sequential read speed"""
    print_header("Sequential Read Test")
    print(f"Reading {size_mb} MB from test file...")

    try:
        # Clear page cache
        try:
            subprocess.run(['sudo', 'sh', '-c', 'sync; echo 3 > /proc/sys/vm/drop_caches'],
                         check=False)
        except Exception:
            print("(Could not clear cache - results may be optimistic)")

        start_time = time.time()

        # Read test
        with open(test_file, 'rb') as f:
            while f.read(BLOCK_SIZE):
                pass

        elapsed = time.time() - start_time
        speed_mbps = size_mb / elapsed

        print_result("Read Speed", speed_mbps, "MB/s",
                    get_read_recommendation(speed_mbps))
        return speed_mbps
    except Exception as e:
        print(f"{Colors.RED}Read test failed: {e}{Colors.END}")
        return None

def test_random_iops(test_file: str) -> float | None:
    """Test random I/O operations"""
    print_header("Random I/O Test (4K blocks)")
    print("Testing random read/write performance...")

    random_file = test_file + '.random'
    try:
        # Create 100MB file for random access
        file_size = 100 * 1024 * 1024  # 100MB
        block_size = 4096  # 4K blocks
        num_ops = 1000

        # Random write test
        start_time = time.time()
        with open(random_file, 'wb') as f:
            # Pre-allocate file
            f.write(b'\0' * file_size)
            f.flush()

        with open(random_file, 'r+b') as f:
            for _ in range(num_ops):
                offset = (os.urandom(4)[0] % (file_size // block_size)) * block_size
                f.seek(offset)
                f.write(os.urandom(block_size))
            f.flush()
            os.fsync(f.fileno())

        elapsed = time.time() - start_time
        iops = num_ops / elapsed

        print_result("Random Write IOPS", iops, "ops/sec",
                    get_iops_recommendation(iops))

        # Clean up
        if os.path.exists(random_file):
            os.remove(random_file)
        return iops
    except Exception as e:
        print(f"{Colors.RED}Random I/O test failed: {e}{Colors.END}")
        # Clean up on error
        if os.path.exists(random_file):
            os.remove(random_file)
        return None

def test_sustained_write(test_file: str) -> float | None:
    """Test sustained write performance over longer duration"""
    print_header("Sustained Write Test (30 seconds)")
    print("Testing write performance over extended period...")

    try:
        duration = 30  # seconds
        start_time = time.time()
        bytes_written = 0

        with open(test_file + '.sustained', 'wb') as f:
            data = os.urandom(BLOCK_SIZE)
            while time.time() - start_time < duration:
                f.write(data)
                bytes_written += BLOCK_SIZE
                if bytes_written % (10 * BLOCK_SIZE) == 0:
                    f.flush()
                    os.fsync(f.fileno())

        elapsed = time.time() - start_time
        mb_written = bytes_written / (1024 * 1024)
        avg_speed = mb_written / elapsed

        print_result("Sustained Write Speed", avg_speed, "MB/s",
                    get_sustained_recommendation(avg_speed))

        # Clean up
        os.remove(test_file + '.sustained')
        return avg_speed
    except Exception as e:
        print(f"{Colors.RED}Sustained write test failed: {e}{Colors.END}")
        return None

def get_write_recommendation(speed: float) -> str:
    """Get recommendation based on write speed"""
    if speed >= 40:
        return "Excellent! Well above openpilot requirements"
    elif speed >= 25:
        return "Good! Suitable for openpilot logging"
    elif speed >= 15:
        return "Acceptable, but may struggle with multiple cameras"
    else:
        return "POOR - May cause dropped frames and storage issues!"

def get_read_recommendation(speed: float) -> str:
    """Get recommendation based on read speed"""
    if speed >= 50:
        return "Excellent! Fast replay and uploads"
    elif speed >= 30:
        return "Good! Sufficient for normal operations"
    elif speed >= 20:
        return "Acceptable for basic operations"
    else:
        return "POOR - Slow uploads and replay"

def get_iops_recommendation(iops: float) -> str:
    """Get recommendation based on IOPS"""
    if iops >= 100:
        return "Excellent! Good for metadata operations"
    elif iops >= 50:
        return "Good! Sufficient for logging"
    elif iops >= 25:
        return "Acceptable"
    else:
        return "POOR - May cause issues with file operations"

def get_sustained_recommendation(speed: float) -> str:
    """Get recommendation based on sustained write"""
    if speed >= 20:
        return "Good! Consistent performance"
    elif speed >= 15:
        return "Acceptable, minor slowdowns possible"
    else:
        return "POOR - SD card may be throttling/worn out"

def check_sd_health():
    """Check SD card health information"""
    print_header("SD Card Health Check")

    # Try to get device info
    commands = [
        ("Device Info", ['lsblk', '-o', 'NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT', '/dev/mmcblk1']),
        ("Mount Options", ['mount', '|', 'grep', 'mmcblk1']),
    ]

    for name, cmd in commands:
        try:
            if '|' in cmd:
                # Handle piped commands
                result = subprocess.run(' '.join(cmd), shell=True,
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout:
                print(f"{Colors.BOLD}{name}:{Colors.END}")
                print(result.stdout)
        except Exception as e:
            print(f"Could not get {name}: {e}")

    # Check for errors in dmesg (filter out false positives)
    try:
        result = subprocess.run(['dmesg'], capture_output=True, text=True)
        mmcblk1_lines = [line for line in result.stdout.split('\n') if 'mmcblk1' in line.lower()]
        # Filter out false positives: mount options, success messages
        error_keywords = [' error ', ' failed', ' timeout', ' i/o error', 'cannot', 'unable']
        error_lines = [line for line in mmcblk1_lines
                      if any(keyword in line.lower() for keyword in error_keywords)]
        if error_lines:
            print(f"{Colors.YELLOW}⚠ Warning: Errors found in dmesg for mmcblk1{Colors.END}")
            for line in error_lines[-10:]:  # Last 10 error lines
                print(f"  {line}")
        else:
            print(f"{Colors.GREEN}✓ No errors found in system logs{Colors.END}")
    except Exception:
        pass

def main():
    print(f"\n{Colors.BOLD}{'='*60}")
    print("  SD Card Performance Test for openpilot/KOMMU")
    print(f"{'='*60}{Colors.END}\n")

    # Check if running on device
    if not os.path.exists(MOUNT_POINT):
        print(f"{Colors.RED}Error: {MOUNT_POINT} does not exist!{Colors.END}")
        print("This script must be run on the KA2 device.")
        sys.exit(1)

    # Check mount
    if not check_mount():
        print(f"\n{Colors.RED}Cannot proceed - storage not mounted!{Colors.END}")
        sys.exit(1)

    # Get storage info
    get_storage_info()

    # Get SD card mode and speed
    get_sd_card_mode_and_speed()

    # Check SD health
    check_sd_health()

    # Confirm before testing
    print(f"\n{Colors.YELLOW}About to run performance tests...{Colors.END}")
    print(f"This will create temporary files (~{TEST_SIZE_MB}MB) in {MOUNT_POINT}")
    response = input("Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Test cancelled.")
        sys.exit(0)

    # Create test file path
    test_file = os.path.join(MOUNT_POINT, f'.sd_test_{os.getpid()}.tmp')

    try:
        # Run tests
        write_speed = test_sequential_write(test_file, TEST_SIZE_MB)
        buffered_write_speed = test_buffered_write_openpilot_style(test_file, TEST_SIZE_MB)
        read_speed = test_sequential_read(test_file, TEST_SIZE_MB)
        sustained_speed = test_sustained_write(test_file)
        iops = test_random_iops(test_file)

        # Clean up main test file
        if os.path.exists(test_file):
            os.remove(test_file)

        # Summary
        print_header("Test Summary")
        print(f"{Colors.BOLD}openpilot Requirements:{Colors.END}")
        print("  • Sequential Write: 20-30 MB/s minimum")
        print("  • Sequential Read:  20+ MB/s recommended")
        print("  • Random IOPS:      50+ for smooth operation")
        print("  • Sustained Write:  15+ MB/s for reliability")

        print(f"\n{Colors.BOLD}Your Results:{Colors.END}")
        if write_speed:
            print(f"  • Sequential Write: {write_speed:.2f} MB/s")
        if buffered_write_speed:
            print(f"  • Buffered Write (openpilot-style): {buffered_write_speed:.2f} MB/s")
        if read_speed:
            print(f"  • Sequential Read:  {read_speed:.2f} MB/s")
        if sustained_speed:
            print(f"  • Sustained Write:  {sustained_speed:.2f} MB/s")
        if iops:
            print(f"  • Random IOPS:      {iops:.0f} ops/sec")

        # Overall recommendation
        print(f"\n{Colors.BOLD}Overall Assessment:{Colors.END}")
        if write_speed and write_speed >= 25 and sustained_speed and sustained_speed >= 15:
            print(f"{Colors.GREEN}✓ SD card performance is GOOD for openpilot!{Colors.END}")
        elif write_speed and write_speed >= 15:
            print(f"{Colors.YELLOW}⚠ SD card performance is ACCEPTABLE but not optimal.{Colors.END}")
            print(f"{Colors.YELLOW}  Consider upgrading to UHS-I or better SD card.{Colors.END}")
        else:
            print(f"{Colors.RED}✗ SD card performance is POOR!{Colors.END}")
            print(f"{Colors.RED}  Strongly recommend replacing with a faster card.{Colors.END}")
            print(f"{Colors.RED}  You may experience dropped frames and logging issues.{Colors.END}")

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Test failed: {e}{Colors.END}")
    finally:
        # Cleanup any remaining test files
        for pattern in ['.sd_test_*', '.sustained', '.random']:
            try:
                for f in Path(MOUNT_POINT).glob(pattern):
                    f.unlink()
            except Exception:
                pass

if __name__ == "__main__":
    # Check if we're root (some tests need it)
    if os.geteuid() != 0:
        print(f"{Colors.YELLOW}Note: Not running as root. Some tests may be less accurate.{Colors.END}")
        print(f"{Colors.YELLOW}Run with 'sudo python3 {sys.argv[0]}' for best results.{Colors.END}")

    main()
