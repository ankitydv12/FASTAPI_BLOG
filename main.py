from urllib.request import Request

from fastapi import FastAPI , Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="template")


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

#  same content on the multiple url
@app.get("/")
@app.get("/home" , include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request,"home.html",{"post":post})


@app.get("/api/posts")
def get_posts():
    return post