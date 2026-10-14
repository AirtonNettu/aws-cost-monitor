"""Testes para o parser de argumentos de linha de comando."""

from src.main import parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert args.days is None
    assert args.granularity is None
    assert args.format is None
    assert args.no_ai is False
    assert args.dashboard is False
    assert args.no_db is False


def test_parse_args_custom():
    args = parse_args([
        "--days", "15",
        "--granularity", "DAILY",
        "--format", "html",
        "--tag", "Environment",
        "--no-ai",
        "--no-db",
    ])
    assert args.days == 15
    assert args.granularity == "DAILY"
    assert args.format == "html"
    assert args.tag == "Environment"
    assert args.no_ai is True
    assert args.no_db is True


def test_parse_args_dashboard_flag():
    args = parse_args(["--dashboard"])
    assert args.dashboard is True
