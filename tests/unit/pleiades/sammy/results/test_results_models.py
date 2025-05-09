import pytest
from pleiades.sammy.results.models import FitResults, RunResults, ChiSquaredResults
from pleiades.experimental.models import PhysicsParameters
from pleiades.nuclear.models import nuclearParameters
from pleiades.sammy.data.options import sammyData


def test_fit_results_initialization():
    fit_results = FitResults()
    assert isinstance(fit_results.nuclear_data, nuclearParameters)
    assert isinstance(fit_results.physics_data, PhysicsParameters)
    assert isinstance(fit_results.chi_squared_results, ChiSquaredResults)


def test_fit_results_update_nuclear_data():
    fit_results = FitResults()
    new_nuclear_data = nuclearParameters()
    fit_results.update_nuclear_data(new_nuclear_data)
    assert fit_results.nuclear_data == new_nuclear_data


def test_fit_results_update_physics_data():
    fit_results = FitResults()
    new_physics_data = PhysicsParameters()
    fit_results.update_physics_data(new_physics_data)
    assert fit_results.physics_data == new_physics_data


def test_fit_results_getters():
    fit_results = FitResults()
    assert fit_results.get_nuclear_data() == fit_results.nuclear_data
    assert fit_results.get_physics_data() == fit_results.physics_data
    assert fit_results.get_chi_squared_results() == fit_results.chi_squared_results


def test_run_results_initialization():
    run_results = RunResults()
    assert isinstance(run_results.fit_results, list)
    assert isinstance(run_results.data, sammyData)
    assert len(run_results.fit_results) == 0


def test_run_results_add_fit_result():
    run_results = RunResults()
    fit_result = FitResults()
    run_results.add_fit_result(fit_result)
    assert len(run_results.fit_results) == 1
    assert run_results.fit_results[0] == fit_result
