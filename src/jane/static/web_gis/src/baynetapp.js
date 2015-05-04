var module = angular.module("bayNetApp", ["mgcrea.ngStrap",
    "mgcrea.ngStrap.tooltip",
    "ngAnimate",
    "ngSanitize",
    "ui.bootstrap-slider",
    "toggle-switch"]);

// Jane server constant.
module.constant('jane_server', '../..');

// Bing API Key
module.constant(
    'bing_key',
    'Ak-dzM4wZjSqTlzveKz5u0d4IQ4bRzVI309GxmkgSVr1ewS6iPSrOvOKhA-CJlm3');

// Colors for the different event agencies. From the color brewer website.
module.constant('event_agency_colors', [
    'rgba(0, 0, 255, 0.7)',
    'rgba(152, 78, 163, 0.7)',
    'rgba(228, 26, 28, 0.7)',
    'rgba(255, 127, 0, 0.7)',
    'rgba(55, 126, 184, 0.7)',
    'rgba(255, 255, 51, 0.7)']);


module.constant('station_colors', [
    '#ff7f00',
    '#1f78b4',
    '#a6cee3',
    '#33a02c',
    '#b2df8a',
    '#e31a1c',
    '#fb9a99',
    '#fdbf6f']);


// Factory dealing with events.
module.factory('events', function($http, $log, jane_server) {
    return {
        events: {
            "type": "FeatureCollection",
            "features": []
        },
        update: function() {
            var self = this;
            var url = jane_server + "/rest/quakeml/";
            $http.get(url).success(function(data) {
                // Filter events to only keep those with a valid origin and
                // magnitude.
                var data = _(data)
                    .filter(function(i) {
                        if (!i.indexed_data.latitude && !i.indexed_data.longitude) {
                            return false;
                        }
                        if (i.indexed_data.magnitude === null) {
                            return false;
                        }
                        return true;
                    })
                    .map(function(i) {
                        var j = i.indexed_data;
                        j.id = i.id;
                        j.origin_time = new Date(j.origin_time);
                        // Now create GeoJSON
                        return {
                            "type": "Feature",
                            "properties": j,
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    j.longitude, j.latitude
                                ]
                            }
                        };
                    }).value();
                // Update the event set.
                self.events.features.length = 0;
                _.forEach(data, function(i) {
                    self.events.features.push(i);
                });
            })
        }
    }
});

// Factory dealing with stations.
module.factory('stations', function($http, $log, jane_server) {
    return {
        stations: {
            "type": "FeatureCollection",
            "features": []
        },
        update: function() {
            var self = this;
            var url = jane_server + "/rest/stationxml/";
            $http.get(url).success(function(data) {
                var stations = {};
                _.forEach(data, function(item) {
                    var j = item.indexed_data;
                    var station_id = [j.network, j.station];
                    var n_sd = new Date(j.start_date);
                    if (!j.end_date || (j.end_date == "None")) {
                        n_ed = null;
                    }
                    else {
                        n_ed = new Date(j.end_date);
                    }
                    if (!_.has(stations, station_id)) {
                        stations[station_id] = {
                            "type": "Feature",
                            "properties": {
                                "network": j.network,
                                "network_name": j.network_name,
                                "station": j.station,
                                "station_name": j.station_name,
                                "latitude": j.latitude,
                                "longitude": j.longitude,
                                "channels": [],
                                "min_startdate": n_sd,
                                "max_enddate": n_ed
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    j.longitude, j.latitude
                                ]
                            }
                        };
                    }
                    else {
                        // Make sure the minimum and maximum start and end
                        // dates of the station are consistent with the data.
                        var o_sd = stations[station_id].min_startdate;
                        var o_ed = stations[station_id].max_startdate;
                        if (n_sd) {
                            if (!o_sd || (n_sd < o_sd)) {
                                stations[station_id].min_startdate = n_sd;
                            }
                        }
                        if (n_ed) {
                            if (!o_ed || (n_ed > o_ed)) {
                                stations[station_id].min_startdate = n_ed;
                            }
                        }

                    }
                    stations[station_id].properties.channels.push(item);
                });
                // Update the stations set.
                self.stations.features.length = 0;
                _.forEach(stations, function(i) {
                    self.stations.features.push(i);
                });
            })
        }
    }
});


