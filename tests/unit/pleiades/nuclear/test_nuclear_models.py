import unittest

from pleiades.nuclear.manager import NuclearDataManager
from pleiades.nuclear.models import RadiusParameters, ResonanceEntry, nuclearParameters
from pleiades.utils.helper import VaryFlag


class TestRadiusParameters(unittest.TestCase):
    def test_radius_parameters_initialization(self):
        params = RadiusParameters(
            effective_radius=1.0,
            true_radius=1.0,
            channel_mode=0,
            vary_effective=VaryFlag.YES,
            vary_true=VaryFlag.YES,
            spin_groups=[1, 2, 3],
        )
        self.assertEqual(params.effective_radius, 1.0)
        self.assertEqual(params.true_radius, 1.0)
        self.assertEqual(params.channel_mode, 0)
        self.assertEqual(params.vary_effective, VaryFlag.YES)
        self.assertEqual(params.vary_true, VaryFlag.YES)
        self.assertEqual(params.spin_groups, [1, 2, 3])

    def test_invalid_spin_groups(self):
        with self.assertRaises(ValueError):
            RadiusParameters(
                effective_radius=1.0,
                true_radius=1.0,
                channel_mode=0,
                vary_effective=VaryFlag.YES,
                vary_true=VaryFlag.YES,
                spin_groups=[-1, 2, 3],
            )


class TestResonanceEntry(unittest.TestCase):
    def test_resonance_entry_initialization(self):
        entry = ResonanceEntry(
            resonance_energy=1.0,
            capture_width=1.0,
            channel1_width=1.0,
            channel2_width=1.0,
            channel3_width=1.0,
            vary_energy=VaryFlag.YES,
            vary_capture_width=VaryFlag.YES,
            vary_channel1=VaryFlag.YES,
            vary_channel2=VaryFlag.YES,
            vary_channel3=VaryFlag.YES,
            igroup=1,
        )
        self.assertEqual(entry.resonance_energy, 1.0)
        self.assertEqual(entry.capture_width, 1.0)
        self.assertEqual(entry.channel1_width, 1.0)
        self.assertEqual(entry.channel2_width, 1.0)
        self.assertEqual(entry.channel3_width, 1.0)
        self.assertEqual(entry.vary_energy, VaryFlag.YES)
        self.assertEqual(entry.vary_capture_width, VaryFlag.YES)
        self.assertEqual(entry.vary_channel1, VaryFlag.YES)
        self.assertEqual(entry.vary_channel2, VaryFlag.YES)
        self.assertEqual(entry.vary_channel3, VaryFlag.YES)
        self.assertEqual(entry.igroup, 1)


class TestIsotopeParameters(unittest.TestCase):
    def test_isotope_parameters_initialization(self):
        data_manager = NuclearDataManager()
        isotope_params = data_manager.create_isotope_parameters_from_string("U-238")

        radius_params = RadiusParameters(
            effective_radius=1.0,
            true_radius=1.0,
            channel_mode=0,
            vary_effective=VaryFlag.YES,
            vary_true=VaryFlag.YES,
            spin_groups=[1, 2, 3],
        )
        resonance_entry = ResonanceEntry(
            resonance_energy=1.0,
            capture_width=1.0,
            channel1_width=1.0,
            channel2_width=1.0,
            channel3_width=1.0,
            vary_energy=VaryFlag.YES,
            vary_capture_width=VaryFlag.YES,
            vary_channel1=VaryFlag.YES,
            vary_channel2=VaryFlag.YES,
            vary_channel3=VaryFlag.YES,
            igroup=1,
        )

        isotope_params.radius_parameters = [radius_params]
        isotope_params.resonances = [resonance_entry]
        isotope_params.abundance = 1
        isotope_params.uncertainty = 0.001
        isotope_params.vary_abundance = VaryFlag.YES
        isotope_params.spin_groups = [1, 2, 3]

        self.assertEqual(isotope_params.isotope_infomation.name, "U-238")
        self.assertEqual(isotope_params.isotope_infomation.mass_number, 238)
        self.assertEqual(isotope_params.isotope_infomation.element, "U")
        self.assertEqual(isotope_params.isotope_infomation.material_number, 9237)
        self.assertEqual(isotope_params.isotope_infomation.abundance, 99.2745)

        self.assertEqual(isotope_params.abundance, 1)
        self.assertEqual(isotope_params.uncertainty, 0.001)
        self.assertEqual(isotope_params.vary_abundance, VaryFlag.YES)
        self.assertEqual(isotope_params.spin_groups, [1, 2, 3])
        self.assertEqual(isotope_params.resonances, [resonance_entry])
        self.assertEqual(isotope_params.radius_parameters, [radius_params])


class TestNuclearParameters(unittest.TestCase):
    def test_nuclear_parameters_initialization(self):
        data_manager = NuclearDataManager()
        isotope_params = data_manager.create_isotope_parameters_from_string("U-238")

        radius_params = RadiusParameters(
            effective_radius=1.0,
            true_radius=1.0,
            channel_mode=0,
            vary_effective=VaryFlag.YES,
            vary_true=VaryFlag.YES,
            spin_groups=[1, 2, 3],
        )
        resonance_entry = ResonanceEntry(
            resonance_energy=1.0,
            capture_width=1.0,
            channel1_width=1.0,
            channel2_width=1.0,
            channel3_width=1.0,
            vary_energy=VaryFlag.YES,
            vary_capture_width=VaryFlag.YES,
            vary_channel1=VaryFlag.YES,
            vary_channel2=VaryFlag.YES,
            vary_channel3=VaryFlag.YES,
            igroup=1,
        )

        isotope_params.radius_parameters = [radius_params]
        isotope_params.resonances = [resonance_entry]
        isotope_params.abundance = 1
        isotope_params.uncertainty = 0.001
        isotope_params.vary_abundance = VaryFlag.YES
        isotope_params.spin_groups = [1, 2, 3]

        params = nuclearParameters(isotopes=[isotope_params])

        # Assert that the first isotope in the nuclearParameters object matches the expected IsotopeParameters object
        self.assertEqual(params.isotopes[0].isotope_infomation.name, "U-238")
        self.assertEqual(params.isotopes[0].isotope_infomation.mass_number, 238)
        self.assertEqual(params.isotopes[0].isotope_infomation.element, "U")
        self.assertEqual(params.isotopes[0].isotope_infomation.material_number, 9237)
        self.assertEqual(params.isotopes[0].abundance, 1)
        self.assertEqual(params.isotopes[0].uncertainty, 0.001)
        self.assertEqual(params.isotopes[0].vary_abundance, VaryFlag.YES)
        self.assertEqual(params.isotopes[0].spin_groups, [1, 2, 3])
        self.assertEqual(params.isotopes[0].resonances, [resonance_entry])
        self.assertEqual(params.isotopes[0].radius_parameters, [radius_params])


if __name__ == "__main__":
    unittest.main()
