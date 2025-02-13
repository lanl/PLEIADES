#!/usr/bin/env python
"""Unit tests for SAMMY parameter file parsing."""

import os
import pathlib
import tempfile
from typing import Generator

import pytest

from pleiades.sammy.parameters.helper import VaryFlag
from pleiades.sammy.parfile import SammyParameterFile


@pytest.fixture
def basic_fudge_input():
    """Sample input with just fudge factor."""
    return "0.1000\n"


@pytest.fixture
def single_card_input():
    """Sample input with fudge factor and single broadening card."""
    return (
        "0.1000\n"
        "BROADening parameters may be varied\n"
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0\n"
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02\n"
        "\n"
    )


@pytest.fixture
def multi_card_input():
    """Sample input with multiple cards."""
    return (
        "0.1000\n"
        "BROADening parameters may be varied\n"
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0\n"
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02\n"
        "\n"
        "NORMAlization and background are next\n"
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0\n"
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02\n"
        "\n"
    )


def test_parse_fudge_only(basic_fudge_input):
    """Test parsing file with only fudge factor."""
    parfile = SammyParameterFile.from_string(basic_fudge_input)
    assert parfile.fudge == pytest.approx(0.1)
    assert parfile.broadening is None
    assert parfile.resonance is None
    assert parfile.normalization is None


def test_parse_single_card(single_card_input):
    """Test parsing file with fudge factor and single broadening card."""
    parfile = SammyParameterFile.from_string(single_card_input)

    # Check fudge factor
    assert parfile.fudge == pytest.approx(0.1)

    # Check broadening card parsed correctly
    assert parfile.broadening is not None
    assert parfile.broadening.parameters.crfn == pytest.approx(1.234)
    assert parfile.broadening.parameters.temp == pytest.approx(298.0)
    assert parfile.broadening.parameters.flag_crfn == VaryFlag.YES

    # Verify other cards are None
    assert parfile.resonance is None
    assert parfile.normalization is None
    assert parfile.radius is None


def test_parse_multi_card(multi_card_input):
    """Test parsing file with multiple cards."""
    parfile = SammyParameterFile.from_string(multi_card_input)

    # Check fudge factor
    assert parfile.fudge == pytest.approx(0.1)

    # Check broadening card
    assert parfile.broadening is not None
    assert parfile.broadening.parameters.crfn == pytest.approx(1.234)

    # Check normalization card
    assert parfile.normalization is not None
    assert parfile.normalization.angle_sets[0].anorm == pytest.approx(1.234)


def test_roundtrip_single_card(single_card_input):
    """Test round-trip parsing and formatting of single card file."""
    parfile = SammyParameterFile.from_string(single_card_input)
    output = parfile.to_string()
    reparsed = SammyParameterFile.from_string(output)

    # Compare original and reparsed objects
    assert parfile.fudge == reparsed.fudge
    assert parfile.broadening.parameters.crfn == reparsed.broadening.parameters.crfn
    assert parfile.broadening.parameters.temp == reparsed.broadening.parameters.temp
    assert parfile.broadening.parameters.flag_crfn == reparsed.broadening.parameters.flag_crfn


@pytest.mark.parametrize(
    "invalid_input,error_pattern",
    [
        ("", "Empty parameter file content"),
        ("abc\n", "Failed to parse"),
        ("0.1\nINVALID card header\n", "Failed to parse"),
        ("0.1\nBROADening parameters may be varied\nINVALID DATA\n", "Failed to parse BROADENING card"),
    ],
)
def test_parse_errors(invalid_input, error_pattern):
    """Test error handling for invalid inputs."""
    with pytest.raises(ValueError, match=error_pattern):
        tmp = SammyParameterFile.from_string(invalid_input)
        print(tmp)


