import json
from collections import Counter

import numpy as np
import pytest
from pydantic import ValidationError

from resolveflow.ml.artifact import TrainingConfig, decode, read_artifact
from resolveflow.ml.classifier import LocalTicketClassifier
from resolveflow.ml.contracts import (
    CATEGORY_VERSION,
    LABELS,
    ModelUnavailable,
    Prediction,
    TicketText,
)
from resolveflow.ml.dataset import DATASET_PATH, load_dataset, split_dataset, split_manifest
from resolveflow.ml.evaluation import evaluate
from resolveflow.ml.training import train


@pytest.fixture(scope="session")
def trained_model(tmp_path_factory):
    root = tmp_path_factory.mktemp("classifier")
    train(root, "test-v1", TrainingConfig())
    return root


def test_dataset_groups_and_train_only_vocabulary(trained_model):
    rows, digest = load_dataset()
    assert len(rows) == 280 and Counter(r.label for r in rows) == dict.fromkeys(LABELS, 40)
    splits = split_dataset(rows, 42)
    assert [len(splits[key]) for key in ("train", "validation", "test")] == [168, 56, 56]
    manifests = split_manifest(splits)
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        assert not set(manifests[left]["groups"]) & set(manifests[right]["groups"])
        assert not set(manifests[left]["ids"]) & set(manifests[right]["ids"])
    artifact = read_artifact(trained_model, "test-v1")
    assert artifact.dataset_sha256 == digest
    pipeline = decode(artifact, "test-v1")
    analyzer = pipeline.named_steps["tfidf"].build_analyzer()
    train_tokens = {token for r in splits["train"] for token in analyzer(r.combined())}
    heldout_tokens = {
        token for r in splits["test"] for token in analyzer(r.combined())
    } - train_tokens
    assert heldout_tokens and not heldout_tokens & artifact.vocabulary.keys()
    assert artifact.vocabulary.keys() <= train_tokens
    assert manifests == artifact.evaluation["split"]


@pytest.mark.parametrize("change", ["duplicate", "label", "near_duplicate", "mixed_group"])
def test_dataset_rejects_invalid_records(tmp_path, change):
    rows = [json.loads(line) for line in DATASET_PATH.read_text().splitlines()]
    if change == "duplicate":
        rows.append(rows[0])
    elif change == "label":
        rows[0]["label"] = "Imaginary category"
    elif change == "mixed_group":
        rows[0]["group_id"] = rows[-1]["group_id"]
    else:
        row = {
            **rows[0],
            "id": "near-copy",
            "group_id": "near-copy",
            "description": rows[0]["description"] + " Please.",
        }
        rows.append(row)
    path = tmp_path / "bad.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError):
        load_dataset(path)


