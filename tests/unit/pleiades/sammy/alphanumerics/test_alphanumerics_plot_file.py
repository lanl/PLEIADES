import pytest

from pleiades.sammy.alphanumerics.plot_file import PlotFileOptions


def test_default_options():
    """Test the default options."""
    plot_options = PlotFileOptions()

    # Check default values
    assert plot_options.ev_units_on_energy_in_plot_file is False
    assert plot_options.kev_units_on_energy_in_plot_file is False
    assert plot_options.mev_units_on_energy_in_plot_file is False
    assert plot_options.odf_file_is_wanted_zeroth_order is False
    assert plot_options.odf_file_is_wanted_final_calculation is False
    assert plot_options.do_not_generate_plot_file_automatically is True  # Default
    assert plot_options.generate_plot_file_automatically is False
    assert plot_options.do_not_include_theoretical_uncertainties is True  # Default
    assert plot_options.include_theoretical_uncertainties_in_plot_file is False
    assert plot_options.plot_unbroadened_cross_sections is False

    # Check default alphanumeric commands - should only include defaults that are True
    commands = plot_options.get_alphanumeric_commands()
    assert "DO NOT GENERATE PLOT FILE AUTOMATICALLY" in commands
    assert "DO NOT INCLUDE THEORETICAL UNCERTAINTIES" in commands
    assert len(commands) == 2


def test_energy_units_options():
    """Test energy units options."""
    # Test eV units
    plot_options = PlotFileOptions(ev_units_on_energy_in_plot_file=True)
    assert plot_options.ev_units_on_energy_in_plot_file is True
    assert "EV = UNITS ON ENERGY IN PLOT FILE" in plot_options.get_alphanumeric_commands()

    # Test keV units
    plot_options = PlotFileOptions(kev_units_on_energy_in_plot_file=True)
    assert plot_options.kev_units_on_energy_in_plot_file is True
    assert "KEV = UNITS ON ENERGY IN PLOT FILE" in plot_options.get_alphanumeric_commands()

    # Test MeV units
    plot_options = PlotFileOptions(mev_units_on_energy_in_plot_file=True)
    assert plot_options.mev_units_on_energy_in_plot_file is True
    assert "MEV = UNITS ON ENERGY IN PLOT FILE" in plot_options.get_alphanumeric_commands()


def test_mutually_exclusive_energy_units():
    """Test mutual exclusivity of energy units options."""
    # Test eV and keV together - should raise error
    with pytest.raises(ValueError):
        PlotFileOptions(ev_units_on_energy_in_plot_file=True, kev_units_on_energy_in_plot_file=True)

    # Test eV and MeV together - should raise error
    with pytest.raises(ValueError):
        PlotFileOptions(ev_units_on_energy_in_plot_file=True, mev_units_on_energy_in_plot_file=True)

    # Test keV and MeV together - should raise error
    with pytest.raises(ValueError):
        PlotFileOptions(kev_units_on_energy_in_plot_file=True, mev_units_on_energy_in_plot_file=True)

    # Test all three together - should raise error
    with pytest.raises(ValueError):
        PlotFileOptions(
            ev_units_on_energy_in_plot_file=True,
            kev_units_on_energy_in_plot_file=True,
            mev_units_on_energy_in_plot_file=True,
        )


def test_odf_file_options():
    """Test ODF file options."""
    # Test zeroth order ODF
    plot_options = PlotFileOptions(odf_file_is_wanted_zeroth_order=True)
    assert plot_options.odf_file_is_wanted_zeroth_order is True
    assert "ODF FILE IS WANTED-- ZEROTH ORDER" in plot_options.get_alphanumeric_commands()

    # Test final calculation ODF
    plot_options = PlotFileOptions(odf_file_is_wanted_final_calculation=True)
    assert plot_options.odf_file_is_wanted_final_calculation is True
    assert "ODF FILE IS WANTED-- FINAL CALCULATION" in plot_options.get_alphanumeric_commands()

    # Test both ODF options together
    plot_options = PlotFileOptions(odf_file_is_wanted_zeroth_order=True, odf_file_is_wanted_final_calculation=True)
    commands = plot_options.get_alphanumeric_commands()
    assert "ODF FILE IS WANTED-- ZEROTH ORDER" in commands
    assert "ODF FILE IS WANTED-- FINAL CALCULATION" in commands


