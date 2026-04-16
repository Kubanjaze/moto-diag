"""Phase 06 — symptom taxonomy + repository tests."""

import json
import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.symptom_repo import (
    add_symptom, get_symptom, search_symptoms,
    list_symptoms_by_category, count_symptoms,
)
from motodiag.knowledge.loader import load_symptom_file


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


class TestSymptomRepo:
    def test_add_and_get(self, db_path):
        add_symptom("Won't start", "Engine cranks but won't fire", "starting",
                     ["fuel", "electrical"], db_path)
        result = get_symptom("Won't start", db_path)
        assert result is not None
        assert result["category"] == "starting"
        assert "fuel" in result["related_systems"]

    def test_get_not_found(self, db_path):
        assert get_symptom("Nonexistent", db_path) is None

    def test_search_by_query(self, db_path):
        add_symptom("Stalls at idle", "Dies at idle", "idle", db_path=db_path)
        add_symptom("Rough idle", "Runs rough", "idle", db_path=db_path)
        results = search_symptoms(query="idle", db_path=db_path)
        assert len(results) == 2

    def test_search_by_category(self, db_path):
        add_symptom("Stalls at idle", "Dies at idle", "idle", db_path=db_path)
        add_symptom("Loss of power", "No power", "engine", db_path=db_path)
        results = search_symptoms(category="idle", db_path=db_path)
        assert len(results) == 1
        assert results[0]["name"] == "Stalls at idle"

    def test_list_by_category(self, db_path):
        add_symptom("Spongy brakes", "Soft lever", "brakes", db_path=db_path)
        add_symptom("Brake squeal", "Squealing", "brakes", db_path=db_path)
        results = list_symptoms_by_category("brakes", db_path)
        assert len(results) == 2

    def test_count(self, db_path):
        add_symptom("A", "desc A", "engine", db_path=db_path)
        add_symptom("B", "desc B", "fuel", db_path=db_path)
        assert count_symptoms(db_path) == 2

    def test_related_systems_parsed(self, db_path):
        add_symptom("Misfires", "Skips", "engine", ["fuel", "engine", "electrical"], db_path)
        result = get_symptom("Misfires", db_path)
        assert isinstance(result["related_systems"], list)
        assert len(result["related_systems"]) == 3


class TestSymptomLoader:
    def test_load_file(self, db_path, tmp_path):
        data = [
            {"name": "Stalls", "description": "Engine dies", "category": "idle"},
            {"name": "Knock", "description": "Pinging", "category": "noise",
             "related_systems": ["engine", "fuel"]},
        ]
        f = tmp_path / "test_symptoms.json"
        f.write_text(json.dumps(data))
        count = load_symptom_file(f, db_path)
        assert count == 2
        assert count_symptoms(db_path) == 2

    def test_load_real_symptoms(self, db_path):
        from motodiag.core.config import DATA_DIR
        symptoms_file = DATA_DIR / "knowledge" / "symptoms.json"
        if symptoms_file.exists():
            count = load_symptom_file(symptoms_file, db_path)
            assert count == 40

    def test_file_not_found(self, db_path):
        with pytest.raises(FileNotFoundError):
            load_symptom_file("/nonexistent.json", db_path)
