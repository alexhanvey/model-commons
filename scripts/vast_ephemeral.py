#!/usr/bin/env python3
"""Create and destroy Vast.ai GPU instances for short, reproducible runs.

Requires:
  VAST_API_KEY environment variable
  SSH key already registered with Vast.ai
  rsync and ssh available locally

Examples:
  python scripts/vast_ephemeral.py search --gpu-name "RTX 4090" --min-vram 48000
  python scripts/vast_ephemeral.py run --gpu-name "RTX 4090" --min-vram 48000 --disk 48 \
      --sync . --command "cd /workspace/community-llm && uv sync --extra vllm"
  python scripts/vast_ephemeral.py destroy --instance-id 12345678
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "https://console.vast.ai/api/v0"
DEFAULT_IMAGE = "vastai/base-image:@vastai-automatic-tag"
BAD_STATES = {"exited", "unknown", "offline", "error"}
SYNC_EXCLUDES = [
    ".git",
    ".venv",
    ".env",
    ".env.*",
    ".sandbox",
    "runs",
    "node_modules",
    ".next",
    "__pycache__",
    "*.pyc",
    ".DS_Store",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".pnpm-store",
]


def load_dotenv() -> None:
    """Load the repo .env without overriding existing environment variables."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = value
        return


class VastError(RuntimeError):
    pass


def api(
    method: str,
    path: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    retries: int = 3,
    timeout: int = 30,
) -> dict[str, Any]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers=headers,
        method=method,
    )

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            last_error = VastError(f"Vast API {method} {path} failed {exc.code}: {detail}")
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise last_error from exc
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise VastError(f"Vast API {method} {path} failed: {exc}") from exc
    raise VastError(str(last_error))


def require_api_key(args: argparse.Namespace) -> str:
    key = args.api_key or os.environ.get("VAST_API_KEY")
    if not key:
        raise VastError("Set VAST_API_KEY or pass --api-key.")
    return key


def build_offer_query(args: argparse.Namespace) -> dict[str, Any]:
    query: dict[str, Any] = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "num_gpus": {"eq": 1},
        "direct_port_count": {"gte": 1},
        "type": "on-demand",
        "order": [["dph_total", "asc"]],
        "limit": args.limit,
    }
    if args.gpu_name:
        query["gpu_name"] = {"eq": args.gpu_name}
    if args.min_vram:
        query["gpu_ram"] = {"gte": args.min_vram}
    if args.disk:
        query["disk_space"] = {"gte": args.disk}
    if args.max_hourly:
        query["dph_total"] = {"lte": args.max_hourly}
    if getattr(args, "geolocation", None):
        query["geolocation"] = {"in": args.geolocation}
    return query


def search_offers(args: argparse.Namespace, api_key: str) -> list[dict[str, Any]]:
    response = api("POST", "/bundles/", api_key, build_offer_query(args))
    return response.get("offers", [])


def print_offers(offers: list[dict[str, Any]]) -> None:
    if not offers:
        print("No offers matched.")
        return
    print(f"{'offer_id':>12}  {'gpu':<24} {'vram_gb':>8} {'dph':>8} {'disk_gb':>8}  location")
    for offer in offers:
        print(
            f"{offer.get('id'):>12}  {str(offer.get('gpu_name')):<24} "
            f"{float(offer.get('gpu_ram') or 0) / 1024:>8.0f} "
            f"{float(offer.get('dph_total') or 0):>8.3f} "
            f"{float(offer.get('disk_space') or 0):>8.0f}  "
            f"{offer.get('geolocation', '')}"
        )


def create_instance(args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    offers = search_offers(args, api_key)
    if not offers:
        raise VastError("No offers matched. Relax --min-vram, --max-hourly, or --gpu-name.")

    offer = offers[0]
    if args.dry_run:
        print(json.dumps({"offer": offer, "create_payload": create_payload(args)}, indent=2))
        return {"dry_run": True, "offer": offer}

    print(
        f"Creating {offer.get('gpu_name')} "
        f"({float(offer.get('gpu_ram') or 0) / 1024:.0f}GB) "
        f"at ${float(offer.get('dph_total') or 0):.3f}/hr from offer {offer.get('id')}"
    )
    response = api("PUT", f"/asks/{offer['id']}/", api_key, create_payload(args))
    if not response.get("success"):
        raise VastError(f"Create failed: {response}")
    instance_id = response.get("new_contract") or response.get("id")
    if not instance_id:
        raise VastError(f"Create response had no instance ID: {response}")
    print(f"Instance ID: {instance_id}")
    return {"instance_id": int(instance_id), "offer": offer}


def create_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "image": args.image,
        "disk": args.disk,
        "label": args.label,
        "runtype": "ssh",
        "target_state": "running",
        "cancel_unavail": True,
    }


