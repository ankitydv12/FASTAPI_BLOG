from urllib.request import Request

from fastapi import FastAPI , Request , HTTPException , status
from fastapi.templating import Jinja2Templates

from fastapi.staticfiles import StaticFiles


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static",StaticFiles(directory="static"),name="static")

posts :  list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "Jane Doe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]

title = "Abc title "

#  same content on the multiple url
@app.get("/",include_in_schema=False ,name="home")
@app.get("/posts" , include_in_schema=False,name="post")
def home(request: Request):
    return templates.TemplateResponse(request,"home.html",{"posts":posts,"title":title})


@app.get("/posts/{post_id}" , include_in_schema=False )
def get_post(request : Request , post_id:int):
    for post in posts:
        if post["id"] == post_id:
            title =  post["title"]
            return templates.TemplateResponse(request,"post.html",{"post":post,"title":title})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"postById {post_id} does not exits")

@app.get("/api/posts")
def get_posts():
    return posts

@app.get("/api/post/{post_id}")
def get_posts(post_id:int):
    for post in posts:
        if post["id"] == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"{post_id} does not  exits ")

@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler( request:Request , exception : StarletteHTTPException ):
    message = exception.detail if exception.detail else "An error Occured Please check and try again "

    if request.url.path.startswith('/api'):
        return JSONResponse(
            status_code= exception.status_code,
            content= {"detail":message},
        )

    return templates.TemplateResponse(request ,
                                     "error.html"  , 
                                     {"status_code":exception.status_code, "title":exception.status_code , "message" : message},
                                     status_code=exception.status_code)


@app.exception_handler(RequestValidationError)
def validation_Exception_handler(request:Request , exception : RequestValidationError):

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT,
            content= {"details":exception.errors()},
        )

    return templates.TemplateResponse(request, "error.html",
                                      
                                      {
                                          "status_code" : status.HTTP_422_UNPROCESSABLE_CONTENT,
                                          "title" : status.HTTP_422_UNPROCESSABLE_CONTENT ,
                                          "message" : "Invalid request . Please check it "
                                      },status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)