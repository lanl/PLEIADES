PROTON_CHARGE_UNCERTAINTY = 0.005


class Roi:
    def __init__(self, x1=0, y1=0, x2=None, y2=None, width=None, height=None):
        """x1 and x2 are mandatory
        y2 or height are mandatory
        x2 or width are mandatory"""

        if x1 < 0 or y1 < 0:
            raise ValueError("ROI top left corner coordinates must be non-negative")

        if x2 is not None and width is not None:
            raise ValueError("ROI cannot have both x2 and width defined")

        if y2 is not None and height is not None:
            raise ValueError("ROI cannot have both y2 and height defined")

        if x2 is not None:
            if x2 < 0:
                raise ValueError("ROI x2 must be non-negative")

            if x2 < x1:
                raise ValueError("ROI x2 must be greater than or equal to x1")

            if width is not None:
                raise ValueError("ROI cannot have both x2 and width defined")

        else:
            if width is None or width <= 0:
                raise ValueError("ROI width must be positive when x2 is not defined")
            x2 = x1 + width

        if y2 is not None:
            if y2 < 0:
                raise ValueError("ROI y2 must be non-negative")

            if y2 < y1:
                raise ValueError("ROI y2 must be greater than or equal to y1")

            if height is not None:
                raise ValueError("ROI cannot have both y2 and height defined")

        else:
            if height is None or height <= 0:
                raise ValueError("ROI height must be positive when y2 is not defined")
            y2 = y1 + height

        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def get_roi(self):
        return (self.x1, self.y1, self.x2, self.y2)

    def set_roi(self, x1, y1, x2, y2):
        if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
            raise ValueError("ROI coordinates must be non-negative")

        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __repr__(self):
        return f"Roi(x1={self.x1}, y1={self.y1}, x2={self.x2}, y2={self.y2})"

    def __str__(self):
        return f"Roi: (x1={self.x1}, y1={self.y1}) to (x2={self.x2}, y2={self.y2})"


class DataType:
    sample = "sample"
    ob = "ob"
    normalization = "normalization"


class MasterDictKeys:
    data_type = "data_type"
    list_folders = "list_folders"

    obs_data_combined = "obs_data_combined"
    sample_data = "sample_data"
    uncertainties_obs_data_combined = "uncertainties_obs_data_combined"
    uncertainties_sample_data = "uncertainties_sample_data"

    frame_number = "frame_number"
    proton_charge = "proton_charge"
    matching_ob = "matching_ob"
    list_images = "list_images"
    data = "data"
    nexus_path = "nexus_path"
    data_path = "data_path"
    shutter_counts = "shutter_counts"
    list_spectra = "list_spectra"
    list_shutters = "list_shutters"
    ext = "ext"


class Facility:
    ornl = "ornl"
    lanl = "lanl"


class NormalizationStatus:
    all_nexus_file_found = False
    all_spectra_file_found = False
    all_shutter_counts_file_found = False
    all_proton_charge_value_found = False
    all_list_shutter_values_for_each_image_found = False
