"""
Users router
Handles user profile and admin user management endpoints
"""
import os
import json
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.auth.dependencies import get_current_user, get_current_admin_user
from backend.users.service import update_user, get_users, delete_user, get_user_by_id
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/profile', tags=["Users"])
@router.options('/profile/', tags=["Users"])
async def profile_options(request: Request):
    """Handle CORS preflight requests for profile endpoints"""
    # Get CORS configuration from environment to match middleware settings
    cors_origins = os.getenv("CORS_ORIGINS", '["*"]')
    cors_allow_methods = os.getenv("CORS_ALLOW_METHODS", '["*"]')
    cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", '["*"]')
    
    try:
        cors_origins = json.loads(cors_origins)
        cors_allow_methods = json.loads(cors_allow_methods)
        cors_allow_headers = json.loads(cors_allow_headers)
    except json.JSONDecodeError:
        cors_origins = ["*"]
        cors_allow_methods = ["*"]
        cors_allow_headers = ["*"]
    
    # Get origin from request if available
    origin = request.headers.get("origin")
    allowed_origin = "*"
    if origin and cors_origins != ["*"]:
        # Check if origin is in allowed list
        if origin in cors_origins:
            allowed_origin = origin
    elif cors_origins == ["*"]:
        allowed_origin = "*"
    
    # Build response with CORS headers
    headers = {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": ", ".join(cors_allow_methods) if isinstance(cors_allow_methods, list) else cors_allow_methods,
        "Access-Control-Allow-Headers": ", ".join(cors_allow_headers) if isinstance(cors_allow_headers, list) else cors_allow_headers,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "3600"
    }
    
    return Response(status_code=200, headers=headers)

@router.options('/users', tags=["Users"])
async def users_options():
    """Handle CORS preflight requests for users list"""
    return Response(status_code=200)

@router.options('/users/{user_id}', tags=["Users"])
async def user_options():
    """Handle CORS preflight requests for user by ID"""
    return Response(status_code=200)


@router.get('/profile', response_model=schemas.UserOut, tags=["Users"])
@router.get('/profile/', response_model=schemas.UserOut, tags=["Users"])
async def get_profile(current_user: models.User = Depends(get_current_user), request: Request = None):
    """Get current user's profile"""
    # Log request details for debugging
    if request:
        logger.info(f"Profile request - Headers: {dict(request.headers)}")
        logger.info(f"Profile request - URL: {request.url}")
        logger.info(f"Profile request - Forwarded-Proto: {request.headers.get('X-Forwarded-Proto')}")
        logger.info(f"Profile request - Forwarded-Host: {request.headers.get('X-Forwarded-Host')}")
    return current_user


@router.put('/profile', response_model=schemas.UserOut, tags=["Users"])
@router.put('/profile/', response_model=schemas.UserOut, tags=["Users"])
async def update_profile(
    user_update: schemas.UserUpdate, 
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Update current user's profile with conditional logic for user types"""
    # Log request details for debugging
    logger.info(f"PUT /profile request - User ID: {current_user.id}, Username: {current_user.username}")
    if request:
        logger.info(f"PUT /profile - Method: {request.method}, URL: {request.url}")
        logger.info(f"PUT /profile - Headers: {dict(request.headers)}")
        auth_header = request.headers.get("authorization", "Not provided")
        logger.info(f"PUT /profile - Authorization header present: {bool(auth_header and auth_header != 'Not provided')}")
    
    # If user_type is being changed, validate the change
    if user_update.user_type is not None and user_update.user_type != current_user.user_type:
        logger.info(f"User {current_user.id} changing user_type from {current_user.user_type} to {user_update.user_type}")
    
    # For legal entities, ensure required fields are provided when switching to legal
    if user_update.user_type == 'legal':
        # Check if switching from individual to legal
        if current_user.user_type == 'individual':
            logger.info(f"User {current_user.id} switching to legal entity - additional fields may be required")
    
    try:
        logger.info(f"Attempting to update profile for user {current_user.id}")
        updated_user = await update_user(db, current_user.id, user_update)
        if not updated_user:
            logger.error(f"User {current_user.id} not found after update attempt")
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Profile updated successfully for user {current_user.id} (type: {updated_user.user_type})")
        return updated_user
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except ValueError as e:
        logger.error(f"Validation error updating profile for user {current_user.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating profile for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.get('/users', response_model=List[schemas.UserOut], tags=["Admin", "Users"])
async def list_users(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """List all users (admin only)"""
    users = await get_users(db)
    logger.info(f"Listing users: found {len(users)} users")
    return users

@router.get('/users/{user_id}', response_model=schemas.UserOut, tags=["Admin", "Users"])
async def get_user_by_id_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get user by ID (admin only)"""
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")

@router.put('/users/{user_id}', response_model=schemas.UserOut, tags=["Admin", "Users"])
async def update_user_by_id_endpoint(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Update user by ID (admin only)"""
    try:
        updated_user = await update_user(db, user_id, user_update)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")

@router.delete('/users/{user_id}', response_model=schemas.MessageResponse, tags=["Admin", "Users"])
async def delete_user_endpoint(
    user_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete user (admin only)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    success = await delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
