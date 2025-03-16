from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from urllib.parse import quote_plus
from datetime import datetime, date, time, timedelta
import math
import random
import numpy as np
from typing import Dict, Any
from fastapi.responses import JSONResponse

# Create FastAPI app
app = FastAPI(
    title="Namma Yatri Incentive System API",
    description="API for managing the Namma Yatri driver incentive system",
    version="1.0.0"
)

# Database connection
# Update these with your MySQL connection details
DB_USER = "root"
DB_PASSWORD = quote_plus("akash561@2910")  # URL encode the password
DB_HOST = "localhost"
DB_PORT = "3306"  # Explicitly specify the port
DB_NAME = "namma_yatri"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Location(Base):
    __tablename__ = "locations"
    
    location_id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

class Driver(Base):
    __tablename__ = "drivers"
    
    driver_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100))
    experience_years = Column(Integer)
    rating = Column(Float)
    home_location_id = Column(Integer, ForeignKey("locations.location_id"))
    current_location_id = Column(Integer, ForeignKey("locations.location_id"))
    daily_avg_distance_km = Column(Float)
    target_distance_60_percent = Column(Float)
    target_distance_100_percent = Column(Float)
    ride_acceptance_rate = Column(Float)
    cancellation_rate = Column(Float)
    consecutive_target_days = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    
    home_location = relationship("Location", foreign_keys=[home_location_id])
    current_location = relationship("Location", foreign_keys=[current_location_id])

class DriverDailyStat(Base):
    __tablename__ = "driver_daily_stats"
    
    stat_id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(String(50), ForeignKey("drivers.driver_id"))
    date = Column(Date, default=date.today)
    distance_covered_today = Column(Float, default=0)
    coins_earned = Column(Integer, default=0)
    hours_active = Column(Float, default=0)
    consecutive_trips = Column(Integer, default=0)
    multiplier_active = Column(Boolean, default=False)
    multiplier_value = Column(Float, default=1.0)
    multiplier_expires_at = Column(DateTime, nullable=True)
    go_home_mode_active = Column(Boolean, default=False)
    
    driver = relationship("Driver")

class Trip(Base):
    __tablename__ = "trips"
    
    trip_id = Column(String(50), primary_key=True, index=True)
    driver_id = Column(String(50), ForeignKey("drivers.driver_id"))
    pickup_location_id = Column(Integer, ForeignKey("locations.location_id"))
    destination_location_id = Column(Integer, ForeignKey("locations.location_id"))
    estimated_trip_distance_km = Column(Float)
    distance_to_pickup_km = Column(Float)
    traffic_factor = Column(Float)
    time_of_day = Column(String(20))
    at_event = Column(Boolean, default=False)
    event_type = Column(String(50), nullable=True)
    base_fare = Column(Float)
    base_trip_fare = Column(Float)
    multiplier_applied = Column(Float, default=1.0)
    final_fare = Column(Float)
    trip_duration_minutes = Column(Integer)
    trip_date = Column(Date, default=date.today)
    trip_time = Column(String(10))
    coins_earned = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    
    driver = relationship("Driver")
    pickup_location = relationship("Location", foreign_keys=[pickup_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])

class Cancellation(Base):
    __tablename__ = "cancellations"
    
    cancellation_id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(String(50), ForeignKey("drivers.driver_id"))
    trip_id = Column(String(50))
    time_since_accept_seconds = Column(Integer)
    reason = Column(String(100))
    penalty_coins = Column(Integer, default=0)
    cooldown_minutes = Column(Integer, default=0)
    cooldown_until = Column(DateTime, nullable=True)
    cancellation_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.now)
    
    driver = relationship("Driver")

class TrafficData(Base):
    __tablename__ = "traffic_data"
    
    traffic_id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.location_id"))
    time_of_day = Column(String(20))
    traffic_intensity = Column(Float)
    ride_requests = Column(Integer)
    date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.now)
    
    location = relationship("Location")

