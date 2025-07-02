// Initialize the map and set its view to Romania
var mymap = L.map('mapid').setView([45.9432, 24.9668], 7);

// Add a tile layer (OpenStreetMap)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(mymap);

// Object to store vehicle markers, using vehicle_id as key
let vehicleMarkers = {};
let liveRoutePolylines = {}; // Stores live route polylines for each vehicle
let historyRoutePolyline = null; // Stores the currently displayed history route
let latestVehicleData = []; // Store the latest full data for all vehicles

const vehicleInfoPanel = document.getElementById('vehicleInfoPanel');

// Function to update the vehicle information panel
function updateVehicleInfoPanel(vehicle) {
    if (vehicle) {
        vehicleInfoPanel.innerHTML = `
            <h3>Informații Vehicul: ${vehicle.vehicle_id}</h3>
            <p><strong>Status:</strong> ${vehicle.status}</p>
            <p><strong>Viteză:</strong> ${vehicle.speed} km/h</p>
            <p><strong>Combustibil:</strong> ${vehicle.fuel_level} / ${vehicle.fuel_capacity} L</p>
            <p><strong>Odometru:</strong> ${vehicle.odometer} km</p>
            <p><strong>Ore motor:</strong> ${vehicle.engine_hours} h</p>
            <p><strong>Latitudine:</strong> ${vehicle.latitude.toFixed(4)}</p>
            <p><strong>Longitudine:</strong> ${vehicle.longitude.toFixed(4)}</p>
        `;
    } else {
        vehicleInfoPanel.innerHTML = `<h3>Informații Vehicul Selectat</h3><p>Selectați un vehicul sau click pe un marker.</p>`;
    }
}

// Function to update vehicle markers and their live routes on the map
function updateUIVehicles(vehicles) {
    latestVehicleData = vehicles; // Cache the latest data

    vehicles.forEach(vehicle => {
        const lat = vehicle.latitude;
        const lon = vehicle.longitude;
        const vehicleId = vehicle.vehicle_id;
        const popupContent = `
            <b>Vehicul:</b> ${vehicleId}<br>
            <b>Status:</b> ${vehicle.status}<br>
            <b>Viteză:</b> ${vehicle.speed} km/h<br>
            <b>Combustibil:</b> ${vehicle.fuel_level} / ${vehicle.fuel_capacity} L
        `;

        if (vehicleMarkers[vehicleId]) {
            vehicleMarkers[vehicleId].setLatLng([lat, lon]);
            vehicleMarkers[vehicleId].getPopup().setContent(popupContent);
            vehicleMarkers[vehicleId].vehicleData = vehicle; // Update stored data
        } else {
            vehicleMarkers[vehicleId] = L.marker([lat, lon]).addTo(mymap)
                .bindPopup(popupContent);
            vehicleMarkers[vehicleId].vehicleData = vehicle; // Store data on marker
            vehicleMarkers[vehicleId].on('click', () => {
                updateVehicleInfoPanel(vehicleMarkers[vehicleId].vehicleData);
                document.getElementById('vehicleSelect').value = vehicleId; // Sync dropdown
            });
        }

        // Update live route polyline
        if (vehicle.route_segment && vehicle.route_segment.length > 1) {
            const latLngs = vehicle.route_segment.map(point => [point[0], point[1]]);
            if (liveRoutePolylines[vehicleId]) {
                liveRoutePolylines[vehicleId].setLatLngs(latLngs);
            } else {
                liveRoutePolylines[vehicleId] = L.polyline(latLngs, { color: 'blue', weight: 3, opacity: 0.7 }).addTo(mymap);
            }
        } else {
            // If no route segment or too short, remove existing polyline if any
            if (liveRoutePolylines[vehicleId]) {
                mymap.removeLayer(liveRoutePolylines[vehicleId]);
                delete liveRoutePolylines[vehicleId];
            }
        }
    });

    // Update info panel if a vehicle is selected in the dropdown
    const selectedVehicleId = document.getElementById('vehicleSelect').value;
    if (selectedVehicleId) {
        const selectedVehicleData = latestVehicleData.find(v => v.vehicle_id === selectedVehicleId);
        if (selectedVehicleData) {
            updateVehicleInfoPanel(selectedVehicleData);
        }
    } else {
        // If "All vehicles" is selected, clear the panel
        updateVehicleInfoPanel(null);
    }
}

// Function to fetch vehicle data from the API
async function fetchVehicleData() {
    try {
        const response = await fetch('/api/vehicles');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const vehicles = await response.json();
        updateUIVehicles(vehicles); // Use the corrected function name
    } catch (error) {
        console.error("Could not fetch vehicle data:", error);
    }
}

// Function to display historical route
async function displayHistoricalRoute(vehicleId) {
    if (!vehicleId) {
        alert("Vă rugăm selectați un vehicul.");
        return;
    }
    try {
        const response = await fetch(`/api/vehicle/${vehicleId}/history`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const historyData = await response.json();

        if (historyRoutePolyline) {
            mymap.removeLayer(historyRoutePolyline);
        }

        if (historyData && historyData.length > 0) {
            const latLngs = historyData.map(p => [p.latitude, p.longitude]);
            historyRoutePolyline = L.polyline(latLngs, { color: 'red', weight: 4 }).addTo(mymap);
            mymap.fitBounds(historyRoutePolyline.getBounds());
        } else {
            alert("Nu există date istorice pentru acest vehicul.");
            historyRoutePolyline = null; // Ensure it's cleared if no data
        }
    } catch (error) {
        console.error("Could not fetch historical route:", error);
        alert("Eroare la încărcarea istoricului traseului.");
        historyRoutePolyline = null; // Ensure it's cleared on error
    }
}

// Event Listeners
document.getElementById('showHistoryBtn').addEventListener('click', () => {
    const selectedVehicleId = document.getElementById('vehicleSelect').value;
    displayHistoricalRoute(selectedVehicleId);
});

document.getElementById('clearHistoryBtn').addEventListener('click', () => {
    if (historyRoutePolyline) {
        mymap.removeLayer(historyRoutePolyline);
        historyRoutePolyline = null;
    }
});

document.getElementById('vehicleSelect').addEventListener('change', (event) => {
    const selectedVehicleId = event.target.value;
    if (selectedVehicleId) {
        const vehicleData = latestVehicleData.find(v => v.vehicle_id === selectedVehicleId);
        if (vehicleData) {
             updateVehicleInfoPanel(vehicleData);
        } else {
            updateVehicleInfoPanel(null);
        }
    } else {
        updateVehicleInfoPanel(null);
    }
});


// Initial fetch and interval
fetchVehicleData();
setInterval(fetchVehicleData, 5000); // Update every 5 seconds
