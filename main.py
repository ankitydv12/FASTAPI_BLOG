from urllib.request import Request

from fastapi import FastAPI , Request
from fastapi.templating import Jinja2Templates

from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static",StaticFiles(directory="static"),name="static")

post :  list[dict] = [
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
@app.get("/post" , include_in_schema=False,name="post")
def home(request: Request):
    return templates.TemplateResponse(request,"home.html",{"posts":post,"title":title})


@app.get("/api/posts")
def get_posts():
    return post