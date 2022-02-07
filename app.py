from flask import Flask, redirect
import requests
from flask_ask_sdk.skill_adapter import SkillAdapter

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.utils import is_intent_name
from ask_sdk_core.utils import is_request_type
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.api_client import DefaultApiClient

from ask_sdk_model import Response
from ask_sdk_model.ui import AskForPermissionsConsentCard
from ask_sdk_model.ui import StandardCard
from ask_sdk_model.ui import Image
from ask_sdk_model import Context

from APIs.apiHandler import ApiHandler
from APIs.baseApi import ApiLocation
from geopy.geocoders import Nominatim

api_handler = ApiHandler.get_instance()
geolocator = Nominatim(user_agent="stay safe alexa skill")

app = Flask(__name__)

WELCOME_MESSAGE = "Hallo zum Stay Safe skill"
REPROMT_WELCOME = "Was kann ich für dich tun?"


# Handler for skill launch with no intent
class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        response_builder = handler_input.response_builder

        return(
            handler_input.response_builder
            .speak(WELCOME_MESSAGE)
            .ask(REPROMT_WELCOME)
            .response
        )


# Custom Handler for Inzidenz Value
class InzidenzIntentHandler(AbstractRequestHandler):
    """Handler for Hgetting the Inzidenz value in general."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("InzidenzIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        if handler_input.request_envelope.context.system.device.supported_interfaces.geolocation:
            if not handler_input.request_envelope.context.geolocation:
                return(
                    handler_input.response_builder
                        .speak('Stay Safe benötigt zugriff auf Ihren standort. Bitte bestätigen Sie die Brechtigung zum Standort Teilen in ihrer Alexa App Einstellung.')
                        .set_card(AskForPermissionsConsentCard(['alexa::devices:all:geolocation:read']))
                        .response
                )
            else:
                geo_location = handler_input.request_envelope.context.geolocation
                lat = geo_location.coordinate.latitude_in_degrees
                long = geo_location.coordinate.longitude_in_degrees
                location = get_geo_from_coords((lat, long), True)
                return inzidenz_response(handler_input, location)

        location = get_alexa_location(handler_input.request_envelope.context)
        if not location:
            return(
                handler_input.response_builder
                .speak('Stay Safe benötigt zugriff auf Ihren standort. Bitte bestätigen Sie die Brechtigung zum Standort Teilen in ihrer Alexa App Einstellung.')
                .set_card(AskForPermissionsConsentCard(['read::alexa:device:all:address']))
                .response
            )
        geo_location = None
        addrLine = location["addressLine1"]
        if not addrLine:
            addrLine = location["addressLine2"]
        if addrLine:
            geo_location = get_geo_from_address(location["addressLine1"] + " " + location["postalCode"] + " " + location["city"], True)

        if not geo_location:
            return(
                handler_input.response_builder
                .speak("Ich konnte deinen Standort nicht bestimmen. Bitte stelle sicher, dass du deine Addresse in der Alexa App angegeben hast!")
                .response
            )
        print(geo_location.raw)
        return inzidenz_response(handler_input, geo_location)


# Custom Handler to searching for a Teststation
class TestIntentHandler(AbstractRequestHandler):
    """Handler for getting the nearest Test Station"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("TestIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        if handler_input.request_envelope.context.system.device.supported_interfaces.geolocation:
            if not handler_input.request_envelope.context.geolocation:
                return(
                    handler_input.response_builder
                    .speak('Stay Safe benötigt zugriff auf Ihren standort. Bitte bestätigen Sie die Brechtigung zum Standort Teilen in ihrer Alexa App Einstellung.')
                    .set_card(AskForPermissionsConsentCard(['alexa::devices:all:geolocation:read']))
                    .response
                )
            else:
                #get the nearest test station based on geolocation
                geo_location = handler_input.request_envelope.context.geolocation
                lat = geo_location.coordinate.latitude_in_degrees
                long = geo_location.coordinate.longitude_in_degrees
                teststation = api_handler.get_nearest_test(lat, long)
                if not teststation:
                    return(
                        handler_input.response_builder
                        .speak("Ich konnte leider keine Teststation in deiner Nähe finden")
                        .response
                    )

                return teststation_response(handler_input, teststation)

        location = get_alexa_location(handler_input.request_envelope.context)
        if not location:
            return(
                handler_input.response_builder
                .speak('Stay Safe benötigt zugriff auf Ihren standort. Bitte bestätigen Sie die Brechtigung zum Standort Teilen in ihrer Alexa App Einstellung.')
                .set_card(AskForPermissionsConsentCard(['read::alexa:device:all:address']))
                .response
            )

        # get coordinates from location
        geo_location = None
        addrLine = location["addressLine1"]
        if not addrLine:
            addrLine = location["addressLine2"]
        if addrLine:
            geo_location = get_geo_from_address(location["addressLine1"] + " " + location["postalCode"] + " " + location["city"])

        if not geo_location:
            return(
                handler_input.response_builder
                .speak("Ich konnte deinen Standort nicht bestimmen. Bitte stelle sicher, dass du deine Addresse in der Alexa App angegeben hast!")
                .response
            )

        # use the geo_location to get nearest test station
        teststation = api_handler.get_nearest_test(geo_location.latitude, geo_location.longitude)

        if not teststation:
            return(
                handler_input.response_builder
                .speak("Ich konnte leider keine Teststation in deiner Nähe finden")
                .response
            )

        return teststation_response(handler_input, teststation)


