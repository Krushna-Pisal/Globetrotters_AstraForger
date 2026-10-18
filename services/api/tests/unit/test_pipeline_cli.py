from app.core.config import get_settings
from pipelines.run import main


def test_unimplemented_step_fails_loudly(capsys):
    assert main(["--dataset", "thar1_demo_2024", "--steps", "attribution"]) == 2
    assert "M4" in capsys.readouterr().err


def test_configs_dir_resolves():
    assert (get_settings().configs_dir / "plant" / "thar1.yaml").is_file()