def test_plot_generation_options():
    """Test plot generation options."""
    # Test do not generate plot file (default)
    plot_options = PlotFileOptions(do_not_generate_plot_file_automatically=True, generate_plot_file_automatically=False)
    assert plot_options.do_not_generate_plot_file_automatically is True
    assert plot_options.generate_plot_file_automatically is False
    commands = plot_options.get_alphanumeric_commands()
    assert "DO NOT GENERATE PLOT FILE AUTOMATICALLY" in commands
    assert "GENERATE PLOT FILE AUTOMATICALLY" not in commands

    # Test generate plot file
    plot_options = PlotFileOptions(do_not_generate_plot_file_automatically=False, generate_plot_file_automatically=True)
    assert plot_options.do_not_generate_plot_file_automatically is False
    assert plot_options.generate_plot_file_automatically is True
    commands = plot_options.get_alphanumeric_commands()
    assert "DO NOT GENERATE PLOT FILE AUTOMATICALLY" not in commands
    assert "GENERATE PLOT FILE AUTOMATICALLY" in commands


def test_mutually_exclusive_plot_generation():
    """Test mutual exclusivity of plot generation options."""
    # Both do_not_generate and generate set to True should raise error
    with pytest.raises(ValueError):
        PlotFileOptions(do_not_generate_plot_file_automatically=True, generate_plot_file_automatically=True)


def test_theoretical_uncertainties_options():
    """Test theoretical uncertainties options."""
    # Test do not include theoretical uncertainties (default)
    plot_options = PlotFileOptions(
        do_not_include_theoretical_uncertainties=True, include_theoretical_uncertainties_in_plot_file=False
    )
    assert plot_options.do_not_include_theoretical_uncertainties is True
    assert plot_options.include_theoretical_uncertainties_in_plot_file is False
    commands = plot_options.get_alphanumeric_commands()
    assert "DO NOT INCLUDE THEORETICAL UNCERTAINTIES" in commands
    assert "INCLUDE THEORETICAL UNCERTAINTIES IN PLOT FILE" not in commands

    # Test include theoretical uncertainties
    plot_options = PlotFileOptions(
        do_not_include_theoretical_uncertainties=False, include_theoretical_uncertainties_in_plot_file=True
    )
    assert plot_options.do_not_include_theoretical_uncertainties is False
    assert plot_options.include_theoretical_uncertainties_in_plot_file is True
    commands = plot_options.get_alphanumeric_commands()
    assert "DO NOT INCLUDE THEORETICAL UNCERTAINTIES" not in commands
    assert "INCLUDE THEORETICAL UNCERTAINTIES IN PLOT FILE" in commands


def test_mutually_exclusive_theoretical_uncertainties():
    """Test mutual exclusivity of theoretical uncertainties options."""
    # Both do_not_include and include set to True should raise error
    with pytest.raises(ValueError):
        PlotFileOptions(
            do_not_include_theoretical_uncertainties=True, include_theoretical_uncertainties_in_plot_file=True
        )


def test_unbroadened_cross_section_option():
    """Test unbroadened cross section option."""
    plot_options = PlotFileOptions(plot_unbroadened_cross_sections=True)
    assert plot_options.plot_unbroadened_cross_sections is True
    assert "PLOT UNBROADENED CROSS SECTIONS" in plot_options.get_alphanumeric_commands()


def test_multiple_options():
    """Test multiple non-conflicting options together."""
    plot_options = PlotFileOptions(
        ev_units_on_energy_in_plot_file=True,
        generate_plot_file_automatically=True,
        do_not_generate_plot_file_automatically=False,
        include_theoretical_uncertainties_in_plot_file=True,
        do_not_include_theoretical_uncertainties=False,
        plot_unbroadened_cross_sections=True,
        odf_file_is_wanted_zeroth_order=True,
    )

    commands = plot_options.get_alphanumeric_commands()
    assert "EV = UNITS ON ENERGY IN PLOT FILE" in commands
    assert "GENERATE PLOT FILE AUTOMATICALLY" in commands
    assert "INCLUDE THEORETICAL UNCERTAINTIES IN PLOT FILE" in commands
    assert "PLOT UNBROADENED CROSS SECTIONS" in commands
    assert "ODF FILE IS WANTED-- ZEROTH ORDER" in commands
    assert len(commands) == 5


if __name__ == "__main__":
    pytest.main()