class NoIntentHandler(AbstractRequestHandler):
    """Handler for no Intent"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.NoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        return(
            handler_input.response_builder
            .speak('Das kann ich Ihnen nicht beantworten.')
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Frag mich wo Du eine Teststation finden kannst oder wie hoch die inzidenz ist."
        return(
            handler_input.response_builder
            # .speak(speak_output)
            .ask(speak_output)
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech = (
            "Tut mir leid, damit kann ich dir nicht helfen"
            "Finde eine Teststation, indem du Stay Safe fragst: Finde eine Teststation."
        )
        reprompt = "Das konnte ich nicht finden. Womit kann ich dir helfen?"

        return handler_input.response_builder.speak(speech).ask(
            reprompt).response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors."""

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        print(exception)
        speak_output = "Tut mir leid ich konnte deine Anfrage nicht verarbeiten."

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(REPROMT_WELCOME)
            .response
        )


sb = CustomSkillBuilder(api_client=DefaultApiClient())

# Request Handlers
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(InzidenzIntentHandler())
sb.add_request_handler(TestIntentHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())

# Exception Handlers
sb.add_exception_handler(CatchAllExceptionHandler())

skill_adapter = SkillAdapter(skill=sb.create(), skill_id=1, app=app)


@app.route('/', methods=['GET', 'POST'])
def invoke_skill():
    return skill_adapter.dispatch_request()


@app.route('/test')
def hello_world():  # put application's code here
    return "hallo world"

@app.route('/address')
def test_address():
    return get_geo_from_address("Erenburgerstraße 19 Worms").raw

@app.route('/map')
def test_map():
    return redirect(get_static_map_url("8.344000", "49.632630"), code=302)

@app.route('/inzidenz')
def test_inzidenz():
    data = get_rki_data(get_rki_admunit("LK Mannheim", "Baden-Württemberg"))
    return data if data else "Not Found"


@app.route('/inzidenz/geo')
def test_inzidenz_geo():
    # geo = get_geo_from_address("Uhlbacherstraße 1 Obertürkheim", True)
    geo = get_geo_from_address("Mutzenreisstraße 1 Esslingen", True)
    county = geo.raw["address"]["county"]
    state = geo.raw["address"]["state"]
    if "Landkreis" in county:
        county = county.replace("Landkreis", "LK")
    else:
        county = "LK "+county
    return get_rki_data(get_rki_admunit(county, state))


##### utility functions #####
def get_alexa_location(context: Context):
    URL = context.system.api_endpoint+"/v1/devices/{}/settings/address".format(context.system.device.device_id)
    TOKEN = context.system.api_access_token
    HEADER = {'Accept': 'application/json',
              'Authorization': 'Bearer {}'.format(TOKEN)}
    r = requests.get(URL, headers=HEADER)
    if r.status_code == 200:
        return r.json()


