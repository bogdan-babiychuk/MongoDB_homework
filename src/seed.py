"""
Наполнение базы тестовыми данными при помощи Faker.

Генерируется:
- 5 факультетов × 4 группы = 20 групп
- ~200 студентов (распределены по группам)
- 30 преподавателей
- 25 курсов
- enrollments + grades за два учебных года (4 семестра)
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from faker import Faker
from pymongo.database import Database

fake = Faker("ru_RU")
Faker.seed(42)
random.seed(42)

FACULTIES = [
    ("ФИТ", "Программная инженерия"),
    ("ФИТ", "Информационные системы"),
    ("ММФ", "Прикладная математика"),
    ("ФФ", "Теоретическая физика"),
    ("ЭФ", "Экономика"),
]

POSITIONS = [
    "assistant",
    "senior_lecturer",
    "associate_professor",
    "professor",
    "head_of_department",
]

COURSE_CATALOG = [
    ("CS101", "Введение в программирование", "ФИТ", 5),
    ("CS201", "Алгоритмы и структуры данных", "ФИТ", 6),
    ("CS301", "Базы данных", "ФИТ", 5),
    ("CS302", "Операционные системы", "ФИТ", 5),
    ("CS401", "Компиляторы", "ФИТ", 4),
    ("CS402", "Распределённые системы", "ФИТ", 4),
    ("CS501", "Машинное обучение", "ФИТ", 6),
    ("CS502", "Computer Vision", "ФИТ", 4),
    ("MA101", "Математический анализ I", "ММФ", 7),
    ("MA102", "Математический анализ II", "ММФ", 7),
    ("MA201", "Линейная алгебра", "ММФ", 5),
    ("MA202", "Дискретная математика", "ММФ", 5),
    ("MA301", "Теория вероятностей", "ММФ", 5),
    ("MA302", "Математическая статистика", "ММФ", 4),
    ("MA401", "Численные методы", "ММФ", 4),
    ("PH101", "Общая физика: механика", "ФФ", 5),
    ("PH102", "Электродинамика", "ФФ", 5),
    ("PH201", "Квантовая механика", "ФФ", 6),
    ("EC101", "Микроэкономика", "ЭФ", 4),
    ("EC102", "Макроэкономика", "ЭФ", 4),
    ("EC201", "Эконометрика", "ЭФ", 5),
    ("HUM01", "Иностранный язык", "ГФ", 3),
    ("HUM02", "Философия", "ГФ", 3),
    ("HUM03", "История", "ГФ", 3),
    ("PE001", "Физическая культура", "ОФ", 2),
]


def _clear(db: Database) -> None:
    for name in ["students", "professors", "courses", "groups", "enrollments", "grades"]:
        db[name].delete_many({})


def _seed_groups(db: Database) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for faculty, spec in FACULTIES:
        for i in range(1, 5):
            year = random.randint(1, 4)
            name = f"{faculty[:2]}-{23 - year + 1}-{i}"
            docs.append({
                "_id": ObjectId(),
                "name": name,
                "faculty": faculty,
                "year": year,
                "specialization": spec,
            })
    db.groups.insert_many(docs)
    print(f"[seed] groups: {len(docs)}")
    return docs


def _seed_professors(db: Database) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    departments = list({c[2] for c in COURSE_CATALOG})
    for _ in range(30):
        first = fake.first_name()
        last = fake.last_name()
        middle = fake.middle_name()
        docs.append({
            "_id": ObjectId(),
            "full_name": f"{last} {first} {middle}",
            "email": fake.unique.email(),
            "department": random.choice(departments),
            "position": random.choice(POSITIONS),
            "hire_date": fake.date_time_between(start_date="-25y", end_date="-1y", tzinfo=timezone.utc),
            "degree": random.choice(["к.ф.-м.н.", "д.ф.-м.н.", "к.т.н.", "д.т.н.", ""]),
        })
    db.professors.insert_many(docs)
    print(f"[seed] professors: {len(docs)}")
    return docs


def _seed_courses(db: Database) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for code, title, dept, credits in COURSE_CATALOG:
        docs.append({
            "_id": ObjectId(),
            "code": code,
            "title": title,
            "department": dept,
            "credits": credits,
            "description": fake.sentence(nb_words=12),
            "semester_offered": random.sample([1, 2, 3, 4, 5, 6, 7, 8], k=random.randint(1, 3)),
        })
    db.courses.insert_many(docs)
    print(f"[seed] courses: {len(docs)}")
    return docs


def _seed_students(db: Database, groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    statuses = ["active"] * 18 + ["academic_leave", "expelled"]  # большинство активны
    for _ in range(200):
        first = fake.first_name()
        last = fake.last_name()
        middle = fake.middle_name()
        group = random.choice(groups)
        enrollment_year = 2026 - group["year"]
        docs.append({
            "_id": ObjectId(),
            "full_name": f"{last} {first} {middle}",
            "email": fake.unique.email(),
            "group_id": group["_id"],
            "enrollment_year": enrollment_year,
            "status": random.choice(statuses),
            "birth_date": fake.date_time_between(start_date="-25y", end_date="-17y", tzinfo=timezone.utc),
            "contacts": {
                "phone": fake.phone_number(),
                "address": fake.address(),
            },
        })
    db.students.insert_many(docs)
    print(f"[seed] students: {len(docs)}")
    return docs


def _seed_enrollments_and_grades(
    db: Database,
    students: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    professors: list[dict[str, Any]],
) -> None:
    enrollments: list[dict[str, Any]] = []
    grades: list[dict[str, Any]] = []
    periods = [(2024, 1), (2024, 2), (2025, 1), (2025, 2)]
    for student in students:
        if student["status"] == "expelled":
            continue
        # Каждый студент: ~5 курсов на каждый из периодов (но не всех)
        for year, semester in periods:
            chosen_courses = random.sample(courses, k=5)
            for course in chosen_courses:
                professor = random.choice(professors)
                enrollment_id = ObjectId()
                enrollments.append({
                    "_id": enrollment_id,
                    "student_id": student["_id"],
                    "course_id": course["_id"],
                    "professor_id": professor["_id"],
                    "semester": semester,
                    "year": year,
                })
                # Оценка с реалистичным распределением: больше 4 и 5, чем 2 и 3.
                value = random.choices([2, 3, 4, 5], weights=[5, 15, 40, 40])[0]
                grades.append({
                    "_id": ObjectId(),
                    "student_id": student["_id"],
                    "course_id": course["_id"],
                    "professor_id": professor["_id"],
                    "enrollment_id": enrollment_id,
                    "value": value,
                    "date": datetime(year, 6 if semester == 2 else 12, random.randint(10, 28), tzinfo=timezone.utc),
                    "type": random.choice(["exam", "credit", "midterm", "coursework"]),
                    "semester": semester,
                    "year": year,
                    "comment": "",
                })
    if enrollments:
        db.enrollments.insert_many(enrollments)
        print(f"[seed] enrollments: {len(enrollments)}")
    if grades:
        db.grades.insert_many(grades)
        print(f"[seed] grades: {len(grades)}")


def seed(db: Database, *, clear: bool = True) -> None:
    if clear:
        _clear(db)
        print("[seed] коллекции очищены")
    groups = _seed_groups(db)
    professors = _seed_professors(db)
    courses = _seed_courses(db)
    students = _seed_students(db, groups)
    _seed_enrollments_and_grades(db, students, courses, professors)
