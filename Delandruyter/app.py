from flask import Flask, render_template, request
import geopandas as gpd
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Function to geocode an address
def geocodeAdres(adres):
    geolocator = Nominatim(user_agent="my_app")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    try:
        location = geocode(adres)
        if location:
            return location.latitude, location.longitude
        else:
            return None  # Return None if not found
    except Exception as e:
        print(f"Error occurred during geocoding: {e}")
        return None

# Load data from CSV
df = pd.read_csv('DATA/POI_aangepast.csv', delimiter=';')

# Convert commas to dots in coordinate columns and convert to numeric
df['WGS84_LATITUDE'] = pd.to_numeric(df['WGS84_LATITUDE'].astype(str).str.replace(',', '.', regex=False))
df['WGS84_LONGITUDE'] = pd.to_numeric(df['WGS84_LONGITUDE'].astype(str).str.replace(',', '.', regex=False))

# Extract unique values for the 'CATEGORIE' column
unique_categories = df['CATEGORIE'].unique().tolist()
unique_gemeentes = df['GEMEENTE'].unique().tolist()

# Create GeoDataFrame
geometry = gpd.points_from_xy(df['WGS84_LONGITUDE'], df['WGS84_LATITUDE'])
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        address = request.form.get("input_address")
        onderwijsniveau = request.form.get("tags-level")
        gemeente = request.form.get("input_gemeente")
        print("Filter inputs:", onderwijsniveau, gemeente)

        # Filter the GeoDataFrame
        filtered_gdf = gdf[
            (gdf['CATEGORIE'] == onderwijsniveau) &
            (gdf['GEMEENTE'] == gemeente)
        ]
        print(f"Filtered DataFrame: {filtered_gdf}")

        # Debug: Print coordinates of filtered locations
        for index, row in filtered_gdf.iterrows():
            print(f"Location {index}: {row['NAAM']} - LAT: {row['WGS84_LATITUDE']}, LON: {row['WGS84_LONGITUDE']}")

        # Load the shapefile and reproject to WGS84
        shapefile_path = "DATA/Gevaarlijke punten 2023.shp"
        gkp = gpd.read_file(shapefile_path)
        gkp = gkp.to_crs(epsg=4326)

        # Create the map and add markers for both the shapefile and the filtered locations
        map_center = geocodeAdres(address)
        if map_center:
            my_map = folium.Map(location=map_center, zoom_start=12)
            
            # Add markers from the shapefile
            for idx, row in gkp.iterrows():
                coords = row.geometry.centroid.coords[0]
                folium.Marker(
                    location=[coords[1], coords[0]],  # Note the order: [latitude, longitude]
                    icon=folium.Icon(icon="exclamation-triangle", prefix='fa', color="darkred", icon_color="white"),
                    popup=f"<b>{row['gemeente']}</b> {row['beschrijvi']}",
                ).add_to(my_map)
            
            # Add markers for filtered locations
            for index, row in filtered_gdf.iterrows():
                folium.Marker(
                    [row['WGS84_LATITUDE'], row['WGS84_LONGITUDE']],
                    popup=f"<b>{row['NAAM']}</b> {row['CATEGORIE']}, <i>{row['STRAAT']}</i>, <i>{row['GEMEENTE']}</i><br><b>{row['LINK']}</b>",
                    icon=folium.Icon(icon="graduation-cap", prefix='fa')
                ).add_to(my_map)

            # Mark the input address (if found)
            folium.Marker(map_center,
                          icon=folium.Icon(icon="home", color="darkblue", icon_color="white"),
                          popup=folium.Popup(f'<b>Jouw adres:</b><br>{address}<br><b>COÃ–RDINATEN:</b><br>{map_center}')).add_to(my_map)

            return render_template("kaart.html", folium_map=my_map._repr_html_(), categories=unique_categories, gemeentes=unique_gemeentes)
        else:
            print("Geocoding failed for address:", address)
            return render_template("kaartapplicatie.html", error="Geocoding mislukt. Controleer het adres.", categories=unique_categories, gemeentes=unique_gemeentes)
    else:
        return render_template("kaartapplicatie.html", categories=unique_categories, gemeentes=unique_gemeentes)


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
    

