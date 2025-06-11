import copy
from typing import List, Optional, Union

import numpy as np
from pydantic import BaseModel, field_validator, computed_field, Field
import numbers
import math


class PolygonBox(BaseModel):
    polygon: List[List[float]] = Field(description="Polygon coordinates")
    confidence: Optional[float] = None

    @field_validator("polygon", mode="before")
    @classmethod
    def convert_bbox_to_polygon(cls, value):
        if isinstance(value, (list, tuple)) and len(value) == 4:
            if all(isinstance(x, numbers.Number) for x in value):
                value = [float(v) for v in value]
                x_min, y_min, x_max, y_max = value
                polygon = [
                    [x_min, y_min],
                    [x_max, y_min],
                    [x_max, y_max],
                    [x_min, y_max],
                ]
                return polygon
            elif all(
                isinstance(point, (list, tuple)) and len(point) == 2 for point in value
            ):
                value = [[float(v) for v in point] for point in value]
                return value
        elif isinstance(value, np.ndarray):
            if value.shape == (4, 2):
                return value.tolist()

        raise ValueError(
            f"Input must be either a bbox [x_min, y_min, x_max, y_max] or a polygon with 4 corners [(x,y), (x,y), (x,y), (x,y)].  All values must be numeric. You passed {value} of type {type(value)}.  The first value is of type {type(value[0])}."
        )

    @computed_field
    @property
    def bbox(self) -> List[float]:
        x_coords = [p[0] for p in self.polygon]
        y_coords = [p[1] for p in self.polygon]
        return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

    @computed_field
    @property
    def area(self) -> float:
        # Shoelace formula
        n = len(self.polygon)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.polygon[i][0] * self.polygon[j][1]
            area -= self.polygon[j][0] * self.polygon[i][1]
        return abs(area) / 2.0

    @computed_field
    @property
    def width(self) -> float:
        bbox = self.bbox
        return bbox[2] - bbox[0]

    @computed_field
    @property
    def height(self) -> float:
        bbox = self.bbox
        return bbox[3] - bbox[1]

    def rescale(self, scale_x: float, scale_y: float) -> "PolygonBox":
        scaled_polygon = [[p[0] * scale_x, p[1] * scale_y] for p in self.polygon]
        return PolygonBox(polygon=scaled_polygon)

    def round(self, divisor):
        for corner in self.polygon:
            corner[0] = int(corner[0] / divisor) * divisor
            corner[1] = int(corner[1] / divisor) * divisor

    def fit_to_bounds(self, bounds: List[float]) -> "PolygonBox":
        # bounds = [min_x, min_y, max_x, max_y]
        min_x, min_y, max_x, max_y = bounds
        
        fitted_polygon = []
        for p in self.polygon:
            x = max(min_x, min(max_x, p[0]))
            y = max(min_y, min(max_y, p[1]))
            fitted_polygon.append([x, y])
        
        return PolygonBox(polygon=fitted_polygon)

    def merge(self, other):
        x1 = min(self.bbox[0], other.bbox[0])
        y1 = min(self.bbox[1], other.bbox[1])
        x2 = max(self.bbox[2], other.bbox[2])
        y2 = max(self.bbox[3], other.bbox[3])
        self.polygon = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def merge_left(self, other):
        x1 = min(self.bbox[0], other.bbox[0])
        self.polygon[0][0] = x1
        self.polygon[3][0] = x1

    def merge_right(self, other):
        x2 = max(self.bbox[2], other.bbox[2])
        self.polygon[1][0] = x2
        self.polygon[2][0] = x2

    def expand(self, x_margin: float, y_margin: float):
        new_polygon = []
        x_margin = x_margin * self.width
        y_margin = y_margin * self.height
        for idx, poly in enumerate(self.polygon):
            if idx == 0:
                new_polygon.append([int(poly[0] - x_margin), int(poly[1] - y_margin)])
            elif idx == 1:
                new_polygon.append([int(poly[0] + x_margin), int(poly[1] - y_margin)])
            elif idx == 2:
                new_polygon.append([int(poly[0] + x_margin), int(poly[1] + y_margin)])
            elif idx == 3:
                new_polygon.append([int(poly[0] - x_margin), int(poly[1] + y_margin)])
        self.polygon = new_polygon

    def intersection_polygon(self, other) -> List[List[float]]:
        new_poly = []
        for i in range(4):
            if i == 0:
                new_corner = [
                    max(self.polygon[0][0], other.polygon[0][0]),
                    max(self.polygon[0][1], other.polygon[0][1]),
                ]
            elif i == 1:
                new_corner = [
                    min(self.polygon[1][0], other.polygon[1][0]),
                    max(self.polygon[1][1], other.polygon[1][1]),
                ]
            elif i == 2:
                new_corner = [
                    min(self.polygon[2][0], other.polygon[2][0]),
                    min(self.polygon[2][1], other.polygon[2][1]),
                ]
            elif i == 3:
                new_corner = [
                    max(self.polygon[3][0], other.polygon[3][0]),
                    min(self.polygon[3][1], other.polygon[3][1]),
                ]
            new_poly.append(new_corner)

        return new_poly

    def intersection_area(self, other: "PolygonBox") -> float:
        from shapely.geometry import Polygon
        poly1 = Polygon(self.polygon)
        poly2 = Polygon(other.polygon)
        intersection = poly1.intersection(poly2)
        return intersection.area

    def intersection_pct(self, other: "PolygonBox") -> float:
        intersection_area = self.intersection_area(other)
        return intersection_area / self.area

    def union_area(self, other: "PolygonBox") -> float:
        return self.area + other.area - self.intersection_area(other)

    def iou(self, other: "PolygonBox") -> float:
        intersection_area = self.intersection_area(other)
        union_area = self.union_area(other)
        return intersection_area / union_area if union_area > 0 else 0

    def is_overlap_significant(self, other: "PolygonBox", threshold: float = 0.5) -> bool:
        return self.intersection_pct(other) > threshold

    def distance_to(self, other: "PolygonBox") -> float:
        bbox1 = self.bbox
        bbox2 = other.bbox
        
        # Calculate center points
        center1 = [(bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2]
        center2 = [(bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2]
        
        # Euclidean distance
        return math.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)

    def merge_with(self, other: "PolygonBox") -> "PolygonBox":
        bbox1 = self.bbox
        bbox2 = other.bbox
        
        # Create merged bounding box
        merged_bbox = [
            min(bbox1[0], bbox2[0]),  # min x
            min(bbox1[1], bbox2[1]),  # min y
            max(bbox1[2], bbox2[2]),  # max x
            max(bbox1[3], bbox2[3])   # max y
        ]
        
        # Convert back to polygon (rectangle)
        merged_polygon = [
            [merged_bbox[0], merged_bbox[1]],  # top-left
            [merged_bbox[2], merged_bbox[1]],  # top-right
            [merged_bbox[2], merged_bbox[3]],  # bottom-right
            [merged_bbox[0], merged_bbox[3]]   # bottom-left
        ]
        
        return PolygonBox(polygon=merged_polygon)

    def shift(self, x_shift: Optional[float] = None, y_shift: Optional[float] = None):
        if x_shift is None:
            x_shift = 0
        if y_shift is None:
            y_shift = 0
        
        shifted_polygon = [[p[0] + x_shift, p[1] + y_shift] for p in self.polygon]
        return PolygonBox(polygon=shifted_polygon)

    def clamp(self, bbox: List[float]):
        for corner in self.polygon:
            corner[0] = max(min(corner[0], bbox[2]), bbox[0])
            corner[1] = max(min(corner[1], bbox[3]), bbox[1])

    @property
    def center(self):
        return [(self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2]

    def __hash__(self):
        return hash(tuple(self.bbox))

    def to_dict(self) -> dict:
        return {
            "polygon": self.polygon,
            "bbox": self.bbox,
            "area": self.area,
            "width": self.width,
            "height": self.height
        }

    @classmethod
    def from_bbox(cls, bbox: List[float]) -> "PolygonBox":
        # bbox = [x1, y1, x2, y2]
        polygon = [
            [bbox[0], bbox[1]],  # top-left
            [bbox[2], bbox[1]],  # top-right
            [bbox[2], bbox[3]],  # bottom-right
            [bbox[0], bbox[3]]   # bottom-left
        ]
        return cls(polygon=polygon)

    def __str__(self) -> str:
        bbox = self.bbox
        return f"PolygonBox(bbox=[{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}], area={self.area:.1f})"

    def __repr__(self) -> str:
        return self.__str__()
