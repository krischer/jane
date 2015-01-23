var lasifApp = angular.module("bayNetApp");


lasifApp.controller('stationInfoController', function($scope, $log, stations) {
    for (var i=0; i < stations.stations.features.length; i++) {
        var j = stations.stations.features[i];
        if (j.properties.network !== $scope.network ||
            j.properties.station != $scope.station) {
            continue;
        }
        $scope.station_object = j;
        $scope.network_name = j.properties.network_name;
        $scope.station_name = j.properties.station_name;
        $scope.channels = j.properties.channels;
        $log.info($scope.channels);
        break;
    }
});
