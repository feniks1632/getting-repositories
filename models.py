from pydantic import BaseModel
from typing import List


class RepoItem(BaseModel):
    name: str
    description: str
    stars: int
    url: str
    updated_at: str

class UserReposResponse(BaseModel):
    username: str
    total: int
    repositories: List[RepoItem]    