from pydantic import BaseModel , ConfigDict , Field , EmailStr

from datetime import datetime

class UserBase(BaseModel):
    username : str = Field(min_length=1 , max_length= 50 )
    email : EmailStr = Field(max_length=30)

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    username : str | None  = Field(default=None,min_length=1,max_length=50)
    email : str | None = Field(default=None,min_length=1 , max_length=100)
    img_path : str | None = Field(default=None,min_length=1 , max_length=200)

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id : int 
    image_file : str | None
    image_path : str



class PostBase(BaseModel):
    title : str = Field(min_length=1 , max_length= 50)
    content : str = Field(min_length=1)
    
class PostUpdate(PostBase):
    title : str | None = Field(min_length=1,max_length=50,default=None)
    content : str | None = Field(min_length=1,default=None)



class PostCreate(PostBase):
    user_id : int 

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id : int
    user_id : int
    date_posted : datetime
    author : UserResponse

