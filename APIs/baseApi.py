from abc import ABC, abstractmethod
import requests


class ApiLocation:
    title = ""
    address = None
    latitude = None
    longitude = None
    services = None

    def __init__(self, title: str, longitude: float, latitude: float):
        self.title = title
        self.longitude = longitude
        self.latitude = latitude

    def __str__(self):
        result = self.title
        if self.longitude and self.latitude:
            result += " | (" + str(self.longitude) + "," + str(self.latitude) + ")"
        if self.address:
            result += " | " + self.address
        if self.services:
            result += " | " + self.services
        return result

    def set_address(self, street: str, plz: str, city: str):
        self.address = street + " " + plz + " " + city

    def set_services(self, quick: bool, pcr: bool):
        if quick:
            services = "Schnelltest"
        if pcr:
            if quick:
                services = "Schnelltest und PCR Test"
            else:
                services = "PCR Test"


class APIResolver(ABC):
    url = None

    @abstractmethod
    def handle(self):
        pass

    def send_request(self):
        try:
            response = requests.get(
                url=self.url,
            )
            return response.json()
        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return dict()