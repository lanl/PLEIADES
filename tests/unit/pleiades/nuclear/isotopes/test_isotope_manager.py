from pathlib import Path

import pytest

from pleiades.nuclear.isotopes.manager import IsotopeManager
from pleiades.nuclear.isotopes.models import FileCategory, IsotopeInfo


@pytest.fixture
def manager():
    return IsotopeManager()


def test_initialize_cache(manager):
    manager._initialize_cache()
    print("Cached files:", manager._cached_files)
    cached_files = {file.name for file in manager._cached_files[FileCategory.ISOTOPES]}  # Extract filenames as strings
    assert "isotopes.info" in cached_files
    assert "mass.mas20" in cached_files
    assert "neutrons.list" in cached_files


def test_get_category_path():
    assert IsotopeManager._get_category_path(FileCategory.ISOTOPES) == "isotopes"


def test_get_file_path_valid(manager):
    # Grab the path to the actual files directory
    files_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "src/pleiades/nuclear/isotopes/files"
    test_file = files_dir / "isotopes.info"

    # Ensure the test file exists
    assert test_file.exists(), f"Test file {test_file} does not exist."

    # Debug: Print cached files
    print("Cached files:", manager._cached_files)

    # Call the method under test
    path = manager.get_file_path(FileCategory.ISOTOPES, "isotopes.info")

    # Assert that the returned path matches the actual file path
    assert path == test_file


def test_get_file_path_invalid_extension(manager):
    with pytest.raises(ValueError, match="Invalid file extension"):
        manager.get_file_path(FileCategory.ISOTOPES, "test.invalid")


def test_get_file_path_not_found(manager):
    with pytest.raises(FileNotFoundError, match="File test.info not found"):
        manager.get_file_path(FileCategory.ISOTOPES, "test.info")


def test_list_files(manager):
    manager._initialize_cache()
    files = manager.list_files()

    # Ensure the category exists in the returned files
    assert FileCategory.ISOTOPES in files

    # Extract filenames from the returned Path objects
    filenames = [file.name for file in files[FileCategory.ISOTOPES]]

    # Assert that the filenames match the expected list
    assert sorted(filenames) == ["isotopes.info", "mass.mas20", "neutrons.list"]


def test_list_files_invalid_category(manager):
    with pytest.raises(ValueError, match="Invalid category"):
        manager.list_files("invalid_category")


def test_validate_file(manager):
    manager._initialize_cache()
    assert manager.validate_file(FileCategory.ISOTOPES, "isotopes.info") is True
    assert manager.validate_file(FileCategory.ISOTOPES, "test.invalid") is False


def test_get_isotope_info_valid(manager):
    manager._initialize_cache()
    isotope_info = manager.get_isotope_info("U-238")

    # Assert that the returned IsotopeInfo object has the correct properties
    assert isotope_info is not None
    assert isotope_info.element == "U"
    assert isotope_info.mass_number == 238
    assert isotope_info.mass_data is not None
    assert isotope_info.abundance is not None
    assert isotope_info.spin is not None


def test_check_and_get_mass_data_valid(manager):
    manager._initialize_cache()
    mass_data = manager.check_and_get_mass_data("U", 238)

    # Assert that the returned IsotopeMassData object has the correct properties
    assert mass_data is not None
    assert mass_data.atomic_mass > 0
    assert mass_data.mass_uncertainty >= 0
    assert mass_data.binding_energy is not None
    assert mass_data.beta_decay_energy is not None


def test_check_and_get_mass_data_invalid(manager):
    manager._initialize_cache()
    with pytest.raises(ValueError, match="Mass data for Invalid-999 not found"):
        manager.check_and_get_mass_data("Invalid", 999)


def test_check_and_set_abundance_and_spins_valid(manager):
    manager._initialize_cache()
    isotope_info = IsotopeInfo(name="U-238", element="U", mass_number=238)

    # Call the method to set abundance and spin
    manager.check_and_set_abundance_and_spins(isotope_info)

    # Assert that the abundance and spin are set correctly
    assert isotope_info.abundance is not None
    assert isotope_info.spin is not None


def test_check_and_set_abundance_and_spins_invalid(manager):
    manager._initialize_cache()
    isotope_info = IsotopeInfo(name="Invalid-999", element="Invalid", mass_number=999)

    # Call the method with an invalid isotope
    manager.check_and_set_abundance_and_spins(isotope_info)

    # Assert that abundance and spin remain unset
    assert isotope_info.abundance is None
    assert isotope_info.spin is None


def test_get_mat_number_valid(manager):
    manager._initialize_cache()
    isotope_info = IsotopeInfo(name="U-238", element="U", mass_number=238)

    # Call the method to get the MAT number
    mat_number = manager.get_mat_number(isotope_info)

    # Assert that the MAT number is returned correctly
    assert mat_number is not None
    assert isinstance(mat_number, int)


def test_get_mat_number_invalid(manager):
    manager._initialize_cache()
    isotope_info = IsotopeInfo(name="Invalid-999", element="Invalid", mass_number=999)

    # Call the method with an invalid isotope
    mat_number = manager.get_mat_number(isotope_info)

    # Assert that None is returned for an invalid isotope
    assert mat_number is None


# =============================================================================
# Tests for get_isotopes_by_element() and get_natural_composition()
# Issue #204: Replace hardcoded demo values with data-driven isotope lookup
# =============================================================================


