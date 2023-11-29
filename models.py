from pydantic import BaseModel, model_validator


class LocationModel(BaseModel):
    accuracy_radius: int
    latitude: float
    longitude: float
    time_zone: str

    @model_validator(mode='before')
    def validate_time_zone(cls, values):
        time_zone = values.get('time_zone')
        if time_zone is None:
            raise KeyError
        return values

