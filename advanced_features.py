# Additional advanced features
import geocoder
from datetime import datetime

class GeoAttendance:
    def __init__(self, allowed_locations=None):
        self.allowed_locations = allowed_locations or []
    
    def get_current_location(self):
        """Get current device location"""
        try:
            # Using Termux-location API
            import subprocess
            result = subprocess.run(['termux-location'], 
                                 capture_output=True, text=True)
            location_data = json.loads(result.stdout)
            
            return {
                'latitude': location_data.get('latitude'),
                'longitude': location_data.get('longitude'),
                'address': location_data.get('address', 'Unknown')
            }
        except:
            return None
    
    def is_within_school_premises(self, current_loc, school_loc, radius_km=0.5):
        """Check if device is within school premises"""
        if not current_loc or not school_loc:
            return False
            
        # Simple distance calculation (Haversine formula)
        from math import radians, sin, cos, sqrt, atan2
        
        lat1, lon1 = radians(current_loc['latitude']), radians(current_loc['longitude'])
        lat2, lon2 = radians(school_loc['latitude']), radians(school_loc['longitude'])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = 6371 * c  # Earth radius in km
        
        return distance <= radius_km

class TimeBasedFeatures:
    @staticmethod
    def is_within_attendance_time():
        """Check if current time is within allowed attendance hours"""
        current_hour = datetime.now().hour
        # Assuming school hours 8 AM to 3 PM
        return 8 <= current_hour < 15
    
    @staticmethod
    def get_attendance_period():
        """Get current school period based on time"""
        current_time = datetime.now().hour
        if 8 <= current_time < 9:
            return "Morning"
        elif 9 <= current_time < 12:
            return "Before Lunch"
        elif 12 <= current_time < 13:
            return "Lunch"
        elif 13 <= current_time < 15:
            return "After Lunch"
        else:
            return "After School"
