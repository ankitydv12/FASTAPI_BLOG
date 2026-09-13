## Imports for Posts Router
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import model
from database import get_db
from schema import PostCreate, PostResponse, PostUpdate

router = APIRouter()

#Creating a post
@router.post("",response_model = PostResponse , status_code=status.HTTP_201_CREATED )
async def create_post(post : PostCreate,db:Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id==post.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found ")
    new_post = model.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post,attribute_names=["author"])
    return new_post

@router.put("/{post_id}",response_model=PostResponse)
async def update_post_full(post_id:int , post_data:PostCreate , db:Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id==post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Post is not exits")
    if post_data.user_id != post.user_id:
        result = await db.execute(
            select(model.User).where(model.User.id == post_data.user_id),
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post)
    return post

@router.patch("/{post_id}",response_model=PostCreate)
async def update_post_partial(post_id:int , patch_data:PostUpdate,db:Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post is not exits")
    updated_data = PostUpdate.model_dump(exclude_unset=True)
    for key , values in updated_data.items():
        setattr(post,key,values)

    await db.commit()
    await db.refresh(post)
    return post

@router.delete("/{post_id}" , status_code= status.HTTP_204_NO_CONTENT)
async def delete_post(post_id:int , db : Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Post is not found ")
    await db.delete(post)
    await db.commit()

@router.get("",response_model=list[PostResponse])
async def get_posts(db:Annotated[AsyncSession,Depends(get_db)]):
    post = await db.execute(select(model.Post).options(selectinload(model.Post.author))).scalars().all()
    return post



@router.get("/{post_id}",response_model=PostResponse)
async def get_post(post_id:int , db:Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="post does not  exits ")
    return post
