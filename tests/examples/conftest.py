"""Fixtures for testing the examples."""

import pathlib
import re
import shutil
from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture(scope="session")
def examples_dir() -> pathlib.Path:
    """Return the Path of the examples directory."""
    examples_dir = pathlib.Path(__file__).parent.parent.parent.joinpath("examples").resolve()
    assert examples_dir.exists()
    assert examples_dir.is_dir()
    return examples_dir


@pytest.fixture(scope="session")
def fixture_dir(
    tmp_path_factory: pytest.TempPathFactory,
    backend_tf_builder: Callable[..., None],
    common_fixture_dir_ignores: Callable[[Any, list[str]], set[str]],
    root_module_dir: pathlib.Path,
    managed_module_dir: pathlib.Path,
    examples_dir: pathlib.Path,
) -> Callable[[str], pathlib.Path]:
    """Return a builder that makes a copy of the example with modified backend and module source set to local copy."""
    root_module_pattern = re.compile(
        pattern=r'source\s*=\s*"(?:(?:registry.(?:opentofu|terraform).io/)?memes/tls-certificate/google|(?:git::)?https://github\.com/memes/terraform-google-tls-certificate/?(?:\?ref=.*)?)"\B(?:\s*version\s*=\s*".*"\B)?',
        flags=re.MULTILINE,
    )
    managed_module_pattern = re.compile(
        pattern=r'source\s*=\s*"(?:(?:registry.(?:opentofu|terraform).io/)?memes/tls-certificate/google//modules/managed|(?:git::)?https://github\.com/memes/terraform-google-tls-certificate//modules/managed/?(?:\?ref=.*)?)"\B(?:\s*version\s*=\s*".*"\B)?',
        flags=re.MULTILINE,
    )

    def _builder(name: str) -> pathlib.Path:
        fixture_dir = tmp_path_factory.mktemp(name)
        source_dir = examples_dir.joinpath(name).resolve()
        assert source_dir.exists()
        assert source_dir.is_dir()
        assert source_dir.joinpath("main.tf").exists()
        shutil.copytree(
            src=examples_dir,
            dst=fixture_dir,
            dirs_exist_ok=True,
            ignore=common_fixture_dir_ignores,
        )
        backend_tf_builder(
            fixture_dir=fixture_dir,
            name=name,
        )
        main_tf = fixture_dir.joinpath("main.tf").resolve()
        assert main_tf.exists()
        assert main_tf.is_file()
        with main_tf.open(mode="r+", encoding="utf-8") as f:
            original = f.read()
            modified = re.sub(
                pattern=root_module_pattern,
                repl=f'source = "{root_module_dir.name}/"',
                string=re.sub(
                    pattern=managed_module_pattern,
                    repl=f'source = "{managed_module_dir.name}/"',
                    string=original,
                ),
            )
            f.seek(0)
            f.write(modified)
            f.truncate()

        return fixture_dir

    return _builder
