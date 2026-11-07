from __future__ import annotations

from pathlib import Path

import pytest

from planting import guard, make_tree


def deployment(
    root: Path,
    target: str,
    *,
    pages: bool = False,
    service: bool = False,
    nginx: str | None = None,
) -> Path:
    repo = make_tree(root, "scripts/check_deploy_place.py")
    deploy = repo / "deploy"
    deploy.mkdir()
    (deploy / "TARGET").write_text(target, encoding="utf-8")
    if service:
        (deploy / "app.service").write_text("[Service]\n", encoding="utf-8")
    if nginx:
        (deploy / nginx).write_text("server {}\n", encoding="utf-8")
    if pages:
        workflow = repo / ".github" / "workflows" / "deploy-pages.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("name: Deploy Pages\n", encoding="utf-8")
    return repo


@pytest.mark.parametrize("target", ["pages\n", "vps\n"])
def test_existing_plain_targets_remain_valid(tmp_path: Path, target: str) -> None:
    repo = deployment(
        tmp_path / target.strip(),
        target,
        pages=target.strip() == "pages",
        service=target.strip() == "vps",
        nginx="domain.nginx" if target.strip() == "vps" else None,
    )
    result = guard(repo, "check_deploy_place.py", ok_marker="deploy place: OK")
    assert result.returncode == 0, result.stdout


def test_structured_static_plus_service_vps_target_is_valid(tmp_path: Path) -> None:
    target = (
        "target: vps-static+vps-service\n"
        "hostname: neuraxis.example\n"
        "static: /var/www/neuraxis.example\n"
        "service: bounded operations API\n"
    )
    repo = deployment(tmp_path / "composite", target, service=True, nginx="neuraxis.nginx.tls")
    result = guard(repo, "check_deploy_place.py", ok_marker="deploy place: OK, vps-static+vps-service only")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("service", "nginx", "message"),
    [
        (False, "site.nginx", "no service unit"),
        (True, None, "no nginx site configuration"),
    ],
)
def test_composite_vps_requires_service_and_static_host(
    tmp_path: Path, service: bool, nginx: str | None, message: str
) -> None:
    target = "target: vps-static+vps-service\n"
    repo = deployment(tmp_path / "incomplete", target, service=service, nginx=nginx)
    result = guard(repo, "check_deploy_place.py")
    assert result.returncode == 1 and message in result.stdout, result.stdout


@pytest.mark.parametrize(
    "target",
    [
        "hostname: neuraxis.example\nstatic: /var/www/neuraxis.example\n",
        "target: vps\ntarget: pages\n",
        "target:\n",
    ],
)
def test_structured_target_must_name_exactly_one_non_empty_target(tmp_path: Path, target: str) -> None:
    repo = deployment(tmp_path / "malformed", target)
    result = guard(repo, "check_deploy_place.py")
    assert result.returncode == 1 and "exactly one non-empty target field" in result.stdout, result.stdout


def test_pages_cannot_keep_a_vps_service_or_site(tmp_path: Path) -> None:
    repo = deployment(tmp_path / "mixed", "pages\n", pages=True, service=True, nginx="site.nginx")
    result = guard(repo, "check_deploy_place.py")
    assert result.returncode == 1 and "VPS files remain" in result.stdout, result.stdout
