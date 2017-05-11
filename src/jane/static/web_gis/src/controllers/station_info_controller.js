var baynetApp = angular.module("bayNetApp");


baynetApp.controller('stationInfoController', function ($scope, $log, stations) {
    for (var i = 0; i < stations.stations.features.length; i++) {
        var j = stations.stations.features[i];
        if (j.properties.network !== $scope.network ||
            j.properties.station != $scope.station) {
            continue;
        }
        $scope.station_object = j;
        $scope.network_name = j.properties.network_name;
        $scope.station_name = j.properties.station_name;
        $scope.channels = j.properties.channels;
        for (var i = 0; i < $scope.channels.length; i++) {
            var i = $scope.channels[i];
            // A bit ugly but I'm currently not sure how to do it in a
            // better way. Should work well enough I guess.
            jQuery.ajax({
                url: i["attachments_url"],
                success: function (result) {
                    i["attachments"] = result.results;
                },
                async: false
            });
            console.log(i);
        }
        break;
    }
});