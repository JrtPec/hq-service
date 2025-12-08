import math
import random
from typing import Literal

from pydantic import BaseModel


class Location(BaseModel):
    """Class representing a location in the game."""

    latitude: float
    longitude: float

    @classmethod
    def from_coordinates(
        cls,
        lat_deg: int,
        lat_min: int,
        lat_sec: int,
        lat_dir: Literal["N", "S"],
        lon_deg: int,
        lon_min: int,
        lon_sec: int,
        lon_dir: Literal["E", "W"],
    ) -> "Location":
        """Create a Location instance from degrees, minutes, seconds, and direction."""
        latitude = lat_deg + lat_min / 60 + lat_sec / 3600
        if lat_dir == "S":
            latitude = -latitude

        longitude = lon_deg + lon_min / 60 + lon_sec / 3600
        if lon_dir == "W":
            longitude = -longitude

        return cls(latitude=latitude, longitude=longitude)

    def random_location_at_distance(self, distance_km: float = 10.0) -> "Location":
        """
        Returns a random Location at a specified distance (in km) from this location.
        Uses a random bearing.
        """
        return random_location_at_distance(self.latitude, self.longitude, distance_km)

    def distance_to(self, other: "Location") -> float:
        """Calculate the Haversine distance in meters to another Location."""
        return (
            haversine_km(self.latitude, self.longitude, other.latitude, other.longitude)
            * 1000
        )

    def bearing_to(self, other: "Location") -> float:
        """Calculate the bearing in degrees to another Location."""
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        diff_long = math.radians(other.longitude - self.longitude)

        x = math.sin(diff_long) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (
            math.sin(lat1) * math.cos(lat2) * math.cos(diff_long)
        )

        initial_bearing = math.atan2(x, y)
        initial_bearing_deg = math.degrees(initial_bearing)
        compass_bearing = (initial_bearing_deg + 360) % 360

        return compass_bearing


def random_location_at_distance(
    latitude: float, longitude: float, distance_km: float = 10.0
) -> Location:
    """
    Returns a random Location at a specified distance (in km) from the given latitude/longitude.
    Uses a random bearing.
    """
    # Earth radius in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)

    # Central angle (distance in radians)
    ang_dist = distance_km / R

    # Pick a random bearing (angle in radians)
    bearing = random.uniform(0.0, 2.0 * math.pi)

    # Calculate new latitude
    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(ang_dist)
        + math.cos(lat_rad) * math.sin(ang_dist) * math.cos(bearing)
    )

    # Calculate new longitude
    new_lon_rad = lon_rad + math.atan2(
        math.sin(bearing) * math.sin(ang_dist) * math.cos(lat_rad),
        math.cos(ang_dist) - math.sin(lat_rad) * math.sin(new_lat_rad),
    )

    # Convert back to degrees
    new_lat = math.degrees(new_lat_rad)

    # Normalize longitude to [-180, 180]
    new_lon = (math.degrees(new_lon_rad) + 540.0) % 360.0 - 180.0

    return Location(latitude=new_lat, longitude=new_lon)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
