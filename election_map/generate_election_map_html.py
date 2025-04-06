import folium

# Create a base map centered on Canada
m = folium.Map(location=[56, -94], zoom_start=4, tiles='CartoDB positron')

# Add a title
title_html = '''
<div style="position: fixed; 
    top: 10px; left: 50%; transform: translateX(-50%);
    z-index: 9999; font-size: 18px; font-weight: bold;
    background-color: white; padding: 10px; border-radius: 5px;
    box-shadow: 0 0 5px rgba(0,0,0,0.2);">
    Canadian Federal Election Model
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# Add legend
legend_html = '''
<div style="position: fixed; 
    bottom: 50px; left: 50px; z-index: 9999; 
    background-color: white; padding: 10px; border-radius: 5px;
    box-shadow: 0 0 5px rgba(0,0,0,0.2);">
    <div><strong>Party Prediction</strong></div>
    <div style="margin-bottom: 5px;"><span style="color: #ff0000; font-weight: bold;">■</span> Liberal</div>
    <div style="margin-bottom: 5px;"><span style="color: #0000ff; font-weight: bold;">■</span> Conservative</div>
    <div style="margin-bottom: 5px;"><span style="color: #ff9900; font-weight: bold;">■</span> NDP</div>
    <div style="margin-bottom: 5px;"><span style="color: #00cc00; font-weight: bold;">■</span> Green</div>
    <div style="margin-bottom: 5px;"><span style="color: #00ccff; font-weight: bold;">■</span> Bloc Québécois</div>
    <div style="margin-bottom: 5px;"><span style="color: #808080; font-weight: bold;">■</span> People's Party</div>
    <div style="margin-top: 10px;"><strong>Last Updated:</strong> <span id="lastUpdated">Loading...</span></div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Add custom JavaScript to load GeoJSON dynamically and create custom popups
custom_js = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Party name mapping
    const partyMapping = {
        'LPC': 'Liberal Party',
        'CPC': 'Conservative Party',
        'NDP': 'New Democratic Party',
        'GPC': 'Green Party',
        'BQ': 'Bloc Québécois',
        'PPC': 'People\\'s Party'
    };
    
    // Party color mapping
    const partyColors = {
        'LPC': '#ff0000',
        'CPC': '#0000ff',
        'NDP': '#ff9900',
        'GPC': '#00cc00',
        'BQ': '#00ccff',
        'PPC': '#808080'
    };
    
    // Get timestamp of the latest update
    fetch('election_forecast_2025.geojson', { method: 'HEAD' })
        .then(response => {
            const lastModified = new Date(response.headers.get('Last-Modified'));
            document.getElementById('lastUpdated').textContent = lastModified.toLocaleString();
        })
        .catch(error => {
            console.error('Error fetching file metadata:', error);
            document.getElementById('lastUpdated').textContent = 'Unknown';
        });
    
    // Load GeoJSON data
    fetch('election_forecast_2025.geojson')
        .then(response => response.json())
        .then(data => {
            // Create custom popup function
            function onEachFeature(feature, layer) {
                // Create popup content
                let popupContent = document.createElement('div');
                popupContent.style.width = '250px';
                popupContent.style.padding = '10px';
                popupContent.style.backgroundColor = 'white';
                popupContent.style.borderRadius = '5px';
                popupContent.style.boxShadow = '0 0 10px rgba(0,0,0,0.1)';
                
                let districtName = feature.properties.ED_NAMEE || 'District';
                let districtNum = feature.properties.FED_NUM || 'N/A';
                
                // Add district header
                let header = document.createElement('h4');
                header.textContent = `${districtName} (${districtNum})`;
                popupContent.appendChild(header);
                
                // Get all party data
                const partyData = [];
                for (const [key, value] of Object.entries(feature.properties)) {
                    if (key.toLowerCase().endsWith('wins')) {
                        const partyShort = key.replace('wins', '').toUpperCase();
                        const stdKey = partyShort.toLowerCase() + 'std';
                        
                        if (feature.properties[stdKey] !== undefined) {
                            partyData.push({
                                name: partyMapping[partyShort] || partyShort,
                                short: partyShort,
                                votePct: value,
                                stdDev: feature.properties[stdKey],
                                margin: 2 * feature.properties[stdKey]
                            });
                        }
                    }
                }
                
                // Sort by vote percentage
                partyData.sort((a, b) => b.votePct - a.votePct);
                
                // Add party results
                partyData.forEach(party => {
                    const color = partyColors[party.short] || '#000000';
                    
                    let partyDiv = document.createElement('div');
                    partyDiv.style.marginBottom = '5px';
                    
                    let partyName = document.createElement('span');
                    partyName.style.color = color;
                    partyName.style.fontWeight = 'bold';
                    partyName.textContent = party.name;
                    
                    partyDiv.appendChild(partyName);
                    partyDiv.appendChild(document.createTextNode(': '));
                    partyDiv.appendChild(document.createTextNode(
                        `${party.votePct.toFixed(1)}% ±${party.margin.toFixed(1)}`
                    ));
                    
                    popupContent.appendChild(partyDiv);
                });
                
                // Create popup
                const popup = L.popup({maxWidth: 300})
                    .setContent(popupContent);
                
                // Bind popup to layer
                layer.bindPopup(popup);
                
                // Custom hover behavior
                layer.on({
                    mouseover: function(e) {
                        const layer = e.target;
                        layer.setStyle({
                            fillColor: feature.properties.Fill,
                            fillOpacity: 0.9,
                            color: '#444444',
                            weight: 3,
                            opacity: 1
                        });
                        
                        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                            layer.bringToFront();
                        }
                    },
                    mouseout: function(e) {
                        const layer = e.target;
                        layer.setStyle({
                            fillColor: feature.properties.Fill,
                            fillOpacity: 0.7,
                            color: '#1f1f1f',
                            weight: 1,
                            opacity: 0.7
                        });
                    }
                });
            }
            
            // Add GeoJSON to map directly using Leaflet
            L.geoJSON(data, {
                style: function(feature) {
                    return {
                        fillColor: feature.properties.Fill,
                        fillOpacity: 0.7,
                        color: '#1f1f1f',
                        weight: 1,
                        opacity: 0.7
                    };
                },
                onEachFeature: onEachFeature
            }).addTo(map_MAPID);  // MAPID will be replaced by Folium
        })
        .catch(error => {
            console.error('Error loading GeoJSON:', error);
            alert('Failed to load election data. Please try again later.');
        });
});
</script>
"""

# Add the custom JavaScript to the map
custom_js = custom_js.replace('MAPID', m.get_name())
m.get_root().html.add_child(folium.Element(custom_js))

# Save the base map to an HTML file
m.save('index.html')

print("Map template has been saved as index.html")