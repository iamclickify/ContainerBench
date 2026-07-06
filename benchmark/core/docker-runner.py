import warnings
from benchmark.core.docker_runner import build_image

warnings.warn(
    "docker-runner is deprecated, use docker_runner instead",
    DeprecationWarning,
    stacklevel=2
)