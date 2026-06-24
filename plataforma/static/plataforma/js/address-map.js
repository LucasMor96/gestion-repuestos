(function () {
    const DEFAULT_CENTER = [-34.6037, -58.3816];
    const DEFAULT_ZOOM = 12;
    const RESULT_ZOOM = 17;
    const STATIC_ZOOM = 18;

    function debounce(fn, delay) {
        let timer = null;
        return function (...args) {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function setStatus(statusEl, message, tone) {
        if (!statusEl) return;
        statusEl.textContent = message;
        statusEl.className = `small mt-2 ${tone || 'text-muted'}`;
    }

    function setCoordinates(latInput, lngInput, lat, lng) {
        if (!latInput || !lngInput) return;
        latInput.value = Number(lat).toFixed(7);
        lngInput.value = Number(lng).toFixed(7);
    }

    function addTiles(map) {
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map);
    }

    function locationDotIcon() {
        return L.divIcon({
            className: '',
            html: '<span class="location-dot" aria-hidden="true"></span>',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        });
    }

    function getPointFromInputs(latInput, lngInput) {
        const lat = parseFloat(String((latInput && latInput.value) || '').replace(',', '.'));
        const lng = parseFloat(String((lngInput && lngInput.value) || '').replace(',', '.'));
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
        return { lat, lng };
    }

    function initAddressMap(container) {
        const addressInput = document.querySelector(container.dataset.addressInput);
        const latInput = document.querySelector(container.dataset.latInput);
        const lngInput = document.querySelector(container.dataset.lngInput);
        const button = document.querySelector(container.dataset.searchButton);
        const statusEl = document.querySelector(container.dataset.status);

        if (!addressInput || !latInput || !lngInput || !window.L) return;

        const initialPoint = getPointFromInputs(latInput, lngInput);
        const map = L.map(container).setView(
            initialPoint ? [initialPoint.lat, initialPoint.lng] : DEFAULT_CENTER,
            initialPoint ? RESULT_ZOOM : DEFAULT_ZOOM
        );
        addTiles(map);

        let marker = null;
        function moveMarker(lat, lng, status) {
            const coords = [lat, lng];
            if (!marker) {
                marker = L.marker(coords, { draggable: true }).addTo(map);
                marker.on('dragend', () => {
                    const next = marker.getLatLng();
                    setCoordinates(latInput, lngInput, next.lat, next.lng);
                    setStatus(statusEl, 'Ubicacion ajustada manualmente en el mapa.', 'text-muted');
                });
            } else {
                marker.setLatLng(coords);
            }
            setCoordinates(latInput, lngInput, lat, lng);
            if (status) setStatus(statusEl, status, 'text-muted');
        }

        if (initialPoint) {
            moveMarker(initialPoint.lat, initialPoint.lng);
        }

        async function geocode() {
            const query = addressInput.value.trim();
            if (query.length < 4) {
                setStatus(statusEl, 'Ingresa una direccion para verla en el mapa.', 'text-muted');
                return;
            }

            setStatus(statusEl, 'Buscando direccion...', 'text-muted');
            try {
                const url = new URL('https://nominatim.openstreetmap.org/search');
                url.searchParams.set('format', 'json');
                url.searchParams.set('limit', '1');
                url.searchParams.set('addressdetails', '1');
                url.searchParams.set('q', query);

                const response = await fetch(url.toString(), {
                    headers: { Accept: 'application/json' },
                });
                if (!response.ok) throw new Error('No se pudo consultar OpenStreetMap.');

                const results = await response.json();
                if (!results.length) {
                    setStatus(statusEl, 'No encontramos esa direccion. Proba agregando ciudad o provincia.', 'text-warning');
                    return;
                }

                const result = results[0];
                const lat = parseFloat(result.lat);
                const lng = parseFloat(result.lon);
                map.setView([lat, lng], RESULT_ZOOM);
                moveMarker(lat, lng, result.display_name);
            } catch (error) {
                setStatus(statusEl, 'No pudimos cargar la direccion en el mapa. Intenta de nuevo.', 'text-danger');
            }
        }

        map.on('click', (event) => {
            moveMarker(event.latlng.lat, event.latlng.lng, 'Ubicacion seleccionada manualmente en el mapa.');
        });

        if (button) button.addEventListener('click', geocode);
        addressInput.addEventListener('input', debounce(geocode, 900));
        window.setTimeout(() => map.invalidateSize(), 250);
    }

    function initStaticMap(container) {
        if (!window.L) return;
        const lat = parseFloat(String(container.dataset.lat || '').replace(',', '.'));
        const lng = parseFloat(String(container.dataset.lng || '').replace(',', '.'));
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        const map = L.map(container, {
            dragging: false,
            scrollWheelZoom: false,
            doubleClickZoom: false,
            boxZoom: false,
            keyboard: false,
            tap: false,
            zoomControl: false,
            attributionControl: false,
        }).setView([lat, lng], Number(container.dataset.zoom || STATIC_ZOOM));

        addTiles(map);
        const marker = L.marker([lat, lng], {
            icon: locationDotIcon(),
            interactive: false,
        }).addTo(map);
        if (container.dataset.label) marker.bindPopup(container.dataset.label);
        window.setTimeout(() => map.invalidateSize(), 250);
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-address-map]').forEach(initAddressMap);
        document.querySelectorAll('[data-static-map]').forEach(initStaticMap);
    });
})();
