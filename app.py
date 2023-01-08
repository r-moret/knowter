from datetime import datetime
from fastapi import FastAPI, UploadFile, HTTPException, Body
from tinydb import TinyDB, Query
from pydantic import BaseModel, validator, root_validator
from typing import BinaryIO
from base64 import b64encode

db = TinyDB("db.json")
app = FastAPI()


class Item(BaseModel):
    user: int
    id: int
    created: str
    content: str | None = None
    image: str | None = None

    @root_validator(pre=True)
    def ensure_content_or_image(cls, values):
        if not (
            (("content" not in values) and ("image" in values))
            or (("content" in values) and ("image" not in values))
        ):
            raise ValueError(
                'One of the fields "content" or "image" is needed, but '
                'just one of them at the same time.'
            )
        return values
    
    @validator("image", pre=True)
    def encode_image(cls, img: BinaryIO):
        return b64encode(img.read()).decode("ascii")

    class Config:
        arbitrary_types_allowed = True


def next_id(user_id):
    items_ids = [_i["id"] for _i in list_items(user_id)]
    last_id = max(items_ids, default=-1)
    new_id = last_id + 1
    return new_id


@app.get("/{user_id}/items")
def list_items(user_id: int):
    item = Query()
    return db.search(item.user == user_id)


@app.get("/{user_id}/items/{item_id}")
def get_item(user_id: int, item_id: int):
    item = Query()
    return db.search((item.user == user_id) & (item.id == item_id))


@app.post("/{user_id}/items/content")
def add_content(user_id: int, content: str = Body()):
    new_id = next_id(user_id)

    item = Item(
        user=user_id, 
        id=new_id, 
        created=datetime.now().isoformat(), 
        content=content,
    )
    db.insert(item.dict())


@app.post("/{user_id}/items/images")
def add_image(user_id: int, upload_file: UploadFile):
    if not upload_file.content_type.startswith("image"):
        raise HTTPException(
            status_code=415, 
            detail=(
                f"The content type {upload_file.content_type} is not "
                f"supported, only images are allowed."
            )
        )

    new_id = next_id(user_id)

    item = Item(
        user=user_id,
        id=new_id,
        created=datetime.now().isoformat(),
        image=upload_file.file,
    )
    db.insert(item.dict())


@app.delete("/{user_id}/items/{item_id}")
def delete_item(user_id: int, item_id: int):
    item = Query()
    db.remove((item.user == user_id) & (item.id == item_id))
