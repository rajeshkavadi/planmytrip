"""Minimal API-key auth — enough to own saved trips, not a full IdP.

A user is created with `POST /users` and gets an opaque key; they send it as
the `X-API-Key` header. Swap for OAuth/JWT before production; the dependency
boundary here keeps that a localized change.
"""
from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import User


def new_api_key() -> str:
    return "pmt_" + secrets.token_urlsafe(24)


def current_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    if not x_api_key:
        raise HTTPException(401, "Missing X-API-Key header. Create a user at POST /users.")
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(401, "Invalid API key.")
    return user
