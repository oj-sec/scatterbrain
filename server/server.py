import hashlib
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles

from embedder import Embedder

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

clients = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Scatterbrain server initialising clients.")
    clients["embedder"] = Embedder(None, None)
    logging.info("Scatterbrain server initialised.")
    yield
    clients.clear()


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


@app.get("/api/reset")
async def reset():
    try:
        clients["embedder"] = Embedder(None, None)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


@app.post("/api/set-model")
async def select_model(request: Request):
    try:
        data = await request.json()
        clients["embedder"].model = data["model"]
        clients["embedder"].dimensions = data["dimensions"]
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


@app.get("/api/check-model")
async def check_model():
    return {"status": clients["embedder"].check_model()}


@app.get("/api/download-model")
async def download_model():
    try:
        clients["embedder"].download_model()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


@app.post("/api/embed-text")
async def embed_text(request: Request):
    try:
        data = await request.json()
        embeddings = (
            clients["embedder"]
            .embed_text(data["row"], data["field"], data["overflow"])
            .tolist()
        )
        return {"status": "success", "embeddings": embeddings}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


@app.post("/api/reduce-dims")
async def reduce_dims(request: Request):
    try:
        data = await request.json()
        reduced = clients["embedder"].reduce_dimensions(
            plot_dimensions=data["plotDimensions"]
        )
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


@app.post("/api/plot")
async def plot(request: Request):
    try:
        data = await request.json()
        plotHTML = clients["embedder"].generate_scatter(
            data["field"], cmap=data["cmap"], category=data["category"]
        )
        return {"status": "success", "plot": plotHTML}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


@app.post("/api/embed-category")
async def embed_category(request: Request):
    try:
        data = await request.json()
        embeddings = clients["embedder"].embed_comparison_text(data["text"]).tolist()
        return {"status": "success", "embeddings": embeddings}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


@app.post("/api/categorise")
async def compare(request: Request):
    try:
        data = await request.json()
        comparison = clients["embedder"].compare_embeddings(data["text"])
        return {"status": "success", "closest": comparison}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "message": str(e)}


app.mount("/", StaticFiles(directory="../client/build", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
