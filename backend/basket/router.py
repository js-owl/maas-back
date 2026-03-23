from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.auth.dependencies import get_current_user
from backend.basket.service import (
    add_to_basket,
    checkout_basket,
    clear_basket,
    get_basket,
    remove_from_basket,
    update_basket_item,
)
from backend.core.dependencies import get_request_db as get_db
from backend.core.redis import get_redis

router = APIRouter()


@router.post("/basket", response_model=schemas.BasketOut, tags=["Basket"])
async def add_item_to_basket(
    payload: schemas.BasketItemIn,
    current_user: models.User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    return await add_to_basket(redis, current_user.id, payload)


@router.get("/basket", response_model=schemas.BasketOut, tags=["Basket"])
async def get_basket_items(
    current_user: models.User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    return await get_basket(redis, current_user.id)


@router.patch("/basket/{item_id}", response_model=schemas.BasketOut, tags=["Basket"])
async def update_basket_item_endpoint(
    item_id: str,
    payload: schemas.BasketItemUpdate,
    current_user: models.User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    return await update_basket_item(redis, current_user.id, item_id, payload)


@router.delete("/basket/{item_id}", response_model=schemas.BasketOut, tags=["Basket"])
async def delete_basket_item_endpoint(
    item_id: str,
    current_user: models.User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    return await remove_from_basket(redis, current_user.id, item_id)


@router.post(
    "/basket/checkout",
    response_model=schemas.KitOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Basket"],
)
async def checkout_basket_endpoint(
    payload: schemas.BasketCheckoutIn,
    current_user: models.User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    return await checkout_basket(db, redis, current_user, payload)


@router.delete("/basket", status_code=status.HTTP_204_NO_CONTENT, tags=["Basket"])
async def clear_basket_endpoint(
    current_user: models.User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    await clear_basket(redis, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
