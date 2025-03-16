import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import uuid
import time
import threading

# Set random seed for reproducibility
np.random.seed(42)

BENGALURU_LOCATIONS = {
    'HSR Layout': (12.9116, 77.6474),
    'Madiwala': (12.9226, 77.6174),
    'Bannerghatta': (12.8614, 77.5968),
    'Hosur Road': (12.8941, 77.6339),
    'Mahadevapura': (12.9901, 77.6966),
    'Krishnarajapuram': (13.0053, 77.6962),
    'BTM Layout': (12.9166, 77.6101),
    'Byatarayanapura': (13.0629, 77.5937),
    'CV Raman Nagar': (12.9850, 77.6661),
    'Bommanahalli': (12.8994, 77.6178),
    'Sarvagnanagar': (13.0207, 77.6431),
    'Shanti Nagar': (12.9626, 77.5995),
    'Rajarajeshwarinagar': (12.9219, 77.5193),
    'Hebbal': (13.0356, 77.5964),
    'Shivajinagar': (12.9850, 77.6075),
    'Jayanagar': (12.9299, 77.5833),
    'Malleshwaram': (13.0035, 77.5709),
    'Padmanabhanagar': (12.9143, 77.5626),
    'Chickpet': (12.9720, 77.5761),
    'Gandhi Nagar': (12.9777, 77.5766),
    'Yeshwantpur': (13.0279, 77.5498),
    'Pulakeshinagar': (12.9921, 77.6317),
    'Yelahanka': (13.1005, 77.5963),
    'Basavanagudi': (12.9418, 77.5697),
    'Dasarahalli': (13.0301, 77.5144),
    'Vijay Nagar': (12.9719, 77.5306),
    'Mahalakshmi Layout': (13.0184, 77.5474),
    'Rajaji Nagar': (12.9884, 77.5554),
    'Anekal': (12.7083, 77.6955),
    'Govindraj Nagar': (12.9609, 77.5372),
    'Chamrajpet': (12.9566, 77.5726),
    'Devanahalli': (13.2437, 77.7147),
    'Hoskote': (13.0707, 77.7987),
    'Nelamangala': (13.0996, 77.3953),
    'Doddaballapur': (13.2957, 77.5374),
    'Magadi': (12.9564, 77.2259),
    'Ramanagaram': (12.7148, 77.2982),
    'Kanakapura': (12.5462, 77.4177),
    'Channapatna': (12.6513, 77.2065),
    'Indiranagar': (12.9784, 77.6408),
    'Marathahalli': (12.9591, 77.6974),
    'Koramangala': (12.9279, 77.6271),
    'JP Nagar': (12.9063, 77.5906),
    'KR Puram': (13.0054, 77.6964),
    'Mysore Road': (12.9415, 77.5364),
    'Mekhri Circle': (13.0122, 77.5761),
    'Hennur': (13.0485, 77.6317),
    'Whitefield': (12.9698, 77.7499)
}

def generate_location():
    """Generate a random location from the defined Bengaluru areas."""
    location_name = random.choice(list(BENGALURU_LOCATIONS.keys()))
    base_lat, base_long = BENGALURU_LOCATIONS[location_name]

    lat = base_lat + np.random.uniform(-0.01, 0.01)
    long = base_long + np.random.uniform(-0.01, 0.01)

    return lat, long, location_name

