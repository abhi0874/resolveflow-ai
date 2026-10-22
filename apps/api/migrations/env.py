from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

from resolveflow.core.config import Settings
from resolveflow.db import models  # noqa: F401 -- register migration metadata
from resolveflow.db.base import Base
from resolveflow.documents import models as document_models  # noqa: F401
from resolveflow.jobs import models as job_models  # noqa: F401
from resolveflow.rag import models as rag_models  # noqa: F401
from resolveflow.retrieval import models as retrieval_models  # noqa: F401
from resolveflow.workflows import models as workflow_models  # noqa: F401

config = context.config


def database_url():
    settings = Settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is required for Alembic; see docs/DATABASE.md")
    return make_url(settings.database_url.get_secret_value())


def migrate(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=database_url(),
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    migrate(config.attributes["connection"])
else:
    engine = create_engine(
        database_url(),
        poolclass=pool.NullPool,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        with engine.connect() as connection:
            migrate(connection)
    finally:
        engine.dispose()
