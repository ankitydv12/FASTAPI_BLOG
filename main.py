from fastapi import FastAPI
from fastapi.responses import HTMLResponse
#creating a fastapi object , the fastapi object is used to route the reuest

app = FastAPI()

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
@app.get("/",response_class=HTMLResponse , include_in_schema=False)
@app.get("/home",response_class=HTMLResponse)
def home():
    # return {"message": "Hello World"} #this will return json to the endpoint

    return f"<h1>Hello World</h1>" #returning the html response

@app.get("/api/posts")
def get_posts():
    return post