def get_instance(api_key: str, instance_id: int) -> dict[str, Any]:
    response = api("GET", f"/instances/{instance_id}/", api_key)
    instance = response.get("instances", response)
    if not isinstance(instance, dict):
        raise VastError(f"Unexpected instance response: {response}")
    return instance


def wait_for_ssh(host: str, port: int, timeout: int, interval: int = 5) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-p",
                str(port),
                f"root@{host}",
                "true",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        time.sleep(interval)
    raise VastError(f"SSH did not become ready at {host}:{port} within {timeout}s")


def wait_for_instance(args: argparse.Namespace, api_key: str, instance_id: int) -> dict[str, Any]:
    deadline = time.time() + args.boot_timeout
    last_status = None
    while time.time() < deadline:
        instance = get_instance(api_key, instance_id)
        status = instance.get("actual_status") or instance.get("status")
        if status != last_status:
            print(f"Status: {status}")
            last_status = status
        if status == "running":
            return instance
        if status in BAD_STATES:
            raise VastError(f"Instance entered bad state: {status}")
        time.sleep(args.poll_interval)
    raise VastError(f"Instance did not become ready within {args.boot_timeout}s")


def destroy_instance(args: argparse.Namespace, api_key: str, instance_id: int) -> None:
    print(f"Destroying instance {instance_id}...")
    response = api("DELETE", f"/instances/{instance_id}/", api_key)
    if not response.get("success"):
        raise VastError(f"Destroy failed: {response}")
    print("Destroyed.")


def download_path(host: str, port: int, remote: str, local: str) -> None:
    if shutil.which("rsync"):
        local_path = Path(local)
        if local.endswith("/"):
            local_path.mkdir(parents=True, exist_ok=True)
        else:
            local_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["rsync", "-avz", "-e", f"ssh -p {port}", f"root@{host}:{remote}", local],
            check=True,
        )
        return

    remote_path = Path(remote)
    parent = str(remote_path.parent) or "."
    local_path = Path(local)
    if local.endswith("/") or local_path.is_dir():
        destination = local_path
        destination.mkdir(parents=True, exist_ok=True)
    else:
        destination = local_path.parent
        destination.mkdir(parents=True, exist_ok=True)

    ssh_command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-p",
        str(port),
        f"root@{host}",
        f"tar -C {shlex.quote(parent)} -czf - {shlex.quote(remote_path.name)}",
    ]
    with subprocess.Popen(ssh_command, stdout=subprocess.PIPE) as producer:
        assert producer.stdout is not None
        result = subprocess.run(
            ["tar", "-C", str(destination), "-xzf", "-"],
            stdin=producer.stdout,
            check=False,
        )
        producer.stdout.close()
        producer_status = producer.wait()
    if producer_status != 0 or result.returncode != 0:
        raise VastError("tar download failed")


def sync_repo(local_path: Path, host: str, port: int, remote_dir: str) -> None:
    if shutil.which("rsync"):
        subprocess.run(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-p",
                str(port),
                f"root@{host}",
                f"mkdir -p {remote_dir}",
            ],
            check=True,
        )
        command = ["rsync", "-avz", "-e", f"ssh -p {port}", "--exclude", SYNC_EXCLUDES[0]]
        for item in SYNC_EXCLUDES[1:]:
            command.extend(["--exclude", item])
        command.extend([str(local_path).rstrip("/") + "/", f"root@{host}:{remote_dir}/"])
        subprocess.run(command, check=True)
        return

    remote_command = (
        f"mkdir -p {shlex.quote(remote_dir)} && tar -xzf - -C {shlex.quote(remote_dir)}"
    )
    ssh_command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-p",
        str(port),
        f"root@{host}",
        remote_command,
    ]
    tar_command = ["tar", "-C", str(local_path), "-czf", "-"]
    for item in SYNC_EXCLUDES:
        tar_command.append(f"--exclude={item}")
    tar_command.append(".")
    with subprocess.Popen(tar_command, stdout=subprocess.PIPE) as producer:
        assert producer.stdout is not None
        result = subprocess.run(
            ssh_command,
            stdin=producer.stdout,
            check=False,
        )
        producer.stdout.close()
        producer_status = producer.wait()
    if producer_status != 0 or result.returncode != 0:
        raise VastError("tar sync failed")