def generate_driver_data(num_drivers=100):
    """Generate synthetic data for drivers."""
    drivers_data = []

    for _ in range(num_drivers):
        driver_id = str(uuid.uuid4())
        lat, long, location = generate_location()

        online_status = np.random.choice(['Online', 'Offline'], p=[0.75, 0.25])
        trip_status = np.random.choice(['Idle', 'En Route', 'Occupied'], p=[0.4, 0.3, 0.3])

        # Historical Performance
        ride_acceptance_rate = np.random.beta(8, 2) * 100
        cancellation_rate = np.random.beta(2, 8) * 100

        # Trip Patterns
        avg_trip_duration = np.random.gamma(2, 10)
        avg_trip_distance = np.random.gamma(2, 3)

        # Driver Profile
        experience_years = np.random.randint(1, 11)
        rating = np.random.uniform(3.0, 5.0)
        completed_trips = np.random.randint(100, 5000)

        # Time Sensitivity
        preferred_shift = np.random.choice(['Morning', 'Afternoon', 'Evening', 'Night', 'All Day'])
        peak_acceptance_rate = min(ride_acceptance_rate + np.random.uniform(0, 10), 100)
        off_peak_acceptance_rate = min(ride_acceptance_rate - np.random.uniform(0, 10), 100)

        # Trip Type Preference
        preferred_trip_type = np.random.choice(['Short', 'Long', 'Both'], p=[0.3, 0.3, 0.4])

        # Incentive & Behavior
        incentive_responsiveness = np.random.uniform(0.5, 1.0)
        event_sensitivity = np.random.uniform(0.0, 1.0)

        # Namma Yatri Coin System fields
        daily_avg_distance_km = round(np.random.uniform(40, 120), 2)
        coins_earned = np.random.randint(0, 100)
        target_distance_60_percent = round(daily_avg_distance_km * 0.6, 2)
        target_distance_100_percent = daily_avg_distance_km
        multiplier_active = np.random.choice([True, False], p=[0.2, 0.8])
        multiplier_value = 1.25 if 50 <= coins_earned < 100 else 1.5 if coins_earned >= 100 else 1.0
        multiplier_valid_until = datetime.now() + timedelta(days=np.random.randint(0, 3))
        distance_covered_today = round(np.random.uniform(0, daily_avg_distance_km), 2)
        
        # Home location (random location, but we'll store it)
        home_lat, home_long, home_location = generate_location()

        drivers_data.append({
            'driver_id': driver_id,
            'latitude': lat,
            'longitude': long,
            'location': location,
            'online_status': online_status,
            'trip_status': trip_status,
            'ride_acceptance_rate': round(ride_acceptance_rate, 2),
            'cancellation_rate': round(cancellation_rate, 2),
            'avg_trip_duration_minutes': round(avg_trip_duration, 2),
            'avg_trip_distance_km': round(avg_trip_distance, 2),
            'experience_years': experience_years,
            'rating': round(rating, 2),
            'completed_trips': completed_trips,
            'preferred_shift': preferred_shift,
            'peak_acceptance_rate': round(peak_acceptance_rate, 2),
            'off_peak_acceptance_rate': round(off_peak_acceptance_rate, 2),
            'preferred_trip_type': preferred_trip_type,
            'incentive_responsiveness': round(incentive_responsiveness, 2),
            'event_sensitivity': round(event_sensitivity, 2),
            'daily_avg_distance_km': daily_avg_distance_km,
            'coins_earned': coins_earned,
            'target_distance_60_percent': target_distance_60_percent,
            'target_distance_100_percent': target_distance_100_percent,
            'multiplier_active': multiplier_active,
            'multiplier_value': multiplier_value,
            'multiplier_valid_until': multiplier_valid_until,
            'distance_covered_today': distance_covered_today,
            'home_latitude': home_lat,
            'home_longitude': home_long,
            'home_location': home_location,
            'consecutive_trips': np.random.randint(0, 5)
        })

    return pd.DataFrame(drivers_data)

