from APIs.baseApi import APIResolver
from APIs.apiHandler import ApiHandler
from APIs.baseApi import ApiLocation

class RlpApi(APIResolver):
    url = "https://covid-19-support.lsjv.rlp.de/hilfe/covid-19-test-dashboard/teststellen.geojson"

    def handle(self):
        content = self.send_request()["features"]
        result = []
        for feature in content:
            name = feature["properties"]["name"]
            location = ApiLocation(
                name,
                feature["geometry"]["coordinates"][0],
                feature["geometry"]["coordinates"][1]
            )
            location.address = feature["properties"]["complete_address"]
            location.set_services(not feature["properties"]["services"], feature["properties"]["services"] == "PCR Tests")
            result.append(location)
        return result


ApiHandler.get_instance().register_test(RlpApi())
