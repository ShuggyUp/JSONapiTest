import time
from threading import Thread
import uvicorn
from fastapi import FastAPI
import requests
from pydantic import BaseModel


class Cache:

    def __init__(self, cache_life):
        self.cache_life = cache_life
        self.items = {}
        self.items_life = {}

    def save_information(self, city, params, output_string):
        params.sort()
        key = city + "".join(params)

        self.items[key] = output_string
        self.items_life[key] = self.cache_life

    def search_item(self, city, params):
        params.sort()
        key = city + "".join(params)

        result = self.items[key] if key in self.items.keys() else None
        return result

    def decrease_lifetime(self):
        if self.items_life:
            for key in self.items_life.keys():
                self.items_life[key] -= 1
                if self.items_life[key] == 0:
                    self.delete_item(key)

    def delete_item(self, key):
        self.items.pop(key)
        self.items_life.pop(key)


def search_parameters(parameters, json_file, params_dict):
    for key, value in json_file.items():
        if type(value) is dict:
            params_dict |= search_parameters(parameters, value, params_dict)

        if key in parameters:
            params_dict[key] = value

    return params_dict


def processing_data_for_output(data):
    output_string = ""

    for name, value in data.items():
        if name == "temp":
            output_string += f"Temperature is {round(value, 1)} degrees Celsius. "
        if name == "feels_like":
            output_string += f"Temperature feels like is {round(value, 1)} degrees Celsius. "
        if name == "temp_min":
            output_string += f"Minimum temperature is {round(value, 1)} degrees Celsius. "
        if name == "temp_max":
            output_string += f"Maximum temperature is {round(value, 1)} degrees Celsius. "
        if name == "pressure":
            output_string += f"Pressure is {value} Pa. "
        if name == "humidity":
            output_string += f"Humidity is {value}%. "
        if name == "visibility":
            output_string += f"Visibility is {value} m. "
        if name == "wind":
            output_string += f"Wind speed is {value['speed']} m/s, direction {value['deg']} degrees. "

    return output_string


def clearing_cache():
    while True:
        time.sleep(60.0)
        cache.decrease_lifetime()


class ResponseForm(BaseModel):
    city: str = None
    cities: str = None
    parameters: str = None


app = FastAPI()

APIkey = "4cc428405eb5f164ee303a44d930ee92"
cache_life = 10
cache = Cache(cache_life)
params_dict = {}

th = Thread(target=clearing_cache, daemon=True)
th.start()


@app.post("/")
def root(response: ResponseForm):
    if (response.city is None and response.cities is None) or (response.city is not None and response.cities is not None):
        return "Fill in the data for only one of the 'city' or 'cities' cells."

    if response.city is not None and len(response.city.split()) == 1:
        cities = [response.city]
    elif response.cities is not None and len(response.cities.split()) != 1:
        cities = response.cities.split()
    else:
        return "Invalid value of 'city' or 'cities' variable."

    if response.parameters is not None:
        parameters = response.parameters.split()
    else:
        return "'Parameter' cell is missing in the request."

    output_data = ''
    for city in cities:
        result = cache.search_item(city, parameters)
        if result is None:
            resp = requests.get(
                f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={APIkey}&units=metric')

            if resp.status_code == 200:
                data_dict = search_parameters(parameters, resp.json(), params_dict)
                output_data += f"Weather forecast in {city}: " + processing_data_for_output(data_dict)
                cache.save_information(city, parameters, output_data)
            else:
                output_data = "Site is unavailable and no query matches were found in the cache."
        else:
            output_data = result

    return output_data


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
