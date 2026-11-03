import subprocess


class Adb:
    def __init__(self, runner=None, *, serial=None):
        self.serial = serial
        self.runner = runner or self._run

    def _run(self, args):
        return subprocess.run(["adb", *args], text=True, capture_output=True, check=False)

    def command(self, *args):
        # Prepend -s <serial> at the command level so the serial flag is honoured
        # regardless of whether a custom runner is injected (e.g. in tests).
        prefixed = (["-s", self.serial] if self.serial else []) + list(args)
        result = self.runner(prefixed)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "adb command failed")
        return result.stdout.strip()

    def devices(self):
        return self.command("devices")

    def shell(self, *args):
        return self.command("shell", *args)
