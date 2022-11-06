from decorator import decorator
from calc_api.vizz import units


@decorator
def wrangle_endpoint_units(func, *args, **kwargs):
    """
    This is a wrapper function that converts the units of an API endpoint request to CLIMADA's (and my) preferred units,
    makes the request, and then converts the results back. It's only purpose is for cacheing: this way if the
    same request is made with different units, the cache values that are retrieved are the same.
    """
    # args[1] is the request schema from the user
    unit_parameters = units.get_request_unit_parameters(args[1])
    requested_units = units.get_request_unittype_to_unitname_mapping(args[1])
    parameter_to_unittype = units.get_request_parameter_to_unittype_mapping(args[1])

    for param in unit_parameters:
        unit_type = parameter_to_unittype[param]
        args[1].__setattr__(param, units.NATIVE_UNITS_CLIMADA[unit_type])

    # Run the calculation (or get cached result from database)
    result = func(*args, **kwargs)

    print("REQUESTED UNITS")
    print(str(requested_units))

    if result.response:
        result.response.convert_units(requested_units)

    return result

