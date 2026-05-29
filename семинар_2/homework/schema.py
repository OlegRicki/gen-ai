"""
Pydantic-схема заявки на курс повышения квалификации (ДПО).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CITIES = {
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Самара",
    "Краснодар",
    "Ростов-на-Дону",
    "Воронеж",
}


class Address(BaseModel):
    city: str
    district: str = Field(min_length=2, max_length=40)

    @field_validator("city")
    @classmethod
    def city_must_be_in_list(cls, v: str) -> str:
        if v not in CITIES:
            raise ValueError(f"Город «{v}» не из утверждённого списка")
        return v


class Application(BaseModel):
    full_name: str = Field(min_length=5, max_length=80)
    age: int = Field(ge=22, le=65)
    address: Address
    speciality: Literal[
        "учитель",
        "врач",
        "инженер",
        "бухгалтер",
        "юрист",
        "менеджер",
        "IT-специалист",
        "психолог",
        "социальный работник",
    ]
    desired_course: Literal[
        "цифровая грамотность",
        "управление проектами",
        "педагогика и методика",
        "медицинская реабилитация",
        "налогообложение и бухучёт",
        "кибербезопасность",
        "психологическое консультирование",
    ]
    years_of_experience: int = Field(ge=0, le=40)
    graduation_year: int = Field(ge=1980, le=2024)

    @model_validator(mode="after")
    def age_and_graduation_consistent(self) -> "Application":
        current_year = date.today().year
        if self.graduation_year > current_year:
            raise ValueError("Год окончания не может быть позже текущего года")
        # Человек не мог закончить вуз раньше, чем ему исполнилось ~18 лет.
        earliest_graduation = current_year - self.age + 18
        if self.graduation_year < earliest_graduation - 4:
            raise ValueError(
                f"Возраст {self.age} и год окончания {self.graduation_year} "
                "противоречат друг другу"
            )
        return self
