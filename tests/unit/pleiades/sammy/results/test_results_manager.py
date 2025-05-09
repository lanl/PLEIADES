from unittest.mock import MagicMock

import pytest

from pleiades.sammy.results.manager import ResultsManager
from pleiades.sammy.results.models import FitResults, RunResults
from pleiades.utils.logger import loguru_logger


@pytest.fixture(autouse=True)
def configure_loguru_logger(caplog):
    """Configure loguru logger to integrate with pytest's caplog."""
    loguru_logger.remove()  # Remove existing handlers
    loguru_logger.add(caplog.handler, format="{message}", level="INFO")


def test_results_manager_initialization():
    manager = ResultsManager()
    assert isinstance(manager.run_results, RunResults)


def test_add_fit_result():
    manager = ResultsManager()
    fit_result = FitResults()
    manager.add_fit_result(fit_result)
    assert len(manager.run_results.fit_results) == 1
    assert manager.run_results.fit_results[0] == fit_result


def test_get_single_fit_results():
    manager = ResultsManager()
    fit_result = FitResults()
    manager.add_fit_result(fit_result)
    retrieved_result = manager.get_single_fit_results(0)
    assert retrieved_result == fit_result


def test_get_single_fit_results_no_results():
    manager = ResultsManager()
    with pytest.raises(ValueError, match="No fit results available."):
        manager.get_single_fit_results(0)


def test_print_fit_result(caplog):
    manager = ResultsManager()
    fit_result = FitResults()
    manager.add_fit_result(fit_result)
    manager.print_fit_result(0)
    assert "Fit Result 0:" in caplog.text


def test_print_fit_result_no_results(caplog):
    manager = ResultsManager()
    manager.print_fit_result(0)
    assert "No fit result found at index 0." in caplog.text


def test_print_number_of_fit_results(caplog):
    manager = ResultsManager()
    manager.add_fit_result(FitResults())
    manager.print_number_of_fit_results()
    assert "Number of fit results: 1" in caplog.text


def test_print_run_results(caplog):
    manager = ResultsManager()
    fit_result = FitResults()
    manager.add_fit_result(fit_result)
    manager.print_run_results()
    assert "Fit Result:" in caplog.text


def test_print_run_results_no_results(caplog):
    manager = ResultsManager()
    manager.print_run_results()
    assert "No fit results available." in caplog.text


def test_print_results_data(caplog):
    manager = ResultsManager()
    manager.run_results.data = MagicMock()
    manager.print_results_data()
    assert "Results Data:" in caplog.text


def test_print_results_data_no_data(caplog):
    manager = ResultsManager()
    manager.print_results_data()
    assert "No results data available." in caplog.text


def test_plot_transmission():
    manager = ResultsManager()
    manager.run_results.data = MagicMock()
    manager.run_results.data.data_type = "TRANSMISSION"
    manager.plot_transmission()
    manager.run_results.data.plot_transmission.assert_called_once()


def test_plot_transmission_wrong_data_type(caplog):
    manager = ResultsManager()
    manager.run_results.data = MagicMock()
    manager.run_results.data.data_type = "CROSS_SECTION"
    manager.plot_transmission()
    assert "Data type is not transmission. Cannot plot." in caplog.text


def test_plot_cross_section():
    manager = ResultsManager()
    manager.run_results.data = MagicMock()
    manager.run_results.data.data_type = "CROSS_SECTION"
    manager.plot_cross_section()
    manager.run_results.data.plot_cross_section.assert_called_once()


def test_plot_cross_section_wrong_data_type(caplog):
    manager = ResultsManager()
    manager.run_results.data = MagicMock()
    manager.run_results.data.data_type = "TRANSMISSION"
    manager.plot_cross_section()
    assert "Data type is not cross-section. Cannot plot." in caplog.text
