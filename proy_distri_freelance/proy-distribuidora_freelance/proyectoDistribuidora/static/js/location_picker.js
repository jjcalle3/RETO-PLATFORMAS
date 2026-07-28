(function () {
  var cfg = window.PICKER_CFG || {};
  var DEFAULT_LAT = -3.9931, DEFAULT_LNG = -79.2042; // Loja, Ecuador

  var initLat  = cfg.lat || DEFAULT_LAT;
  var initLng  = cfg.lng || DEFAULT_LNG;
  var initZoom = cfg.lat ? 16 : 13;

  var latInput = document.getElementById(cfg.latId || 'id_latitude');
  var lngInput = document.getElementById(cfg.lngId || 'id_longitude');

  var map    = L.map('location-picker-map').setView([initLat, initLng], initZoom);
  var marker = null;

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  function setMarker(latlng) {
    if (marker) {
      marker.setLatLng(latlng);
    } else {
      marker = L.marker(latlng, { draggable: true }).addTo(map);
      marker.on('dragend', function (e) { writeInputs(e.target.getLatLng()); });
    }
    writeInputs(latlng);
  }

  function writeInputs(latlng) {
    latInput.value = latlng.lat.toFixed(6);
    lngInput.value = latlng.lng.toFixed(6);
  }

  map.on('click', function (e) { setMarker(e.latlng); });

  L.Control.geocoder({ defaultMarkGeocode: false })
    .on('markgeocode', function (e) {
      var c = e.geocode.center;
      map.setView(c, 16);
      setMarker(c);
    })
    .addTo(map);

  if (cfg.lat && cfg.lng) {
    setMarker(L.latLng(cfg.lat, cfg.lng));
  }
}());