class TestGetIsotopesByElement:
    """Tests for IsotopeManager.get_isotopes_by_element()."""

    def test_hafnium_returns_six_isotopes(self, manager):
        """Hafnium has 6 naturally occurring isotopes."""
        isotopes = manager.get_isotopes_by_element("Hf")
        assert len(isotopes) == 6
        assert set(isotopes) == {"Hf-174", "Hf-176", "Hf-177", "Hf-178", "Hf-179", "Hf-180"}

    def test_gold_returns_one_isotope(self, manager):
        """Gold (Au) has only one naturally occurring isotope."""
        isotopes = manager.get_isotopes_by_element("Au")
        assert len(isotopes) == 1
        assert isotopes == ["Au-197"]

    def test_uranium_returns_natural_isotopes(self, manager):
        """Uranium has 3 naturally occurring isotopes (234, 235, 238)."""
        isotopes = manager.get_isotopes_by_element("U")
        assert len(isotopes) == 3
        assert set(isotopes) == {"U-234", "U-235", "U-238"}

    def test_case_insensitive_lookup(self, manager):
        """Element lookup should be case-insensitive."""
        isotopes_upper = manager.get_isotopes_by_element("HF")
        isotopes_lower = manager.get_isotopes_by_element("hf")
        isotopes_mixed = manager.get_isotopes_by_element("Hf")
        assert isotopes_upper == isotopes_mixed
        assert isotopes_lower == isotopes_mixed

    def test_invalid_element_returns_empty_list(self, manager):
        """Invalid element should return empty list, not raise exception."""
        isotopes = manager.get_isotopes_by_element("Xx")
        assert isotopes == []

    def test_results_sorted_by_mass_number(self, manager):
        """Results should be sorted by mass number."""
        isotopes = manager.get_isotopes_by_element("Hf")
        mass_numbers = [int(iso.split("-")[1]) for iso in isotopes]
        assert mass_numbers == sorted(mass_numbers)

    def test_excludes_radioactive_isotopes(self, manager):
        """By default, should only return stable (naturally occurring) isotopes.

        Uranium is special - its isotopes are marked radioactive (*) in isotopes.info
        but they do have natural abundances. We include isotopes with non-zero abundance.
        """
        # Carbon has C-12, C-13 stable and C-14 radioactive (no natural abundance)
        isotopes = manager.get_isotopes_by_element("C")
        assert "C-14" not in isotopes  # Radioactive with 0.0 abundance
        assert "C-12" in isotopes
        assert "C-13" in isotopes


class TestGetNaturalComposition:
    """Tests for IsotopeManager.get_natural_composition()."""

    def test_hafnium_abundances_as_fractions(self, manager):
        """Abundances should be returned as fractions (0-1), not percentages."""
        composition = manager.get_natural_composition("Hf")
        # Values from isotopes.info are in percent, method should convert to fractions
        assert abs(composition["Hf-174"] - 0.0016) < 0.0001
        assert abs(composition["Hf-176"] - 0.0526) < 0.0001
        assert abs(composition["Hf-177"] - 0.1860) < 0.0001
        assert abs(composition["Hf-178"] - 0.2728) < 0.0001
        assert abs(composition["Hf-179"] - 0.1362) < 0.0001
        assert abs(composition["Hf-180"] - 0.3508) < 0.0001

    def test_abundances_sum_to_one(self, manager):
        """Natural abundances should sum to approximately 1.0."""
        composition = manager.get_natural_composition("Hf")
        total = sum(composition.values())
        assert abs(total - 1.0) < 0.01  # Allow small rounding error

    def test_gold_single_isotope_is_100_percent(self, manager):
        """Single-isotope elements should have abundance ~1.0."""
        composition = manager.get_natural_composition("Au")
        assert len(composition) == 1
        assert abs(composition["Au-197"] - 1.0) < 0.01

    def test_case_insensitive_lookup(self, manager):
        """Element lookup should be case-insensitive."""
        comp_upper = manager.get_natural_composition("HF")
        comp_lower = manager.get_natural_composition("hf")
        comp_mixed = manager.get_natural_composition("Hf")
        assert comp_upper == comp_mixed
        assert comp_lower == comp_mixed

    def test_invalid_element_returns_empty_dict(self, manager):
        """Invalid element should return empty dict, not raise exception."""
        composition = manager.get_natural_composition("Xx")
        assert composition == {}

    def test_includes_zero_abundance_isotopes(self, manager):
        """Should include isotopes with zero spin (and non-zero abundance) but not radioactive zeros.

        Some stable isotopes have zero nuclear spin but non-zero abundance.
        Example: Hf-174 has spin 0.0 but abundance 0.16%.
        """
        composition = manager.get_natural_composition("Hf")
        # Hf-174 has spin 0.0 but should be included (has natural abundance)
        assert "Hf-174" in composition
        assert composition["Hf-174"] > 0

    def test_uranium_natural_composition(self, manager):
        """Test uranium's known natural composition."""
        composition = manager.get_natural_composition("U")
        # U-238 is ~99.27%, U-235 is ~0.72%, U-234 is ~0.0055%
        assert "U-238" in composition
        assert "U-235" in composition
        assert "U-234" in composition
        assert composition["U-238"] > 0.99  # Most abundant
        assert composition["U-235"] > 0.007  # ~0.72%