def get_geo_from_address(address, details=False):
    location = geolocator.geocode(address, addressdetails=details)
    return location


def get_geo_from_coords(coords, details=False):
    location = geolocator.reverse(coords, addressdetails=details)
    return location


def get_static_map_url(long, lat, width, zoom):
    base_url = "https://api.mapbox.com/styles/v1/gnamly/ckz2jgkt4001e16r7cpd89kmi/static/"+long+","+lat+","+zoom+"/"+width
    TOKEN = "pk.eyJ1IjoiZ25hbWx5IiwiYSI6ImNrejJqOW9pYTFvMzMybm12dHVraGZ0ajAifQ.71-_TRyKU5RZj6huHgOQ6g"
    url = base_url+"?access_token="+TOKEN
    return url


def teststation_response(handler_input, teststation: ApiLocation):
    return(
        handler_input.response_builder
        .speak("Die Teststation "+teststation.title+" findest du bei "+teststation.address.replace("<br>", " "))
        .set_card(StandardCard(
            title=teststation.title,
            text=teststation.address.replace("<br>", "\n"),
            image=Image(
                small_image_url=get_static_map_url(str(teststation.longitude), str(teststation.latitude), "200x200", "15"),
                large_image_url=get_static_map_url(str(teststation.longitude), str(teststation.latitude), "400x350", "17")
            )
        ))
        .response
    )


def get_rki_admunit(county: str, state: str):
    url = "https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/rest/services/rki_admunit_v/FeatureServer/0/query"
    parameter = {
        'user-agent': 'python-requests',
        'where': '1=1',
        'outFields': '*',
        'returnGeometry': False,
        'f': 'json',
        'cacheHint': False
    }
    response = requests.get(url=url, params=parameter)
    json = response.json()
    for unit in json["features"]:
        if unit["attributes"]["Name"] == county:
            return unit["attributes"]["AdmUnitId"]
        elif unit["attributes"]["Name"] == county.replace("LK", "SK"):
            return unit["attributes"]["AdmUnitId"]
    for unit in json["features"]:
        if unit["attributes"]["Name"] == state:
            return unit["attributes"]["AdmUnitId"]
    print("No AdmId found "+county)
    return None


def get_rki_data(adm_id):
    where = 'AdmUnitId = 0'
    if adm_id:
        where = f'AdmUnitId = 0 OR AdmUnitId = {adm_id}'
    url = "https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/rest/services/rki_key_data_v/FeatureServer/0/query?"
    parameter = {
        'user-agent': 'python-requests',
        'where': where,
        'outFields': '*',
        'returnGeometry': False,
        'f': 'json',
        'cacheHint': False
    }
    result = requests.get(url=url, params=parameter)
    return result.json()


def inzidenz_response(handler_input, location):
    county = location.raw["address"]["county"]
    state = location.raw["address"]["state"]
    if "Landkreis" in county:
        county = county.replace("Landkreis", "LK")
    else:
        county = "LK "+county
    data = get_rki_data(get_rki_admunit(county, state))
    if not data:
        return(
            handler_input.response_builder
                .speak("Leider ist bei der Anfrage etwas schief gelaufen")
                .response
        )

    dt = data["features"][1] if len(data["features"]) > 1 else data["features"][0]
    local = data["features"][0] if len(data["features"]) > 1 else None
    print(dt)
    print(local)
    output_dt = "Die sieben Tage Inzidenz liegt in Deutschland bei "+str(dt["attributes"]["Inz7T"])
    output_local = "Und für "+county.replace("LK ", "")+"liegt Sie bei "+str(local["attributes"]["Inz7T"]) if local else ""
    text = "Deutschland: "+str(dt["attributes"]["Inz7T"])
    if local:
        text += "\n"+county.replace("LK ", "")+": "+str(local["attributes"]["Inz7T"])
    return(
        handler_input.response_builder
            .speak(output_dt + "\n" + output_local)
            .set_card(StandardCard(
            title="Inzidenz",
            text=text
        ))
            .response
    )


if __name__ == '__main__':
    app.run()
