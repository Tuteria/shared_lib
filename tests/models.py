import typing
from datetime import datetime

import sqlalchemy
from pydantic import EmailStr, SecretStr, validator

from orm import Base, CacheBase, fields, BareBase


class Bare(BareBase):
    special_id: int
    name: str

    @classmethod
    def get_primary_key(cls):
        return "special_id"

    class Config:
        table_name = "special_table"
        table_config = {"special_id": {"primary_key": True, "index": True}}


class User(Base):
    full_name: str
    email: EmailStr
    password: SecretStr = ""
    is_active: bool = True
    created: datetime = None
    modified: datetime = None

    class Config:
        table_name = "users"
        cache_field = "email"
        table_config = {
            "id": {"primary_key": True, "index": True},
            "full_name": {"index": True},
            "email": {"unique": True},
            "is_active": {"default": True},
            "created": {"default": datetime.now},
            "modified": {"onupdate": datetime.now},
        }

    @validator("full_name", pre=True, always=True)
    def set_full_name(cls, v):
        return v or ""

    @validator("email", pre=True, always=True)
    def set_email(cls,v):
        return v or ""


class Skill(Base):
    name: str

    class Config:
        table_name = "skills"
        cache_field = "name"
        table_config = {"id": {"primary_key": True}}


class PhoneNumber(Base):
    number: str
    user: fields.Foreign(User)

    class Config:
        table_name = "phone_numbers"
        table_config = {
            "id": {"primary_key": True},
            "number": {"index": True, "length": 15},
            "user": {"name": "user_id", "type": int},
        }


class Profile(Base):
    addresses: typing.Optional[fields.JSON()] = []
    user: fields.Foreign(User)

    class Config:
        table_name = "profiles"
        table_config = {
            "id": {"primary_key": True},
            "user": {"name": "user_id", "type": int},
            "addresses": {"jsonb": True},
        }

    @validator("addresses", pre=True, always=True)
    def set_addresses(cls, v):
        return v or []


class UserInfo(CacheBase):
    full_name: str
    email: EmailStr
    is_active: bool = True
    addresses: typing.List[dict] = []
    numbers: typing.List[str] = []

    class Config:
        cache_key = "user_info"
        cache_field = "email"

    @classmethod
    async def get_data(cls, key):
        profile = await Profile.objects.filter(user__email=key).get()
        phone_numbers = await PhoneNumber.objects.filter(user__email=key).all()
        user = profile.user
        return dict(
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            addresses=profile.addresses,
            numbers=[x.number for x in phone_numbers],
        )


class ProfileCache(CacheBase):
    email: EmailStr
    user: User

    class Config:
        cache_key = "profile_info"
        cache_field = "email"

    @classmethod
    async def get_data(cls, key):
        user = await User.objects.filter(email=key).get()
        return dict(email=user.email, user=user)


def init_tables(database, replica_database=None):
    metadata = orm.utils.init_tables(Base, database, replica_database=replica_database)
    metadata = orm.utils.init_tables(
        BareBase, database, replica_database=replica_database, metadata=metadata
    )
    return metadata
