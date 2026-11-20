from sqlalchemy.orm import Session

from resolveflow.services.erasure_journal import initialize


def provision(engine, settings, root):
    assert settings.environment == "test"
    settings.erasure_journal_root = root.resolve() / "journal"
    settings.erasure_witness_root = root.resolve() / "witness"
    for path in (settings.erasure_journal_root, settings.erasure_witness_root):
        path.mkdir(mode=0o700)
    with Session(engine) as db:
        initialize(db, settings)