def test_training_reproducibility_artifact_and_independent_evaluation(trained_model, tmp_path):
    train(tmp_path, "second-v1", TrainingConfig())
    first, second = read_artifact(trained_model, "test-v1"), read_artifact(tmp_path, "second-v1")
    assert first.coefficients == second.coefficients
    assert first.idf == second.idf and first.vocabulary == second.vocabulary
    assert first.evaluation == second.evaluation
    assert first.info.category_mapping_version == CATEGORY_VERSION
    rows, _ = load_dataset()
    pipeline = decode(first, "test-v1")
    test = split_dataset(rows, 42)["test"]
    actual = evaluate(pipeline, test, first.config.threshold)
    assert actual == first.evaluation["test"]
    # Useful baseline beats a uniform guess; this is no production accuracy guarantee.
    assert actual["macro_f1"] > 1 / 7
    assert sum(map(sum, actual["confusion_matrix"])) == len(test)
    assert (tmp_path / "second-v1/evaluation.json").is_file()
    assert (tmp_path / "second-v1/model.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError, match="already exists"):
        train(tmp_path, "second-v1", TrainingConfig())


@pytest.mark.parametrize(
    "values",
    [
        {"title": " ", "description": "\n"},
        {"title": None},
        {"title": 7},
        {"title": "x" * 201},
        {"title": "ok", "description": "x" * 8001},
        {"title": "nul\x00"},
    ],
)
def test_invalid_inference_text(values):
    with pytest.raises(ValidationError):
        TicketText(**values)


def test_model_predictions_batch_score_and_uncertainty(trained_model, monkeypatch):
    model = LocalTicketClassifier(trained_model, "test-v1", 0.45)
    assert model.health_check()
    ticket = TicketText(
        title="  Password reset  ",
        description="I forgot my password and the reset email never arrives.",
    )
    assert ticket.title == "Password reset"
    prediction = model.predict(ticket)
    Prediction.model_validate(prediction.model_dump())
    assert prediction.predicted_category in LABELS
    assert prediction.human_review_recommended and prediction.model_version == "test-v1"
    assert prediction.score_kind == "uncalibrated_model_probability"
    direct = decode(read_artifact(trained_model, "test-v1"), "test-v1").predict_proba(
        [ticket.combined()]
    )[0]
    assert prediction.score == pytest.approx(float(direct.max()), abs=1e-12)
    assert model.predict_batch([ticket, ticket]) == [prediction, prediction]
    unknown = model.predict(TicketText(title="zzzzzzz qqqqqqq xxxxzzzz"))
    assert unknown.uncertain and unknown.suggested_category is None
    strict = LocalTicketClassifier(trained_model, "test-v1", 1)
    assert strict.predict(ticket).uncertain
    # Loading happens once. Inference still works if the loader subsequently fails.
    monkeypatch.setattr(
        "resolveflow.ml.classifier.read_artifact", lambda *a: (_ for _ in ()).throw(RuntimeError())
    )
    assert model.predict(ticket) == prediction
    assert model.get_model_info().category_mapping_version == CATEGORY_VERSION
    for batch in ([], [ticket] * 33, ["raw unvalidated text"]):
        with pytest.raises(ValueError):
            model.predict_batch(batch)


def test_missing_invalid_models_are_unavailable_and_do_not_execute(tmp_path, trained_model):
    for version in ("missing", "../escape"):
        model = LocalTicketClassifier(tmp_path, version, 0.45)
        assert not model.health_check()
        with pytest.raises(ModelUnavailable):
            model.predict(TicketText(title="Valid request"))
    folder = tmp_path / "test-v1"
    folder.mkdir()
    target = folder / "model.json"
    target.write_bytes(b"cos\nsystem\n(S'never execute'\ntR.")
    assert not LocalTicketClassifier(tmp_path, "test-v1", 0.45).health_check()
    artifact = read_artifact(trained_model, "test-v1")
    for updates in (
        {"sklearn_version": "0.0.0"},
        {"classes": ["invalid"]},
        {"coefficients": [[0.0]]},
        {"schema_version": 99},
    ):
        target.write_text(artifact.model_copy(update=updates).model_dump_json())
        assert not LocalTicketClassifier(tmp_path, "test-v1", 0.45).health_check()
        with pytest.raises(ValueError):
            decode(artifact.model_copy(update=updates), "test-v1")
    target.unlink()
    target.symlink_to(trained_model / "test-v1/model.json")
    assert not LocalTicketClassifier(tmp_path, "test-v1", 0.45).health_check()


def test_inference_failure_and_capacity_are_safe(trained_model, monkeypatch):
    model = LocalTicketClassifier(trained_model, "test-v1", 0.45)
    text = TicketText(title="A valid question")
    for _ in range(2):
        assert model._slots.acquire(blocking=False)
    with pytest.raises(ModelUnavailable, match="busy"):
        model.predict(text)
    for _ in range(2):
        model._slots.release()
    monkeypatch.setattr(
        model._pipeline.named_steps["classifier"],
        "predict_proba",
        lambda _: np.full((1, 7), np.nan),
    )
    with pytest.raises(ModelUnavailable) as failure:
        model.predict(text)
    assert "valid question" not in str(failure.value)
