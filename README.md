# JetBot hardware test

Run the motor sequence once, then open a live CSI camera preview in your browser. The preview travels over SSH and is available only at `127.0.0.1:8765` on your computer.

## Requirements

- [uv](https://docs.astral.sh/uv/) and OpenSSH (`ssh`) on your computer (macOS or Windows).
- The course JetBot image with SSH and a running `jetbot_jupyter` container.
- The JetBot IP address and its SSH/sudo credentials. Passwords are prompted, never stored.
- Lift the wheels or place the robot in a clear, safe area before running the motor sequence.

## Run

In Terminal or PowerShell:

```sh
git clone https://github.com/henry753951/jetbot-hardware-test.git
cd jetbot-hardware-test
uv run python jetbot_test.py 192.168.0.162
```

Replace the IP with your JetBot's current address. The command sends forward, left, and right motor commands for one second each at speed `0.2`, stopping between commands and at the end. It then checks CSI 0 and CSI 1 and opens the live preview in your default browser. The terminal shows each result. Press **Ctrl+C** when finished.

Optional controls:

```sh
uv run python jetbot_test.py 192.168.0.162 --speed 0.25
uv run python jetbot_test.py 192.168.0.162 --camera-only
```

Speed must be between `0.05` and `0.5`. The software confirms commands were sent; watch the wheels to confirm physical movement.

If the JetBot has no `/dev/video*` device, the preview page shows a camera error. Check the CSI ribbon connection and reboot the JetBot before retrying. Local `uv` manages only this project's launcher; the JetBot uses Python and libraries already present in its Jupyter container.

Run the small local check with `uv run python test_jetbot.py`.
