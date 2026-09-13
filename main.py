from sys import modules
from unittest import result
from urllib.request import Request
from contextlib import asynccontextmanager
from fastapi import FastAPI , Request , HTTPException , status , Depends
from fastapi.templating import Jinja2Templates

from fastapi.staticfiles import StaticFiles

from fastapi.exception_handlers import  (http_exception_handler , request_validation_exception_handler)
from sqlalchemy.orm import selectinload
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from watchfiles import awatch

from schema import PostCreate , PostResponse , Patch_post , UserResponse , UserCreate , UserUpdate
from typing import Annotated
import model
from database import Base , engine , get_db 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Base.metadata.create_all(bind=engine) #this synchronus method cant call from async enginr

@asynccontextmanager #make asynccontexmanager
async def lifespan(app_:FastAPI):
    #startup
    async with engine.begin() as conn: # get async connect
        conn.run_sync(Base.metadata.create_all) # calling a synchronus in async
    yield
    #shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

app.mount("/static",StaticFiles(directory="static"),name="static")
app.mount("/media",StaticFiles(directory="media"),name="media")
title = "Abc title"

#  same content on the multiple url
@app.get("/",include_in_schema=False ,name="home")
@app.get("/posts" , include_in_schema=False,name="post")
async def home(request: Request,  db: Annotated[AsyncAsyncSession , Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)))
    posts = result.scalars().all()
    return templates.TemplateResponse(request,"home.html",{"posts":posts,"title":title})

@app.get("/posts/{post_id}", response_model=PostResponse)
async def post_page(request:Request,post_id:int , db : Annotated[AsyncAsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found"
        )
    title = post.title[:50]
    return templates.TemplateResponse(request,"post.html",{"post":post,"title":title})

@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncAsyncSession, Depends(get_db)],
):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )

#creating a user
@app.post("/api/users",response_model=UserResponse,status_code=status.HTTP_201_CREATED)
async def create_user(user:UserCreate, db : Annotated[AsyncAsyncSession,Depends(get_db)]):
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

@app.get("/api/users/{user_id}", response_model=UserResponse  )
async def get_user(user_id:int ,db : Annotated[AsyncAsyncSession , Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    exiting_user = result.scalars().first()
    if not exiting_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return exiting_user


#Getting All post of user
@app.get("/api/users/{user_id}/posts",response_model=list[PostResponse] , status_code = status.HTTP_200_OK)
async def get_user_post(user_id:int , db : Annotated[AsyncAsyncSession , Depends((get_db))]):
    result = await db.execute(select(model.User).where(model.Post.user_id == user_id))
    exting_user = result.scalars().first()
    if not exting_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts

@app.patch("/api/users/{user_id}",response_model=UserResponse)
async def update_user(user_id:int , update_data : UserUpdate , db : Annotated[AsyncAsyncSession,Depends(get_db)]):
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

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncAsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()

#Creating a post
@app.post("/api/posts",response_model = PostResponse , status_code=status.HTTP_201_CREATED )
async def create_post(post : PostCreate,db:Annotated[AsyncAsyncSession,Depends(get_db)]):
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
    await db.refresh(new_post)
    return new_post

@app.put("/api/posts/{post_id}",response_model=PostResponse)
async def update_post_full(post_id:int , post_data:PostCreate , db:Annotated[AsyncAsyncSession,Depends(get_db)]):
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

@app.patch("/api/patch_post/{post_id}",response_model=PostCreate)
async def patch_post(post_id:int , patch_data:Patch_post,db:Annotated[AsyncAsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post is not exits")
    updated_data = Patch_post.model_dump(exclude_unset=True)
    for key , values in updated_data.items():
        setattr(post,key,values)

    await db.commit()
    await db.refresh(post)
    return post

@app.delete("/api/posts/{post_id}" , status_code= status.HTTP_204_NO_CONTENT)
async def delete_post(post_id:int , db : Annotated[AsyncAsyncSession , Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Post is not found ")
    await db.delete(post)
    await db.commit()

@app.get("/api/posts",response_model=list[PostResponse])
async def get_posts(db:Annotated[AsyncAsyncSession,Depends(get_db)]):
    post = await db.execute(select(model.Post).options(selectinload(model.Post.author))).scalars().all()
    return post



@app.get("/api/post/{post_id}",response_model=PostResponse)
async def get_post(post_id:int , db:Annotated[AsyncAsyncSession,Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="post does not  exits ")
    return post

@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )