"""Quiesced PostgreSQL snapshots plus referenced private objects, encrypted by restic."""

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import text

from resolveflow.backups.safety import private, require, run, safe_path, save_json, sha256
from resolveflow.core.config import API_ROOT
from resolveflow.documents.storage import LocalFileStorage


def owned(engine, *, empty=False, development_directory=None):
    url = engine.url
    require(
        url.host in {"127.0.0.1", "localhost", "::1"} and not url.query, "local_database_required"
    )
    require(
        url.database == "resolveflow_dev"
        or bool(re.fullmatch(r"resolveflow_test_[a-f0-9]{32}", url.database or "")),
        "unowned_database",
    )
    with engine.connect() as conn:
        if url.database == "resolveflow_dev":
            require(
                not empty and development_directory is not None, "development_restore_forbidden"
            )
            require(
                Path(conn.scalar(text("SHOW data_directory"))).resolve()
                == development_directory.resolve(),
                "database_ownership_mismatch",
            )
        else:
            require(
                bool(re.fullmatch(r"resolveflow_test_[a-f0-9]{32}", url.database or "")),
                "unowned_database",
            )
            marker = conn.scalar(
                text(
                    "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE "
                    "datname=current_database()"
                )
            )
            require(
                marker and marker.startswith(("resolveflow-pytest-", "resolveflow-backup-")),
                "unowned_database",
            )
        if empty:
            require(
                conn.scalar(
                    text(
                        "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN "
                        "('pg_catalog','information_schema')"
                    )
                )
                == 0,
                "restore_target_not_empty",
            )


def pg(engine, binary_directory, tool, *args):
    url = engine.url
    # libpq password-file protocol; no password in process argv/environment.
    with tempfile.TemporaryDirectory(prefix="resolveflow-pgpass-") as directory:
        password = Path(directory) / "pgpass"

        def escape(value):
            return str(value).replace("\\", "\\\\").replace(":", "\\:")

        password.write_text(
            ":".join(
                escape(x)
                for x in (url.host, url.port, url.database, url.username, url.password or "")
            )
            + "\n"
        )
        password.chmod(0o600)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PGHOST": url.host,
            "PGPORT": str(url.port),
            "PGUSER": url.username,
            "PGDATABASE": url.database,
            "PGPASSFILE": str(password),
            "PGCONNECT_TIMEOUT": "5",
        }
        return run(binary_directory / tool, args, env, timeout=300)


def fingerprints(cursor):
    tables = cursor.execute(
        "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN "
        "('pg_catalog','information_schema') ORDER BY 1,2"
    ).fetchall()
    values = {}
    for schema, table in tables:
        query = sql.SQL("SELECT row_to_json(t)::text FROM {}.{} t ORDER BY 1").format(
            sql.Identifier(schema), sql.Identifier(table)
        )
        digest = hashlib.sha256()
        count = 0
        for row in cursor.execute(query):
            digest.update(row[0].encode() + b"\n")
            count += 1
        values[schema + "." + table] = {"rows": count, "sha256": digest.hexdigest()}
    return values


def enough_space(path, required):
    require(shutil.disk_usage(path).free >= required, "insufficient_disk_space")


def components(root):
    result = {}
    for path in root.rglob("*"):
        safe_path(path)
        require(path.is_dir() or path.is_file(), "unsafe_component")
        if path.is_file() and path.name != "manifest.json":
            result[str(path.relative_to(root))] = {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
    return result


def validate_bundle(root):
    private(root, directory=True)
    manifest = json.loads((root / "manifest.json").read_text())
    require(
        manifest["version"] == 1 and manifest["files"] == components(root),
        "component_integrity_failed",
    )
    require(
        "database.dump" in manifest["files"] and manifest["files"]["database.dump"]["bytes"] > 0,
        "missing_database_archive",
    )
    require(
        manifest["tables"] and manifest["revision"] and isinstance(manifest["documents"], list),
        "incomplete_manifest",
    )
    for doc in manifest["documents"]:
        name = f"documents/{uuid.UUID(doc['workspace_id']).hex}/{doc['storage_key']}"
        require(re.fullmatch(r"[a-f0-9]{32}", doc["storage_key"]), "unsafe_storage_key")
        require(
            manifest["files"].get(name) == {"sha256": doc["checksum"], "bytes": doc["file_size"]},
            "document_integrity_failed",
        )
    return manifest


def capture(repo, engine, settings, *, quiesced=False, development_directory=None):
    require(quiesced, "maintenance_confirmation_required")
    owned(engine, development_directory=development_directory)
    require(not settings.ai_live_enabled, "live_ai_must_be_disabled")
    safe_path(settings.document_storage_root)
    for root in (settings.document_storage_root, settings.classifier_artifact_root):
        require(
            not repo.state.is_relative_to(root)
            and not repo.config.repository.is_relative_to(root)
            and not root.is_relative_to(repo.state)
            and not root.is_relative_to(repo.config.repository),
            "overlapping_storage",
        )
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="snapshot-", dir=repo.state) as directory:
        stage = Path(directory)
        bundle = stage / "bundle"
        bundle.mkdir(mode=0o700)
        with engine.connect() as connection:
            raw = connection.connection.driver_connection
            cursor = raw.cursor()
            cursor.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            cursor.execute("SET LOCAL lock_timeout='3s'")
            cursor.execute("SET LOCAL statement_timeout='300s'")
            active = cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid()"
            ).fetchone()[0]
            require(active == 0, "database_clients_active_stop_writers")
            tables = cursor.execute(
                "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN "
                "('pg_catalog','information_schema') ORDER BY 1,2"
            ).fetchall()
            require(tables, "empty_source_database")
            # SHARE blocks INSERT/UPDATE/DELETE while pg_dump's ACCESS SHARE can read.
            for schema, table in tables:
                cursor.execute(
                    sql.SQL("LOCK TABLE {}.{} IN SHARE MODE").format(
                        sql.Identifier(schema), sql.Identifier(table)
                    )
                )
            revision = cursor.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            require(
                ScriptDirectory.from_config(Config(str(API_ROOT / "alembic.ini"))).get_heads()
                == [revision],
                "schema_revision_mismatch",
            )
            server = int(cursor.execute("SHOW server_version_num").fetchone()[0]) // 10000
            for tool in ("pg_dump", "pg_restore"):
                version = pg(engine, repo.config.pg_bin, tool, "--version").decode()
                require(re.search(rf"\b{server}\.", version), "postgres_tool_version_mismatch")
            docs = cursor.execute(
                "SELECT "
                "workspace_id,storage_key,checksum,file_size,processing_status,"
                "indexing_status FROM documents"
            ).fetchall()
            require(
                all(
                    row[4] not in {"pending", "processing", "deleting"} and row[5] != "indexing"
                    for row in docs
                ),
                "document_mutation_incomplete",
            )
            database_bytes = cursor.execute(
                "SELECT pg_database_size(current_database())"
            ).fetchone()[0]
            estimated = (
                database_bytes * 2 + sum(row[3] for row in docs) * 2 + repo.config.min_free_bytes
            )
            enough_space(repo.state, estimated)
            enough_space(repo.config.repository, estimated)
            table_state = fingerprints(cursor)
            snapshot = cursor.execute("SELECT pg_export_snapshot()").fetchone()[0]
            pg(
                engine,
                repo.config.pg_bin,
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--lock-wait-timeout=3s",
                "--snapshot",
                snapshot,
                "--file",
                bundle / "database.dump",
            )
            pg(engine, repo.config.pg_bin, "pg_restore", "--list", bundle / "database.dump")
            documents = []
            storage = LocalFileStorage(settings.document_storage_root)
            for workspace, key, checksum, size, _, _ in docs:
                private(settings.document_storage_root, directory=True)
                private(settings.document_storage_root / workspace.hex, directory=True)
                content = storage.read(workspace, key, size)
                require(
                    len(content) == size and hashlib.sha256(content).hexdigest() == checksum,
                    "document_integrity_failed",
                )
                destination = bundle / "documents" / workspace.hex / key
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                destination.write_bytes(content)
                documents.append(
                    {
                        "workspace_id": str(workspace),
                        "storage_key": key,
                        "checksum": checksum,
                        "file_size": size,
                    }
                )
            # Keep immutable classifiers, but exclude reproducible downloaded embedding weights.
            classifier = settings.classifier_artifact_root
            safe_path(classifier)
            if classifier.exists():
                for path in classifier.rglob("*"):
                    safe_path(path)
                    require(
                        path.is_dir()
                        or (path.is_file() and path.name in {"model.json", "evaluation.json"}),
                        "unexpected_classifier_file",
                    )
                    if path.is_file():
                        enough_space(repo.state, path.stat().st_size + repo.config.min_free_bytes)
                        destination = bundle / "classifier" / path.relative_to(classifier)
                        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                        shutil.copyfile(path, destination)
            embedding_manifest = settings.embedding_model_root / "manifest.json"
            if embedding_manifest.exists():
                safe_path(embedding_manifest)
                destination = bundle / "dependencies"
                destination.mkdir(mode=0o700)
                shutil.copyfile(embedding_manifest, destination / "embedding-manifest.json")
            extensions = cursor.execute(
                "SELECT extname,extversion FROM pg_extension ORDER BY extname"
            ).fetchall()
            manifest = {
                "version": 1,
                "backup_id": uuid.uuid4().hex,
                "created_at": time.time(),
                "revision": revision,
                "postgres_major": server,
                "extensions": extensions,
                "tables": table_state,
                "documents": documents,
                "classifier_version": settings.classifier_model_version,
                "dependencies": {
                    name: sha256(API_ROOT / name) for name in ("uv.lock", "pyproject.toml")
                },
                "files": components(bundle),
                "consistency": "offline-writers-stopped-plus-share-locks-exported-snapshot",
            }
            save_json(bundle / "manifest.json", manifest)
            raw.rollback()
        for path in bundle.rglob("*"):
            path.chmod(0o700 if path.is_dir() else 0o600)
        validate_bundle(bundle)
        output = repo.call(
            "backup",
            "--json",
            "--host",
            "resolveflow",
            "--tag",
            "resolveflow-v1",
            "bundle",
            cwd=stage,
        )
        summary = next(
            json.loads(line)
            for line in output.splitlines()
            if json.loads(line).get("message_type") == "summary"
        )
        identity = repo.select(summary["snapshot_id"])
        repo.check()
        result = {
            "snapshot": identity,
            "seconds": round(time.monotonic() - started, 3),
            "bytes": sum(v["bytes"] for v in manifest["files"].values()),
            "documents": len(documents),
        }
        repo.event("backup", result)
        return result


def unpack(repo, identity, destination):
    require(not destination.exists(), "restore_directory_exists")
    safe_path(destination)
    identity = repo.select(identity)
    repo.check()
    destination.mkdir(mode=0o700)
    repo.call("restore", identity, "--target", destination, "--verify")
    return identity, validate_bundle(destination / "bundle")


def restore_into(repo, identity, engine, destination):
    """Only owned empty disposable DBs; caller owns creation and guarded cleanup."""
    started = time.monotonic()
    owned(engine, empty=True)
    identity, manifest = unpack(repo, identity, destination)
    require(
        ScriptDirectory.from_config(Config(str(API_ROOT / "alembic.ini"))).get_heads()
        == [manifest["revision"]],
        "restore_code_revision_mismatch",
    )
    pg(engine, repo.config.pg_bin, "pg_restore", "--list", destination / "bundle/database.dump")
    pg(
        engine,
        repo.config.pg_bin,
        "pg_restore",
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        "--single-transaction",
        "--dbname",
        engine.url.database,
        destination / "bundle/database.dump",
    )
    with engine.connect() as conn:
        require(
            conn.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'")),
            "pgvector_missing",
        )
        require(
            conn.scalar(text("SELECT version_num FROM alembic_version")) == manifest["revision"],
            "restored_revision_mismatch",
        )
        require(
            fingerprints(conn.connection.driver_connection.cursor()) == manifest["tables"],
            "restored_records_mismatch",
        )
        config = Config(str(API_ROOT / "alembic.ini"))
        config.attributes["connection"] = conn
        command.check(config)
    result = {
        "snapshot": identity,
        "seconds": round(time.monotonic() - started, 3),
        "tables": len(manifest["tables"]),
        "documents": len(manifest["documents"]),
        "workers_started": False,
    }
    repo.event("restore", result)
    return result
