"""
World Clock module for displaying time in different cities/countries
"""
import logging
from datetime import datetime
from typing import Optional, List, Tuple
import pytz
from pytz import timezone, all_timezones, country_timezones
from pytz.exceptions import UnknownTimeZoneError

logger = logging.getLogger(__name__)

class WorldClock:
    """Handles world clock functionality for different cities and countries"""
    
    # Common city to timezone mappings
    CITY_TIMEZONES = {
        # Europe
        'london': 'Europe/London',
        'paris': 'Europe/Paris',
        'berlin': 'Europe/Berlin',
        'rome': 'Europe/Rome',
        'madrid': 'Europe/Madrid',
        'amsterdam': 'Europe/Amsterdam',
        'brussels': 'Europe/Brussels',
        'vienna': 'Europe/Vienna',
        'prague': 'Europe/Prague',
        'warsaw': 'Europe/Warsaw',
        'budapest': 'Europe/Budapest',
        'athens': 'Europe/Athens',
        'stockholm': 'Europe/Stockholm',
        'oslo': 'Europe/Oslo',
        'copenhagen': 'Europe/Copenhagen',
        'helsinki': 'Europe/Helsinki',
        'dublin': 'Europe/Dublin',
        'lisbon': 'Europe/Lisbon',
        'zurich': 'Europe/Zurich',
        'moscow': 'Europe/Moscow',
        'kiev': 'Europe/Kiev',
        'kyiv': 'Europe/Kiev',
        'istanbul': 'Europe/Istanbul',
        
        # Americas
        'new york': 'America/New_York',
        'newyork': 'America/New_York',
        'nyc': 'America/New_York',
        'los angeles': 'America/Los_Angeles',
        'losangeles': 'America/Los_Angeles',
        'la': 'America/Los_Angeles',
        'chicago': 'America/Chicago',
        'houston': 'America/Chicago',
        'phoenix': 'America/Phoenix',
        'philadelphia': 'America/New_York',
        'san antonio': 'America/Chicago',
        'san diego': 'America/Los_Angeles',
        'sandiego': 'America/Los_Angeles',
        'dallas': 'America/Chicago',
        'san jose': 'America/Los_Angeles',
        'sanjose': 'America/Los_Angeles',
        'austin': 'America/Chicago',
        'jacksonville': 'America/New_York',
        'san francisco': 'America/Los_Angeles',
        'sanfrancisco': 'America/Los_Angeles',
        'sf': 'America/Los_Angeles',
        'columbus': 'America/New_York',
        'indianapolis': 'America/Indiana/Indianapolis',
        'seattle': 'America/Los_Angeles',
        'denver': 'America/Denver',
        'boston': 'America/New_York',
        'miami': 'America/New_York',
        'atlanta': 'America/New_York',
        'las vegas': 'America/Los_Angeles',
        'lasvegas': 'America/Los_Angeles',
        'toronto': 'America/Toronto',
        'montreal': 'America/Montreal',
        'vancouver': 'America/Vancouver',
        'mexico city': 'America/Mexico_City',
        'mexicocity': 'America/Mexico_City',
        'sao paulo': 'America/Sao_Paulo',
        'saopaulo': 'America/Sao_Paulo',
        'rio': 'America/Sao_Paulo',
        'rio de janeiro': 'America/Sao_Paulo',
        'buenos aires': 'America/Argentina/Buenos_Aires',
        'buenosaires': 'America/Argentina/Buenos_Aires',
        'lima': 'America/Lima',
        'bogota': 'America/Bogota',
        'santiago': 'America/Santiago',
        'caracas': 'America/Caracas',
        
        # Asia
        'tokyo': 'Asia/Tokyo',
        'osaka': 'Asia/Tokyo',
        'kyoto': 'Asia/Tokyo',
        'beijing': 'Asia/Shanghai',
        'shanghai': 'Asia/Shanghai',
        'hong kong': 'Asia/Hong_Kong',
        'hongkong': 'Asia/Hong_Kong',
        'singapore': 'Asia/Singapore',
        'seoul': 'Asia/Seoul',
        'taipei': 'Asia/Taipei',
        'bangkok': 'Asia/Bangkok',
        'jakarta': 'Asia/Jakarta',
        'manila': 'Asia/Manila',
        'kuala lumpur': 'Asia/Kuala_Lumpur',
        'kualalumpur': 'Asia/Kuala_Lumpur',
        'kl': 'Asia/Kuala_Lumpur',
        'new delhi': 'Asia/Kolkata',
        'newdelhi': 'Asia/Kolkata',
        'delhi': 'Asia/Kolkata',
        'mumbai': 'Asia/Kolkata',
        'bangalore': 'Asia/Kolkata',
        'kolkata': 'Asia/Kolkata',
        'chennai': 'Asia/Kolkata',
        'hyderabad': 'Asia/Kolkata',
        'karachi': 'Asia/Karachi',
        'lahore': 'Asia/Karachi',
        'dhaka': 'Asia/Dhaka',
        'dubai': 'Asia/Dubai',
        'abu dhabi': 'Asia/Dubai',
        'abudhabi': 'Asia/Dubai',
        'riyadh': 'Asia/Riyadh',
        'tehran': 'Asia/Tehran',
        'tel aviv': 'Asia/Tel_Aviv',
        'telaviv': 'Asia/Tel_Aviv',
        'jerusalem': 'Asia/Jerusalem',
        
        # Oceania
        'sydney': 'Australia/Sydney',
        'melbourne': 'Australia/Melbourne',
        'brisbane': 'Australia/Brisbane',
        'perth': 'Australia/Perth',
        'adelaide': 'Australia/Adelaide',
        'auckland': 'Pacific/Auckland',
        'wellington': 'Pacific/Auckland',
        
        # Africa
        'cairo': 'Africa/Cairo',
        'lagos': 'Africa/Lagos',
        'johannesburg': 'Africa/Johannesburg',
        'cape town': 'Africa/Johannesburg',
        'capetown': 'Africa/Johannesburg',
        'nairobi': 'Africa/Nairobi',
        'casablanca': 'Africa/Casablanca',
        'algiers': 'Africa/Algiers',
        'tunis': 'Africa/Tunis',
    }
    
    # Country to primary timezone mappings
    COUNTRY_TIMEZONES = {
        'usa': 'America/New_York',
        'us': 'America/New_York',
        'united states': 'America/New_York',
        'america': 'America/New_York',
        'uk': 'Europe/London',
        'united kingdom': 'Europe/London',
        'britain': 'Europe/London',
        'england': 'Europe/London',
        'france': 'Europe/Paris',
        'germany': 'Europe/Berlin',
        'spain': 'Europe/Madrid',
        'italy': 'Europe/Rome',
        'netherlands': 'Europe/Amsterdam',
        'holland': 'Europe/Amsterdam',
        'belgium': 'Europe/Brussels',
        'switzerland': 'Europe/Zurich',
        'austria': 'Europe/Vienna',
        'poland': 'Europe/Warsaw',
        'czech republic': 'Europe/Prague',
        'czechia': 'Europe/Prague',
        'hungary': 'Europe/Budapest',
        'greece': 'Europe/Athens',
        'portugal': 'Europe/Lisbon',
        'sweden': 'Europe/Stockholm',
        'norway': 'Europe/Oslo',
        'denmark': 'Europe/Copenhagen',
        'finland': 'Europe/Helsinki',
        'ireland': 'Europe/Dublin',
        'russia': 'Europe/Moscow',
        'ukraine': 'Europe/Kiev',
        'turkey': 'Europe/Istanbul',
        'canada': 'America/Toronto',
        'mexico': 'America/Mexico_City',
        'brazil': 'America/Sao_Paulo',
        'argentina': 'America/Argentina/Buenos_Aires',
        'chile': 'America/Santiago',
        'colombia': 'America/Bogota',
        'peru': 'America/Lima',
        'venezuela': 'America/Caracas',
        'china': 'Asia/Shanghai',
        'japan': 'Asia/Tokyo',
        'south korea': 'Asia/Seoul',
        'korea': 'Asia/Seoul',
        'india': 'Asia/Kolkata',
        'pakistan': 'Asia/Karachi',
        'bangladesh': 'Asia/Dhaka',
        'indonesia': 'Asia/Jakarta',
        'thailand': 'Asia/Bangkok',
        'vietnam': 'Asia/Ho_Chi_Minh',
        'philippines': 'Asia/Manila',
        'malaysia': 'Asia/Kuala_Lumpur',
        'singapore': 'Asia/Singapore',
        'taiwan': 'Asia/Taipei',
        'hong kong': 'Asia/Hong_Kong',
        'israel': 'Asia/Tel_Aviv',
        'uae': 'Asia/Dubai',
        'saudi arabia': 'Asia/Riyadh',
        'iran': 'Asia/Tehran',
        'egypt': 'Africa/Cairo',
        'south africa': 'Africa/Johannesburg',
        'nigeria': 'Africa/Lagos',
        'kenya': 'Africa/Nairobi',
        'morocco': 'Africa/Casablanca',
        'australia': 'Australia/Sydney',
        'new zealand': 'Pacific/Auckland',
        'nz': 'Pacific/Auckland',
    }
    
    @classmethod
    def get_timezone_for_location(cls, location: str) -> Optional[str]:
        """Get timezone for a given location (city or country)"""
        location_lower = location.lower().strip()
        
        # Check if it's a city
        if location_lower in cls.CITY_TIMEZONES:
            return cls.CITY_TIMEZONES[location_lower]
        
        # Check if it's a country
        if location_lower in cls.COUNTRY_TIMEZONES:
            return cls.COUNTRY_TIMEZONES[location_lower]
        
        # Try to find it as a timezone directly (e.g., "UTC", "EST", "PST")
        try:
            # Check common abbreviations
            tz_abbreviations = {
                'utc': 'UTC',
                'gmt': 'GMT',
                'est': 'US/Eastern',
                'edt': 'US/Eastern',
                'cst': 'US/Central',
                'cdt': 'US/Central',
                'mst': 'US/Mountain',
                'mdt': 'US/Mountain',
                'pst': 'US/Pacific',
                'pdt': 'US/Pacific',
                'bst': 'Europe/London',
                'cet': 'Europe/Paris',
                'cest': 'Europe/Paris',
                'jst': 'Asia/Tokyo',
                'ist': 'Asia/Kolkata',
                'aest': 'Australia/Sydney',
                'aedt': 'Australia/Sydney',
            }
            
            if location_lower in tz_abbreviations:
                return tz_abbreviations[location_lower]
            
            # Try to find it in all timezones (case-insensitive)
            for tz in all_timezones:
                if location_lower == tz.lower():
                    return tz
                # Also check the last part of the timezone (e.g., "paris" for "Europe/Paris")
                if '/' in tz and location_lower == tz.split('/')[-1].lower():
                    return tz
            
        except Exception as e:
            logger.error(f"Error checking timezone: {e}")
        
        return None
    
    @classmethod
    def get_time_for_location(cls, location: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get current time for a location
        Returns: (formatted_time_string, error_message)
        """
        tz_name = cls.get_timezone_for_location(location)
        
        if not tz_name:
            # Try to provide helpful suggestions
            suggestions = cls.get_location_suggestions(location)
            if suggestions:
                return None, f"Location '{location}' not found. Did you mean: {', '.join(suggestions[:5])}?"
            return None, f"Sorry, I couldn't find the timezone for '{location}'. Try a major city or country name."
        
        try:
            tz = timezone(tz_name)
            now = datetime.now(tz)
            
            # Format the time nicely
            time_str = now.strftime("%I:%M %p")  # 12-hour format with AM/PM
            date_str = now.strftime("%A, %B %d, %Y")  # Full date
            timezone_abbr = now.strftime("%Z")  # Timezone abbreviation
            utc_offset = now.strftime("%z")  # UTC offset
            
            # Format UTC offset nicely (e.g., +0530 -> +05:30)
            if utc_offset:
                utc_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
            
            # Create formatted response
            formatted_location = location.title()
            response = (
                f"🕐 **{formatted_location}**\n"
                f"Time: {time_str}\n"
                f"Date: {date_str}\n"
                f"Timezone: {timezone_abbr} (UTC{utc_offset})"
            )
            
            return response, None
            
        except Exception as e:
            logger.error(f"Error getting time for {location}: {e}")
            return None, f"Error getting time for '{location}': {str(e)}"
    
    @classmethod
    def get_location_suggestions(cls, query: str) -> List[str]:
        """Get suggestions for similar location names"""
        query_lower = query.lower()
        suggestions = []
        
        # Check cities
        for city in cls.CITY_TIMEZONES.keys():
            if query_lower in city or city.startswith(query_lower):
                suggestions.append(city.title())
        
        # Check countries
        for country in cls.COUNTRY_TIMEZONES.keys():
            if query_lower in country or country.startswith(query_lower):
                suggestions.append(country.title())
        
        return suggestions[:5]  # Return top 5 suggestions
    
    @classmethod
    def get_multiple_times(cls, locations: List[str]) -> str:
        """Get times for multiple locations at once"""
        results = []
        errors = []
        
        for location in locations[:5]:  # Limit to 5 locations
            time_str, error = cls.get_time_for_location(location)
            if time_str:
                results.append(time_str)
            elif error:
                errors.append(error)
        
        response = ""
        if results:
            response = "\n\n".join(results)
        if errors:
            if response:
                response += "\n\n"
            response += "⚠️ " + "\n".join(errors)
        
        return response if response else "No valid locations found."
    
    @classmethod
    async def handle_clock_command(cls, query: str) -> str:
        """
        Handle clock command
        Args:
            query: The location query (e.g., "paris", "tokyo", "usa")
        Returns:
            Formatted time information or error message
        """
        if not query:
            # Show current UTC time if no location specified
            utc_now = datetime.now(pytz.UTC)
            return (
                f"🕐 **Current UTC Time**\n"
                f"Time: {utc_now.strftime('%I:%M %p')}\n"
                f"Date: {utc_now.strftime('%A, %B %d, %Y')}\n\n"
                f"💡 Tip: Use `?clock <city/country>` to get time for a specific location.\n"
                f"Examples: `?clock paris`, `?clock tokyo`, `?clock new york`"
            )
        
        # Check if multiple locations are requested (separated by comma)
        if ',' in query:
            locations = [loc.strip() for loc in query.split(',')]
            return cls.get_multiple_times(locations)
        
        # Single location
        time_str, error = cls.get_time_for_location(query)
        return time_str if time_str else error

# Create singleton instance
world_clock = WorldClock()
