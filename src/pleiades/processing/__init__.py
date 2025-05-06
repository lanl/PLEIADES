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
