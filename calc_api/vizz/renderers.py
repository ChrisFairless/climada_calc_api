import logging
import json
import orjson
from typing import Any, Type, Mapping

from kombu.exceptions import EncodeError
from ninja import Schema
from ninja.renderers import JSONRenderer, NinjaJSONEncoder

from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# Update: look at these works and despair. I did, and that's why we're encoding with pickle for now. All this is unused.


# Don't know how to actually get this used within ninja
class SchemaJSONEncoder(NinjaJSONEncoder):
    def default(self, o: Any) -> Any:
        try:
            return super().default(o)
        except TypeError as err:
            print("TROUBLE")
            print('class')
            print(o.__class__)
            print(f'print: {o}')
            try:
                print(o.json())
                print('encoding to json was fine')
            except:
                print('cannot encode to json')
            print(err)


class SchemaJSONRenderer(JSONRenderer):
    media_type = "application/json"
    encoder_class: Type[json.JSONEncoder] = NinjaJSONEncoder
#    encoder_class: Type[json.JSONEncoder] = SchemaJSONEncoder
    json_dumps_params: Mapping[str, Any] = {}

    def render(self, request, data, *, response_status):
        #return json.dumps(data, cls=SchemaJSONEncoder)
        try:
            print("ZERO")
            return data.dict()
        except AttributeError:
            LOGGER.debug('Renderer: dict encoding failed. Falling back.')
        try:
            print("ONE")
            LOGGER.debug('Trying regular object method')
            print(f'class: {data.__class__}')
            print(data)
            return data.json(encoder=self.encoder_class)
        except AttributeError:
            LOGGER.debug('Renderer: schema encoding failed. Falling back.')
        try:
            print("TWO")
            return super().render(request, data, response_status=response_status)
        except TypeError:
            LOGGER.debug('Renderer: regular encoding failed. Falling back.')
        except EncodeError:
            LOGGER.debug('Renderer: regular encoding failed. Falling back.')
        except:
            print("TWOOOOOOOOOOOOOO")

        try:
            print("THREE")
            return json.dumps(data, encoder=SchemaJSONEncoder)
        except TypeError:
            LOGGER.debug('Renderer: json with new encoder failed. Falling back.')

        try:
            print("FOUR")
            return orjson.dumps(data)
        except TypeError as err:
            LOGGER.debug(f'Renderer: orjson failed. Giving up: {err}')