from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, Optional

from models.vin_result import VINResult


class VINTool:
    VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
    TRANSLATION_MAP = {
        "1": "USA",
        "4": "USA",
        "5": "USA",
        "2": "Canada",
        "3": "Mexico",
    }

    @classmethod
    def validate(cls, vin: str) -> bool:
        if not isinstance(vin, str):
            return False
        return bool(cls.VIN_PATTERN.fullmatch(vin.strip().upper()))

    @classmethod
    def decode(cls, vin: str) -> Optional[Dict[str, Optional[str]]]:
        vin = vin.strip().upper()
        if not cls.validate(vin):
            return None

        return {
            "vin": vin,
            "year": cls._decode_year(vin[9]),
            "make": cls._decode_make(vin[1:3]),
            "model": cls._decode_model(vin[3:6]),
            "trim": cls._decode_trim(vin[6]),
            "engine": cls._decode_engine(vin[10]),
            "transmission": cls._decode_transmission(vin[11]),
            "drivetrain": cls._decode_drivetrain(vin[12]),
            "body_style": cls._decode_body_style(vin[13]),
            "manufacturer": cls._decode_manufacturer(vin[0]),
        }

    @classmethod
    def build_result(cls, vin: str, specialist: str, confidence_score: float) -> Optional[VINResult]:
        decoded = cls.decode(vin)
        if decoded is None:
            return None

        return VINResult(
            id=vin,
            specialist=specialist,
            timestamp=datetime.now(timezone.utc),
            confidence_score=confidence_score,
            metadata={"validated": True},
            vin=decoded["vin"],
            year=decoded["year"],
            make=decoded["make"],
            model=decoded["model"],
            trim=decoded["trim"],
            engine=decoded["engine"],
            transmission=decoded["transmission"],
            drivetrain=decoded["drivetrain"],
            body_style=decoded["body_style"],
            manufacturer=decoded["manufacturer"],
        )

    @staticmethod
    def _decode_year(char: str) -> Optional[int]:
        mapping = {
            "A": 2010,
            "B": 2011,
            "C": 2012,
            "D": 2013,
            "E": 2014,
            "F": 2015,
            "G": 2016,
            "H": 2017,
            "J": 2018,
            "K": 2019,
            "L": 2020,
            "M": 2021,
            "N": 2022,
            "P": 2023,
            "R": 2024,
            "S": 2025,
            "T": 2026,
            "V": 2027,
            "W": 2028,
            "X": 2029,
            "Y": 2030,
            "1": 2001,
            "2": 2002,
            "3": 2003,
            "4": 2004,
            "5": 2005,
            "6": 2006,
            "7": 2007,
            "8": 2008,
            "9": 2009,
        }
        return mapping.get(char)

    @staticmethod
    def _decode_make(chars: str) -> Optional[str]:
        if chars.startswith("1") or chars.startswith("4") or chars.startswith("5"):
            return "Ford"
        if chars.startswith("2") or chars.startswith("3"):
            return "General Motors"
        return "Unknown"

    @staticmethod
    def _decode_model(chars: str) -> Optional[str]:
        if chars == "ABC":
            return "Model S"
        if chars == "DEF":
            return "Model 3"
        return "Unknown"

    @staticmethod
    def _decode_trim(char: str) -> Optional[str]:
        return {
            "1": "Base",
            "2": "Sport",
            "3": "Limited",
        }.get(char, "Standard")

    @staticmethod
    def _decode_engine(char: str) -> Optional[str]:
        return {
            "A": "2.0L I4",
            "B": "3.5L V6",
            "C": "Electric",
        }.get(char, None)

    @staticmethod
    def _decode_transmission(char: str) -> Optional[str]:
        return {
            "A": "Automatic",
            "M": "Manual",
            "E": "Electric",
        }.get(char, None)

    @staticmethod
    def _decode_drivetrain(char: str) -> Optional[str]:
        return {
            "F": "FWD",
            "R": "RWD",
            "A": "AWD",
        }.get(char, None)

    @staticmethod
    def _decode_body_style(char: str) -> Optional[str]:
        return {
            "S": "Sedan",
            "T": "Truck",
            "U": "SUV",
            "C": "Coupe",
            "H": "Hatchback",
        }.get(char, None)

    @classmethod
    def _decode_manufacturer(cls, char: str) -> Optional[str]:
        return cls.TRANSLATION_MAP.get(char, "Unknown")