module.controller("BayNetController", function($scope, $log, stations, station_colors,
                                               events, event_agency_colors) {
    $scope.center = {
        latitude: 48.505,
        longitude: 12.09,
        zoom: 5
    };

    $scope.rotation = 0;
    $scope.base_layer_opacity = 100.0;

    $scope.show_bavaria_outline = false;

    // XXX: This has to be in sync with the base layer that has the default
    // visibility.
    $scope.current_base_layer = "Stamen Toner-Lite";
    // The map directive will fill this with a list of available base layers.
    $scope.base_layer_names_dropdown = [];

    $scope.popover = {
        "content": "Hello Popover<br />This is a multiline message!",
        "saved": false
    };

    events.update();
    $scope.geojson_events = events.events;

    stations.update();
    $scope.geojson_stations = stations.stations;

    // Flags.
    $scope.show_event_layer = true;
    $scope.show_station_layer = true;
    $scope.event_layer_show_points = true;

    $scope.event_settings = {
        "min_date": new Date("2014-06-01"),
        "max_date": new Date("2014-10-26"),
        "magnitude_range": [-5, 10],
        "selected_agencies": [],
        "agency_colors": {},
        "agency_icons": [],
        "available_authors": [],
        "selected_authors": [],
        "show_public_and_private": true,
        "show_automatic_and_manual": true
    };

    $scope.station_settings = {
        "min_date": new Date("1990-01-01"),
        "max_date": new Date()
    };

    $scope.station_colors = {};

    $scope.$watchCollection("geojson_events.features", function(f) {
        // Get all unique agencies.
        var agencies = _.uniq(_.map(f, function(i) {
            return i.properties.agency;
        }));

        // Distribute colors to the agencies..
        $scope.event_settings.agency_colors = {};
        for (var i = 0; i < agencies.length; i++) {
            $scope.event_settings.agency_colors[agencies[i]] =
                event_agency_colors[i % event_agency_colors.length];
        }

        // Set the available choices.
        $scope.event_settings.agency_icons = _.map(agencies, function(i) {
            return {
                value: i,
                label: '<i class="fa fa-circle" style="color:' +
                    $scope.event_settings.agency_colors[i] +
                    '"></i> ' + i}
        });

        $scope.event_settings.selected_agencies = [agencies[0]];

        // Get all authors.
        $scope.event_settings.selected_authors = _.uniq(_.map(f, function(i) {
            return i.properties.author;
        }));

        $scope.event_settings.available_authors = _.map($scope.event_settings.selected_authors, function(i){
            return {
                value: i,
                label: '<i class="fa fa-user"></i> ' + i
            }
        });

        $scope.event_settings.selected_authors.push("UNKNOWN");
        $scope.event_settings.available_authors.push({
            value: "UNKNOWN",
            label: "<i>No given author</i>"
        });

        $scope.update_event_source(
            $scope.geojson_events,
            $scope.show_event_layer,
            $scope.event_layer_show_points,
            $scope.event_settings);
    });


    $scope.$watchCollection("geojson_stations.features", function(f) {
        var networks = _(f).map(function(i) {return i.properties.network})
                           .uniq().value();
        networks.sort();
        $scope.station_colors = {};
        _.forEach(networks, function(i, d) {
            $scope.station_colors[i] = station_colors[d % station_colors.length];
        });

        $scope.update_station_source(
            $scope.geojson_stations,
            $scope.show_station_layer,
            $scope.station_colors,
            $scope.station_settings);
    });

    $scope.$watch("show_station_layer", function(new_value, old_value) {
        if (new_value == old_value) {
            return;
        }
        $scope.update_station_source(
            $scope.geojson_stations,
            $scope.show_station_layer,
            $scope.station_colors,
            $scope.station_settings);
    });


    $scope.$watch("event_layer_show_points", function(new_value, old_value) {
        if (new_value == old_value) {
            return;
        }
        $scope.update_event_source(
            $scope.geojson_events,
            $scope.show_event_layer,
            $scope.event_layer_show_points,
            $scope.event_settings);
    });

    $scope.$watch("show_event_layer", function(new_value, old_value) {
        if (new_value == old_value) {
            return;
        }
        $scope.update_event_source(
            $scope.geojson_events,
            $scope.show_event_layer,
            $scope.event_layer_show_points,
            $scope.event_settings);
    });

    $scope.$watchCollection(
        "event_settings", function() {
            $scope.update_event_source(
                $scope.geojson_events,
                $scope.show_event_layer,
                $scope.event_layer_show_points,
                $scope.event_settings);
        }
    );

    $scope.$watchCollection(
        "station_settings", function() {
            $scope.update_station_source(
                $scope.geojson_stations,
                $scope.show_station_layer,
                $scope.station_colors,
                $scope.station_settings);
        }
    );

});
