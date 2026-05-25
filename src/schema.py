"""
JSON Schema-валидаторы для коллекций.

Идея архитектуры:
- Долгоживущие сущности (студенты, преподаватели, курсы, группы) — отдельные
  коллекции со ссылками по ObjectId. Это даёт нормализацию и обновляемость.
- Связь "студент-курс-семестр" вынесена в коллекцию `enrollments`.
- Оценки — отдельная коллекция `grades` (write-heavy, нужны индексы по
  разным осям: студент, курс, преподаватель, период).
- Контакты студента/преподавателя — вложенный документ (embedded),
  потому что они всегда читаются вместе с владельцем и не нужны отдельно.
"""
from __future__ import annotations

from typing import Any

GRADE_VALUE_MIN = 2
GRADE_VALUE_MAX = 5

STUDENT_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["full_name", "email", "group_id", "enrollment_year", "status"],
        "properties": {
            "full_name": {"bsonType": "string", "minLength": 3},
            "email": {"bsonType": "string", "pattern": r"^.+@.+\..+$"},
            "group_id": {"bsonType": "objectId"},
            "enrollment_year": {"bsonType": "int", "minimum": 2000, "maximum": 2100},
            "status": {"enum": ["active", "expelled", "graduated", "academic_leave"]},
            "birth_date": {"bsonType": "date"},
            "contacts": {
                "bsonType": "object",
                "properties": {
                    "phone": {"bsonType": "string"},
                    "address": {"bsonType": "string"},
                },
            },
        },
    }
}

PROFESSOR_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["full_name", "email", "department", "position"],
        "properties": {
            "full_name": {"bsonType": "string", "minLength": 3},
            "email": {"bsonType": "string", "pattern": r"^.+@.+\..+$"},
            "department": {"bsonType": "string"},
            "position": {
                "enum": [
                    "assistant",
                    "senior_lecturer",
                    "associate_professor",
                    "professor",
                    "head_of_department",
                ]
            },
            "hire_date": {"bsonType": "date"},
            "degree": {"bsonType": "string"},
        },
    }
}

COURSE_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["title", "code", "credits", "department"],
        "properties": {
            "title": {"bsonType": "string", "minLength": 3},
            "code": {"bsonType": "string", "minLength": 3},
            "credits": {"bsonType": "int", "minimum": 1, "maximum": 30},
            "department": {"bsonType": "string"},
            "description": {"bsonType": "string"},
            "semester_offered": {
                "bsonType": "array",
                "items": {"bsonType": "int", "minimum": 1, "maximum": 8},
            },
        },
    }
}

GROUP_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "faculty", "year", "specialization"],
        "properties": {
            "name": {"bsonType": "string"},
            "faculty": {"bsonType": "string"},
            "year": {"bsonType": "int", "minimum": 1, "maximum": 6},
            "specialization": {"bsonType": "string"},
        },
    }
}

ENROLLMENT_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["student_id", "course_id", "professor_id", "semester", "year"],
        "properties": {
            "student_id": {"bsonType": "objectId"},
            "course_id": {"bsonType": "objectId"},
            "professor_id": {"bsonType": "objectId"},
            "semester": {"bsonType": "int", "minimum": 1, "maximum": 2},
            "year": {"bsonType": "int", "minimum": 2000, "maximum": 2100},
        },
    }
}

GRADE_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "student_id",
            "course_id",
            "professor_id",
            "value",
            "date",
            "type",
            "semester",
            "year",
        ],
        "properties": {
            "student_id": {"bsonType": "objectId"},
            "course_id": {"bsonType": "objectId"},
            "professor_id": {"bsonType": "objectId"},
            "enrollment_id": {"bsonType": "objectId"},
            "value": {
                "bsonType": "int",
                "minimum": GRADE_VALUE_MIN,
                "maximum": GRADE_VALUE_MAX,
            },
            "date": {"bsonType": "date"},
            "type": {"enum": ["exam", "credit", "midterm", "coursework"]},
            "semester": {"bsonType": "int", "minimum": 1, "maximum": 2},
            "year": {"bsonType": "int", "minimum": 2000, "maximum": 2100},
            "comment": {"bsonType": "string"},
        },
    }
}

COLLECTIONS: dict[str, dict[str, Any]] = {
    "students": STUDENT_VALIDATOR,
    "professors": PROFESSOR_VALIDATOR,
    "courses": COURSE_VALIDATOR,
    "groups": GROUP_VALIDATOR,
    "enrollments": ENROLLMENT_VALIDATOR,
    "grades": GRADE_VALIDATOR,
}


def apply_schemas(db) -> None:
    """Создаёт коллекции с валидаторами (или обновляет существующие)."""
    existing = set(db.list_collection_names())
    for name, validator in COLLECTIONS.items():
        if name in existing:
            db.command("collMod", name, validator=validator, validationLevel="moderate")
            print(f"[schema] обновлён валидатор: {name}")
        else:
            db.create_collection(name, validator=validator, validationLevel="moderate")
            print(f"[schema] создана коллекция: {name}")
