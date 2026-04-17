"""
AWS 凭证配置 API。
三个子账号（PLM / 主业务 / 国内）各自独立，拥有独立的 Access Key、Secret Key、Region 和 Account ID。
凭证保存到数据库，运行时通过 get_account_credentials() 读取，无需重启容器。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.models import AwsCredentialSetting

router = APIRouter()

# 三个账号的 key 前缀
ACCOUNT_PREFIXES = ["PLM", "MAIN", "CN"]
CREDENTIAL_FIELDS = ["ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "REGION", "ACCOUNT_ID"]

ALL_KEYS = [
    f"{prefix}_{field}"
    for prefix in ACCOUNT_PREFIXES
    for field in CREDENTIAL_FIELDS
]


class AccountCredential(BaseModel):
    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    account_id: str


class AccountCredentialResponse(BaseModel):
    access_key_id: str
    secret_access_key: str  # 脱敏
    region: str
    account_id: str
    is_configured: bool


class AwsAllCredentials(BaseModel):
    plm: AccountCredential
    main: AccountCredential
    cn: AccountCredential


class AwsAllCredentialsResponse(BaseModel):
    plm: AccountCredentialResponse
    main: AccountCredentialResponse
    cn: AccountCredentialResponse


def _mask_secret(secret: str) -> str:
    if len(secret) > 8 and secret not in ("", "your-secret-access-key"):
        return secret[:4] + "****" + secret[-4:]
    return ""


def _is_placeholder(key: str) -> bool:
    return key in ("", "your-access-key-id", "AKIA...")


async def _load_all_db_credentials(db: AsyncSession) -> dict[str, str]:
    """从数据库读取所有账号凭证。"""
    result = await db.execute(
        select(AwsCredentialSetting).where(AwsCredentialSetting.key.in_(ALL_KEYS))
    )
    return {row.key: row.value for row in result.scalars().all()}


def get_account_credentials(creds: dict[str, str], prefix: str) -> dict:
    """从凭证字典中提取指定账号的凭证。"""
    return {
        "access_key_id": creds.get(f"{prefix}_ACCESS_KEY_ID", ""),
        "secret_access_key": creds.get(f"{prefix}_SECRET_ACCESS_KEY", ""),
        "region": creds.get(f"{prefix}_REGION", "us-east-1"),
        "account_id": creds.get(f"{prefix}_ACCOUNT_ID", ""),
    }


def _build_response(creds: dict[str, str], prefix: str) -> AccountCredentialResponse:
    access_key = creds.get(f"{prefix}_ACCESS_KEY_ID", "")
    secret_key = creds.get(f"{prefix}_SECRET_ACCESS_KEY", "")
    region = creds.get(f"{prefix}_REGION", "us-east-1")
    account_id = creds.get(f"{prefix}_ACCOUNT_ID", "")
    configured = not _is_placeholder(access_key) and bool(access_key)
    return AccountCredentialResponse(
        access_key_id=access_key if configured else "",
        secret_access_key=_mask_secret(secret_key) if configured else "",
        region=region,
        account_id=account_id,
        is_configured=configured,
    )


@router.get("/settings/aws", response_model=AwsAllCredentialsResponse)
async def get_aws_credentials(db: AsyncSession = Depends(get_db)):
    """读取三个账号的 AWS 凭证（Secret Key 脱敏）。"""
    creds = await _load_all_db_credentials(db)
    return AwsAllCredentialsResponse(
        plm=_build_response(creds, "PLM"),
        main=_build_response(creds, "MAIN"),
        cn=_build_response(creds, "CN"),
    )


def _account_to_rows(prefix: str, account: AccountCredential, now: datetime) -> list[dict]:
    return [
        {"key": f"{prefix}_ACCESS_KEY_ID", "value": account.access_key_id, "updated_at": now},
        {"key": f"{prefix}_SECRET_ACCESS_KEY", "value": account.secret_access_key, "updated_at": now},
        {"key": f"{prefix}_REGION", "value": account.region, "updated_at": now},
        {"key": f"{prefix}_ACCOUNT_ID", "value": account.account_id, "updated_at": now},
    ]


async def _upsert_rows(db: AsyncSession, rows: list[dict]) -> None:
    stmt = pg_insert(AwsCredentialSetting).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": stmt.excluded.value, "updated_at": stmt.excluded.updated_at},
    )
    await db.execute(stmt)
    await db.commit()


@router.put("/settings/aws", status_code=200)
async def save_all_aws_credentials(
    body: AwsAllCredentials,
    db: AsyncSession = Depends(get_db),
):
    """保存三个账号的 AWS 凭证到数据库。"""
    for name, account in [("PLM", body.plm), ("主业务", body.main), ("国内", body.cn)]:
        if not account.access_key_id or not account.secret_access_key:
            raise HTTPException(status_code=400, detail=f"{name} 账号的 Access Key 和 Secret Key 不能为空")

    now = datetime.now(tz=timezone.utc)
    rows = (
        _account_to_rows("PLM", body.plm, now)
        + _account_to_rows("MAIN", body.main, now)
        + _account_to_rows("CN", body.cn, now)
    )
    await _upsert_rows(db, rows)
    return {"message": "三个账号凭证已保存并生效"}


@router.put("/settings/aws/{account}", status_code=200)
async def save_single_account_credentials(
    account: str,
    body: AccountCredential,
    db: AsyncSession = Depends(get_db),
):
    """单独保存某个账号的凭证（account: plm / main / cn）。"""
    prefix_map = {"plm": "PLM", "main": "MAIN", "cn": "CN"}
    prefix = prefix_map.get(account.lower())
    if not prefix:
        raise HTTPException(status_code=404, detail="账号不存在，可选值: plm / main / cn")
    if not body.access_key_id or not body.secret_access_key:
        raise HTTPException(status_code=400, detail="Access Key 和 Secret Key 不能为空")

    now = datetime.now(tz=timezone.utc)
    rows = _account_to_rows(prefix, body, now)
    await _upsert_rows(db, rows)
    return {"message": f"{account.upper()} 账号凭证已保存并生效"}
