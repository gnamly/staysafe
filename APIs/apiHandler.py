from geopy.distance import geodesic


class ApiHandler:
    instance = None

    @classmethod
    def get_instance(cls):
        if cls.instance:
            return cls.instance
        cls.instance = cls()
        return cls.instance

    resolvers_test = []

    def register_test(self, resolver):
        self.resolvers_test.append(resolver)

    def get_nearest_test(self, lat, long):
        locations = []
        for resolver in self.resolvers_test:
            locations.extend(resolver.handle())

        if len(locations) == 0:
            return None

        nearest = locations[0]
        for location in locations:
            current_dist = geodesic((nearest.latitude, nearest.longitude), (lat, long))
            dist = geodesic((location.latitude, location.longitude), (lat, long))
            if dist < current_dist:
                nearest = location
        return nearest