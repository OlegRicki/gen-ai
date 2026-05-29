"""
Генератор синтетических заявок на курсы ДПО.
Возвращает 50 валидных заявок, сохраняет CSV и гистограммы.
"""

import json
import time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from llm_client import get_model, make_client
from schema import Application, CITIES

client = make_client()
MODEL = get_model()
N_APPLICATIONS = 50

SYSTEM_PROMPT = """Ты генерируешь синтетические заявки на курсы повышения
квалификации (ДПО) в России. Данные должны быть правдоподобными и согласованными:
возраст, стаж работы, год окончания вуза и специальность не должны
противоречить друг другу.

Поле address — объект с city и district (район/округ города).
Специальность и желаемый курс выбирай только из допустимых значений схемы.
ФИО — реалистичное русское, три слова."""


def build_user_prompt(seed_city: str, seed_speciality: str | None = None) -> str:
    parts = [
        "Создай одну заявку на курс ДПО.",
        f"Обязательно укажи address.city = «{seed_city}».",
        "Район (address.district) придумай реалистичный для этого города.",
    ]
    if seed_speciality:
        parts.append(f"Текущая специальность заявителя: «{seed_speciality}».")
    parts.append(
        "Желаемый курс должен логично соответствовать специальности "
        "и карьерным целям заявителя."
    )
    return " ".join(parts)


def stratified_seeds(n: int) -> list[tuple[str, str | None]]:
    """По 5 заявок на каждый из 10 городов; специальности — round-robin."""
    cities = sorted(CITIES)
    specialities = list(Application.model_fields["speciality"].annotation.__args__)
    seeds: list[tuple[str, str | None]] = []
    for i in range(n):
        city = cities[i % len(cities)]
        speciality = specialities[i % len(specialities)]
        seeds.append((city, speciality))
    return seeds


def generate_one(seed_city: str, seed_speciality: str | None = None) -> Application:
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(seed_city, seed_speciality)},
        ],
        response_model=Application,
        max_retries=3,
        temperature=0.9,
    )


def save_histogram(series: pd.Series, title: str, out: str, color: str) -> Counter:
    counts = series.value_counts()
    plt.figure(figsize=(9, 4))
    counts.plot.bar(color=color, edgecolor="white")
    plt.title(title)
    plt.ylabel("Число заявок")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()
    return Counter(counts.to_dict())


def main():
    applications: list[Application] = []
    validator_retries = 0
    seeds = stratified_seeds(N_APPLICATIONS)

    for i, (seed_city, seed_speciality) in enumerate(seeds, 1):
        print(f"[{i}/{N_APPLICATIONS}] city={seed_city}, speciality={seed_speciality}")
        try:
            app = generate_one(seed_city, seed_speciality)
            applications.append(app)
            print(f"  → {app.full_name}, {app.age} лет, {app.desired_course}")
        except Exception as e:
            print(f"  ✗ упало: {type(e).__name__}: {e}")
            validator_retries += 1
        time.sleep(0.3)

    rows = [
        {
            "full_name": a.full_name,
            "age": a.age,
            "city": a.address.city,
            "district": a.address.district,
            "speciality": a.speciality,
            "desired_course": a.desired_course,
            "years_of_experience": a.years_of_experience,
            "graduation_year": a.graduation_year,
        }
        for a in applications
    ]

    df = pd.DataFrame(rows)
    df.to_csv("applications.csv", index=False, encoding="utf-8")

    with open("applications.json", "w", encoding="utf-8") as f:
        json.dump([a.model_dump() for a in applications], f, ensure_ascii=False, indent=2)

    city_counts = save_histogram(
        df["city"], f"Распределение по городам ({len(df)} заявок)", "cities.png", "#7AB66E"
    )
    spec_counts = save_histogram(
        df["speciality"],
        f"Распределение по специальностям ({len(df)} заявок)",
        "specialities.png",
        "#4A90D9",
    )

    stats = {
        "total": len(df),
        "city_counts": dict(city_counts),
        "speciality_counts": dict(spec_counts),
        "failed_requests": validator_retries,
    }
    Path("generation_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nСгенерировано: {len(applications)}/{N_APPLICATIONS}")
    print("Сохранено: applications.csv, cities.png, specialities.png")


if __name__ == "__main__":
    main()
