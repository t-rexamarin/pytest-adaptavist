"""Test general plugin functionality."""

from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize("marker", ["mark.block", "mark.project", "mark.testcase"])
def test_adaptavist_markers(pytester: pytest.Pytester, marker: str):
    """Test registration of custom markers."""
    result = pytester.runpytest("--markers")
    assert any(marker in line for line in result.stdout.lines)


def test_adaptavist_disabled(pytester: pytest.Pytester):
    """Test absence of adaptavist config if disabled."""
    config = pytester.parseconfig()
    assert not config.getoption("adaptavist")
    assert not config.getini("adaptavist")


def test_adaptavist_enabled(pytester: pytest.Pytester):
    """Test presence of adaptavist config if enabled."""
    config = pytester.parseconfig("--adaptavist")
    assert config.getoption("adaptavist")

    pytester.makeini("""
        [pytest]
        adaptavist = 1
    """)
    config = pytester.parseconfig()
    assert config.getini("adaptavist")


@pytest.mark.usefixtures("adaptavist")
def test_block_decorator(pytester: pytest.Pytester):
    """Test block decorator."""
    pytester.makepyfile("""
        import pytest

        @pytest.mark.block()
        def test_dummy():
            assert True
    """)
    outcome = pytester.runpytest().parseoutcomes()
    assert outcome["blocked"] == 1
    assert "passed" not in outcome


@pytest.mark.usefixtures("adaptavist")
def test_block_call(pytester: pytest.Pytester):
    """Test calling block."""
    pytester.makepyfile("""
        import pytest

        def test_dummy():
            pytest.block()
            assert True
    """)
    outcome = pytester.runpytest().parseoutcomes()
    assert outcome["blocked"] == 1
    assert "passed" not in outcome


@pytest.mark.usefixtures("adaptavist")
def test_xdist_handling(pytester):
    """Test coexistence with xdist."""
    pytester.makepyfile("""
        import pytest
        def test_dummy():
            assert True
    """)
    with patch("_pytest.config.PytestPluginManager.hasplugin", return_value=True):
        config = pytester.parseconfigure("--adaptavist")
        assert config.pluginmanager.getplugin("_xdist_adaptavist")
    with patch("_pytest.config.PytestPluginManager.hasplugin", return_value=False):
        config = pytester.parseconfigure("--adaptavist")
        assert not config.pluginmanager.getplugin("_xdist_adaptavist")


def test_adaptavist_reporting(pytester: pytest.Pytester, adaptavist: Tuple[MagicMock, MagicMock, MagicMock]):
    """Test reporting results to Adaptavist."""
    pytester.makepyfile("""
        import pytest

        def test_TEST_T123():
            assert True
    """)
    ctr, _, _ = adaptavist
    pytester.runpytest("--adaptavist")
    ctr.assert_called_once_with(test_run_key="TEST-C1", test_case_key="TEST-T123", environment="")


@pytest.mark.usefixtures("adaptavist")
def test_unknown_user(pytester: pytest.Pytester):
    """Test the correct behavior of an unknown user."""
    pytester.makepyfile("""
        import pytest

        def test_TEST_T123():
            assert True
    """)
    with patch("pytest_adaptavist.atm_user_is_valid", return_value=False):
        report = pytester.runpytest("--adaptavist")
        assert any("is not known in Adaptavist" in x for x in report.outlines)

        report = pytester.runpytest()
        assert all(" is not known in Adaptavist" not in x for x in report.outlines)
