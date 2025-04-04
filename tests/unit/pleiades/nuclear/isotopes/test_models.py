import pytest
from pydantic import ValidationError

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData, EndfLibrary

def test_isotope_info_from_string_valid():
    isotope = IsotopeInfo.from_string("U-235")
    assert isotope.name == "U-235"
    assert isotope.element == "U"
    assert isotope.mass_number == 235

    isotope = IsotopeInfo.from_string("235-U")
    assert isotope.name == "U-235"
    assert isotope.element == "U"
    assert isotope.mass_number == 235

def test_isotope_info_from_string_invalid():
    with pytest.raises(ValueError, match="Invalid isotope format"):
        IsotopeInfo.from_string("InvalidFormat")

def test_isotope_info_defaults():
    isotope = IsotopeInfo(name="U-235", element="U", mass_number=235)
    assert isotope.atomic_number is None
    assert isotope.mass_data is None
    assert isotope.abundance is None
    assert isotope.spin is None
    assert isotope.material_number is None
    assert isotope.endf_library == EndfLibrary.ENDF_B_VIII_0

def test_isotope_info_validation():
    with pytest.raises(ValidationError):
        IsotopeInfo(name="U-235", element="U", mass_number=-1)  # Invalid mass_number

    with pytest.raises(ValidationError):
        IsotopeInfo(name="U-235", element="U", mass_number=235, abundance=-0.1)  # Invalid abundance

def test_isotope_mass_data_validation():
    mass_data = IsotopeMassData(
        atomic_mass=235.0439299,
        mass_uncertainty=0.000002,
        binding_energy=7.6,
        beta_decay_energy=None
    )
    assert mass_data.atomic_mass == 235.0439299
    assert mass_data.mass_uncertainty == 0.000002
    assert mass_data.binding_energy == 7.6
    assert mass_data.beta_decay_energy is None

    with pytest.raises(ValidationError):
        IsotopeMassData(atomic_mass=235.0439299, mass_uncertainty=-0.1)  # Invalid mass_uncertainty

def test_endf_library_enum():
    assert EndfLibrary.ENDF_B_VIII_0.value == "ENDF-B-VIII.0"
    assert EndfLibrary.JEFF_3_3.value == "JEFF-3.3"
