import streamlit as st
import requests
import pandas as pd
import numpy as np
import time
import random
import uuid
import json
import math
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import pydeck as pdk

API_BASE_URL = "http://localhost:8000"  # Your FastAPI endpoint

BENGALURU_LAT = 12.9716
BENGALURU_LON = 77.5946

st.set_page_config(
    page_title="Namma Yatri Driver Simulator",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Namma Yatri Driver Simulator")

if 'current_trip' not in st.session_state:
    st.session_state.current_trip = None
if 'driver_mode' not in st.session_state:
    st.session_state.driver_mode = "Available"  # Available, OnTrip, GoHome
if 'trip_stage' not in st.session_state:
    st.session_state.trip_stage = None
if 'notification' not in st.session_state:
    st.session_state.notification = None
if 'coins' not in st.session_state:
    st.session_state.coins = 0
if 'multiplier' not in st.session_state:
    st.session_state.multiplier = 1.0
if 'multiplier_active' not in st.session_state:
    st.session_state.multiplier_active = False
if 'go_home_active' not in st.session_state:
    st.session_state.go_home_active = False
if 'distance_today' not in st.session_state:
    st.session_state.distance_today = 0
if 'trips_today' not in st.session_state:
    st.session_state.trips_today = 0
if 'consecutive_trips' not in st.session_state:
    st.session_state.consecutive_trips = 0
if 'ride_requests' not in st.session_state:
    st.session_state.ride_requests = []
if 'completed_trips' not in st.session_state:
    st.session_state.completed_trips = []
if 'driver_location' not in st.session_state:
    st.session_state.driver_location = (BENGALURU_LAT, BENGALURU_LON)
if 'destination_location' not in st.session_state:
    st.session_state.destination_location = None
if 'pickup_location' not in st.session_state:
    st.session_state.pickup_location = None
if 'simulation_active' not in st.session_state:
    st.session_state.simulation_active = False
if 'simulation_step' not in st.session_state:
    st.session_state.simulation_step = 0
if 'simulation_trips' not in st.session_state:
    st.session_state.simulation_trips = []
if 'simulation_log' not in st.session_state:
    st.session_state.simulation_log = []
if 'total_earnings' not in st.session_state:
    st.session_state.total_earnings = 0
if 'simulation_time' not in st.session_state:
    st.session_state.simulation_time = datetime(2023, 11, 14, 8, 0, 0)  # Starting at 8 AM

def get_all_drivers():
    try:
        response = requests.get(f"{API_BASE_URL}/drivers/")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch drivers: {response.text}")
            return []
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return []

def get_driver_stats(driver_id):
    try:
        response = requests.get(f"{API_BASE_URL}/drivers/{driver_id}/daily-stats")
        if response.status_code == 200:
            return response.json()
        else:
            st.warning(f"No daily stats for driver, creating new: {response.text}")
            return {
                "distance_covered_today": 0,
                "coins_earned": 0,
                "hours_active": 0,
                "consecutive_trips": 0,
                "multiplier_active": False,
                "multiplier_value": 1.0,
                "go_home_mode_active": False
            }
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return None

def get_trips(driver_id=None):
    """Get trips from the API"""
    try:
        params = {}
        if driver_id:
            params["driver_id"] = driver_id
            
        response = requests.get(f"{API_BASE_URL}/trips/", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning(f"Failed to fetch trips: {response.text}")
            return []
    except Exception as e:
        st.warning(f"API connection error when getting trips: {str(e)}")
        return []

def get_driver_details(driver_id):
    try:
        response = requests.get(f"{API_BASE_URL}/drivers/{driver_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch driver details: {response.text}")
            return None
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return None

def toggle_multiplier():
    """Toggle multiplier status using API"""
    if st.session_state.multiplier_active:
        st.session_state.notification = "Multiplier already active."
        st.rerun()
        return
    
    result = activate_multiplier(st.session_state.selected_driver)
    
    if result and result.get("success", False):
        st.session_state.multiplier_active = True
        st.session_state.multiplier = result.get("multiplier_value", 1.0)
        st.session_state.notification = result.get("message", "Multiplier activated!")
        
        if st.session_state.simulation_active:
            log_entry = {
                "time": st.session_state.simulation_time.strftime("%I:%M %p"),
                "action": "Multiplier Activated",
                "details": f"{st.session_state.multiplier}x multiplier activated",
                "coins": st.session_state.coins,
                "distance": st.session_state.distance_today
            }
            st.session_state.simulation_log.append(log_entry)
    else:
        st.session_state.notification = result.get("message", "Failed to activate multiplier.")
    
    st.rerun()

def toggle_go_home_mode():
    """Toggle go-home mode using API"""
    if st.session_state.go_home_active:
        st.session_state.notification = "Go-Home mode already active."
        st.rerun()
        return
    
    result = activate_go_home(st.session_state.selected_driver)
    
    if result and result.get("success", False):
        st.session_state.go_home_active = True
        st.session_state.driver_mode = "GoHome"
        st.session_state.notification = result.get("message", "Go-Home mode activated!")
        
        recommendations = get_go_home_recommendations(st.session_state.selected_driver)
        if recommendations and recommendations.get("success", False) and recommendations.get("recommendations", []):
            recs = recommendations.get("recommendations", [])
            rec_list = "\n".join([f"• {r['destination_location']} (₹{r['estimated_fare']})" for r in recs[:2]])
            st.session_state.notification += f"\n\nRecommended routes:\n{rec_list}"
            
        if st.session_state.simulation_active:
            log_entry = {
                "time": st.session_state.simulation_time.strftime("%I:%M %p"),
                "action": "Go-Home Mode Activated",
                "details": "Driver is heading home",
                "coins": st.session_state.coins,
                "distance": st.session_state.distance_today
            }
            st.session_state.simulation_log.append(log_entry)
    else:
        st.session_state.notification = result.get("message", "Failed to activate Go-Home mode.")
    
    st.rerun()

def cancel_ride():
    """Cancel the current ride"""
    st.session_state.trip_stage = None
    st.session_state.current_trip = None
    st.session_state.pickup_location = None
    st.session_state.destination_location = None
    st.session_state.notification = "Ride cancelled"
    st.rerun()

def complete_trip():
    """Complete the current trip"""
    if st.session_state.current_trip and "trip_id" in st.session_state.current_trip:
        process_trip(st.session_state.current_trip["trip_id"])
    
    st.session_state.trip_stage = None
    st.session_state.current_trip = None
    st.session_state.destination_location = None
    st.session_state.notification = "Trip completed successfully"
    st.session_state.trips_today += 1
    st.rerun()

def get_locations():
    try:
        response = requests.get(f"{API_BASE_URL}/locations/")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch locations: {response.text}")
            return []
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return []

def create_location(location_name, latitude, longitude):
    """Create a new location in the API"""
    try:
        location_data = {
            "location_name": location_name,
            "latitude": latitude,
            "longitude": longitude
        }
        
        response = requests.post(f"{API_BASE_URL}/locations/", json=location_data)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning(f"Failed to create location: {response.text}")
            return None
    except Exception as e:
        st.warning(f"API connection error when creating location: {str(e)}")
        return None

def process_trip(trip_id):
    """Process a trip in the API with better error handling"""
    try:
        response = requests.post(f"{API_BASE_URL}/trips/{trip_id}/process")
        
        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_json = response.json()
                detail = error_json.get('detail', 'Unknown error')
                st.error(f"Failed to process trip: {detail}")
            except:
                st.error(f"Failed to process trip: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"API connection error during trip processing: {str(e)}")
        return None

def create_trip(trip_data):
    """Create a new trip in the API with improved error handling"""
    try:
        if trip_data.get("event_type") == "NULL" or trip_data.get("event_type") is None:
            trip_data["event_type"] = None  # lowercase null for JSON
        
        # Ensure boolean values are proper booleans
        if isinstance(trip_data.get("at_event"), str):
            trip_data["at_event"] = trip_data["at_event"].lower() == "true"
        
        # st.write("DEBUG - Trip Data:")
        # st.json(trip_data)  # Use st.json for proper formatting
        
        response = requests.post(f"{API_BASE_URL}/trips/", json=trip_data)
        
        if response.status_code != 200:
            st.error(f"API Response ({response.status_code}):")
            try:
                error_json = response.json()
                st.json(error_json)
            except:
                st.error(response.text)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_text = response.text
            try:
                error_json = response.json()
                if 'detail' in error_json:
                    error_text = error_json['detail']
            except:
                pass
            
            st.error(f"Failed to create trip: {response.status_code} - {error_text}")
            
            st.warning("Common issues to check:")
            st.warning("- Ensure all required fields are present")
            st.warning("- Verify location IDs exist in the database")
            st.warning("- Check if driver_id exists")
            st.warning("- Check if trip_id is unique")
            return None
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return None


def process_cancellation(cancellation_data):
    """Create and process a cancellation via the API"""
    try:
        response = requests.post(f"{API_BASE_URL}/cancellations/", json=cancellation_data)
        if response.status_code == 200:
            cancellation_id = response.json()["cancellation_id"]
            
            process_response = requests.post(f"{API_BASE_URL}/cancellations/{cancellation_id}/process")
            if process_response.status_code == 200:
                return process_response.json()
            else:
                st.error(f"Failed to process cancellation: {process_response.text}")
                return None
        else:
            st.error(f"Failed to create cancellation: {response.text}")
            return None
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return None

def activate_multiplier(driver_id):
    """Activate a driver's multiplier via the API"""
    try:
        response = requests.post(f"{API_BASE_URL}/drivers/{driver_id}/activate-multiplier")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to activate multiplier: {response.text}")
            return None
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return None

def activate_go_home(driver_id):
    """Activate go-home mode via the API"""
    try:
        response = requests.post(f"{API_BASE_URL}/drivers/{driver_id}/activate-go-home")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to activate go-home mode: {response.text}")
            return None
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return None

def get_go_home_recommendations(driver_id):
    """Get go-home recommendations via the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/drivers/{driver_id}/go-home-recommendations")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get go-home recommendations: {response.text}")
            return None
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return None

def create_simulation_data():
    """Create the predefined simulation trip data based on the scenario"""
    if st.session_state.simulation_trips:
        return  
    
    locations = {
        "Shanti Nagar": {"lat": 12.9716, "lon": 77.5946},
        "Koramangala": {"lat": 12.9279, "lon": 77.6271},
        "Silk Board": {"lat": 12.9161, "lon": 77.6226},
        "Jayanagar": {"lat": 12.9299, "lon": 77.5833},
        "Electronic City": {"lat": 12.8445, "lon": 77.6612},
        "Whitefield": {"lat": 12.9698, "lon": 77.7499},
        "M. Chinnaswamy Stadium": {"lat": 12.9788, "lon": 77.5996},
        "Indiranagar": {"lat": 12.9784, "lon": 77.6408},
        "Domlur": {"lat": 12.9609, "lon": 77.6378},
        "Ejipura": {"lat": 12.9432, "lon": 77.6266}
    }
    
    create_simulation_locations(locations)
    
    # Trip 1: Shanti Nagar → Koramangala (8:15 AM)
    trip1 = {
        'trip_id': 'T001',
        'pickup_location': "Shanti Nagar",
        'destination_location': "Koramangala",
        'estimated_trip_distance_km': 5.2,
        'distance_to_pickup_km': 0.8,
        'traffic_factor': 0.85,  # Morning traffic
        'time_of_day': 'Morning',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 108,
        'trip_duration_minutes': 22,
        'pickup_coords': locations["Shanti Nagar"],
        'destination_coords': locations["Koramangala"],
        'simulation_time': datetime(2023, 11, 14, 8, 15, 0)
    }
    
    # Trip 2: Koramangala → Silk Board (8:50 AM)
    trip2 = {
        'trip_id': 'T002',
        'pickup_location': "Koramangala",
        'destination_location': "Silk Board",
        'estimated_trip_distance_km': 4.5,
        'distance_to_pickup_km': 1.2,
        'traffic_factor': 0.95,  # Very heavy traffic
        'time_of_day': 'Morning',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 97.5,
        'trip_duration_minutes': 35,
        'pickup_coords': locations["Koramangala"],
        'destination_coords': locations["Silk Board"],
        'simulation_time': datetime(2023, 11, 14, 8, 50, 0)
    }
    
    # Cancellation 1: Vehicle issue (9:40 AM)
    cancel1 = {
        'cancellation_id': 'C001',
        'reason': 'vehicle_damage',
        'time_since_accept_seconds': 45,
        'simulation_time': datetime(2023, 11, 14, 9, 40, 0)
    }
    
    # Trip 4: Silk Board → Jayanagar (10:30 AM)
    trip4 = {
        'trip_id': 'T004',
        'pickup_location': "Silk Board",
        'destination_location': "Jayanagar",
        'estimated_trip_distance_km': 7.8,
        'distance_to_pickup_km': 0.9,
        'traffic_factor': 0.65,  # Moderate traffic
        'time_of_day': 'Morning',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 147,
        'trip_duration_minutes': 28,
        'pickup_coords': locations["Silk Board"],
        'destination_coords': locations["Jayanagar"],
        'simulation_time': datetime(2023, 11, 14, 10, 30, 0)
    }
    
    # Trip 5: Jayanagar → Electronic City (11:15 AM)
    trip5 = {
        'trip_id': 'T005',
        'pickup_location': "Jayanagar",
        'destination_location': "Electronic City",
        'estimated_trip_distance_km': 14.5,
        'distance_to_pickup_km': 1.2,
        'traffic_factor': 0.7,
        'time_of_day': 'Afternoon',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 247.5,
        'trip_duration_minutes': 42,
        'pickup_coords': locations["Jayanagar"],
        'destination_coords': locations["Electronic City"],
        'simulation_time': datetime(2023, 11, 14, 11, 15, 0)
    }
    
    # Activate multiplier (1:00 PM)
    multiplier = {
        'action': 'activate_multiplier',
        'simulation_time': datetime(2023, 11, 14, 13, 0, 0)
    }
    
    # Trip 6: Electronic City → Whitefield (1:30 PM)
    trip6 = {
        'trip_id': 'T006',
        'pickup_location': "Electronic City",
        'destination_location': "Whitefield",
        'estimated_trip_distance_km': 13.2,
        'distance_to_pickup_km': 1.5,
        'traffic_factor': 0.6,
        'time_of_day': 'Afternoon',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 228,
        'trip_duration_minutes': 38,
        'pickup_coords': locations["Electronic City"],
        'destination_coords': locations["Whitefield"],
        'simulation_time': datetime(2023, 11, 14, 13, 30, 0)
    }
    
    # Cancellation 2: Driver preference (2:30 PM)
    cancel2 = {
        'cancellation_id': 'C002',
        'reason': 'destination_too_far',
        'time_since_accept_seconds': 120,
        'simulation_time': datetime(2023, 11, 14, 14, 30, 0)
    }
    
    # Trip 8: Whitefield → M. Chinnaswamy Stadium (3:30 PM)
    trip8 = {
        'trip_id': 'T008',
        'pickup_location': "Whitefield",
        'destination_location': "M. Chinnaswamy Stadium",
        'estimated_trip_distance_km': 11.8,
        'distance_to_pickup_km': 1.2,
        'traffic_factor': 0.8,  # Higher for event
        'time_of_day': 'Afternoon',
        'at_event': True,
        'event_type': 'Cricket Match',
        'base_fare': 30,
        'base_trip_fare': 207,
        'trip_duration_minutes': 45,
        'pickup_coords': locations["Whitefield"],
        'destination_coords': locations["M. Chinnaswamy Stadium"],
        'simulation_time': datetime(2023, 11, 14, 15, 30, 0)
    }
    
    # Trip 9: M. Chinnaswamy Stadium → Whitefield (5:15 PM)
    trip9 = {
        'trip_id': 'T009',
        'pickup_location': "M. Chinnaswamy Stadium",
        'destination_location': "Whitefield",
        'estimated_trip_distance_km': 16.5,
        'distance_to_pickup_km': 0.8,
        'traffic_factor': 0.9,  # Heavy evening traffic
        'time_of_day': 'Evening',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 277.5,
        'trip_duration_minutes': 65,
        'pickup_coords': locations["M. Chinnaswamy Stadium"],
        'destination_coords': locations["Whitefield"],
        'simulation_time': datetime(2023, 11, 14, 17, 15, 0)
    }
    
    # Trip 10: Whitefield → Koramangala (7:00 PM)
    trip10 = {
        'trip_id': 'T010',
        'pickup_location': "Whitefield",
        'destination_location': "Koramangala",
        'estimated_trip_distance_km': 9.2,
        'distance_to_pickup_km': 1.4,
        'traffic_factor': 0.75,
        'time_of_day': 'Evening',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 168,
        'trip_duration_minutes': 35,
        'pickup_coords': locations["Whitefield"],
        'destination_coords': locations["Koramangala"],
        'simulation_time': datetime(2023, 11, 14, 19, 0, 0)
    }
    
    # Activate Go-Home Mode (9:00 PM)
    go_home = {
        'action': 'activate_go_home',
        'simulation_time': datetime(2023, 11, 14, 21, 0, 0)
    }
    
    # Final Go-Home Trip: Koramangala → Indiranagar (9:15 PM)
    trip_home = {
        'trip_id': 'HOME-A',
        'pickup_location': "Koramangala",
        'destination_location': "Indiranagar",
        'estimated_trip_distance_km': 5.8,
        'distance_to_pickup_km': 0.5,
        'traffic_factor': 0.6,
        'time_of_day': 'Night',
        'at_event': False,
        'event_type': None,
        'base_fare': 30,
        'base_trip_fare': 117,
        'trip_duration_minutes': 22,
        'pickup_coords': locations["Koramangala"],
        'destination_coords': locations["Indiranagar"],
        'simulation_time': datetime(2023, 11, 14, 21, 15, 0)
    }
    
    st.session_state.simulation_trips = [
        trip1, trip2, cancel1, trip4, trip5, multiplier, 
        trip6, cancel2, trip8, trip9, trip10, go_home, trip_home
    ]

def create_simulation_locations(locations):
    """Create locations for the simulation in the database if they don't exist"""
    existing_locations = get_locations()
    existing_names = [loc["location_name"] for loc in existing_locations]
    
    for name, coords in locations.items():
        if name not in existing_names:
            create_location(name, coords["lat"], coords["lon"])
    
    updated_locations = get_locations()
    st.session_state.all_locations = updated_locations
    
    return updated_locations

def handle_trip_event(trip, driver_id):
    """Process a trip event in the simulation with better error handling"""
    locations = ensure_simulation_locations()
    
    pickup_id = None
    destination_id = None
    
    for loc in locations:
        if loc["location_name"] == trip["pickup_location"]:
            pickup_id = loc["location_id"]
        if loc["location_name"] == trip["destination_location"]:
            destination_id = loc["location_id"]
    
    if not pickup_id:
        st.warning(f"Creating pickup location: {trip['pickup_location']}")
        pickup_coords = trip["pickup_coords"]
        new_loc = create_location(trip["pickup_location"], pickup_coords["lat"], pickup_coords["lon"])
        if new_loc:
            pickup_id = new_loc["location_id"]
        else:
            st.error(f"Failed to create pickup location: {trip['pickup_location']}")
            return False
    
    if not destination_id:
        st.warning(f"Creating destination location: {trip['destination_location']}")
        dest_coords = trip["destination_coords"]
        new_loc = create_location(trip["destination_location"], dest_coords["lat"], dest_coords["lon"])
        if new_loc:
            destination_id = new_loc["location_id"]
        else:
            st.error(f"Failed to create destination location: {trip['destination_location']}")
            return False
    
    import time
    trip_id = f"{trip['trip_id']}-{int(time.time())}"
    
    trip_data = {
        "trip_id": trip_id,  # Use the unique ID
        "driver_id": driver_id,
        "pickup_location_id": pickup_id,
        "destination_location_id": destination_id,
        "estimated_trip_distance_km": trip["estimated_trip_distance_km"],
        "distance_to_pickup_km": trip["distance_to_pickup_km"],
        "traffic_factor": trip["traffic_factor"],
        "time_of_day": trip["time_of_day"],
        "at_event": trip["at_event"],
        "event_type": trip["event_type"],
        "base_fare": trip["base_fare"],
        "base_trip_fare": trip["base_trip_fare"],
        "trip_duration_minutes": trip["trip_duration_minutes"]
    }
    
    created_trip = create_trip(trip_data)
    
    if created_trip:
        st.session_state.trip_stage = "ToPickup"
        
        if 'pickup_coords' in trip:
            st.session_state.pickup_location = (
                trip['pickup_coords']['lat'], 
                trip['pickup_coords']['lon']
            )
        
        if 'destination_coords' in trip:
            st.session_state.destination_location = (
                trip['destination_coords']['lat'], 
                trip['destination_coords']['lon']
            )
        
        result = process_trip(created_trip["trip_id"])
        
        if result:
            st.session_state.coins = result.get("new_coins_balance", st.session_state.coins)
            st.session_state.distance_today = result.get("distance_covered_today", st.session_state.distance_today)
            st.session_state.trips_today += 1
            st.session_state.consecutive_trips = result.get("consecutive_trips", st.session_state.consecutive_trips)
            
            fare = trip["base_trip_fare"]
            if st.session_state.multiplier_active:
                fare *= st.session_state.multiplier
            
            st.session_state.total_earnings += fare
            
            st.session_state.driver_location = (
                trip["destination_coords"]["lat"],
                trip["destination_coords"]["lon"]
            )
            
            log_entry = {
                "time": trip["simulation_time"].strftime("%I:%M %p"),
                "action": "Trip Completed",
                "details": f"{trip['pickup_location']} → {trip['destination_location']} ({trip['estimated_trip_distance_km']} km, ₹{fare:.2f})",
                "coins": st.session_state.coins,
                "distance": st.session_state.distance_today
            }
            st.session_state.simulation_log.append(log_entry)
            st.session_state.trip_stage = None
   
            return True
    
    return False

def ensure_simulation_locations():
    """Make sure all required locations for simulation exist"""
    locations = {
        "Shanti Nagar": {"lat": 12.9716, "lon": 77.5946},
        "Koramangala": {"lat": 12.9279, "lon": 77.6271},
        "Silk Board": {"lat": 12.9161, "lon": 77.6226},
        "Jayanagar": {"lat": 12.9299, "lon": 77.5833},
        "Electronic City": {"lat": 12.8445, "lon": 77.6612},
        "Whitefield": {"lat": 12.9698, "lon": 77.7499},
        "M. Chinnaswamy Stadium": {"lat": 12.9788, "lon": 77.5996},
        "Indiranagar": {"lat": 12.9784, "lon": 77.6408},
        "Domlur": {"lat": 12.9609, "lon": 77.6378},
        "Ejipura": {"lat": 12.9432, "lon": 77.6266}
    }
    
    existing_locations = get_locations()
    existing_names = [loc["location_name"] for loc in existing_locations]
    created = 0
    
    for name, coords in locations.items():
        if name not in existing_names:
            new_loc = create_location(name, coords["lat"], coords["lon"])
            if new_loc:
                existing_locations.append(new_loc)
                created += 1
                st.info(f"Created location: {name} (ID: {new_loc['location_id']})")
    
    if created > 0:
        st.success(f"Created {created} new locations for simulation")
    
    return existing_locations

def handle_cancellation_event(cancellation, driver_id):
    """Process a cancellation event in the simulation"""
    trip_id = cancellation.get("trip_id", f"CANCELLED-{uuid.uuid4().hex[:8]}")
    
    cancellation_data = {
        "driver_id": driver_id,
        "trip_id": trip_id,
        "time_since_accept_seconds": cancellation["time_since_accept_seconds"],
        "reason": cancellation["reason"]
    }
    
    result = process_cancellation(cancellation_data)
    
    if result:
        penalty = result.get("penalty_coins", 0)
        st.session_state.coins = result.get("new_coins_balance", st.session_state.coins)
        
        log_entry = {
            "time": cancellation["simulation_time"].strftime("%I:%M %p"),
            "action": "Trip Cancelled",
            "details": f"Reason: {cancellation['reason']} (Penalty: {penalty} coins)",
            "coins": st.session_state.coins,
            "distance": st.session_state.distance_today
        }
        st.session_state.simulation_log.append(log_entry)
        
        return True
    
    return False

def get_route_points(start_lat, start_lon, end_lat, end_lon, num_points=15, randomness=0.0005):
    """
    Generate route points between two locations with some randomness to simulate real routes.
    
    Args:
        start_lat, start_lon: Starting coordinates
        end_lat, end_lon: Ending coordinates
        num_points: Number of points to generate along the route
        randomness: Amount of random deviation to add (in degrees)
        
    Returns:
        List of [lon, lat] points for the route
    """
    import random
    
    points = []
    
    # Always include the exact start and end points
    points.append([start_lon, start_lat])
    
    for i in range(1, num_points):
        # Calculate the fraction of the way from start to end
        fraction = i / num_points
        
        # Interpolate between start and end coordinates
        lat = start_lat + fraction * (end_lat - start_lat)
        lon = start_lon + fraction * (end_lon - start_lon)
        
        # Add some randomness to intermediate points
        if i != num_points-1:  # Don't add randomness to the last point
            lat += random.uniform(-randomness, randomness)
            lon += random.uniform(-randomness, randomness)
        
        # Add point to list (note: Pydeck expects [lon, lat] order)
        points.append([lon, lat])
    
    # Ensure the exact end point is included
    points.append([end_lon, end_lat])
    
    return points

def handle_multiplier_activation(driver_id):
    """Handle activating a driver's multiplier"""
    try:
        response = requests.post(f"{API_BASE_URL}/drivers/{driver_id}/activate-multiplier")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success', False):
                st.session_state.multiplier_active = True  # Set this flag
                st.session_state.multiplier = result.get('multiplier_value', 1.0)
                
                log_entry = {
                    "time": st.session_state.simulation_time.strftime("%I:%M %p"),
                    "action": "Multiplier Activated",
                    "details": f"{st.session_state.multiplier}x fare multiplier for 4 hours!",
                    "coins": st.session_state.coins,
                    "distance": st.session_state.distance_today
                }
                st.session_state.simulation_log.append(log_entry)
                
                return True
            else:
                st.error(result.get('message', 'Failed to activate multiplier'))
                return False
        else:
            st.error(f"Failed to activate multiplier: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return False

def handle_go_home_activation(driver_id):
    """Handle activating a driver's go-home mode"""
    try:
        response = requests.post(f"{API_BASE_URL}/drivers/{driver_id}/activate-go-home")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success', False):
                st.session_state.go_home_active = True  # Set this flag
                
                log_entry = {
                    "time": st.session_state.simulation_time.strftime("%I:%M %p"),
                    "action": "Go-Home Mode Activated",
                    "details": "Driver is now prioritizing trips toward home",
                    "coins": st.session_state.coins,
                    "distance": st.session_state.distance_today
                }
                st.session_state.simulation_log.append(log_entry)
                
                return True
            else:
                st.error(result.get('message', 'Failed to activate go-home mode'))
                return False
        else:
            st.error(f"Failed to activate go-home mode: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        st.error(f"API connection error: {str(e)}")
        return False

def reset_driver_daily_stats(driver_id):
    """Reset the driver's daily stats to zero at the beginning of the simulation"""
    try:
        payload = {
            "driver_id": driver_id,
            "distance_covered_today": 0,
            "coins_earned": 0,
            "hours_active": 0,
            "consecutive_trips": 0,
            "multiplier_active": False,
            "multiplier_value": 1.0,
            "go_home_mode_active": False,
            "stat_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        response = requests.post(f"{API_BASE_URL}/drivers/{driver_id}/reset-daily-stats", json=payload)
        
        if response.status_code == 200:
            st.success("Driver stats reset for today's simulation")
            return True
        else:
            st.error(f"Failed to reset driver daily stats: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        st.error(f"API connection error when resetting stats: {str(e)}")
        return False

def run_simulation_step():
    """Run a single step of the simulation"""
    if st.session_state.simulation_step == 0 and st.session_state.simulation_active:
        if 'selected_driver' in st.session_state:
            reset_driver_daily_stats(st.session_state.selected_driver)
    
    if st.session_state.simulation_step >= len(st.session_state.simulation_trips):
        st.session_state.simulation_active = False
        return False
    
    current_event = st.session_state.simulation_trips[st.session_state.simulation_step]
    
    st.session_state.simulation_time = current_event["simulation_time"]
    
    success = False
    
    if "action" in current_event:
        # Special action
        if current_event["action"] == "activate_multiplier":
            success = handle_multiplier_activation(st.session_state.selected_driver)
        elif current_event["action"] == "activate_go_home":
            success = handle_go_home_activation(st.session_state.selected_driver)
    elif "cancellation_id" in current_event:
        success = handle_cancellation_event(current_event, st.session_state.selected_driver)
    else:
        success = handle_trip_event(current_event, st.session_state.selected_driver)
    
    st.session_state.simulation_step += 1
    
    return success

def render_driver_phone():
    """Render the phone interface with integrated map during trips"""
    phone_col = st.container()
    
    with phone_col:
        st.markdown("""
        <style>
        .phone-frame {
            background-color: #f0f0f0;
            border: 15px solid #333;
            border-radius: 36px;
            padding: 10px;
            max-width: 360px;
            margin: 0 auto;
            position: relative;
        }
        .phone-header {
            display: flex;
            justify-content: space-between;
            padding: 5px 15px;
            background-color: #333;
            color: white;
            border-radius: 15px 15px 0 0;
            font-size: 14px;
        }
        .phone-content {
            background-color: white;
            min-height: 500px;
            border-radius: 0 0 15px 15px;
            padding: 10px;
            overflow-y: auto;
        }
        .phone-map-container {
            height: 250px;
            margin-bottom: 10px;
            border-radius: 8px;
            overflow: hidden;
        }
        /* ... other styles ... */
        </style>
        """, unsafe_allow_html=True)
        
        # Phone header with current time
        current_time = st.session_state.simulation_time.strftime("%I:%M %p") if st.session_state.simulation_active else datetime.now().strftime("%I:%M %p")
        
        st.markdown(f"""
        <div class="phone-frame">
            <div class="phone-header">
                <div>{current_time}</div>
                <div>📶 100% 🔋</div>
            </div>
            <div class="phone-content">
        """, unsafe_allow_html=True)
        
        # App header
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; border-bottom:1px solid #eee; padding-bottom:10px;">
            <div style="font-size:20px; font-weight:bold;">Namma Yatri Driver</div>
        """, unsafe_allow_html=True)
        
        # Driver status
        if st.session_state.driver_mode == "Available":
            st.markdown('<span class="status-chip status-online">Online</span>', unsafe_allow_html=True)
        elif st.session_state.driver_mode == "OnTrip":
            st.markdown('<span class="status-chip status-busy">On Trip</span>', unsafe_allow_html=True)
        elif st.session_state.driver_mode == "GoHome":
            st.markdown('<span class="status-chip status-go-home">Go Home</span>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Map section - Only show during trips (ToPickup or PickedUp stages)
        if st.session_state.trip_stage in ["ToPickup", "PickedUp"]:
            st.markdown('<div class="phone-map-container">', unsafe_allow_html=True)
            
            # Render the map inside the phone
            render_trip_map_in_phone()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Current trip details if in a trip
        if st.session_state.trip_stage == "ToPickup" and st.session_state.current_trip:
            trip = st.session_state.current_trip
            st.markdown(f"""
            <div style="background-color:#f0fdf4; padding:15px; border-radius:8px; border:1px solid #86efac;">
                <h3 style="margin-top:0;">Heading to Pickup</h3>
                <p><strong>Passenger:</strong> {trip['passenger_name']}</p>
                <p><strong>Pickup:</strong> {trip['pickup_location']['address']}</p>
                <p><strong>Distance remaining:</strong> <span id="remaining-distance">{trip.get('distance_remaining_to_pickup', trip['distance_to_pickup_km'])} km</span></p>
                <p><strong>ETA:</strong> <span id="eta">{trip.get('eta_to_pickup', trip['estimated_pickup_time_min'])} minutes</span></p>
                <button class="cancel-button" id="cancel-ride">Cancel Ride</button>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Cancel Ride", key="cancel_ride_btn"):
                cancel_ride()
                
        elif st.session_state.trip_stage == "PickedUp" and st.session_state.current_trip:
            trip = st.session_state.current_trip
            st.markdown(f"""
            <div style="background-color:#f0f9ff; padding:15px; border-radius:8px; border:1px solid #93c5fd;">
                <h3 style="margin-top:0;">Trip in Progress</h3>
                <p><strong>Passenger:</strong> {trip['passenger_name']}</p>
                <p><strong>Destination:</strong> {trip['destination_location']['address']}</p>
                <p><strong>Distance remaining:</strong> <span id="trip-remaining">{trip.get('distance_remaining', trip['estimated_trip_distance_km'])} km</span></p>
                <p><strong>ETA:</strong> <span id="trip-eta">{trip.get('eta', trip['estimated_trip_time_min'])} minutes</span></p>
                <p><strong>Fare:</strong> ₹{trip['estimated_fare']} {f"(x{st.session_state.multiplier} multiplier)" if st.session_state.multiplier > 1 else ""}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Complete Trip", key="complete_trip_btn"):
                complete_trip()
        
        if not st.session_state.simulation_active:
            if st.button("Run Full Day Simulation", key="start_sim"):
                if 'selected_driver' in st.session_state:
                    reset_driver_daily_stats(st.session_state.selected_driver)
                    
                create_simulation_data()
                st.session_state.simulation_step = 0
                st.session_state.simulation_log = []
                st.session_state.total_earnings = 0
                st.session_state.coins = 0
                st.session_state.distance_today = 0
                st.session_state.trips_today = 0
                st.session_state.consecutive_trips = 0
                st.session_state.multiplier = 1.0
                st.session_state.multiplier_active = False
                st.session_state.go_home_active = False
                st.session_state.simulation_time = datetime(2023, 11, 14, 8, 0, 0)
                
                st.session_state.simulation_active = True
                
                st.session_state.simulation_log.append({
                    "time": "8:00 AM",
                    "action": "Simulation Started",
                    "details": "Driver begins the day at Shanti Nagar",
                    "coins": 0,
                    "distance": 0
                })
                
                st.rerun()
            else:
                if st.button("Stop Simulation", key="stop_sim"):
                    st.session_state.simulation_active = False
                    st.rerun()
                    
            if st.session_state.driver_mode == "Available" and not st.session_state.simulation_active:
                st.markdown("""
                <div style="text-align:center; margin:20px 0;">
                    <p>You're online and available for rides</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                # with col1:
                #     if st.button("Activate Multiplier", key="multiplier_btn"):
                #         toggle_multiplier()
                
                # with col2:
                #     if st.button("Go-Home Mode", key="go_home_btn"):
                #         toggle_go_home_mode()
        
        # Display simulation log
        if st.session_state.simulation_log:
            st.markdown("<h3>Driver Activity Log</h3>", unsafe_allow_html=True)
            
            for entry in st.session_state.simulation_log:
                st.markdown(f"""
                <div class="log-entry">
                    <div><span class="log-time">[{entry['time']}]</span> <span class="log-action">{entry['action']}</span></div>
                    <div class="log-details">{entry['details']}</div>
                    <div class="log-stats">Distance: {entry['distance']:.1f} km | Coins: {entry['coins']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="margin-top:20px; padding:10px; background-color:#f8fafc; border-radius:8px; border:1px solid #e2e8f0;">
            <div style="display:flex; justify-content:space-between;">
                <div style="color:#000000;">
                    <strong>🪙 Coins:</strong> {st.session_state.coins}
                </div>
                <div style="color:#000000;">
                    <strong>🛣️ Distance:</strong> {st.session_state.distance_today:.1f} km
                </div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:8px;">
                <div style="color:#000000;">
                    <strong>🔄 Trips:</strong> {st.session_state.trips_today}
                </div>
                <div style="color:#000000;">
                    <strong>💰 Earnings:</strong> ₹{st.session_state.total_earnings:.2f}
                </div>
            </div>
            {"<div style='background-color:#fee2e2; color:#991b1b; padding:3px 8px; border-radius:12px; font-size:12px; margin-top:8px; display:inline-block;'><strong>✨ Multiplier x" + str(st.session_state.multiplier) + " active!</strong></div>" if st.session_state.multiplier_active else ""}
            {"<div style='background-color:#e0e7ff; color:#3730a3; padding:3px 8px; border-radius:12px; font-size:12px; margin-top:8px; display:inline-block;'><strong>🏠 Go-Home mode active</strong></div>" if st.session_state.go_home_active else ""}
        </div>
        """, unsafe_allow_html=True)
            
        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_trip_map_in_phone():
    """Render the trip map inside the phone UI"""
    if st.session_state.driver_location:
        driver_lat, driver_lon = st.session_state.driver_location
        
        layers = []
        
        driver_layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{
                "position": [driver_lon, driver_lat],
                "radius": 30,  # Smaller for phone
                "color": [255, 150, 0]
            }],
            get_position="position",
            get_radius="radius",
            get_fill_color="color",
            pickable=True
        )
        layers.append(driver_layer)
        
        if st.session_state.trip_stage == "ToPickup" and st.session_state.pickup_location:
            pickup_lat, pickup_lon = st.session_state.pickup_location
            
            route_points = get_route_points(
                driver_lat, driver_lon, 
                pickup_lat, pickup_lon
            )
            # Create route line data
            route_data = []
            for i in range(len(route_points) - 1):
                route_data.append({
                    "path": [
                        [route_points[i][1], route_points[i][0]],
                        [route_points[i+1][1], route_points[i+1][0]]
                    ],
                    "color": [0, 128, 255]
                })
            
            # Add route layer
            route_layer = pdk.Layer(
                "PathLayer",
                data=route_data,
                get_path="path",
                get_color="color",
                width_scale=15,
                width_min_pixels=2,
                get_width=3,
                pickable=True
            )
            layers.append(route_layer)
            
            # Add pickup marker
            pickup_layer = pdk.Layer(
                "ScatterplotLayer",
                data=[{
                    "position": [pickup_lon, pickup_lat],
                    "radius": 30,
                    "color": [0, 128, 255]
                }],
                get_position="position",
                get_radius="radius",
                get_fill_color="color",
                pickable=True
            )
            layers.append(pickup_layer)
            
        elif st.session_state.trip_stage == "PickedUp" and st.session_state.destination_location:
            dest_lat, dest_lon = st.session_state.destination_location
            
            # Generate route points
            route_points = get_route_points(
                driver_lat, driver_lon, 
                dest_lat, dest_lon
            )
            
            # Create route line data
            route_data = []
            for i in range(len(route_points) - 1):
                route_data.append({
                    "path": [
                        [route_points[i][1], route_points[i][0]],
                        [route_points[i+1][1], route_points[i+1][0]]
                    ],
                    "color": [76, 175, 80]
                })
            
            # Add route layer
            route_layer = pdk.Layer(
                "PathLayer",
                data=route_data,
                get_path="path",
                get_color="color",
                width_scale=15,
                width_min_pixels=2,
                get_width=3,
                pickable=True
            )
            layers.append(route_layer)
            
            # Add destination marker
            dest_layer = pdk.Layer(
                "ScatterplotLayer",
                data=[{
                    "position": [dest_lon, dest_lat],
                    "radius": 30,
                    "color": [76, 175, 80]
                }],
                get_position="position",
                get_radius="radius",
                get_fill_color="color",
                pickable=True
            )
            layers.append(dest_layer)
            
        # Create the pydeck view
        view_state = pdk.ViewState(
            longitude=driver_lon,
            latitude=driver_lat,
            zoom=13,
            pitch=0
        )
        
        # Render the deck with a specific height for the phone
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v10",
            initial_view_state=view_state,
            layers=layers,
            height=240
        ))
    else:
        st.info("Driver location not available")

def render_map():
    """Render map with driver location"""
    if st.session_state.driver_location:
        driver_lat, driver_lon = st.session_state.driver_location
        
        # Base map layer
        layers = []
        
        # Driver icon layer
        driver_layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{
                "position": [driver_lon, driver_lat],
                "radius": 50,
                "color": [255, 150, 0]
            }],
            get_position="position",
            get_radius="radius",
            get_fill_color="color",
            pickable=True
        )
        layers.append(driver_layer)
        
        # Create the pydeck view
        view_state = pdk.ViewState(
            longitude=driver_lon,
            latitude=driver_lat,
            zoom=13,
            pitch=0
        )
        
        # Render the deck
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v10",
            initial_view_state=view_state,
            layers=layers
        ))
    else:
        st.info("Driver location not available")

