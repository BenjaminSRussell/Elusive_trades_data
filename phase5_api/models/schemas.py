"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class PartInfo(BaseModel):
    """Part information model."""
    part_id: str = Field(..., description="Part number/ID")
    name: str = Field(default="", description="Part name/description")
    oem: bool = Field(default=False, description="Is this an OEM part?")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")

    class Config:
        json_schema_extra = {
            "example": {
                "part_id": "0131M00008P",
                "name": "Condenser Fan Motor",
                "oem": True,
                "manufacturer": "Goodman"
            }
        }


class SpecInfo(BaseModel):
    """Specification information model."""
    type: str = Field(..., description="Spec type (e.g., MFD, Voltage, HP)")
    value: str = Field(..., description="Spec value")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "MFD",
                "value": "40+5"
            }
        }


class ReplacementInfo(BaseModel):
    """Replacement part information."""
    part_id: str
    name: str
    oem: bool
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    degree: Optional[int] = Field(None, description="Replacement degree (1=direct, 2=2nd degree, etc.)")
    notes: Optional[str] = Field(None, description="Additional notes or context")

    class Config:
        json_schema_extra = {
            "example": {
                "part_id": "0131M00008PS",
                "name": "Condenser Fan Motor - Updated",
                "oem": True,
                "confidence": 0.95,
                "degree": 1,
                "notes": "Direct OEM replacement"
            }
        }


class EquipmentInfo(BaseModel):
    """Equipment information model."""
    model: str
    type: Optional[str] = None
    confidence: float = 0.5

    class Config:
        json_schema_extra = {
            "example": {
                "model": "ARUF37C14",
                "type": "Air Handler",
                "confidence": 0.9
            }
        }


class PartLookupResponse(BaseModel):
    """Response model for part lookup."""
    part: PartInfo
    specifications: List[SpecInfo] = []
    direct_replacements: List[ReplacementInfo] = []
    equivalent_parts: List[ReplacementInfo] = []
    compatible_equipment: List[EquipmentInfo] = []
    source_document_ids: List[int] = []

    class Config:
        json_schema_extra = {
            "example": {
                "part": {
                    "part_id": "0131M00008P",
                    "name": "Condenser Fan Motor",
                    "oem": True,
                    "manufacturer": "Goodman"
                },
                "specifications": [
                    {"type": "HP", "value": "1/3"},
                    {"type": "Voltage", "value": "230V"}
                ],
                "direct_replacements": [
                    {
                        "part_id": "0131M00008PS",
                        "name": "Updated Motor",
                        "oem": True,
                        "confidence": 0.95,
                        "degree": 1
                    }
                ],
                "equivalent_parts": [],
                "compatible_equipment": [],
                "source_document_ids": [12345]
            }
        }


class ReplacementChainResponse(BaseModel):
    """Response model for multi-degree replacement chain."""
    source_part_id: str
    replacements_by_degree: Dict[int, List[ReplacementInfo]]
    total_replacements: int
    max_degree: int
    tribal_knowledge_count: int = Field(default=0, description="Number of forum-sourced replacements")

    class Config:
        json_schema_extra = {
            "example": {
                "source_part_id": "0131M00008P",
                "replacements_by_degree": {
                    "1": [
                        {"part_id": "0131M00008PS", "name": "Direct replacement", "oem": True, "confidence": 0.95, "degree": 1}
                    ],
                    "2": [
                        {"part_id": "ICM282A", "name": "Universal replacement", "oem": False, "confidence": 0.85, "degree": 2}
                    ]
                },
                "total_replacements": 2,
                "max_degree": 2,
                "tribal_knowledge_count": 0
            }
        }


class SpecSearchResponse(BaseModel):
    """Response model for specification-based search."""
    query_specs: List[SpecInfo]
    matching_parts: List[PartInfo]
    total_matches: int

    class Config:
        json_schema_extra = {
            "example": {
                "query_specs": [
                    {"type": "MFD", "value": "40+5"},
                    {"type": "Voltage", "value": "440V"}
                ],
                "matching_parts": [
                    {"part_id": "TRCFD405", "name": "Titan Pro Capacitor", "oem": False}
                ],
                "total_matches": 1
            }
        }


class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    version: str
    services: Dict[str, str]

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "services": {
                    "neo4j": "connected",
                    "postgres": "connected"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[Dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "PartNotFound",
                "message": "Part '0131M00008P' not found in knowledge graph",
                "details": {"part_id": "0131M00008P"}
            }
        }