def generate_passenger_data(num_passengers=200):
    """Generate synthetic data for passengers."""
    passengers_data = []

    for _ in range(num_passengers):
        passenger_id = str(uuid.uuid4())
        pickup_lat, pickup_long, pickup_location = generate_location()

        destinations = [loc for loc in BENGALURU_LOCATIONS.keys() if loc != pickup_location]
        destination_location = random.choice(destinations)
        destination_lat, destination_long = BENGALURU_LOCATIONS[destination_location]

        destination_lat += np.random.uniform(-0.01, 0.01)
        destination_long += np.random.uniform(-0.01, 0.01)

        trip_urgency = np.random.choice(['Low', 'Medium', 'High'], p=[0.2, 0.5, 0.3])

        lat_diff = destination_lat - pickup_lat
        long_diff = destination_long - pickup_long
        trip_distance = np.sqrt((lat_diff * 111)**2 + (long_diff * 111 * np.cos(np.radians(13)))**2)

        ride_frequency = np.random.choice(['Daily', 'Weekly', 'Monthly', 'Occasional'])
        cancellation_tendency = np.random.beta(2, 8) * 100  # Lower cancellation tendency bias
        rating = np.random.uniform(3.5, 5.0)

        current_time = datetime.now()
        minutes_to_add = np.random.randint(0, 1440)  # Random time within next 24 hours
        request_time = current_time + timedelta(minutes=minutes_to_add)
        time_of_day = get_time_of_day(request_time.hour)

        at_event = np.random.choice([True, False], p=[0.2, 0.8])
        event_type = np.random.choice(['None', 'Concert', 'Sports', 'Festival', 'Conference']) if at_event else 'None'

        tip_amount = np.random.choice([0, 10, 20, 30, 50], p=[0.6, 0.2, 0.1, 0.05, 0.05])

        passengers_data.append({
            'passenger_id': passenger_id,
            'pickup_latitude': pickup_lat,
            'pickup_longitude': pickup_long,
            'pickup_location': pickup_location,
            'destination_latitude': destination_lat,
            'destination_longitude': destination_long,
            'destination_location': destination_location,
            'trip_urgency': trip_urgency,
            'estimated_trip_distance_km': round(trip_distance, 2),
            'ride_frequency': ride_frequency,
            'cancellation_tendency': round(cancellation_tendency, 2),
            'passenger_rating': round(rating, 2),
            'request_time': request_time,
            'time_of_day': time_of_day,
            'at_event': at_event,
            'event_type': event_type,
            'tip_amount': tip_amount
        })

    return pd.DataFrame(passengers_data)

def get_time_of_day(hour):
    """Convert hour to time of day category."""
    if 5 <= hour < 12:
        return 'Morning'
    elif 12 <= hour < 17:
        return 'Afternoon'
    elif 17 <= hour < 21:
        return 'Evening'
    else:
        return 'Night'

