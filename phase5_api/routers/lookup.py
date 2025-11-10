"""
API router for part lookup endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from phase5_api.models.schemas import (
    PartLookupResponse, ReplacementChainResponse,
    SpecSearchResponse, ErrorResponse
)
from phase5_api.services.lookup_service import LookupService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lookup", tags=["lookup"])

# Initialize service
lookup_service = LookupService()


@router.get(
    "/part/{part_number}",
    response_model=PartLookupResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Look up part by number",
    description="Returns part details, specifications, and direct replacements"
)
async def lookup_part(
    part_number: str = Path(..., description="Part number to look up", example="0131M00008P")
):
    """
    Primary lookup endpoint for HVAC/plumbing parts.

    Returns:
    - Part information (name, OEM status, manufacturer)
    - Specifications (HP, voltage, capacitance, etc.)
    - Direct (1st degree) replacements
    - Equivalent parts from other manufacturers
    - Compatible equipment models
    """
    result = await lookup_service.lookup_part(part_number)

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PartNotFound",
                "message": f"Part '{part_number}' not found in knowledge graph",
                "details": {"part_id": part_number}
            }
        )

    return result


@router.get(
    "/spec/",
    response_model=SpecSearchResponse,
    summary="Search parts by specification",
    description="Find parts matching specific technical specifications"
)
async def search_by_spec(
    type: str = Query(..., description="Specification type", example="MFD"),
    value: str = Query(..., description="Specification value", example="40+5")
):
    """
    Specification-based search endpoint.

    Use this when you know the specs but not the part number.
    Common spec types: MFD, Voltage, HP, Temperature, etc.

    Example queries:
    - ?type=MFD&value=40+5 (capacitor)
    - ?type=HP&value=1/2 (motor horsepower)
    - ?type=Voltage&value=440V
    """
    result = await lookup_service.search_by_spec(type, value)
    return result


@router.get(
    "/graph/replacements/{part_number}",
    response_model=ReplacementChainResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get replacement chain (multi-degree)",
    description="Find all replacements up to 5 degrees deep - the 'magic' endpoint"
)
async def get_replacement_chain(
    part_number: str = Path(..., description="Source part number", example="0131M00008P"),
    max_depth: int = Query(5, ge=1, le=5, description="Maximum traversal depth")
):
    """
    The "magic" endpoint that demonstrates the power of graph databases.

    This executes a variable-length path traversal in Neo4j to find:
    - 1st degree: Direct replacements (Part A → Part B)
    - 2nd degree: Replacements of replacements (Part A → Part B → Part C)
    - 3rd-5th degree: Transitive replacement chains

    Also identifies which replacements came from "tribal knowledge" (forums).

    **This query is trivial in Cypher but extremely complex in SQL.**
    """
    result = await lookup_service.get_replacement_chain(part_number, max_depth)

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PartNotFound",
                "message": f"Part '{part_number}' not found or has no replacements",
                "details": {"part_id": part_number}
            }
        )

    return result
