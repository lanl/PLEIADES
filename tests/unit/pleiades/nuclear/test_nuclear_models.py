import unittest

from pleiades.nuclear.manager import NuclearDataManager
from pleiades.nuclear.models import RadiusParameters, ResonanceEntry, SpinGroupChannels, SpinGroups, nuclearParameters
from pleiades.utils.helper import VaryFlag


class TestRadiusParameters(unittest.TestCase):
    def test_radius_parameters_initialization(self):
        # Needed for group and channel information
        spin_group1 = SpinGroupChannels(group_number=1, channels=[1])
        spin_group2 = SpinGroupChannels(group_number=2, channels=[1])
        spin_group3 = SpinGroupChannels(group_number=3, channels=[1])

        params = RadiusParameters(
            effective_radius=1.0,
            true_radius=1.0,
            channel_mode=0,
            vary_effective=VaryFlag.YES,
            vary_true=VaryFlag.YES,
            spin_groups=[spin_group1, spin_group2, spin_group3],
        )

        self.assertEqual(params.effective_radius, 1.0)
        self.assertEqual(params.true_radius, 1.0)
        self.assertEqual(params.channel_mode, 0)
        self.assertEqual(params.vary_effective, VaryFlag.YES)
        self.assertEqual(params.vary_true, VaryFlag.YES)
        self.assertEqual(len(params.spin_groups), 3)
        self.assertEqual(params.spin_groups[0].group_number, 1)
        self.assertEqual(params.spin_groups[1].group_number, 2)
        self.assertEqual(params.spin_groups[2].group_number, 3)

    def test_invalid_spin_groups(self):
        # Test invalid group number (must be positive)
        with self.assertRaises(ValueError):
            SpinGroupChannels(group_number=-1, channels=[1])

        # Test invalid channel number (must be positive)
        with self.assertRaises(ValueError):
            SpinGroupChannels(group_number=1, channels=[-1, 2, 3])


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

        # create SpinGroups objects for isotope_params.spin_groups
        spin_group_obj1 = SpinGroups(
            spin_group_number=1,
            excluded=False,
            number_of_entry_channels=1,
            number_of_exit_channels=1,
            spin=0.5,
            abundance=1.0,
            ground_state_spin=0.0,
        )
        spin_group_obj2 = SpinGroups(
            spin_group_number=2,
            excluded=False,
            number_of_entry_channels=1,
            number_of_exit_channels=1,
            spin=1.5,
            abundance=1.0,
            ground_state_spin=0.0,
        )
        spin_group_obj3 = SpinGroups(
            spin_group_number=3,
            excluded=False,
            number_of_entry_channels=1,
            number_of_exit_channels=1,
            spin=2.5,
            abundance=1.0,
            ground_state_spin=0.0,
        )

        # Needed for radius group and channel information
        spin_group1 = SpinGroupChannels(group_number=1, channels=[1])
        spin_group2 = SpinGroupChannels(group_number=2, channels=[1])
        spin_group3 = SpinGroupChannels(group_number=3, channels=[1])

        # Creating a radius parameter
        radius_params = RadiusParameters(
            effective_radius=1.0,
            true_radius=1.0,
            channel_mode=0,
            vary_effective=VaryFlag.YES,
            vary_true=VaryFlag.YES,
            spin_groups=[spin_group1, spin_group2, spin_group3],
        )

        # Creating a resonance entry
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
        isotope_params.spin_groups = [spin_group_obj1, spin_group_obj2, spin_group_obj3]

        self.assertEqual(isotope_params.isotope_information.name, "U-238")
        self.assertEqual(isotope_params.isotope_information.mass_number, 238)
        self.assertEqual(isotope_params.isotope_information.element, "U")
        self.assertEqual(isotope_params.isotope_information.material_number, 9237)
        self.assertEqual(isotope_params.isotope_information.abundance, 99.2745)

        self.assertEqual(isotope_params.abundance, 1)
        self.assertEqual(isotope_params.uncertainty, 0.001)
        self.assertEqual(isotope_params.vary_abundance, VaryFlag.YES)
        self.assertEqual(isotope_params.resonances, [resonance_entry])
        self.assertEqual(isotope_params.radius_parameters, [radius_params])
        self.assertEqual(len(isotope_params.spin_groups), 3)
        self.assertEqual(isotope_params.spin_groups[0].spin_group_number, 1)
        self.assertEqual(isotope_params.spin_groups[1].spin_group_number, 2)
        self.assertEqual(isotope_params.spin_groups[2].spin_group_number, 3)


class TestNuclearParameters(unittest.TestCase):
    def test_nuclear_parameters_initialization(self):
        data_manager = NuclearDataManager()
        isotope_params = data_manager.create_isotope_parameters_from_string("U-238")

        # Create SpinGroups objects for isotope_params.spin_groups
        spin_group_obj1 = SpinGroups(
            spin_group_number=1,
            excluded=False,
            number_of_entry_channels=1,
            number_of_exit_channels=1,
            spin=0.5,
            abundance=1.0,
            ground_state_spin=0.0,
        )
        spin_group_obj2 = SpinGroups(
            spin_group_number=2,
            excluded=False,
            number_of_entry_channels=1,
            number_of_exit_channels=1,
            spin=1.5,
            abundance=1.0,
            ground_state_spin=0.0,
        )
        spin_group_obj3 = SpinGroups(
            spin_group_number=3,
            excluded=False,
            number_of_entry_channels=1,
            number_of_exit_channels=1,
            spin=2.5,
            abundance=1.0,
            ground_state_spin=0.0,
        )

        spin_group1 = SpinGroupChannels(group_number=1, channels=[1])
        spin_group2 = SpinGroupChannels(group_number=2, channels=[1])
        spin_group3 = SpinGroupChannels(group_number=3, channels=[1])

        radius_params = RadiusParameters(
            effective_radius=1.0,
            true_radius=1.0,
            channel_mode=0,
            vary_effective=VaryFlag.YES,
            vary_true=VaryFlag.YES,
            spin_groups=[spin_group1, spin_group2, spin_group3],
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
        isotope_params.spin_groups = [
            spin_group_obj1,
            spin_group_obj2,
            spin_group_obj3,
        ]  # Add all SpinGroups objects to match radius parameter groups

        params = nuclearParameters(isotopes=[isotope_params])

        # Assert that the first isotope in the nuclearParameters object matches the expected IsotopeParameters object
        self.assertEqual(params.isotopes[0].isotope_information.name, "U-238")
        self.assertEqual(params.isotopes[0].isotope_information.mass_number, 238)
        self.assertEqual(params.isotopes[0].isotope_information.element, "U")
        self.assertEqual(params.isotopes[0].isotope_information.material_number, 9237)
        self.assertEqual(params.isotopes[0].abundance, 1)
        self.assertEqual(params.isotopes[0].uncertainty, 0.001)
        self.assertEqual(params.isotopes[0].vary_abundance, VaryFlag.YES)


if __name__ == "__main__":
    unittest.main()
