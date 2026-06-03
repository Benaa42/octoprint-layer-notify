from setuptools import setup

plugin_identifier = "layer_notify"
plugin_package = "octoprint_layer_notify"
plugin_name = "Layer Notify"
plugin_version = "0.1.0"
plugin_description = "Visual and sound alerts when specific layers are reached during printing, with optional GCODE commands per layer"
plugin_author = "Benaa42"
plugin_author_email = "renatobena42@gmail.com"
plugin_url = "https://github.com/Benaa42/octoprint-layer-notify"
plugin_license = "AGPLv3"

setup(
    name=plugin_name,
    version=plugin_version,
    packages=[plugin_package],
    package_data={plugin_package: ["templates/**", "static/**/*"]},
    entry_points={
        "octoprint.plugin": [f"{plugin_identifier} = {plugin_package}"]
    },
    install_requires=["OctoPrint"],
)
