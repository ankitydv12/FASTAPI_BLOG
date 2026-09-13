## Imports for Users Router
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import model
from database import get_db
from schema import PostResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter()


#creating a user
@router.get("",response_model=list[UserResponse],status_code=status.HTTP_200_OK)
async def get_all_users(db:Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.User))
    all_post = result.scalars().all()
    return all_post


@router.post("",response_model=UserResponse,status_code=status.HTTP_201_CREATED)
async def create_user(user:UserCreate, db : Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.username == user.username))
    exiting_user = result.scalars().first()
    if exiting_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exits")
    result = await db.execute(select(model.User.email).where(model.User.email == user.email))
    exiting_email = result.scalars().first()
    if exiting_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Email is already exits")

    #creating a new User
    new_user = model.User(
        username= user.username,
        email = user.email
    )
    db.add(new_user) # stage the user
    await db.commit() # save the user
    await db.refresh(new_user) # reload the obj from data base]

    return new_user

@router.get("/{user_id}", response_model=UserResponse  )
async def get_user(user_id:int ,db : Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    exiting_user = result.scalars().first()
    if not exiting_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return exiting_user

#Getting All post of user
@router.get("/{user_id}/posts",response_model=list[PostResponse] , status_code = status.HTTP_200_OK)
async def get_user_post(user_id:int , db : Annotated[AsyncSession , Depends((get_db))]):
    result = await db.execute(select(model.User).where(model.Post.user_id == user_id))
    exting_user = result.scalars().first()
    if not exting_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts

@router.patch("/{user_id}",response_model=UserResponse)
async def update_user(user_id:int , update_data : UserUpdate , db : Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not  user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if update_data.username is not None and update_data.username != user.username:
        exiting_user = db.execute(select(model.User).where(model.User.username == update_data.username)).scalars().first()
        if exiting_user:
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already exits  ")
    if update_data.email is not None and update_data.email != update_data.email:
        exiting_email = await db.execute(
            select(model.User.email).where(model.User.email == update_data.email)
        ).scalars().first()
        if exiting_email:
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email is already exits  ")

    if update_data.username is not None:
        user.username = update_data.username
    if  update_data.email is not None:
        user.email  = update_data.email
    if update_data.img_path is not None:
        user.image_file = update_data.img_path

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()

