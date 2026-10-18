from app.core.config import get_settings
from pipelines.run import main


def test_unimplemented_step_fails_loudly(capsys):
    assert main(["--dataset", "thar1_demo_2024", "--steps", "settlement"]) == 2
    assert "M3" in capsys.readouterr().err


def test_unimplemented_command_fails_loudly(capsys):
    assert main(["--command", "fetch-weather"]) == 2
    assert "M2" in capsys.readouterr().err


def test_configs_dir_resolves():
    assert (get_settings().configs_dir / "plant" / "thar1.yaml").is_file()
