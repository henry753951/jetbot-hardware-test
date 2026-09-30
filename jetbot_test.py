"""Run JetBot motors once, then open a private live camera preview."""

import argparse
import http.client
import ipaddress
import secrets
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


PORT = 8765


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ip", help="JetBot IPv4 address")
    parser.add_argument("--speed", type=float, default=0.2, help="motor speed (0.05 to 0.5)")
    parser.add_argument("--camera-only", action="store_true", help="skip motor movements")
    args = parser.parse_args()

    try:
        if not isinstance(ipaddress.ip_address(args.ip), ipaddress.IPv4Address):
            raise ValueError("IPv4 required")
    except ValueError:
        parser.error("ip must be a valid IPv4 address")
    if not 0.05 <= args.speed <= 0.5:
        parser.error("speed must be between 0.05 and 0.5")
    if not shutil.which("ssh"):
        parser.error("OpenSSH (ssh) is required on this computer")

    with socket.socket() as check:
        try:
            check.bind(("127.0.0.1", PORT))
        except OSError:
            parser.error("local port {} is already in use".format(PORT))

    target = "jetbot@{}".format(args.ip)
    remote_file = "/tmp/jetbot-test-{}.py".format(secrets.token_hex(6))
    source = Path(__file__).with_name("jetbot_remote.py")
    print("Uploading JetBot test to {} ...".format(target), flush=True)
    with source.open("rb") as script:
        result = subprocess.run(
            ["ssh", "-T", "-o", "ConnectTimeout=8", target, "cat > " + remote_file],
            stdin=script,
            check=False,
        )
    if result.returncode:
        return result.returncode

    speed = "{:.2f}".format(args.speed)
    option = " --camera-only" if args.camera_only else ""
    remote_command = (
        "sudo docker exec -i -e PYTHONIOENCODING=utf-8 jetbot_jupyter "
        "python3 -u - {}{} < {}; status=$?; rm -f {}; exit $status"
    ).format(speed, option, remote_file, remote_file)
    print("Running tests (enter SSH/sudo passwords when prompted) ...", flush=True)
    process = subprocess.Popen(
        ["ssh", "-tt", "-o", "ExitOnForwardFailure=yes", "-o", "LogLevel=QUIET", "-L",
         "{0}:127.0.0.1:{0}".format(PORT), target, remote_command]
    )
    preview_url = "http://127.0.0.1:{}/".format(PORT)
    try:
        while process.poll() is None:
            connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=0.5)
            try:
                connection.request("GET", "/health")
                if connection.getresponse().status == 200:
                    break
            except (OSError, TimeoutError):
                time.sleep(0.5)
            finally:
                connection.close()
        if process.poll() is not None:
            return process.returncode
        print("Preview: {}".format(preview_url), flush=True)
        webbrowser.open_new(preview_url)
        print("Keep this terminal open. Press Ctrl+C to stop the preview.", flush=True)
        return process.wait()
    except KeyboardInterrupt:
        print("\nStopping preview ...", flush=True)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 130


if __name__ == "__main__":
    sys.exit(main())
