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

from schema import  PostResponse
from typing import Annotated
import model
from database import Base , engine , get_db 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from routers import posts , users

@asynccontextmanager # make asynccontexmanager
async def lifespan(app_:FastAPI):
    #startup
    async with engine.begin() as conn: # get async connect
        await conn.run_sync(Base.metadata.create_all) # calling a synchronus in async
    yield
    #shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

app.mount("/static",StaticFiles(directory="static"),name="static")
app.mount("/media",StaticFiles(directory="media"),name="media")
app.include_router(users.router,prefix="/api/users",tags=["users"])
app.include_router(posts.router,prefix="/api/posts",tags=["posts"])
title = "Abc title"

#  same content on the multiple url
@app.get("/",include_in_schema=False ,name="home")
@app.get("/posts" , include_in_schema=False,name="post")
async def home(request: Request,  db: Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)))
    posts = result.scalars().all()
    return templates.TemplateResponse(request,"home.html",{"posts":posts,"title":title})

@app.get("/posts/{post_id}", response_model=PostResponse , include_in_schema=False)
async def post_page(request:Request,post_id:int , db : Annotated[AsyncSession,Depends(get_db)]):
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
    db: Annotated[AsyncSession, Depends(get_db)],
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