def calculate_edge_features(drivers_df, passengers_df, num_edges=500):
    """Generate edge features between drivers and passengers with correct fare handling."""
    edges_data = []

    for _ in range(num_edges):
        driver = drivers_df.iloc[np.random.randint(0, len(drivers_df))]
        passenger = passengers_df.iloc[np.random.randint(0, len(passengers_df))]

        driver_lat, driver_long = driver['latitude'], driver['longitude']
        passenger_lat, passenger_long = passenger['pickup_latitude'], passenger['pickup_longitude']

        lat_diff = driver_lat - passenger_lat
        long_diff = driver_long - passenger_long
        distance_km = np.sqrt((lat_diff * 111)**2 + (long_diff * 111 * np.cos(np.radians(13)))**2)

        # Traffic factor (higher during peak hours)
        traffic_factor = np.random.uniform(0.8, 2.0)
        if passenger['time_of_day'] in ['Morning', 'Evening']:
            traffic_factor *= np.random.uniform(1.2, 1.5)  # Heavier traffic during peak hours
        if passenger['at_event']:
            traffic_factor *= np.random.uniform(1.1, 1.3)  # Heavier traffic around events

        estimated_pickup_time_mins = (distance_km / 20) * 60
        actual_estimated_time = estimated_pickup_time_mins * traffic_factor

        base_fare = 30  # INR
        per_km_rate = 15  # INR
        base_trip_fare = base_fare + (passenger['estimated_trip_distance_km'] * per_km_rate)

        market_surge_factor = 1.0
        if passenger['time_of_day'] in ['Morning', 'Evening']:
            market_surge_factor += np.random.uniform(0, 0.5)  # Peak hours
        if passenger['at_event']:
            market_surge_factor += np.random.uniform(0, 1.0)  # Event surge

        surge_fee = base_trip_fare * (market_surge_factor - 1.0)

        passenger_tip = passenger['tip_amount']

        driver_multiplier_bonus = 0.0
        if driver['multiplier_active']:
            # The driver's multiplier bonus is calculated as a percentage of the base fare
            # This represents the incentive the driver gets for maintaining their coin status
            driver_multiplier_bonus = base_trip_fare * (driver['multiplier_value'] - 1.0)

        total_passenger_payment = base_trip_fare + surge_fee + passenger_tip

        total_driver_earnings = base_trip_fare + surge_fee + passenger_tip + driver_multiplier_bonus

        effective_multiplier = total_driver_earnings / base_trip_fare if base_trip_fare > 0 else 1.0

        compatibility_score = 100

        # Reduce score for longer pickup distances
        if distance_km > 5:
            compatibility_score -= min(50, distance_km * 5)

        trip_length_type = 'Long' if passenger['estimated_trip_distance_km'] > 5 else 'Short'
        if driver['preferred_trip_type'] != 'Both' and driver['preferred_trip_type'] != trip_length_type:
            compatibility_score -= 20

        if driver['preferred_shift'] != 'All Day' and driver['preferred_shift'] != passenger['time_of_day']:
            compatibility_score -= 15

        if market_surge_factor > 1.2:
            compatibility_score += driver['incentive_responsiveness'] * 20

        is_long_distance_pickup = distance_km > 5

        event_awareness_score = 0
        if passenger['at_event']:
            event_awareness_score = driver['event_sensitivity'] * 100

        if passenger_tip > 0:
            tip_boost = min(passenger_tip / 2, 25)
            compatibility_score += tip_boost

        # Higher traffic reduces compatibility (drivers don't like heavy traffic)
        if traffic_factor > 1.5:
            compatibility_score -= min(30, (traffic_factor - 1.5) * 60)

        # Check if trip is towards driver's home
        home_lat, home_long = driver['home_latitude'], driver['home_longitude']
        destination_lat, destination_long = passenger['destination_latitude'], passenger['destination_longitude']
        
        # Calculate vectors
        current_to_home = [home_lat - driver_lat, home_long - driver_long]
        current_to_dest = [destination_lat - driver_lat, destination_long - driver_long]
        
        # Normalize vectors
        current_to_home_mag = (current_to_home[0]**2 + current_to_home[1]**2)**0.5
        current_to_dest_mag = (current_to_dest[0]**2 + current_to_dest[1]**2)**0.5
        
        is_towards_home = False
        if current_to_home_mag > 0 and current_to_dest_mag > 0:
            current_to_home = [x/current_to_home_mag for x in current_to_home]
            current_to_dest = [x/current_to_dest_mag for x in current_to_dest]
            
            # Calculate dot product (cosine of angle)
            dot_product = current_to_home[0]*current_to_dest[0] + current_to_home[1]*current_to_dest[1]
            
            # If angle is less than 45 degrees (dot product > 0.7), destination is towards home
            if dot_product > 0.7:
                is_towards_home = True
                compatibility_score += 25  # Significant boost for trips towards home

        compatibility_score = max(0, min(100, compatibility_score))

        edges_data.append({
            'driver_id': driver['driver_id'],
            'passenger_id': passenger['passenger_id'],
            'distance_to_pickup_km': round(distance_km, 2),
            'estimated_pickup_time_mins': round(actual_estimated_time, 2),
            'traffic_factor': round(traffic_factor, 2),
            'base_fare': base_fare,
            'base_trip_fare': round(base_trip_fare, 2),
            'market_surge_factor': round(market_surge_factor, 2),
            'surge_fee': round(surge_fee, 2),
            'passenger_tip': passenger_tip,
            'driver_multiplier_bonus': round(driver_multiplier_bonus, 2),
            'total_passenger_payment': round(total_passenger_payment, 2),
            'total_driver_earnings': round(total_driver_earnings, 2),
            'effective_multiplier': round(effective_multiplier, 2),
            'compatibility_score': round(compatibility_score, 2),
            'is_long_distance_pickup': is_long_distance_pickup,
            'event_awareness_score': round(event_awareness_score, 2),
            'driver_location': driver['location'],
            'passenger_pickup_location': passenger['pickup_location'],
            'passenger_destination_location': passenger['destination_location'],
            'driver_coin_multiplier': driver['multiplier_value'] if driver['multiplier_active'] else 1.0,
            'is_towards_home': is_towards_home
        })

    return pd.DataFrame(edges_data)

