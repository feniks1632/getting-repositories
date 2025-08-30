import logging
from typing import Literal
import re
import httpx

from fastapi import FastAPI, HTTPException
import asyncio

from models import UserReposResponse

logging.basicConfig(level=logging.INFO)

USERNAME_REGEX_VALIDATOR = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_]{0,38}$")

app = FastAPI(
    title="Github Explorer",
    description="API для получения репозиториев пользователя",
    version="0.1.0",
)

CACHE = {}


async def fetch_repositories(username: str) -> list[dict]:
    """Получаем репозитории из GitHub"""
    url = f"https://api.github.com/users/{username}/repos"

    if username in CACHE:
        return CACHE[username]

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            repos = [
                {
                    "name": repo["name"],
                    "description": repo["description"] or "Нет Описания",
                    "stars": repo["stargazers_count"],
                    "url": repo["html_url"],
                    "updated_at": repo["updated_at"],
                }
                for repo in data
            ]

            CACHE[username] = repos
            return repos

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Пользователь не найден!")
            else:
                raise HTTPException(
                    status_code=500, detail=f"Ошибка GitHub: {e.response.status_code}"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503, detail="Не удалось подключиться к GItHub"
            )


@app.get(
    "/user/{username}/repos",
    response_model=UserReposResponse,
    summary="Получить репозитории пользователя GitHub",
    description="Возвращает список репозиториев с сортировкой по звёздам",
)
async def get_user_repos(
    username: str, sort: Literal["stars", "updated"] | None = None
):

    logging.info(f"Запрос репозиториев для {username}")

    if not username:
        raise HTTPException(
            status_code=400, detail="Имя пользователя не может быть пустым"
        )

    if not USERNAME_REGEX_VALIDATOR.match(username):
        raise HTTPException(
            status_code=400,
            detail="Некорректное имя пользователя. Разрешены: \n буквы, цыфры, -, _. Длинна 1-39 символов, не может начинаться с -/_",
        )

    repos = await fetch_repositories(username)

    if sort == "stars":
        repos = sorted(repos, key=lambda x: x["stars"], reverse=True)
    elif sort == "updated":
        repos = sorted(repos, key=lambda x: x["updated_at"], reverse=True)

    return {"username": username, "total": len(repos), "repositories": repos}


@app.post("/clear-cache")
async def clear_cache():
    CACHE.clear()
    return {"status": "Кеш очищен"}
