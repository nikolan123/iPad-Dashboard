import posixpath
import socket
import sys
import time
from pathlib import Path

import paramiko


IPAD_HOST = "192.168.1.25"
IPAD_USER = "root"
IPAD_PASSWORD = "alpine"

LOCAL_IPA_PATH = r"Y:\Dashboard\Dashboard-unsigned.ipa"
REMOTE_WORK_DIR = "/var/mobile/Documents"
REMOTE_SOURCE_IPA = "Dashboard-unsigned.ipa"
REMOTE_FIXED_IPA = "Dashboard-fixed.ipa"
APP_BUNDLE_ID = "com.richhong.dashboard"
APP_NAME = "Dashboard"


def log(message):
    print(f"[install_on_ipad] {message}", flush=True)


def run_command_streaming(client, command, timeout=600):
    log("Starting remote shell command...")
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout, get_pty=True)
    channel = stdout.channel
    chunks = []

    while True:
        made_progress = False

        while channel.recv_ready():
            data = channel.recv(4096)
            if not data:
                break
            text = data.decode("utf-8", "replace")
            chunks.append(text)
            sys.stdout.write(text)
            sys.stdout.flush()
            made_progress = True

        while channel.recv_stderr_ready():
            data = channel.recv_stderr(4096)
            if not data:
                break
            text = data.decode("utf-8", "replace")
            chunks.append(text)
            sys.stderr.write(text)
            sys.stderr.flush()
            made_progress = True

        if channel.exit_status_ready():
            while channel.recv_ready():
                data = channel.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8", "replace")
                chunks.append(text)
                sys.stdout.write(text)
                sys.stdout.flush()
            while channel.recv_stderr_ready():
                data = channel.recv_stderr(4096)
                if not data:
                    break
                text = data.decode("utf-8", "replace")
                chunks.append(text)
                sys.stderr.write(text)
                sys.stderr.flush()
            break

        if not made_progress:
            time.sleep(0.2)

    code = channel.recv_exit_status()
    return code, "".join(chunks)


def main():
    local_ipa = Path(LOCAL_IPA_PATH)
    remote_source_path = posixpath.join(REMOTE_WORK_DIR, REMOTE_SOURCE_IPA)
    remote_fixed_path = posixpath.join(REMOTE_WORK_DIR, REMOTE_FIXED_IPA)

    if not local_ipa.exists():
        raise SystemExit(f"Local IPA not found: {local_ipa}")

    log(f"Local IPA: {local_ipa}")
    log(f"Local IPA size: {local_ipa.stat().st_size:,} bytes")
    log(f"iPad target: {IPAD_USER}@{IPAD_HOST}")
    log(f"Remote work dir: {REMOTE_WORK_DIR}")
    log(f"Remote source IPA: {remote_source_path}")
    log(f"Remote fixed IPA: {remote_fixed_path}")

    log("Opening SFTP transport to upload IPA...")
    transport = paramiko.Transport((IPAD_HOST, 22))
    transport.banner_timeout = 20
    transport.connect(username=IPAD_USER, password=IPAD_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        try:
            sftp.chdir(REMOTE_WORK_DIR)
        except IOError:
            log(f"Remote directory missing, creating {REMOTE_WORK_DIR}...")
            sftp.mkdir(REMOTE_WORK_DIR)

        def progress(sent, total):
            percent = (sent / total * 100) if total else 100
            sys.stdout.write(f"\r[install_on_ipad] Uploading IPA: {sent:,}/{total:,} bytes ({percent:5.1f}%)")
            sys.stdout.flush()

        log("Uploading IPA to iPad...")
        sftp.put(str(local_ipa), remote_source_path, callback=progress)
        sys.stdout.write("\n")
        sys.stdout.flush()
        sftp.chmod(remote_source_path, 0o644)
        remote_stat = sftp.stat(remote_source_path)
        log(f"Upload complete. Remote IPA size: {remote_stat.st_size:,} bytes")
    finally:
        log("Closing SFTP transport.")
        sftp.close()
        transport.close()

    log("Opening SSH session for unzip, fakesign, package, install, and uicache...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        IPAD_HOST,
        username=IPAD_USER,
        password=IPAD_PASSWORD,
        timeout=20,
        look_for_keys=False,
        allow_agent=False,
    )

    remote_script = f"""\
set -e
echo "[remote] working in {REMOTE_WORK_DIR}"
cd {REMOTE_WORK_DIR}
echo "[remote] cleaning old temp files"
rm -rf {APP_NAME}-fakesign Payload {REMOTE_FIXED_IPA} ent.plist
echo "[remote] creating temp directory"
mkdir {APP_NAME}-fakesign
cd {APP_NAME}-fakesign
echo "[remote] unzipping {REMOTE_SOURCE_IPA}"
unzip -q ../{REMOTE_SOURCE_IPA}
echo "[remote] writing entitlements plist"
cat > ent.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>application-identifier</key>
    <string>{APP_BUNDLE_ID}</string>
    <key>get-task-allow</key>
    <true/>
</dict>
</plist>
EOF
echo "[remote] fakesigning app binary with ldid"
ldid -Sent.plist Payload/{APP_NAME}.app/{APP_NAME}
echo "[remote] packaging fixed ipa"
zip -qry ../{REMOTE_FIXED_IPA} Payload
cd ..
echo "[remote] installing fixed ipa with appinst"
appinst {posixpath.join(REMOTE_WORK_DIR, REMOTE_FIXED_IPA)}
echo "[remote] refreshing icon cache"
uicache
echo "[remote] final ipa info"
ls -l {REMOTE_FIXED_IPA}
"""

    try:
        log("Running remote install pipeline...")
        code, _ = run_command_streaming(client, remote_script)
        log(f"Remote command exit code: {code}")
        if code != 0:
            raise SystemExit(code)
        log("Install completed successfully.")
    except (socket.timeout, TimeoutError) as exc:
        raise SystemExit(f"Network timeout while talking to the iPad: {exc}")
    finally:
        log("Closing SSH session.")
        client.close()


if __name__ == "__main__":
    main()