# Pydantic Models for API
class LocationBase(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    
class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    location_id: int
    
    class Config:
        orm_mode = True

class DriverBase(BaseModel):
    name: str
    experience_years: int
    rating: float
    daily_avg_distance_km: float
    ride_acceptance_rate: float
    cancellation_rate: float
    consecutive_target_days: int

class DriverCreate(DriverBase):
    driver_id: str
    home_location_id: int
    current_location_id: int

class DriverUpdate(BaseModel):
    name: Optional[str] = None
    experience_years: Optional[int] = None
    rating: Optional[float] = None
    home_location_id: Optional[int] = None
    current_location_id: Optional[int] = None
    daily_avg_distance_km: Optional[float] = None
    ride_acceptance_rate: Optional[float] = None
    cancellation_rate: Optional[float] = None
    consecutive_target_days: Optional[int] = None

class DriverResponse(DriverBase):
    driver_id: str
    home_location: LocationResponse
    current_location: LocationResponse
    target_distance_60_percent: float
    target_distance_100_percent: float
    created_at: datetime
    
    class Config:
        orm_mode = True

class DriverDailyStatBase(BaseModel):
    distance_covered_today: float = 0
    coins_earned: int = 0
    hours_active: float = 0
    consecutive_trips: int = 0
    multiplier_active: bool = False
    multiplier_value: float = 1.0
    go_home_mode_active: bool = False

class DriverDailyStatCreate(DriverDailyStatBase):
    driver_id: str
    stat_date: date = Field(default_factory=date.today)

class DriverDailyStatResponse(DriverDailyStatBase):
    stat_id: int
    driver_id: str
    date: date
    multiplier_expires_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class TripBase(BaseModel):
    driver_id: str
    pickup_location_id: int
    destination_location_id: int
    estimated_trip_distance_km: float
    distance_to_pickup_km: float
    traffic_factor: float
    time_of_day: str
    at_event: bool = False
    event_type: Optional[str] = None
    base_fare: float
    base_trip_fare: float
    trip_duration_minutes: int

class TripCreate(TripBase):
    trip_id: str

class TripResponse(TripBase):
    trip_id: str
    multiplier_applied: float
    final_fare: float
    trip_date: date
    trip_time: str
    coins_earned: int
    created_at: datetime
    
    class Config:
        orm_mode = True
    
    @classmethod
    def from_orm(cls, obj):
        # Create a copy of the object to avoid modifying the original
        obj_dict = {col.name: getattr(obj, col.name) for col in obj.__table__.columns}
        
        # Convert timedelta to string if needed
        if isinstance(obj_dict['trip_time'], timedelta):
            seconds = int(obj_dict['trip_time'].total_seconds())
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            obj_dict['trip_time'] = f"{hours:02}:{minutes:02}:{seconds:02}"
        
        return cls(**obj_dict)

class CancellationBase(BaseModel):
    driver_id: str
    trip_id: str
    time_since_accept_seconds: int
    reason: str

class CancellationCreate(CancellationBase):
    pass

class CancellationResponse(CancellationBase):
    cancellation_id: int
    penalty_coins: int
    cooldown_minutes: int
    cooldown_until: Optional[datetime] = None
    cancellation_date: date
    created_at: datetime
    
    class Config:
        orm_mode = True

class TrafficDataBase(BaseModel):
    location_id: int
    time_of_day: str
    traffic_intensity: float
    ride_requests: int

class TrafficDataCreate(TrafficDataBase):
    pass

class TrafficDataResponse(TrafficDataBase):
    traffic_id: int
    date: date
    created_at: datetime
    
    class Config:
        orm_mode = True

class ActivateMultiplierResponse(BaseModel):
    success: bool
    message: str
    multiplier_value: float = 1.0
    multiplier_active: bool = False
    multiplier_expires_at: Optional[datetime] = None

class ActivateGoHomeResponse(BaseModel):
    success: bool
    message: str
    go_home_mode_active: bool = True

class TripRecommendation(BaseModel):
    trip_id: str
    pickup_location: str
    destination_location: str
    score: float
    brings_closer_to_home: bool
    distance_to_pickup_km: float
    trip_distance_km: float
    estimated_fare: float

class GoHomeRecommendationsResponse(BaseModel):
    success: bool
    message: str
    recommendations: List[TripRecommendation] = []

class ProcessTripResponse(BaseModel):
    driver_id: str
    trip_id: str
    success: bool
    coins_earned: int
    total_distance: float
    distance_covered_today: float
    new_coins_balance: int
    streak_bonus_earned: int = 0
    multiplier_applied: float = 1.0
    final_fare: float

class ProcessCancellationResponse(BaseModel):
    success: bool
    message: str
    penalty_coins: int = 0
    new_coins_balance: int
    cooldown_minutes: int = 0
    cooldown_until: Optional[datetime] = None

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Core business logic
class NammaYatriIncentiveSystem:
    def __init__(self, db: Session):
        self.db = db
        # Coin system parameters
        self.coin_system = {
            'daily_milestone_60_percent': 50,  # Coins for 60% of daily target
            'daily_milestone_100_percent': 100,  # Coins for 100% of daily target
            'traffic_max_coins': 20,  # Maximum coins from traffic
            'consecutive_trip_bonus': 5,  # Bonus for consecutive trips
            'streak_thresholds': [3, 5, 10],  # Consecutive trips needed for streak bonus
            'streak_bonuses': [10, 15, 25]  # Coins awarded for each streak level
        }
        
        # Traffic component weights
        self.traffic_weights = {
            'base_weight': 0.5,
            'time_of_day_weight': 0.3,
            'historical_weight': 0.2
        }
        
        # Cancellation penalty system
        self.cancellation_penalties = {
            'legitimate_reasons': ['passenger_no_show', 'passenger_request', 'vehicle_damage', 'emergency'],
            'cooldown_minutes': 15,  # Cooldown for legitimate cancellations
            'standard_penalty': 10,  # Default coin penalty
            'time_thresholds': [60, 180, 300],  # Seconds since acceptance
            'penalty_multipliers': [0.5, 1.0, 1.5]  # Penalty multipliers based on time
        }
        
        # Forgiveness buffer for reliable drivers
        self.forgiveness_buffer = {
            'threshold_acceptance_rate': 90,  # High acceptance rate
            'threshold_cancellation_rate': 5,  # Low cancellation rate
            'buffer_coins': 10  # Coins protected from penalties
        }
    
    def calculate_target_distances(self, driver_avg_distance_km: float):
        """Calculate target distances for a driver based on their historical average."""
        target_tier1_km = driver_avg_distance_km * 0.6  # 60% of daily average
        target_tier2_km = driver_avg_distance_km  # 100% of daily average
        
        return {
            'target_distance_60_percent': round(target_tier1_km, 2),
            'target_distance_100_percent': round(target_tier2_km, 2)
        }
    
    def get_driver_daily_stats(self, driver_id: str, stats_date: date = None):
        """Get or create driver's daily stats."""
        if stats_date is None:
            stats_date = date.today()
            
        stats = self.db.query(DriverDailyStat).filter(
            DriverDailyStat.driver_id == driver_id,
            DriverDailyStat.date == stats_date
        ).first()
        
        if not stats:
            # Create new daily stats for today
            driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
            if not driver:
                raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
                
            stats = DriverDailyStat(
                driver_id=driver_id,
                date=stats_date,
                distance_covered_today=0,
                coins_earned=0,
                hours_active=0,
                consecutive_trips=0,
                multiplier_active=False,
                multiplier_value=1.0,
                go_home_mode_active=False
            )
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(stats)
            
        return stats
    
    def _get_traffic_weight_for_time(self, time_of_day: str):
        """Return traffic weight based on time of day."""
        if time_of_day == 'Morning':
            return 0.8  # Morning rush
        elif time_of_day == 'Evening':
            return 0.9  # Evening rush (highest)
        elif time_of_day == 'Afternoon':
            return 0.5  # Moderate
        elif time_of_day == 'Night':
            return 0.3  # Light traffic
        else:
            return 0.5  # Default
    
    def _calculate_coins_for_trip(self, driver, trip_data):
        """Calculate coins earned for a trip based on distance, traffic, and other factors."""
        # Base coins based on percentage of daily target distance
        base_daily_distance = driver.daily_avg_distance_km
        trip_distance = trip_data.estimated_trip_distance_km
        distance_percentage = (trip_distance / base_daily_distance) * 100
        
        # Base coins: 1 coin per 1% of daily target
        base_coins = int(distance_percentage * 0.55)
        
        # Traffic component - extra coins for heavy traffic
        traffic_factor = trip_data.traffic_factor
        traffic_time_of_day = self._get_traffic_weight_for_time(trip_data.time_of_day)
        
        # Traffic coins calculation
        traffic_coins = (traffic_factor * self.traffic_weights['base_weight'] + 
                         traffic_time_of_day * self.traffic_weights['time_of_day_weight']) * 10
        
        # Apply cap to traffic coins
        traffic_coins = min(traffic_coins, self.coin_system['traffic_max_coins'])
        
        # Event bonus
        event_bonus = 0
        if trip_data.at_event:
            event_type = trip_data.event_type or 'Generic'
            event_bonus = 5  # Default bonus
            
            # Higher bonus for special events
            if event_type in ['Concert', 'Sports']:
                event_bonus = 10
            elif event_type == 'Festival':
                event_bonus = 20
        
        # Total coins for this trip
        total_coins = base_coins + traffic_coins + event_bonus
        
        # Round to nearest whole number
        return round(total_coins)
    
    def _check_for_streak_bonus(self, consecutive_trips: int):
        """Check if driver qualifies for a streak bonus based on consecutive trips."""
        # Check each streak threshold (highest first)
        for i in range(len(self.coin_system['streak_thresholds']) - 1, -1, -1):
            threshold = self.coin_system['streak_thresholds'][i]
            if consecutive_trips == threshold:  # Exact match for streak
                return self.coin_system['streak_bonuses'][i]
        
        return 0  # No streak bonus
    
    def process_new_trip(self, driver_id: str, trip_data: TripCreate):
        """Process a new completed trip and update driver incentives."""
        # Get driver and daily stats
        driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
            
        driver_stats = self.get_driver_daily_stats(driver_id)
        
        # Calculate pickup + trip distance
        total_distance = trip_data.estimated_trip_distance_km + trip_data.distance_to_pickup_km
        
        # Update driver's distance covered today
        driver_stats.distance_covered_today += total_distance
        
        # Calculate coins earned from this trip
        coins_earned = self._calculate_coins_for_trip(driver, trip_data)
        
        # Determine if multiplier applies
        multiplier_applied = driver_stats.multiplier_value if driver_stats.multiplier_active else 1.0
        
        # Calculate final fare
        final_fare = trip_data.base_trip_fare * multiplier_applied
        
        # Create new trip record
        new_trip = Trip(
            trip_id=trip_data.trip_id,
            driver_id=driver_id,
            pickup_location_id=trip_data.pickup_location_id,
            destination_location_id=trip_data.destination_location_id,
            estimated_trip_distance_km=trip_data.estimated_trip_distance_km,
            distance_to_pickup_km=trip_data.distance_to_pickup_km,
            traffic_factor=trip_data.traffic_factor,
            time_of_day=trip_data.time_of_day,
            at_event=trip_data.at_event,
            event_type=trip_data.event_type,
            base_fare=trip_data.base_fare,
            base_trip_fare=trip_data.base_trip_fare,
            multiplier_applied=multiplier_applied,
            final_fare=final_fare,
            trip_duration_minutes=trip_data.trip_duration_minutes,
            trip_date=date.today(),
            trip_time=datetime.now().strftime('%H:%M:%S'),
            coins_earned=coins_earned
        )
        
        # Update driver stats
        driver_stats.consecutive_trips += 1
        driver_stats.coins_earned += coins_earned
        driver_stats.hours_active += (trip_data.trip_duration_minutes / 60)
        
        # Check for streak bonus
        streak_bonus = self._check_for_streak_bonus(driver_stats.consecutive_trips)
        if streak_bonus > 0:
            driver_stats.coins_earned += streak_bonus
        
        # Update driver's current location
        destination_loc = self.db.query(Location).filter(
            Location.location_id == trip_data.destination_location_id
        ).first()
        
        driver.current_location_id = trip_data.destination_location_id
        
        # Save all changes
        self.db.add(new_trip)
        self.db.commit()
        self.db.refresh(driver_stats)
        self.db.refresh(new_trip)
        
        return {
            "driver_id": driver_id,
            "trip_id": trip_data.trip_id,
            "success": True,
            "coins_earned": coins_earned,
            "total_distance": total_distance,
            "distance_covered_today": driver_stats.distance_covered_today,
            "new_coins_balance": driver_stats.coins_earned,
            "streak_bonus_earned": streak_bonus,
            "multiplier_applied": multiplier_applied,
            "final_fare": final_fare
        }
    
    def activate_multiplier(self, driver_id: str):
        """Activate a driver's multiplier if they have enough coins."""
        # Get driver and daily stats
        driver_stats = self.get_driver_daily_stats(driver_id)
        
        if driver_stats.multiplier_active:
            return {
                'success': False,
                'message': "Multiplier already active."
            }
        
        # Check if they have enough coins for the 1.25x multiplier (50 coins)
        if driver_stats.coins_earned >= self.coin_system['daily_milestone_60_percent']:
            # Determine multiplier value based on coins
            if driver_stats.coins_earned >= self.coin_system['daily_milestone_100_percent']:
                multiplier_value = 1.5  # 100+ coins
            else:
                multiplier_value = 1.25  # 50-99 coins
                
            # Set expiration time (4 hours from now)
            expires_at = datetime.now() + timedelta(hours=4)
            
            # Update driver stats
            driver_stats.multiplier_active = True
            driver_stats.multiplier_value = multiplier_value
            driver_stats.multiplier_expires_at = expires_at
            
            self.db.commit()
            self.db.refresh(driver_stats)
            
            return {
                'success': True,
                'message': f"{multiplier_value}x multiplier activated for 4 hours!",
                'multiplier_value': multiplier_value,
                'multiplier_expires_at': expires_at,
                'multiplier_active': True
            }
        else:
            return {
                'success': False,
                'message': f"Not enough coins. Need {self.coin_system['daily_milestone_60_percent']} coins for multiplier activation."
            }
    
    def activate_go_home_mode(self, driver_id: str):
        """Activate go-home mode for a driver."""
        driver_stats = self.get_driver_daily_stats(driver_id)
        driver_stats.go_home_mode_active = True
        
        self.db.commit()
        self.db.refresh(driver_stats)
        
        return {
            'success': True,
            'message': "Go-Home mode activated successfully.",
            'go_home_mode_active': True
        }
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the distance between two lat/long points using Haversine formula."""
        # Convert latitude and longitude to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of Earth in kilometers
        
        return c * r
    
    def find_optimal_trips_for_go_home(self, driver_id: str):
        """Find optimal trips for a driver in go-home mode."""
        # Get driver info
        driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
            
        driver_stats = self.get_driver_daily_stats(driver_id)
        
        if not driver_stats.go_home_mode_active:
            return {
                'success': False,
                'message': 'Driver is not in go-home mode'
            }
        
        # Get driver home and current location
        home_loc = self.db.query(Location).filter(
            Location.location_id == driver.home_location_id
        ).first()
        
        current_loc = self.db.query(Location).filter(
            Location.location_id == driver.current_location_id
        ).first()
        
        if not home_loc or not current_loc:
            return {
                'success': False,
                'message': 'Home or current location not found'
            }
        
        # Generate sample trips (in a real scenario, these would come from real-time data)
        # For demo, we'll generate 3 potential trips
        all_locations = self.db.query(Location).all()
        potential_trips = []
        
        # Calculate current distance to home
        current_distance_to_home = self._calculate_distance(
            current_loc.latitude, current_loc.longitude,
            home_loc.latitude, home_loc.longitude
        )
        
        # Generate potential trips (sample implementation)
        for idx, loc in enumerate(random.sample(all_locations, min(5, len(all_locations)))):
            # Skip if same as current location
            if loc.location_id == driver.current_location_id:
                continue
                
            # Calculate if trip brings driver closer to home
            destination_distance_to_home = self._calculate_distance(
                loc.latitude, loc.longitude,
                home_loc.latitude, home_loc.longitude
            )
            
            brings_closer = destination_distance_to_home < current_distance_to_home
            
            # Random trip properties
            distance_to_pickup = round(random.uniform(0.5, 2.5), 1)
            trip_distance = round(random.uniform(3.0, 15.0), 1)
            
            # Calculate basic score (simple rule-based for demo)
            base_score = random.uniform(30, 90)
            
            # Proximity to home adds score
            if brings_closer:
                distance_improvement = current_distance_to_home - destination_distance_to_home
                base_score += min(40, distance_improvement * 10)
            else:
                # Penalty for going away from home
                distance_penalty = destination_distance_to_home - current_distance_to_home
                base_score -= min(20, distance_penalty * 5)
            
            # Ensure score is between 0-100
            score = max(0, min(100, base_score))
            
            # Trip fare calculation
            base_fare = 30 + (trip_distance * 15)
            
            potential_trips.append({
                'trip_id': f'POTENTIAL-{idx+1}',
                'pickup_location': current_loc.location_name,
                'destination_location': loc.location_name,
                'score': round(score, 1),
                'brings_closer_to_home': brings_closer,
                'distance_to_pickup_km': distance_to_pickup,
                'trip_distance_km': trip_distance,
                'estimated_fare': round(base_fare * driver_stats.multiplier_value, 2)
            })
        
        # Sort by score (highest first)
        potential_trips.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'success': True,
            'message': f"Found {len(potential_trips)} potential trips for go-home",
            'recommendations': potential_trips
        }
    
    def process_cancellation(self, driver_id: str, cancellation_data: CancellationCreate):
        """Process a cancellation and determine any penalties."""
        # Get driver info
        driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
            
        driver_stats = self.get_driver_daily_stats(driver_id)
        
        # Check if reason is legitimate
        is_legitimate = cancellation_data.reason in self.cancellation_penalties['legitimate_reasons']
        
        # Determine time-based multiplier
        time_multiplier = 0.5  # Default
        for i, threshold in enumerate(self.cancellation_penalties['time_thresholds']):
            if cancellation_data.time_since_accept_seconds <= threshold:
                time_multiplier = self.cancellation_penalties['penalty_multipliers'][i]
                break
        
        # Calculate initial penalty
        base_penalty = self.cancellation_penalties['standard_penalty']
        penalty = base_penalty * time_multiplier
        
        # Apply forgiveness buffer for reliable drivers
        buffer_applied = 0
        if (driver.ride_acceptance_rate >= self.forgiveness_buffer['threshold_acceptance_rate'] and
            driver.cancellation_rate <= self.forgiveness_buffer['threshold_cancellation_rate']):
            # Driver qualifies for forgiveness buffer
            available_buffer = self.forgiveness_buffer['buffer_coins']
            buffer_applied = min(available_buffer, penalty)
            penalty -= buffer_applied
        
        # Round penalty to nearest whole number
        penalty = round(penalty)
        
        # Create cancellation record
        new_cancellation = Cancellation(
            driver_id=driver_id,
            trip_id=cancellation_data.trip_id,
            time_since_accept_seconds=cancellation_data.time_since_accept_seconds,
            reason=cancellation_data.reason,
            penalty_coins=penalty if not is_legitimate else 0
        )
        
        # Apply the penalty or set cooldown
        result = {}
        
        if is_legitimate:
            # For legitimate reasons, apply cooldown but no coin penalty
            cooldown_minutes = self.cancellation_penalties['cooldown_minutes']
            cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
            
            new_cancellation.cooldown_minutes = cooldown_minutes
            new_cancellation.cooldown_until = cooldown_until
            
            result = {
                'success': True,
                'message': f"Legitimate cancellation reason. No coin penalty, but driver is on cooldown for {cooldown_minutes} minutes.",
                'penalty_coins': 0,
                'new_coins_balance': driver_stats.coins_earned,
                'cooldown_minutes': cooldown_minutes,
                'cooldown_until': cooldown_until
            }
        else:
            # For non-legitimate reasons, deduct coins
            if penalty > 0:
                driver_stats.coins_earned = max(0, driver_stats.coins_earned - penalty)
                result = {
                    'success': True,
                    'penalty_coins': penalty,
                    'new_coins_balance': driver_stats.coins_earned,
                    'message': f"Coin penalty applied: {penalty} coins deducted"
                }
            else:
                result = {
                    'success': True,
                    'penalty_coins': 0,
                    'new_coins_balance': driver_stats.coins_earned,
                    'message': "No penalty applied due to forgiveness buffer."
                }
        
        # Save changes
        self.db.add(new_cancellation)
        self.db.commit()
        self.db.refresh(driver_stats)
        self.db.refresh(new_cancellation)
        
        return result

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to Namma Yatri Incentive System API"}

# Location endpoints
@app.get("/locations/", response_model=List[LocationResponse])
async def get_locations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    locations = db.query(Location).offset(skip).limit(limit).all()
    return locations

@app.post("/locations/", response_model=LocationResponse)
async def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    new_location = Location(**location.dict())
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return new_location

@app.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(location_id: int, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.location_id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

# Driver endpoints
@app.get("/drivers/", response_model=List[DriverResponse])
async def get_drivers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    drivers = db.query(Driver).offset(skip).limit(limit).all()
    return drivers

@app.post("/drivers/", response_model=DriverResponse)
async def create_driver(driver: DriverCreate, db: Session = Depends(get_db)):
    # Check if home and current locations exist
    home_loc = db.query(Location).filter(Location.location_id == driver.home_location_id).first()
    current_loc = db.query(Location).filter(Location.location_id == driver.current_location_id).first()
    
    if not home_loc or not current_loc:
        raise HTTPException(status_code=400, detail="Invalid location IDs")
    
    # Calculate target distances
    system = NammaYatriIncentiveSystem(db)
    targets = system.calculate_target_distances(driver.daily_avg_distance_km)
    
    # Create driver with calculated targets
    driver_data = driver.dict()
    driver_data.update(targets)
    new_driver = Driver(**driver_data)
    
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    
    # Create initial daily stats
    DriverDailyStat(
        driver_id=new_driver.driver_id,
        date=date.today()
    )
    
    db.add(new_driver)
    db.commit()
    
    return new_driver

@app.get("/drivers/{driver_id}", response_model=DriverResponse)
async def get_driver(driver_id: str, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@app.put("/drivers/{driver_id}", response_model=DriverResponse)
async def update_driver(driver_id: str, driver_update: DriverUpdate, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Update driver fields
    update_data = driver_update.dict(exclude_unset=True)
    
    # Check if daily_avg_distance_km changed, if so recalculate targets
    recalc_targets = False
    if 'daily_avg_distance_km' in update_data and update_data['daily_avg_distance_km'] != driver.daily_avg_distance_km:
        recalc_targets = True
    
    # Update fields
    for key, value in update_data.items():
        setattr(driver, key, value)
    
    # Recalculate targets if needed
    if recalc_targets:
        system = NammaYatriIncentiveSystem(db)
        targets = system.calculate_target_distances(driver.daily_avg_distance_km)
        driver.target_distance_60_percent = targets['target_distance_60_percent']
        driver.target_distance_100_percent = targets['target_distance_100_percent']
    
    db.commit()
    db.refresh(driver)
    return driver


@app.get("/drivers/{driver_id}/daily-stats", response_model=DriverDailyStatResponse)
async def get_driver_daily_stats(
    driver_id: str, 
    stats_date: date = Query(None, description="Date for stats (defaults to today)"),
    db: Session = Depends(get_db)
):
    system = NammaYatriIncentiveSystem(db)
    stats = system.get_driver_daily_stats(driver_id, stats_date)
    if not stats:
        raise HTTPException(status_code=404, detail=f"No daily stats found for driver {driver_id}")
    return stats

# Trip endpoints
@app.post("/trips/", response_model=TripResponse)
async def create_trip(trip: TripCreate, db: Session = Depends(get_db)):
    try:
        # Check if driver exists
        driver = db.query(Driver).filter(Driver.driver_id == trip.driver_id).first()
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
            
        # Check if locations exist
        pickup_loc = db.query(Location).filter(Location.location_id == trip.pickup_location_id).first()
        if not pickup_loc:
            raise HTTPException(status_code=400, detail=f"Pickup location ID {trip.pickup_location_id} not found")
            
        dest_loc = db.query(Location).filter(Location.location_id == trip.destination_location_id).first()
        if not dest_loc:
            raise HTTPException(status_code=400, detail=f"Destination location ID {trip.destination_location_id} not found")
        
        trip_dict = trip.dict()
        
        # Fix "NULL" event_type
        if trip_dict.get('event_type') == "NULL":
            trip_dict['event_type'] = None
        
        new_trip = Trip(**trip_dict)
        
        # IMPORTANT: Store trip_time as a string
        new_trip.trip_date = date.today()
        new_trip.trip_time = datetime.now().strftime('%H:%M:%S')  # Store as string
        
        new_trip.multiplier_applied = 1.0  # Default value
        new_trip.final_fare = trip.base_trip_fare  # Default before processing
        new_trip.coins_earned = 0  # Will be set during processing
        
        db.add(new_trip)
        db.commit()
        db.refresh(new_trip)
        
        # Manually create the response dictionary
        response_data = {
            "trip_id": new_trip.trip_id,
            "driver_id": new_trip.driver_id,
            "pickup_location_id": new_trip.pickup_location_id,
            "destination_location_id": new_trip.destination_location_id,
            "estimated_trip_distance_km": new_trip.estimated_trip_distance_km,
            "distance_to_pickup_km": new_trip.distance_to_pickup_km,
            "traffic_factor": new_trip.traffic_factor,
            "time_of_day": new_trip.time_of_day,
            "at_event": new_trip.at_event,
            "event_type": new_trip.event_type,
            "base_fare": new_trip.base_fare,
            "base_trip_fare": new_trip.base_trip_fare,
            "trip_duration_minutes": new_trip.trip_duration_minutes,
            "multiplier_applied": new_trip.multiplier_applied,
            "final_fare": new_trip.final_fare,
            "trip_date": new_trip.trip_date.isoformat(),
            "trip_time": new_trip.trip_time if isinstance(new_trip.trip_time, str) else datetime.now().strftime('%H:%M:%S'),
            "coins_earned": new_trip.coins_earned,
            "created_at": new_trip.created_at.isoformat()
        }
        
        return JSONResponse(content=response_data)
    except Exception as e:
        import traceback
        error_detail = f"Error creating trip: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/trips/test", response_model=None)
async def create_test_trip(trip: dict, db: Session = Depends(get_db)):
    """A simpler test endpoint without Pydantic validation"""
    try:
        # Create new trip record manually
        new_trip = Trip(
            trip_id=trip.get("trip_id", f"TEST-{int(time.time())}"),
            driver_id=trip.get("driver_id"),
            pickup_location_id=trip.get("pickup_location_id"),
            destination_location_id=trip.get("destination_location_id"),
            estimated_trip_distance_km=trip.get("estimated_trip_distance_km"),
            distance_to_pickup_km=trip.get("distance_to_pickup_km"),
            traffic_factor=trip.get("traffic_factor"),
            time_of_day=trip.get("time_of_day"),
            at_event=trip.get("at_event", False),
            event_type=None if trip.get("event_type") == "NULL" else trip.get("event_type"),
            base_fare=trip.get("base_fare"),
            base_trip_fare=trip.get("base_trip_fare"),
            trip_duration_minutes=trip.get("trip_duration_minutes"),
            trip_date=date.today(),
            trip_time=datetime.now().strftime('%H:%M:%S'),
            multiplier_applied=1.0,
            final_fare=trip.get("base_trip_fare", 0),
            coins_earned=0
        )
        
        db.add(new_trip)
        db.commit()
        
        return {"message": "Trip created successfully", "trip_id": new_trip.trip_id}
    except Exception as e:
        import traceback
        error_detail = f"Error creating trip: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        return {"error": str(e)}

# Add this helper function near the top of your file
def convert_trip_time_to_string(trip):
    """Convert trip_time to string if it's a timedelta"""
    if isinstance(trip.trip_time, timedelta):
        seconds = int(trip.trip_time.total_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        trip.trip_time = f"{hours:02}:{minutes:02}:{seconds:02}"
    return trip


# Update the get_trips endpoint
@app.get("/trips/", response_model=List[TripResponse])
async def get_trips(
    driver_id: str = None,
    start_date: date = None,
    end_date: date = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(Trip)
    
    if driver_id:
        query = query.filter(Trip.driver_id == driver_id)
    
    if start_date:
        query = query.filter(Trip.trip_date >= start_date)
    
    if end_date:
        query = query.filter(Trip.trip_date <= end_date)
    
    trips = query.order_by(Trip.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert all trip_time fields to strings
    for trip in trips:
        convert_trip_time_to_string(trip)
    
    return trips

# Update the get_trip endpoint
@app.get("/trips/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Convert trip_time to string if needed
    convert_trip_time_to_string(trip)
    
    return trip


@app.post("/trips/{trip_id}/process", response_model=ProcessTripResponse)
async def process_trip(trip_id: str, db: Session = Depends(get_db)):
    try:
        # Get trip data
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")
        
        # Check if trip has already been processed (coins already earned)
        if trip.coins_earned > 0:
            # Trip already processed, return existing data
            driver_stats = db.query(DriverDailyStat).filter(
                DriverDailyStat.driver_id == trip.driver_id,
                DriverDailyStat.date == trip.trip_date
            ).first()
            
            return {
                "driver_id": trip.driver_id,
                "trip_id": trip.trip_id,
                "success": True,
                "coins_earned": trip.coins_earned,
                "total_distance": trip.estimated_trip_distance_km + trip.distance_to_pickup_km,
                "distance_covered_today": driver_stats.distance_covered_today if driver_stats else 0,
                "new_coins_balance": driver_stats.coins_earned if driver_stats else 0,
                "streak_bonus_earned": 0,
                "multiplier_applied": trip.multiplier_applied,
                "final_fare": trip.final_fare
            }
        
        # Initialize the incentive system
        system = NammaYatriIncentiveSystem(db)
        
        # Get driver and daily stats
        driver = db.query(Driver).filter(Driver.driver_id == trip.driver_id).first()
        if not driver:
            raise HTTPException(status_code=404, detail=f"Driver {trip.driver_id} not found")
            
        driver_stats = system.get_driver_daily_stats(trip.driver_id)
        
        # Calculate total distance (trip + distance to pickup)
        trip_distance = trip.estimated_trip_distance_km
        pickup_distance = trip.distance_to_pickup_km
        total_distance = trip_distance + pickup_distance
        
        # Print values for debugging
        print(f"DEBUG - Trip processing: trip={trip_id}, driver={trip.driver_id}")
        print(f"DEBUG - Before update: distance_covered={driver_stats.distance_covered_today}")
        print(f"DEBUG - Trip distance: trip={trip_distance}, pickup={pickup_distance}, total={total_distance}")
        
        # Update driver's distance covered today
        driver_stats.distance_covered_today += total_distance
        
        print(f"DEBUG - After update: distance_covered={driver_stats.distance_covered_today}")
        
        # Calculate coins earned from this trip
        coins_earned = system._calculate_coins_for_trip(driver, trip)
        
        # Determine if multiplier applies
        multiplier_applied = driver_stats.multiplier_value if driver_stats.multiplier_active else 1.0
        
        # Calculate final fare
        final_fare = trip.base_trip_fare * multiplier_applied
        
        # Update the existing trip record with the calculated values
        trip.multiplier_applied = multiplier_applied
        trip.final_fare = final_fare
        trip.coins_earned = coins_earned
        
        # Update driver stats
        driver_stats.consecutive_trips += 1
        driver_stats.coins_earned += coins_earned
        driver_stats.hours_active += (trip.trip_duration_minutes / 60)
        
        # Check for streak bonus
        streak_bonus = system._check_for_streak_bonus(driver_stats.consecutive_trips)
        if streak_bonus > 0:
            driver_stats.coins_earned += streak_bonus
        
        # Update driver's current location
        driver.current_location_id = trip.destination_location_id
        
        # Save all changes
        db.commit()
        db.refresh(driver_stats)
        
        # Return processed trip details
        return {
            "driver_id": trip.driver_id,
            "trip_id": trip.trip_id,
            "success": True,
            "coins_earned": coins_earned,
            "total_distance": total_distance,
            "distance_covered_today": driver_stats.distance_covered_today,
            "new_coins_balance": driver_stats.coins_earned,
            "streak_bonus_earned": streak_bonus,
            "multiplier_applied": multiplier_applied,
            "final_fare": final_fare
        }
    except Exception as e:
        import traceback
        error_detail = f"Error processing trip: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=str(e))
# Cancellation endpoints
@app.post("/cancellations/", response_model=CancellationResponse)
async def create_cancellation(cancellation: CancellationCreate, db: Session = Depends(get_db)):
    # Check if driver exists
    driver = db.query(Driver).filter(Driver.driver_id == cancellation.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Create new cancellation record without processing penalties
    new_cancellation = Cancellation(**cancellation.dict())
    new_cancellation.cancellation_date = date.today()
    
    db.add(new_cancellation)
    db.commit()
    db.refresh(new_cancellation)
    
    return new_cancellation

@app.post("/cancellations/{cancellation_id}/process", response_model=ProcessCancellationResponse)
async def process_cancellation(cancellation_id: int, db: Session = Depends(get_db)):
    # Get cancellation data
    cancellation = db.query(Cancellation).filter(Cancellation.cancellation_id == cancellation_id).first()
    if not cancellation:
        raise HTTPException(status_code=404, detail="Cancellation not found")
    
    # Initialize the incentive system
    system = NammaYatriIncentiveSystem(db)
    
    # Process the cancellation
    cancellation_data = CancellationCreate(
        driver_id=cancellation.driver_id,
        trip_id=cancellation.trip_id,
        time_since_accept_seconds=cancellation.time_since_accept_seconds,
        reason=cancellation.reason
    )
    
    result = system.process_cancellation(cancellation.driver_id, cancellation_data)
    return result
@app.post("/drivers/{driver_id}/reset-daily-stats", response_model=DriverDailyStatResponse)
async def reset_driver_daily_stats(
    driver_id: str, 
    data: dict,
    db: Session = Depends(get_db)
):
    """Reset or create daily stats for a driver, used for simulation"""
    # Check if driver exists
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Check if stats for today already exist
    today = date.today()
    existing_stats = db.query(DriverDailyStat).filter(
        DriverDailyStat.driver_id == driver_id,
        DriverDailyStat.date == today
    ).first()
    
    if existing_stats:
        # Reset existing stats
        existing_stats.distance_covered_today = 0
        existing_stats.coins_earned = 0
        existing_stats.hours_active = 0
        existing_stats.consecutive_trips = 0
        existing_stats.multiplier_active = False
        existing_stats.multiplier_value = 1.0
        existing_stats.go_home_mode_active = False
        existing_stats.multiplier_expires_at = None
        
        db.commit()
        db.refresh(existing_stats)
        return existing_stats
    else:
        # Create new stats
        new_stats = DriverDailyStat(
            driver_id=driver_id,
            date=today,
            distance_covered_today=0,
            coins_earned=0,
            hours_active=0,
            consecutive_trips=0,
            multiplier_active=False,
            multiplier_value=1.0,
            go_home_mode_active=False
        )
        
        db.add(new_stats)
        db.commit()
        db.refresh(new_stats)
        return new_stats

@app.get("/cancellations/", response_model=List[CancellationResponse])
async def get_cancellations(
    driver_id: str = None,
    start_date: date = None,
    end_date: date = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(Cancellation)
    
    if driver_id:
        query = query.filter(Cancellation.driver_id == driver_id)
    
    if start_date:
        query = query.filter(Cancellation.cancellation_date >= start_date)
    
    if end_date:
        query = query.filter(Cancellation.cancellation_date <= end_date)
    
    cancellations = query.order_by(Cancellation.created_at.desc()).offset(skip).limit(limit).all()
    return cancellations

# Driver action endpoints
@app.post("/drivers/{driver_id}/activate-multiplier", response_model=ActivateMultiplierResponse)
async def activate_multiplier(driver_id: str, db: Session = Depends(get_db)):
    # Initialize the incentive system
    system = NammaYatriIncentiveSystem(db)
    
    # Activate multiplier
    result = system.activate_multiplier(driver_id)
    return result

@app.post("/drivers/{driver_id}/activate-go-home", response_model=ActivateGoHomeResponse)
async def activate_go_home(driver_id: str, db: Session = Depends(get_db)):
    # Initialize the incentive system
    system = NammaYatriIncentiveSystem(db)
    
    # Activate go-home mode
    result = system.activate_go_home_mode(driver_id)
    return result

@app.get("/drivers/{driver_id}/go-home-recommendations", response_model=GoHomeRecommendationsResponse)
async def get_go_home_recommendations(driver_id: str, db: Session = Depends(get_db)):
    # Initialize the incentive system
    system = NammaYatriIncentiveSystem(db)
    
    # Get recommendations
    result = system.find_optimal_trips_for_go_home(driver_id)
    return result

# Traffic data endpoints
@app.post("/traffic-data/", response_model=TrafficDataResponse)
async def create_traffic_data(traffic_data: TrafficDataCreate, db: Session = Depends(get_db)):
    # Create new traffic data record
    new_traffic_data = TrafficData(**traffic_data.dict())
    new_traffic_data.date = date.today()
    
    db.add(new_traffic_data)
    db.commit()
    db.refresh(new_traffic_data)
    
    return new_traffic_data

@app.get("/traffic-data/", response_model=List[TrafficDataResponse])
async def get_traffic_data(
    location_id: int = None,
    time_of_day: str = None,
    date_filter: date = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(TrafficData)
    
    if location_id:
        query = query.filter(TrafficData.location_id == location_id)
    
    if time_of_day:
        query = query.filter(TrafficData.time_of_day == time_of_day)
    
    if date_filter:
        query = query.filter(TrafficData.date == date_filter)
    
    traffic_data = query.order_by(TrafficData.created_at.desc()).offset(skip).limit(limit).all()
    return traffic_data

# Utility endpoints
@app.get("/stats/driver-leaderboard", response_model=List[dict])
async def get_driver_leaderboard(
    date_filter: date = Query(None, description="Date for stats (defaults to today)"),
    limit: int = 10,
    db: Session = Depends(get_db)
):
    if date_filter is None:
        date_filter = date.today()
    
    # Get top drivers by coins earned for the specified date
    driver_stats = db.query(
        DriverDailyStat.driver_id,
        Driver.name,
        DriverDailyStat.coins_earned,
        DriverDailyStat.distance_covered_today
    ).join(
        Driver, DriverDailyStat.driver_id == Driver.driver_id
    ).filter(
        DriverDailyStat.date == date_filter
    ).order_by(
        DriverDailyStat.coins_earned.desc()
    ).limit(limit).all()
    
    # Format the results
    result = []
    for driver_id, name, coins_earned, distance in driver_stats:
        result.append({
            "driver_id": driver_id,
            "name": name,
            "coins_earned": coins_earned,
            "distance_covered_km": distance,
            "rank": len(result) + 1
        })
    
    return result

@app.get("/stats/driver-earnings", response_model=dict)
async def get_driver_earnings(
    driver_id: str,
    start_date: date = Query(..., description="Start date for the period"),
    end_date: date = Query(..., description="End date for the period"),
    db: Session = Depends(get_db)
):
    # Check if driver exists
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Get daily stats for the period
    daily_stats = db.query(
        DriverDailyStat.date,
        DriverDailyStat.coins_earned,
        DriverDailyStat.distance_covered_today,
        DriverDailyStat.hours_active
    ).filter(
        DriverDailyStat.driver_id == driver_id,
        DriverDailyStat.date >= start_date,
        DriverDailyStat.date <= end_date
    ).all()
    
    # Get trip data for the period
    trips = db.query(
        Trip.trip_date,
        Trip.base_fare,
        Trip.final_fare,
        Trip.multiplier_applied,
        Trip.coins_earned
    ).filter(
        Trip.driver_id == driver_id,
        Trip.trip_date >= start_date,
        Trip.trip_date <= end_date
    ).all()
    
    # Calculate totals
    total_coins = sum(stat.coins_earned for stat in daily_stats)
    total_distance = sum(stat.distance_covered_today for stat in daily_stats)
    total_hours = sum(stat.hours_active for stat in daily_stats)
    total_trips = len(trips)
    total_base_fare = sum(trip.base_fare for trip in trips)
    total_final_fare = sum(trip.final_fare for trip in trips)
    
    # Format daily earnings
    daily_earnings = []
    for stat in daily_stats:
        daily_trips = [trip for trip in trips if trip.trip_date == stat.date]
        daily_earnings.append({
            "date": stat.date.isoformat(),
            "coins_earned": stat.coins_earned,
            "distance_covered_km": stat.distance_covered_today,
            "hours_active": stat.hours_active,
            "trips_count": len(daily_trips),
            "fare_earned": sum(trip.final_fare for trip in daily_trips)
        })
    
    # Calculate averages
    avg_coins_per_day = total_coins / len(daily_stats) if daily_stats else 0
    avg_distance_per_day = total_distance / len(daily_stats) if daily_stats else 0
    avg_fare_per_trip = total_final_fare / total_trips if total_trips else 0
    
    return {
        "driver_id": driver_id,
        "driver_name": driver.name,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": (end_date - start_date).days + 1
        },
        "totals": {
            "coins_earned": total_coins,
            "distance_covered_km": total_distance,
            "hours_active": total_hours,
            "trips_completed": total_trips,
            "base_fare_earned": total_base_fare,
            "final_fare_earned": total_final_fare,
            "bonus_from_multipliers": total_final_fare - total_base_fare
        },
        "averages": {
            "coins_per_day": avg_coins_per_day,
            "distance_per_day": avg_distance_per_day,
            "fare_per_trip": avg_fare_per_trip
        },
        "daily_earnings": daily_earnings
    }

# Run the app with uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Run the app
    uvicorn.run("namma_yatri_api:app", host="0.0.0.0", port=8000, reload=True)