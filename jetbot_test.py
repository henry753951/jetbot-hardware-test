"""Run JetBot motors once, then open a private live camera preview."""

import argparse
import asyncio
import http.client
import ipaddress
import secrets
import sys
import webbrowser
from pathlib import Path

import asyncssh


PORT = 8765
USERNAME = "jetbot"
PASSWORD = "jetbot"


def preview_ready():
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=0.5)
    try:
        connection.request("GET", "/health")
        return connection.getresponse().status == 200
    except (OSError, TimeoutError):
        return False
    finally:
        connection.close()


async def show_output(stream, destination):
    async for line in stream:
        print(line, end="", file=destination, flush=True)


async def run(args):
    remote_file = "/tmp/jetbot-test-{}.py".format(secrets.token_hex(6))
    source = Path(__file__).with_name("jetbot_remote.py")
    print("Connecting to {} ...".format(args.ip), flush=True)
    async with asyncssh.connect(
        args.ip,
        username=USERNAME,
        password=PASSWORD,
        known_hosts=None,
        client_keys=None,
        connect_timeout=8,
    ) as connection:
        upload = await connection.run(
            "cat > " + remote_file,
            input=source.read_text(encoding="utf-8"),
        )
        if upload.exit_status:
            print(upload.stderr, file=sys.stderr)
            return upload.exit_status

        forward = await connection.forward_local_port("127.0.0.1", PORT, "127.0.0.1", PORT)
        speed = "{:.2f}".format(args.speed)
        option = " --camera-only" if args.camera_only else ""
        script = (
            "docker exec -i -e PYTHONIOENCODING=utf-8 jetbot_jupyter "
            "python3 -u - {}{} < {}; status=$?; rm -f {}; exit $status"
        ).format(speed, option, remote_file, remote_file)
        command = "sudo -S -p '' sh -c '{}'".format(script)
        print("Running JetBot tests ...", flush=True)
        process = await connection.create_process(command, encoding="utf-8")
        process.stdin.write(PASSWORD + "\n")
        process.stdin.write_eof()
        stdout = asyncio.create_task(show_output(process.stdout, sys.stdout))
        stderr = asyncio.create_task(show_output(process.stderr, sys.stderr))
        finished = asyncio.create_task(process.wait())
        try:
            while not finished.done():
                if await asyncio.to_thread(preview_ready):
                    preview_url = "http://127.0.0.1:{}/".format(PORT)
                    print("Preview: {}".format(preview_url), flush=True)
                    webbrowser.open_new(preview_url)
                    print("Keep this terminal open. Press Ctrl+C to stop the preview.", flush=True)
                    break
                await asyncio.sleep(0.5)
            result = await finished
            await asyncio.gather(stdout, stderr)
            return result.exit_status
        finally:
            if not finished.done():
                process.terminate()
            forward.close()


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

    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopping preview ...", flush=True)
        return 130
    except (OSError, asyncssh.Error) as error:
        print("Connection failed: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