@pytest.fixture
def temp_dir() -> Generator[pathlib.Path, None, None]:
    """Provide temporary directory for file I/O tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield pathlib.Path(tmpdir)


class TestFileIO:
    """Test suite for file I/O operations."""

    def test_write_and_read(self, temp_dir, single_card_input):
        """Test writing file to disk and reading it back."""
        # Create parameter file from input
        parfile = SammyParameterFile.from_string(single_card_input)

        # Write to temporary file
        test_file = temp_dir / "test_params.txt"
        parfile.to_file(test_file)

        # Verify file exists and has content
        assert test_file.exists()
        assert test_file.stat().st_size > 0

        # Read file back
        loaded = SammyParameterFile.from_file(test_file)

        # Compare objects
        assert loaded.fudge == parfile.fudge
        assert loaded.broadening is not None
        assert loaded.broadening.parameters.crfn == parfile.broadening.parameters.crfn
        assert loaded.broadening.parameters.temp == parfile.broadening.parameters.temp
        assert loaded.broadening.parameters.flag_crfn == parfile.broadening.parameters.flag_crfn

    def test_write_to_nested_path(self, temp_dir):
        """Test writing to nested directory structure."""
        nested_path = temp_dir / "a" / "b" / "c" / "params.txt"

        parfile = SammyParameterFile(fudge=0.1)
        parfile.to_file(nested_path)

        assert nested_path.exists()

        loaded = SammyParameterFile.from_file(nested_path)
        assert loaded.fudge == pytest.approx(0.1)

    def test_file_not_found(self, temp_dir):
        """Test error handling for non-existent file."""
        missing_file = temp_dir / "missing.txt"
        with pytest.raises(FileNotFoundError):
            SammyParameterFile.from_file(missing_file)

    def test_invalid_encoding(self, temp_dir):
        """Test error handling for invalid file encoding."""
        bad_file = temp_dir / "bad_encoding.txt"

        # Write some binary data
        bad_file.write_bytes(b"\x80\x81")

        with pytest.raises(ValueError, match="invalid encoding"):
            SammyParameterFile.from_file(bad_file)

    def test_write_permissions(self, temp_dir):
        """Test error handling for write permission issues."""
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_file = readonly_dir / "params.txt"

        # Make directory readonly
        os.chmod(readonly_dir, 0o444)

        parfile = SammyParameterFile(fudge=0.1)
        with pytest.raises(OSError):
            parfile.to_file(readonly_file)

    def test_full_roundtrip(self, temp_dir):
        """Test complete round-trip with all parameter types.

        Creates a parameter file with all supported card types,
        writes it to disk, reads it back, and verifies all parameters
        match exactly.
        """
        # Create sample parameter file with all card types
        input_str = (
            # First resonance table
            "-3.6616E+06 1.5877E+05 3.6985E+09                       0 0 1     1\n"
            "-8.7373E+05 1.0253E+03 1.0151E+02                       0 0 1     1\n"
            "\n"
            # Then fudge factor
            "0.1000\n"
            # Then broadening parameters
            "BROADening parameters may be varied\n"
            "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0\n"
            "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02\n"
            "\n"
            # Then normalization parameters
            "NORMAlization and background are next\n"
            "1.000E+00 2.000E-02 3.000E-03 4.000E-04 5.000E-05 6.000E-06  1 0 1 0 1 0\n"
            "1.000E-02 2.000E-03 3.000E-04 4.000E-05 5.000E-06 6.000E-07\n"
            "\n"
            # Then radius parameters
            # "RADIUs parameters follow\n"
            # "     3.200     3.200    0    1   -1  101  102  103\n"
            # "\n"
            # Finally data reduction parameters
            "DATA reduction parameters are next\n"
            "PAR1  1   1.234E+00 5.000E-02 1.234E+00\n"
            "PAR2  0   2.345E+00 1.000E-02\n"
            "\n"
        )

        # Create initial parameter file
        orig_parfile = SammyParameterFile.from_string(input_str)

        # Write to file
        test_file = temp_dir / "full_params.txt"
        orig_parfile.to_file(test_file)

        # Read back
        loaded_parfile = SammyParameterFile.from_file(test_file)

        # Compare fudge factor
        assert loaded_parfile.fudge == pytest.approx(orig_parfile.fudge)

        # Compare broadening parameters
        assert loaded_parfile.broadening is not None
        assert orig_parfile.broadening is not None
        assert loaded_parfile.broadening.parameters.crfn == pytest.approx(orig_parfile.broadening.parameters.crfn)
        assert loaded_parfile.broadening.parameters.temp == pytest.approx(orig_parfile.broadening.parameters.temp)
        assert loaded_parfile.broadening.parameters.thick == pytest.approx(orig_parfile.broadening.parameters.thick)
        assert loaded_parfile.broadening.parameters.flag_crfn == orig_parfile.broadening.parameters.flag_crfn
        assert loaded_parfile.broadening.parameters.flag_temp == orig_parfile.broadening.parameters.flag_temp

        # Compare normalization parameters
        assert loaded_parfile.normalization is not None
        assert orig_parfile.normalization is not None
        assert len(loaded_parfile.normalization.angle_sets) == len(orig_parfile.normalization.angle_sets)

        loaded_angle = loaded_parfile.normalization.angle_sets[0]
        orig_angle = orig_parfile.normalization.angle_sets[0]
        assert loaded_angle.anorm == pytest.approx(orig_angle.anorm)
        assert loaded_angle.backa == pytest.approx(orig_angle.backa)
        assert loaded_angle.flag_anorm == orig_angle.flag_anorm
        assert loaded_angle.d_anorm == pytest.approx(orig_angle.d_anorm)

        # Compare radius parameters
        # print(loaded_parfile.radius)
        # assert loaded_parfile.radius is not None
        # assert orig_parfile.radius is not None
        # assert loaded_parfile.radius.parameters.effective_radius == pytest.approx(orig_parfile.radius.parameters.effective_radius)
        # assert loaded_parfile.radius.parameters.true_radius == pytest.approx(orig_parfile.radius.parameters.true_radius)
        # assert loaded_parfile.radius.parameters.spin_groups == orig_parfile.radius.parameters.spin_groups
        # assert loaded_parfile.radius.parameters.vary_effective == orig_parfile.radius.parameters.vary_effective

        # Compare data reduction parameters
        assert loaded_parfile.data_reduction is not None
        assert orig_parfile.data_reduction is not None
        assert len(loaded_parfile.data_reduction.parameters) == len(orig_parfile.data_reduction.parameters)

        for loaded_param, orig_param in zip(loaded_parfile.data_reduction.parameters, orig_parfile.data_reduction.parameters):
            assert loaded_param.name == orig_param.name
            assert loaded_param.value == pytest.approx(orig_param.value)
            assert loaded_param.flag == orig_param.flag
            assert loaded_param.uncertainty == pytest.approx(orig_param.uncertainty)
            if loaded_param.derivative_value is not None:
                assert loaded_param.derivative_value == pytest.approx(orig_param.derivative_value)

        # Verify string output matches exactly
        assert loaded_parfile.to_string() == orig_parfile.to_string()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
