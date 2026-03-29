"""
Assets API Router

Endpoints for creative asset management and feature extraction.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks

from ..models import (
    Asset, AssetListResponse, AssetFilterParams, AssetReprocessRequest,
    IndustryCategory, ScraperSource, ExportRequest, ExportResponse,
    ExportFormat
)
from ..services.firestore_service import FirestoreService, get_firestore_service
from ..services.job_service import JobService, get_job_service
from ..models import JobCreate, JobType

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=AssetListResponse)
async def list_assets(
    industry: Optional[IndustryCategory] = None,
    source: Optional[ScraperSource] = None,
    cta_type: Optional[str] = None,
    focal_point: Optional[str] = None,
    tone: Optional[str] = None,
    has_prompt: Optional[bool] = None,
    min_quality: Optional[float] = Query(default=None, ge=0, le=1),
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List all assets with optional filters."""
    filters = AssetFilterParams(
        industry=industry,
        source=source,
        cta_type=cta_type,
        focal_point=focal_point,
        tone=tone,
        has_prompt=has_prompt,
        min_quality=min_quality,
        search=search
    )
    
    assets, total = await firestore.get_assets(
        filters=filters,
        page=page,
        page_size=page_size
    )
    
    return AssetListResponse(
        assets=assets,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get("/{asset_id}", response_model=Asset)
async def get_asset(
    asset_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific asset by ID."""
    asset = await firestore.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{asset_id}", response_model=Asset)
async def update_asset(
    asset_id: str,
    updates: dict,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Update asset fields (e.g., override industry classification)."""
    asset = await firestore.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Only allow certain fields to be updated
    allowed_fields = {"industry", "industry_tags", "reverse_prompt", "negative_prompt"}
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not filtered_updates:
        raise HTTPException(
            status_code=400, 
            detail=f"No valid fields to update. Allowed: {allowed_fields}"
        )
    
    await firestore.update_asset(asset_id, filtered_updates)
    return await firestore.get_asset(asset_id)


@router.post("/reprocess", response_model=dict)
async def reprocess_assets(
    request: AssetReprocessRequest,
    background_tasks: BackgroundTasks,
    firestore: FirestoreService = Depends(get_firestore_service),
    job_service: JobService = Depends(get_job_service)
):
    """
    Reprocess selected assets through specified pipeline stages.
    
    Stages:
    - extract_features: Re-run feature extraction
    - classify_industry: Re-run industry classification
    - generate_prompt: Re-generate reverse prompt
    """
    # Validate assets exist
    valid_ids = []
    for asset_id in request.asset_ids:
        asset = await firestore.get_asset(asset_id)
        if asset:
            valid_ids.append(asset_id)
    
    if not valid_ids:
        raise HTTPException(status_code=400, detail="No valid assets found")
    
    # Create jobs for each stage
    job_ids = []
    for stage in request.stages:
        if stage == "extract_features":
            job_type = JobType.EXTRACT_FEATURES
        elif stage == "classify_industry":
            job_type = JobType.CLASSIFY_INDUSTRY
        elif stage == "generate_prompt":
            job_type = JobType.GENERATE_PROMPT
        else:
            continue
        
        job = await job_service.create_job(JobCreate(
            job_type=job_type,
            payload={"asset_ids": valid_ids},
            priority=2
        ))
        job_ids.append(job.id)
    
    return {
        "message": f"Queued reprocessing for {len(valid_ids)} assets",
        "asset_ids": valid_ids,
        "job_ids": job_ids,
        "stages": request.stages
    }


@router.post("/export", response_model=ExportResponse)
async def export_assets(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """
    Export assets to a downloadable file.
    
    Supports JSON, CSV, and Excel formats.
    """
    from datetime import datetime, timedelta
    import uuid
    
    # Get assets
    if request.asset_ids:
        assets = []
        for aid in request.asset_ids:
            asset = await firestore.get_asset(aid)
            if asset:
                assets.append(asset)
    else:
        assets, _ = await firestore.get_assets(
            filters=request.filters,
            page_size=10000  # Max export size
        )
    
    if not assets:
        raise HTTPException(status_code=400, detail="No assets to export")
    
    # Generate mock download URL (in production, would create actual file in Cloud Storage)
    export_id = str(uuid.uuid4())
    download_url = f"/api/v1/assets/download/{export_id}.{request.format.value}"
    
    return ExportResponse(
        download_url=download_url,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        file_size_bytes=len(assets) * 1024,  # Estimate
        record_count=len(assets)
    )


@router.get("/distribution/industry")
async def get_industry_distribution(
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get asset count distribution by industry."""
    return await firestore.get_industry_distribution()


@router.get("/distribution/source")
async def get_source_distribution(
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get asset count distribution by source."""
    return await firestore.get_source_distribution()


@router.get("/distribution/cta")
async def get_cta_distribution(
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get asset count distribution by CTA type."""
    return await firestore.get_cta_distribution()


@router.get("/filters/options")
async def get_filter_options():
    """Get available filter options for the UI."""
    return {
        "industries": [{"value": i.value, "label": i.name.replace("_", " ").title()} 
                       for i in IndustryCategory],
        "sources": [{"value": s.value, "label": s.name.replace("_", " ").title()} 
                    for s in ScraperSource],
        "cta_types": [
            {"value": "shop_now", "label": "Shop Now"},
            {"value": "learn_more", "label": "Learn More"},
            {"value": "sign_up", "label": "Sign Up"},
            {"value": "get_started", "label": "Get Started"},
            {"value": "download", "label": "Download"},
            {"value": "subscribe", "label": "Subscribe"},
            {"value": "book_now", "label": "Book Now"},
            {"value": "try_free", "label": "Try Free"},
            {"value": "contact_us", "label": "Contact Us"},
        ],
        "focal_points": [
            {"value": "product", "label": "Product"},
            {"value": "person", "label": "Person"},
            {"value": "text", "label": "Text"},
            {"value": "abstract", "label": "Abstract"},
            {"value": "logo", "label": "Logo"},
            {"value": "scene", "label": "Scene"},
        ],
        "tones": [
            {"value": "professional", "label": "Professional"},
            {"value": "playful", "label": "Playful"},
            {"value": "urgent", "label": "Urgent"},
            {"value": "luxurious", "label": "Luxurious"},
            {"value": "friendly", "label": "Friendly"},
            {"value": "bold", "label": "Bold"},
            {"value": "calm", "label": "Calm"},
            {"value": "energetic", "label": "Energetic"},
        ],
        "layout_types": [
            {"value": "hero", "label": "Hero"},
            {"value": "grid", "label": "Grid"},
            {"value": "split", "label": "Split"},
            {"value": "minimal", "label": "Minimal"},
            {"value": "product_focus", "label": "Product Focus"},
            {"value": "lifestyle", "label": "Lifestyle"},
            {"value": "text_heavy", "label": "Text Heavy"},
        ]
    }

