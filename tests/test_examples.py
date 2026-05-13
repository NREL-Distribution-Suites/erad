import os
import sys
import subprocess
import pytest


def get_example_scripts():
    examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")
    return [os.path.join(examples_dir, f) for f in os.listdir(examples_dir) if f.endswith(".py")]


@pytest.mark.parametrize("script_path", get_example_scripts())
def test_run_example_script(script_path):
    print(script_path)
    """Test that each example script runs without error."""
    result = subprocess.run([sys.executable, script_path], capture_output=True)
    assert (
        result.returncode == 0
    ), f"Script {script_path} failed with error: {result.stderr.decode()}"