def generate_heatmap_data():
    """Generate initial heatmap data for all locations."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    heatmap_data = []

    morning_peak = (datetime.now().replace(hour=8, minute=0, second=0, microsecond=0),
                   datetime.now().replace(hour=10, minute=0, second=0, microsecond=0))
    evening_peak = (datetime.now().replace(hour=17, minute=0, second=0, microsecond=0),
                   datetime.now().replace(hour=20, minute=0, second=0, microsecond=0))

    current_datetime = datetime.now()
    is_peak_time = ((morning_peak[0] <= current_datetime <= morning_peak[1]) or
                   (evening_peak[0] <= current_datetime <= evening_peak[1]))

    for location, coords in BENGALURU_LOCATIONS.items():
        center_lat, center_long = 12.9716, 77.5946  # Approximate center of Bengaluru
        distance_from_center = np.sqrt(((coords[0] - center_lat) * 111)**2 +
                                     ((coords[1] - center_long) * 111 * np.cos(np.radians(13)))**2)

        base_demand = max(10, 50 - distance_from_center * 5)

        time_factor = 2.0 if is_peak_time else 1.0

        random_factor = np.random.uniform(0.7, 1.3)

        ride_requests = int(base_demand * time_factor * random_factor)

        # Traffic intensity (higher in central areas, during peak hours, etc.)
        traffic_base = np.random.uniform(0.3, 0.6)  # Base traffic intensity
        
        # Higher traffic in central areas
        center_factor = max(0, 1 - (distance_from_center / 20))
        
        # Higher traffic during peak hours
        peak_factor = 0.3 if is_peak_time else 0.0
        
        # Generate traffic intensity (0-1 scale)
        traffic_intensity = min(0.95, traffic_base + center_factor * 0.3 + peak_factor)
        
        # Add some known heavy traffic areas
        if location in ['Silk Board', 'Marathahalli', 'KR Puram', 'Hebbal', 'Electronic City']:
            traffic_intensity = min(0.95, traffic_intensity + 0.2)
        
        # Add randomness to traffic
        traffic_intensity = min(0.95, max(0.1, traffic_intensity * np.random.uniform(0.8, 1.2)))

        latitude, longitude = coords

        heatmap_data.append({
            'location': location,
            'latitude': latitude,
            'longitude': longitude,
            'ride_requests': ride_requests,
            'traffic_intensity': round(traffic_intensity, 2),
            'timestamp': current_time
        })

    return pd.DataFrame(heatmap_data)

def save_data_to_csv():
    """Generate and save all datasets to CSV files."""
    print("Generating driver data...")
    drivers_df = generate_driver_data(num_drivers=1000)

    print("Generating passenger data...")
    passengers_df = generate_passenger_data(num_passengers=1500)

    print("Calculating edge features...")
    edges_df = calculate_edge_features(drivers_df, passengers_df, num_edges=5000)

    print("Generating initial heatmap data...")
    heatmap_df = generate_heatmap_data()

    drivers_df.to_csv("drivers_data.csv", index=False)
    passengers_df.to_csv("passengers_data.csv", index=False)
    edges_df.to_csv("matching_edges_data.csv", index=False)
    heatmap_df.to_csv("heatmap_data.csv", index=False)

    print("Data generation complete!")
    print(f"Generated {len(drivers_df)} driver records")
    print(f"Generated {len(passengers_df)} passenger records")
    print(f"Generated {len(edges_df)} matching edge records")
    print(f"Generated {len(heatmap_df)} heatmap location records")

    print("\nSample driver data:")
    print(drivers_df.head(2).to_string())

    print("\nSample passenger data:")
    print(passengers_df.head(2).to_string())

    print("\nSample edge data:")
    print(edges_df.head(2).to_string())

    print("\nSample heatmap data:")
    print(heatmap_df.head(2).to_string())

    return drivers_df, passengers_df, edges_df, heatmap_df

if __name__ == "__main__":
    save_data_to_csv()