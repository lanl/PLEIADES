import unittest
from pleiades.nuclear.parameters import RadiusParameters, ResonanceEntry, IsotopeParameters, nuclearParameters
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
        params = IsotopeParameters(
            isotope_name="U-238",
            mass=238.0,
            abundance=0.992745,
            uncertainty=0.001,
            flag=VaryFlag.YES,
            spin_groups=[1, 2, 3],
            resonances=[resonance_entry],
            radius_parameters=[radius_params],
        )
        self.assertEqual(params.isotope_name, "U-238")
        self.assertEqual(params.mass, 238.0)
        self.assertEqual(params.abundance, 0.992745)
        self.assertEqual(params.uncertainty, 0.001)
        self.assertEqual(params.flag, VaryFlag.YES)
        self.assertEqual(params.spin_groups, [1, 2, 3])
        self.assertEqual(params.resonances, [resonance_entry])
        self.assertEqual(params.radius_parameters, [radius_params])

    def test_from_good_names(self):
        params = IsotopeParameters.from_name("Ta-181")
        self.assertEqual(params.isotope_name, "TA-181")
        self.assertAlmostEqual(params.mass, 180.947998528, places=6)
        self.assertAlmostEqual(params.abundance, 99.988, places=2)

        params = IsotopeParameters.from_name("U-235")
        self.assertEqual(params.isotope_name, "U-235")
        self.assertAlmostEqual(params.mass, 235.043928117, places=6)
        self.assertAlmostEqual(params.abundance, 0.7200, places=3)

        params = IsotopeParameters.from_name("Pb-208")
        self.assertEqual(params.isotope_name, "Pb-208")
        self.assertAlmostEqual(params.mass, 207.976652005, places=6)
        self.assertAlmostEqual(params.abundance, 52.4, places=3)

        params = IsotopeParameters.from_name("Pb-208")

    def test_from_bad_names(self):
        params = IsotopeParameters.from_name("C-123")
        self.assertEqual(params.isotope_name, "C-123")
        self.assertIsNone(params.mass)
        self.assertIsNone(params.abundance)

class TestNuclearParameters(unittest.TestCase):
    def test_nuclear_parameters_initialization(self):
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
        isotope_params = IsotopeParameters(
            isotope_name="U-238",
            mass=238.0,
            abundance=0.992745,
            uncertainty=0.001,
            flag=VaryFlag.YES,
            spin_groups=[1, 2, 3],
            resonances=[resonance_entry],
            radius_parameters=[radius_params],
        )
        params = nuclearParameters(
            isotopes=[isotope_params],
        )
        self.assertEqual(params.isotopes, [isotope_params])

if __name__ == "__main__":
    unittest.main()
