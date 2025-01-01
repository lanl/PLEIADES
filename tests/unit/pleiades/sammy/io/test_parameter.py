#!/usr/bin/env python
"""Unit tests for SAMMY parameter file handling."""

import pytest

from pleiades.sammy.io.parameter import ParFile


@pytest.fixture
def sample_par_content():
    """Sample parameter file content for testing."""
    return (
        "SPIN GROUP INFORMATION\n"
        "  1          2  2    0.5         1.000000\n"  # Fixed format numbers
        "  1 PPair1          1    0.5         0.0000       0.0000\n"
        "  2 PPair1          1    0.5         0.0000       0.0000\n"
        "\n"
        "RESONANCE PARAMETERS\n"
        "   6.6720+0   2.3000-2   1.4760-3   0.0000+0   0.0000+0 1 1 1 0 0 1\n"
        "   2.0870+1   2.3000-2   1.0880-3   0.0000+0   0.0000+0 0 0 1 0 0 1\n"
        "\n"
        "PARTICLE PAIR DEFINITIONS\n"
        "Name=PPair1  Particle a=neutron     Particle b=U-238    \n"
        "      Za=0         Zb=92          Pent=1     Shift=0\n"
        "      Sa=0.5       Sb=0.0         Ma=1.008664915            Mb=238.0508\n"
        "\n"
        "0.1\n"
    )


@pytest.fixture
def tmp_par_file(tmp_path, sample_par_content):
    """Create a temporary parameter file."""
    par_file = tmp_path / "test.par"
    par_file.write_text(sample_par_content)
    return par_file


@pytest.fixture
def par_file(tmp_par_file):
    """Create ParFile instance for testing."""
    return ParFile(filename=str(tmp_par_file)).read()


class TestParFile:
    """Test ParFile class functionality."""

    def test_init(self, tmp_par_file):
        """Test ParFile initialization."""
        par = ParFile(filename=str(tmp_par_file))
        assert par.filename == str(tmp_par_file)
        assert par.weight == 1.0
        assert par.name == "auto"
        assert par.emin == 0.001
        assert par.emax == 100

    def test_read_file(self, par_file):
        """Test reading parameter file."""
        # Check particle pairs
        assert len(par_file.data["particle_pairs"]) == 1

        # Each spin group can have multiple channels, stored as nested list
        assert len(par_file.data["spin_group"]) > 0

        # Check first spin group format
        first_group = par_file.data["spin_group"][0]
        assert "group_number" in first_group[0]
        assert "spin" in first_group[0]
        assert "isotopic_abundance" in first_group[0]

    def test_write_file(self, par_file, tmp_path):
        """Test writing parameter file."""
        print(par_file.data)
        # First validate input structure
        first_group = par_file.data["spin_group"][0][0]
        assert first_group["n_entrance_channel"].strip() != ""
        assert first_group["n_exit_channel"].strip() != ""

        # Test write/read cycle
        output_file = tmp_path / "output.par"
        par_file.write(output_file)

        # Read back and verify
        new_par = ParFile(filename=str(output_file)).read()
        assert len(new_par.data["resonance_params"]) == len(par_file.data["resonance_params"])
        assert len(new_par.data["spin_group"]) == len(par_file.data["spin_group"])


#     def test_combine_parameters(self, par_file, tmp_par_file):
#         """Test combining parameter files."""
#         other_par = ParFile(filename=str(tmp_par_file)).read()
#         combined = par_file + other_par

#         # Check combined data
#         assert len(combined.data["resonance_params"]) == 4  # 2 from each
#         assert len(combined.data["spin_group"]) == 2


# class TestUpdate:
#     """Test Update class functionality."""

#     def test_vary_resonances(self, par_file):
#         """Test varying resonance parameters."""
#         # Set all resonances to vary
#         par_file.update.vary_all_resonances(vary=True)

#         for res in par_file.data["resonance_params"]:
#             assert res["vary_energy"] == "1"
#             assert res["vary_capture_width"] == "1"
#             assert res["vary_neutron_width"] == "1"

#     def test_limit_energies(self, par_file):
#         """Test limiting energy range."""
#         # Set energy limits to exclude some resonances
#         par_file.update.limit_energies_of_parfile()

#         for res in par_file.data["resonance_params"]:
#             energy = float(res["reosnance_energy"])
#             assert par_file.emin <= energy <= par_file.emax

#     def test_isotopic_weight(self, par_file):
#         """Test updating isotopic weight."""
#         new_weight = 0.5
#         par_file.weight = new_weight
#         par_file.update.isotopic_weight()

#         # Check updated weights
#         for group in par_file.data["spin_group"]:
#             assert float(group[0]["isotopic_abundance"]) == new_weight

#     @pytest.mark.parametrize("vary", [True, False])
#     def test_vary_all(self, par_file, vary):
#         """Test varying all parameters."""
#         par_file.update.vary_all(vary=vary, data_key="normalization")

#         # Check normalization vary flags
#         norm = par_file.data["normalization"]
#         for key in [k for k in norm if k.startswith("vary_")]:
#             assert int(norm[key]) == int(vary)


# def test_error_handling(tmp_path):
#     """Test error handling for invalid files."""
#     # Test invalid file
#     with pytest.raises(FileNotFoundError):
#         ParFile(filename=str(tmp_path / "nonexistent.par")).read()

#     # Test invalid format
#     invalid_file = tmp_path / "invalid.par"
#     invalid_file.write_text("Invalid content")
#     with pytest.raises(Exception):
#         ParFile(filename=str(invalid_file)).read()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
