import argparse
import os
from pathlib import Path
from typing import List, Optional


RUNWAY_TOML = "runway.toml"


def prompt(question: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{question}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        print("値が空です。もう一度入力してください。")


def build_toml(service_name: str, gcp_project_id: str, region: str) -> str:
    # 依存無しでシンプルにTOMLを構築
    return (
        """
[runway]
version = 1

[service]
name = "{service_name}"

[gcp]
project = "{project}"
region = "{region}"
""".strip().format(service_name=service_name, project=gcp_project_id, region=region)
        + "\n"
    )


def cmd_init(args: argparse.Namespace) -> int:
    # interactive wizard
    service = args.service or prompt("Please enter the service name", None)
    project = args.project or prompt("Please enter the GCP project ID for deployment", None)
    region_default = args.region or os.environ.get("GOOGLE_CLOUD_REGION") or "asia-northeast1"
    region = args.region or prompt("Please enter the region", region_default)

    config_text = build_toml(service, project, region)

    cfg_path = Path(args.output or RUNWAY_TOML)
    if cfg_path.exists() and not args.force:
        ans = input(f"{cfg_path} already exists. Do you want to overwrite it? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            print("Aborted.")
            return 1

    cfg_path.write_text(config_text, encoding="utf-8")
    print(f"Initialization complete. Configuration saved to {cfg_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runway",
        description="Cloud Runへのデプロイを",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="プロジェクトを初期化し、runway.toml を作成します")
    p_init.add_argument("--service", help="サービス名（未指定なら対話で入力）")
    p_init.add_argument("--project", help="GCPプロジェクトID（未指定なら対話で入力）")
    p_init.add_argument(
        "--region",
        help="GCPリージョン（未指定なら対話で入力。デフォルト: asia-northeast1）",
    )
    p_init.add_argument(
        "-o",
        "--output",
        help=f"出力先ファイル名（デフォルト: {RUNWAY_TOML}）",
    )
    p_init.add_argument(
        "-f", "--force", action="store_true", help="確認なしで上書き保存する"
    )
    p_init.set_defaults(func=cmd_init)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
