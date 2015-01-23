"use strict";

/**
 * @doc function
 * @name angular-openlayers3-directive.main:__getMapDefaults
 *
 * @description Function returning the default configuration parameters.
 */
function __getMapDefaults() {
    return {
        center: {
            latitude: 0,
            longitude: 0,
            zoom: 1
        }
    };
}


// XXX: Find a proper way to deal with different projections!
// From WGS84 to Spherical Mercator.
function __toMapCoods(coods) {
    return ol.proj.transform(coods, "EPSG:4326", "EPSG:3857");
}


// XXX: Find a proper way to deal with different projections!
// From Spherical Mercator to WGS84.
function __fromMapCoods(coods) {
    return ol.proj.transform(coods, "EPSG:3857", "EPSG:4326");
}

