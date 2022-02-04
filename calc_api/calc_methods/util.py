from climada.util.coordinates import country_to_iso


def country_iso_from_parameters(location_scale, location_code, location_poly, representation="alpha3"):
    """
    Decode location parameters to country codes to pass to the API

    Parameters
    ----------
    location_scale: str
        One of 'global', 'ISO3', 'country', 'admin0', 'admin1', 'admin2'
    location_code: str
        String representation of the location of interest
    location_poly: str
        Not yet implemented
    representation: str
        One of "alpha3", "alpha2", "numeric", "name"
    """
    # Identify ISO3 codes needed for query
    if location_poly:
        raise ValueError("API doesn't handle polygon queries yet")

    if location_scale:
        if location_scale == "global":
            raise ValueError("API doesn't handle global queries yet")  # TODO
        if location_code:
            if location_scale in ['ISO3', 'admin0', 'country']:
                country_iso3alpha = country_to_iso(location_code, representation)
            elif location_scale == "admin1":
                raise ValueError("API doesn't handle admin1 data yet")  # TODO
            elif location_scale == "admin2":
                raise ValueError("API doesn't handle admin2 data yet")  # TODO
            else:
                raise ValueError("location_scale parameter must be one of 'ISO3', 'admin0', 'admin1', 'admin2'")
    else:
        raise ValueError("API requires location_scale data (for now)")  # TODO

    if not isinstance(country_iso3alpha, list):
        country_iso3alpha = [country_iso3alpha]

    return country_iso3alpha


# Collection of convenience functions around latlon bounds
class Bbox(list):
    def __init__(self, *args):
        latlon = args[0]
        latlon = latlon_bounds(np.array(latlon[1], latlon[3]), np.array(latlon[0], latlon[2]))
        super(Bbox, self).__init__(latlon)

    def pad(self, padding=None):
        if padding is None:
            padding = config['default_padding']
        return Bbox([self[0] - padding, self[1] - padding, self[2] + padding, self[3] + padding])

    def poly_df(self, name=None):
        return pd.DataFrame({"lon": [self[0], self[0], self[2], self[2], self[0]],
                             "lat": [self[1], self[3], self[3], self[1], self[1]],
                             "name": name})

    def geom(self):
        df = self.poly_df()
        return Polygon(zip(df['lon'], df['lat']))

    def gdf(self, name, crs=None):
        if crs is None:
            crs = config['DEFAULT_CRS']
        return GeoDataFrame({"name": name}, index=[0], crs=crs, geometry=[self.geom()])

    def centroid(self):
        return 0.5*(self[2] + self[0]), 0.5*(self[3] + self[1])
