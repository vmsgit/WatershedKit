from pathlib import Path
import os

PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "inputs"
OUTPUT_DIR = PROJECT_DIR / "outputs"
DEFAULT_DEM_NAME = "input_dem.tif"


def get_demo_dem_path():
    """Return the DEM path from an environment override or the repo default."""
    env_path = os.getenv("WATERSHEDKIT_DEM")
    if env_path:
        env_file = Path(env_path).expanduser()
        if env_file.exists():
            return env_file

    default_path = INPUT_DIR / DEFAULT_DEM_NAME
    if default_path.exists():
        return default_path

    return default_path
