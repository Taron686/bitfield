import sys
import json

from bit_field import render, jsonml_stringify

with open("example.json") as json_file:
    json_data = json.load(json_file)
    json_file.close()

jsonml = render(json_data['payload'],**json_data['config'])
svg = jsonml_stringify(jsonml)

with open("example.svg","w") as f:
    f.write(svg)