def run_remote(args: argparse.Namespace, api_key: str) -> int:
    created = create_instance(args, api_key)
    if created.get("dry_run"):
        return 0
    instance_id = created["instance_id"]
    start = time.time()
    destroy = True
    try:
        instance = wait_for_instance(args, api_key, instance_id)
        host = instance.get("ssh_host")
        port = instance.get("ssh_port")
        if not host or not port:
            raise VastError(f"Instance has no SSH endpoint: {instance}")
        print(f"SSH: ssh -p {port} root@{host}")
        wait_for_ssh(str(host), int(port), args.ssh_timeout)

        if args.sync:
            sync_repo(Path(args.sync).resolve(), host, int(port), args.remote_dir)

        if args.remote_command:
            remote_command = f"cd {args.remote_dir} && {args.remote_command}"
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=accept-new",
                    "-p",
                    str(port),
                    f"root@{host}",
                    remote_command,
                ],
                check=False,
            )
            if result.returncode != 0:
                destroy = not args.keep_on_failure
                raise VastError(f"Remote command failed with code {result.returncode}")
            for remote, local in args.download or []:
                download_path(host, int(port), remote, local)
        else:
            print("No --command supplied; leaving instance running. Use destroy when done.")
            destroy = False
    finally:
        elapsed = time.time() - start
        rate = float(created.get("offer", {}).get("dph_total") or 0)
        print(f"Elapsed: {elapsed / 60:.1f} min; estimated GPU cost: ${rate * elapsed / 3600:.2f}")
        if destroy:
            destroy_instance(args, api_key, instance_id)
        else:
            print(f"Instance {instance_id} kept alive.")
    return 0


def command_search(args: argparse.Namespace, api_key: str) -> int:
    offers = search_offers(args, api_key)
    print_offers(offers)
    return 0


def command_create(args: argparse.Namespace, api_key: str) -> int:
    created = create_instance(args, api_key)
    if created.get("dry_run"):
        return 0
    try:
        instance = wait_for_instance(args, api_key, created["instance_id"])
    except Exception:
        destroy_instance(args, api_key, created["instance_id"])
        raise
    print(
        json.dumps(
            {
                "instance_id": created["instance_id"],
                "ssh_host": instance.get("ssh_host"),
                "ssh_port": instance.get("ssh_port"),
                "dph_total": created["offer"].get("dph_total"),
            },
            indent=2,
        )
    )
    return 0


def command_list(args: argparse.Namespace, api_key: str) -> int:
    response = api("GET", "/instances/", api_key)
    instances = response.get("instances", [])
    for instance in instances:
        print(
            f"{instance.get('id')}  {instance.get('actual_status')}  "
            f"{instance.get('gpu_name')}  {instance.get('label', '')}"
        )
    return 0


def command_destroy(args: argparse.Namespace, api_key: str) -> int:
    destroy_instance(args, api_key, args.instance_id)
    return 0


def add_create_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gpu-name", default="RTX 4090")
    parser.add_argument("--min-vram", type=int, default=24000, help="Minimum GPU RAM in MB")
    parser.add_argument("--disk", type=int, default=48, help="Disk size in GB")
    parser.add_argument("--max-hourly", type=float, default=2.0, help="Maximum $/hour")
    parser.add_argument(
        "--geolocation", nargs="+", default=None, help="Allowed country codes, e.g. US CA"
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--label", default="community-llm-ephemeral")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--boot-timeout", type=int, default=900)
    parser.add_argument("--ssh-timeout", type=int, default=180)
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--api-key", default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search available offers")
    add_create_args(search)
    search.set_defaults(func=command_search)

    create = sub.add_parser("create", help="Create and wait for an instance; keeps it running")
    add_create_args(create)
    create.set_defaults(func=command_create)

    run = sub.add_parser("run", help="Create, sync, run a command, then destroy")
    add_create_args(run)
    run.add_argument("--sync", default=None, help="Local directory to rsync")
    run.add_argument("--remote-dir", default="/workspace/community-llm")
    run.add_argument("--remote-command", default=None, help="Remote shell command")
    run.add_argument(
        "--download",
        nargs=2,
        action="append",
        metavar=("REMOTE", "LOCAL"),
        help="Download a remote file/directory before destroying",
    )
    run.add_argument("--keep-on-failure", action="store_true")
    run.set_defaults(func=run_remote)

    destroy = sub.add_parser("destroy", help="Destroy an instance")
    destroy.add_argument("--instance-id", type=int, required=True)
    destroy.add_argument("--api-key", default=None)
    destroy.set_defaults(func=command_destroy)

    list_cmd = sub.add_parser("list", help="List your instances")
    list_cmd.add_argument("--api-key", default=None)
    list_cmd.set_defaults(func=command_list)

    return parser


def main() -> int:
    load_dotenv()
    args = build_parser().parse_args()
    try:
        api_key = require_api_key(args)
        return int(args.func(args, api_key))
    except (VastError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
