# -*- coding: utf-8 -*-
import requests, pprint

data = {
    'product_id' : 'aXApO1p8yUtjgJ2TXF8iGQ==',
    'license_key' : '1F9CFF2A-835E4D6F-B20CB15B-6C9CF6CF',
    'increment_uses_count' : 'false'
}
response = requests.post("https://api.gumroad.com/v2/licenses/verify", json=data)

pprint.pprint(response.json())
