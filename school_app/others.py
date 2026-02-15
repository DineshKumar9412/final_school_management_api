## Sample check For Encryption and Decryption ##
# curl --location 'http://3.109.139.129:8000/api/users/decryption_check/?name=suhjn&email=3dinesh3%40gmail.com'
# curl --location 'http://3.109.139.129:8000/api/users/encryption_check/' \
# --header 'Content-Type: application/json' \
# --data '{
#     "payload": "Mf9n5AjdQ8Zyi96G0/o9vJ6ajb5OTTJd2pJogPh23P1aJSUGL8wRqnDDbz+plZrap1+Tsv5AY/eBDGjCfQ7bPQIyveHcvHAdb5FZQ5Ry6P4="
# }'

###### gokul

# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.responses import FileResponse
# import os, uuid, aiofiles

# app = FastAPI()

# UPLOAD_DIR = "/home/username/secure_uploads/images"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# @app.post("/api/upload-image")
# async def upload_image(image: UploadFile = File(...)):
#     if image.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
#         raise HTTPException(status_code=400, detail="Invalid image type")

#     image_id = uuid.uuid4().hex
#     ext = image.filename.split(".")[-1]
#     file_path = os.path.join(UPLOAD_DIR, f"{image_id}.{ext}")

#     async with aiofiles.open(file_path, "wb") as f:
#         content = await image.read()
#         await f.write(content)

#     return {
#         "image_id": image_id,
#         "image_url": f"https://yourdomain.com/api/images/{image_id}"
#     }

# @app.get("/api/images/{image_id}")
# async def get_image(image_id: str):
#     for ext in ["png", "jpg", "jpeg"]:
#         file_path = os.path.join(UPLOAD_DIR, f"{image_id}.{ext}")
#         if os.path.exists(file_path):
#             return FileResponse(file_path)

#     raise HTTPException(status_code=404, detail="Image not found")

# import logging

# def setup_logging():
#     logging.basicConfig(
#         level=logging.INFO,
#         format="%(asctime)s - %(levelname)s - %(message)s",
#     )

# from fastapi import FastAPI
# from app.core.logging import setup_logging

# setup_logging()

# app = FastAPI()

# import logging

# logger = logging.getLogger(__name__)

# logger.exception("Unhandled exception")