def render_progress_metrics():
    """Render metrics showing progress toward daily targets"""
    if st.session_state.simulation_active or st.session_state.simulation_step > 0:
        col1, col2 = st.columns(2)
        
        # Target distance progress
        with col1:
            st.subheader("Distance Target")
            daily_target = 90  # From the simulation scenario
            target_60_percent = 54.0
            target_100_percent = 90            
            # Calculate progress percentages
            progress_60 = min(100, (st.session_state.distance_today / target_60_percent) * 100) 
            progress_100 = min(100, (st.session_state.distance_today / target_100_percent) * 100)
            
            st.write("60% Target (50 coins):")
            st.progress(progress_60 / 100)
            st.text(f"{st.session_state.distance_today:.1f} km / {target_60_percent:.1f} km - {progress_60:.1f}%")
            
            st.write("100% Target (100 coins):")
            st.progress(progress_100 / 100)
            st.text(f"{st.session_state.distance_today:.1f} km / {target_100_percent:.1f} km - {progress_100:.1f}%")
        
        # Earnings progress
        with col2:
            st.subheader("Earnings")
            
            # Create a bar chart of earnings
            if st.session_state.trips_today > 0:
                # Calculate earnings breakdown
                base_earnings = st.session_state.total_earnings
                if st.session_state.multiplier_active and st.session_state.multiplier > 1:
                    base_earnings = st.session_state.total_earnings / st.session_state.multiplier
                    multiplier_bonus = st.session_state.total_earnings - base_earnings
                else:
                    multiplier_bonus = 0
                
                # Create earnings data
                earnings_data = pd.DataFrame({
                    'Category': ['Base Fare', 'Multiplier Bonus'],
                    'Amount': [base_earnings, multiplier_bonus]
                })
                
                # Create bar chart
                fig = px.bar(
                    earnings_data, 
                    x='Category', 
                    y='Amount',
                    color='Category',
                    color_discrete_map={'Base Fare': '#3b82f6', 'Multiplier Bonus': '#f59e0b'},
                    title="Earnings Breakdown"
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Complete trips to see earnings breakdown")

def render_driver_stats(driver_id, driver_data, stats_data):
    """Render the driver's statistics and information"""
    
    # Driver profile card
    st.subheader("Driver Profile")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Profile picture placeholder
        st.image("https://i.pravatar.cc/150?img=" + str(hash(driver_id) % 70), width=120)
    
    with col2:
        # Driver details
        st.markdown(f"**Name:** {driver_data['name']}")
        st.markdown(f"**ID:** {driver_id}")
        st.markdown(f"**Rating:** {driver_data['rating']}⭐")
        st.markdown(f"**Experience:** {driver_data['experience_years']} years")
        st.markdown(f"**Home:** Indiranagar, Bengaluru")
    
    # Day summary if simulation has run
    if st.session_state.simulation_step > 0:
        st.subheader("Simulation Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Trips", st.session_state.trips_today)
        
        with col2:
            st.metric("Total Distance", f"{st.session_state.distance_today:.1f} km")
        
        with col3:
            st.metric("Total Earnings", f"₹{st.session_state.total_earnings:.2f}")
        
        trips = get_trips(driver_id)
        if trips:
            st.subheader("Trip History")
            
            trip_data = []
            for trip in trips:
                trip_data.append({
                    "Trip ID": trip["trip_id"],
                    "Distance": f"{trip['estimated_trip_distance_km']} km",
                    "Base Fare": f"₹{trip['base_trip_fare']}",
                    "Multiplier": f"{trip['multiplier_applied']}x",
                    "Final Fare": f"₹{trip['final_fare']}",
                    "Coins": trip.get("coins_earned", "-")
                })
            
            if trip_data:
                df = pd.DataFrame(trip_data)
                st.dataframe(df, use_container_width=True)

def load_bengaluru_locations():
    """Load or create predefined Bengaluru locations needed for simulation"""
    locations = {
        "Shanti Nagar": {"lat": 12.9716, "lon": 77.5946},
        "Koramangala": {"lat": 12.9279, "lon": 77.6271},
        "Silk Board": {"lat": 12.9161, "lon": 77.6226},
        "Jayanagar": {"lat": 12.9299, "lon": 77.5833},
        "Electronic City": {"lat": 12.8445, "lon": 77.6612},
        "Whitefield": {"lat": 12.9698, "lon": 77.7499},
        "M. Chinnaswamy Stadium": {"lat": 12.9788, "lon": 77.5996},
        "Indiranagar": {"lat": 12.9784, "lon": 77.6408},
        "Domlur": {"lat": 12.9609, "lon": 77.6378},
        "Ejipura": {"lat": 12.9432, "lon": 77.6266}
    }
    
    # Get existing locations
    existing_locations = get_locations()
    existing_names = [loc["location_name"] for loc in existing_locations]
    
    # Create missing locations
    created = 0
    for name, coords in locations.items():
        if name not in existing_names:
            create_location(name, coords["lat"], coords["lon"])
            created += 1
    
    if created > 0:
        st.success(f"Created {created} new locations for simulation")
    
    return get_locations()

# Main function
def main():
    drivers = get_all_drivers()
    
    driver_options = {}
    for driver in drivers:
        driver_options[driver["driver_id"]] = f"{driver['name']} ({driver['driver_id']})"
    
    if not driver_options:
        st.error("No drivers found. Please create a driver through the API first.")
        st.info("Use the API to create a driver with ID 'KA01-T-9876', name 'Ramesh', and home in Indiranagar.")
        return
    
    with st.sidebar:
        st.header("Driver Selection")
        
        selected_driver = st.selectbox(
            "Select a driver",
            options=list(driver_options.keys()),
            format_func=lambda x: driver_options[x],
            key="driver_select"
        )
        
        st.session_state.selected_driver = selected_driver
        
        driver_data = get_driver_details(selected_driver)
        driver_stats = get_driver_stats(selected_driver)
        
        st.header("Simulation Settings")
        if st.button("Load/Create Bengaluru Locations"):
            locations = load_bengaluru_locations()
            st.success(f"Loaded {len(locations)} locations")
        
        if st.button("Reset Simulation"):
            if 'selected_driver' in st.session_state:
                reset_driver_daily_stats(st.session_state.selected_driver)
                
            st.session_state.simulation_step = 0
            st.session_state.simulation_log = []
            st.session_state.simulation_active = False
            st.session_state.total_earnings = 0
            st.session_state.coins = 0
            st.session_state.distance_today = 0
            st.session_state.trips_today = 0
            st.session_state.consecutive_trips = 0
            st.session_state.multiplier = 1.0
            st.session_state.multiplier_active = False
            st.session_state.go_home_active = False
            st.session_state.driver_location = (BENGALURU_LAT, BENGALURU_LON)
            st.session_state.simulation_time = datetime(2023, 11, 14, 8, 0, 0)
            st.rerun()
    
    if driver_stats:
        if not st.session_state.simulation_active and st.session_state.simulation_step == 0:
            st.session_state.coins = driver_stats.get("coins_earned", 0)
            st.session_state.distance_today = driver_stats.get("distance_covered_today", 0)
            st.session_state.consecutive_trips = driver_stats.get("consecutive_trips", 0)
            st.session_state.multiplier = driver_stats.get("multiplier_value", 1.0)
            st.session_state.multiplier_active = driver_stats.get("multiplier_active", False)
            st.session_state.go_home_active = driver_stats.get("go_home_mode_active", False)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_driver_phone()
    
    with col2:
        render_driver_stats(selected_driver, driver_data, driver_stats)
        render_progress_metrics()
    if st.button("Ensure Locations Exist", key="create_locations"):
        locations = ensure_simulation_locations()
        st.success(f"Verified {len(locations)} locations")
        return None
    with st.sidebar:
        if st.button("Create Test Trip"):
            test_trip = {
                "trip_id": f"TEST-{int(time.time())}",
                "driver_id": "KA01-T-9876",
                "pickup_location_id": 1,
                "destination_location_id": 5,
                "estimated_trip_distance_km": 4.5,
                "distance_to_pickup_km": 1.2,
                "traffic_factor": 0.95,
                "time_of_day": "Morning",
                "at_event": False,
                "event_type": None,
                "base_fare": 30,
                "base_trip_fare": 97.5,
                "trip_duration_minutes": 35
            }
            result = create_trip(test_trip)
            if result:
                st.success("Test trip created successfully!")
    if st.session_state.simulation_active:
        ensure_simulation_locations()
        run_simulation_step()
        
        if st.session_state.simulation_step < len(st.session_state.simulation_trips):
            placeholder = st.empty()
            time.sleep(2)  
            placeholder.text("")  
            st.rerun()
        else:
            st.session_state.simulation_active = False
            
            st.session_state.simulation_log.append({
                "time": "10:00 PM",
                "action": "Simulation Complete",
                "details": f"Day summary: {st.session_state.trips_today} trips, {st.session_state.distance_today:.1f} km, ₹{st.session_state.total_earnings:.2f} earned, {st.session_state.coins} coins",
                "coins": st.session_state.coins,
                "distance": st.session_state.distance_today
            })
            
            st.success("Full day simulation complete!")
            st.balloons()

if __name__ == "__main__":
    main()