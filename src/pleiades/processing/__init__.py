class Roi:
    def __init__(self, x1, y1, x2, y2):
        if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
            raise ValueError("ROI coordinates must be non-negative")
         
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


class MasterDictKeys:
    frame_number = "frame_number"
    proton_charge = "proton_charge"
    matching_ob = "matching_ob"
    list_tif = "list_tif"
    data = "data"
    nexus_path = "nexus_path"
    data_path = "data_path"
    shutter_counts = "shutter_counts"
    list_spectra = "list_spectra"
    

class Facility:
    ornl = "ornl"
    lanl = "lanl"
    

class NormalizationStatus:
    all_nexus_file_found = False
    all_spectra_file_found = False
    all_shutter_counts_file_found = False
    all_proton_charge_value_found = False
    all_list_shutter_values_for_each_image_found = False
