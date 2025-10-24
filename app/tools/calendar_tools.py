#!/usr/bin/env python3
"""
Calendar Tools
Event management, scheduling, reminders, and calendar integration
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass, asdict
from threading import Thread, Event
from langchain.tools import tool


@dataclass
class CalendarEvent:
    """Calendar event data structure"""
    id: str
    title: str
    description: str
    start_time: str
    end_time: str
    location: str = ""
    attendees: List[str] = None
    reminder_minutes: List[int] = None
    recurring: str = None  # "daily", "weekly", "monthly", "yearly"
    category: str = "general"
    created: str = ""
    modified: str = ""
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []
        if self.reminder_minutes is None:
            self.reminder_minutes = []
        if not self.created:
            self.created = datetime.now().isoformat()
        self.modified = datetime.now().isoformat()


class CalendarManager:
    """Manage calendar events and reminders"""
    
    def __init__(self, data_dir: str = "data/calendar"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.data_dir / "events.json"
        self.reminders_file = self.data_dir / "reminders.json"
        self.events = self._load_events()
        self.reminder_thread = None
        self.stop_reminders = Event()
        
    def _load_events(self) -> Dict[str, CalendarEvent]:
        """Load events from file"""
        if not self.events_file.exists():
            return {}
        
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
                
            events = {}
            for event_id, event_dict in events_data.items():
                events[event_id] = CalendarEvent(**event_dict)
                
            return events
        except Exception:
            return {}
    
    def _save_events(self):
        """Save events to file"""
        try:
            events_data = {}
            for event_id, event in self.events.items():
                events_data[event_id] = asdict(event)
                
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, indent=2, ensure_ascii=False)
                
        except Exception:
            pass
    
    def add_event(self, event: CalendarEvent) -> bool:
        """Add an event to the calendar"""
        self.events[event.id] = event
        self._save_events()
        return True
    
    def update_event(self, event_id: str, updates: Dict) -> bool:
        """Update an existing event"""
        if event_id not in self.events:
            return False
            
        event = self.events[event_id]
        for key, value in updates.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        event.modified = datetime.now().isoformat()
        self._save_events()
        return True
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an event"""
        if event_id in self.events:
            del self.events[event_id]
            self._save_events()
            return True
        return False
    
    def get_events(self, start_date: str = None, end_date: str = None) -> List[CalendarEvent]:
        """Get events within date range"""
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            
        filtered_events = []
        for event in self.events.values():
            event_date = event.start_time.split('T')[0]
            if start_date <= event_date <= end_date:
                filtered_events.append(event)
                
        return sorted(filtered_events, key=lambda e: e.start_time)


# Global calendar manager instance
_calendar_manager = None

def _get_calendar_manager():
    """Get calendar manager instance"""
    global _calendar_manager
    if _calendar_manager is None:
        _calendar_manager = CalendarManager()
    return _calendar_manager


@tool
def create_event(title: str, start_time: str, end_time: str, 
                description: str = "", location: str = "", 
                attendees: List[str] = None, reminder_minutes: List[int] = None,
                recurring: str = None, category: str = "general") -> Dict[str, Any]:
    """
    Create a new calendar event
    
    Args:
        title (str): Event title
        start_time (str): Start time in ISO format (2024-01-15T10:00:00)
        end_time (str): End time in ISO format
        description (str): Event description
        location (str): Event location
        attendees (List[str]): List of attendee email addresses
        reminder_minutes (List[int]): Minutes before event to remind (e.g., [15, 60])
        recurring (str): Recurring pattern ("daily", "weekly", "monthly", "yearly")
        category (str): Event category
        
    Returns:
        Dict: Event creation result
    """
    try:
        # Validate datetime format
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            if start_dt >= end_dt:
                return {
                    "success": False,
                    "error": "End time must be after start time"
                }
                
        except ValueError:
            return {
                "success": False,
                "error": "Invalid datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
            }
        
        # Create event
        event_id = str(uuid.uuid4())
        event = CalendarEvent(
            id=event_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            attendees=attendees or [],
            reminder_minutes=reminder_minutes or [],
            recurring=recurring,
            category=category
        )
        
        # Add to calendar
        calendar_manager = _get_calendar_manager()
        if calendar_manager.add_event(event):
            return {
                "success": True,
                "event_id": event_id,
                "event": asdict(event),
                "message": f"Event created: {title} on {start_dt.strftime('%Y-%m-%d %H:%M')}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to save event"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error creating event: {str(e)}"
        }


@tool
def get_events(start_date: str = None, end_date: str = None, 
               category: str = None, search: str = None) -> Dict[str, Any]:
    """
    Get calendar events with optional filtering
    
    Args:
        start_date (str): Start date filter (YYYY-MM-DD)
        end_date (str): End date filter (YYYY-MM-DD)
        category (str): Category filter
        search (str): Search term for title/description
        
    Returns:
        Dict: Events list and metadata
    """
    try:
        calendar_manager = _get_calendar_manager()
        events = calendar_manager.get_events(start_date, end_date)
        
        # Apply additional filters
        if category:
            events = [e for e in events if e.category.lower() == category.lower()]
        
        if search:
            search_lower = search.lower()
            events = [e for e in events if 
                     search_lower in e.title.lower() or 
                     search_lower in e.description.lower()]
        
        # Convert to dict format
        events_list = [asdict(event) for event in events]
        
        # Group by date
        events_by_date = {}
        for event in events_list:
            date = event['start_time'].split('T')[0]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        return {
            "success": True,
            "total_events": len(events_list),
            "events": events_list,
            "events_by_date": events_by_date,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "category": category,
                "search": search
            },
            "message": f"Found {len(events_list)} events"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting events: {str(e)}"
        }


def update_event(event_id: str, **updates) -> Dict[str, Any]:
    """
    Update an existing event
    
    Args:
        event_id (str): Event ID to update
        **updates: Fields to update (title, description, start_time, etc.)
        
    Returns:
        Dict: Update result
    """
    try:
        calendar_manager = _get_calendar_manager()
        
        if event_id not in calendar_manager.events:
            return {
                "success": False,
                "event_id": event_id,
                "error": "Event not found"
            }
        
        # Validate datetime fields if provided
        for field in ['start_time', 'end_time']:
            if field in updates:
                try:
                    datetime.fromisoformat(updates[field].replace('Z', '+00:00'))
                except ValueError:
                    return {
                        "success": False,
                        "event_id": event_id,
                        "error": f"Invalid {field} format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
                    }
        
        # Check if start_time < end_time after updates
        event = calendar_manager.events[event_id]
        start_time = updates.get('start_time', event.start_time)
        end_time = updates.get('end_time', event.end_time)
        
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        if start_dt >= end_dt:
            return {
                "success": False,
                "event_id": event_id,
                "error": "End time must be after start time"
            }
        
        # Update event
        if calendar_manager.update_event(event_id, updates):
            updated_event = calendar_manager.events[event_id]
            return {
                "success": True,
                "event_id": event_id,
                "event": asdict(updated_event),
                "updates_applied": list(updates.keys()),
                "message": f"Event updated: {updated_event.title}"
            }
        else:
            return {
                "success": False,
                "event_id": event_id,
                "error": "Failed to update event"
            }
        
    except Exception as e:
        return {
            "success": False,
            "event_id": event_id,
            "error": f"Error updating event: {str(e)}"
        }


@tool
def delete_event(event_id: str) -> Dict[str, Any]:
    """
    Delete an event
    
    Args:
        event_id (str): Event ID to delete
        
    Returns:
        Dict: Delete result
    """
    try:
        calendar_manager = _get_calendar_manager()
        
        if event_id not in calendar_manager.events:
            return {
                "success": False,
                "event_id": event_id,
                "error": "Event not found"
            }
        
        event_title = calendar_manager.events[event_id].title
        
        if calendar_manager.delete_event(event_id):
            return {
                "success": True,
                "event_id": event_id,
                "message": f"Event deleted: {event_title}"
            }
        else:
            return {
                "success": False,
                "event_id": event_id,
                "error": "Failed to delete event"
            }
        
    except Exception as e:
        return {
            "success": False,
            "event_id": event_id,
            "error": f"Error deleting event: {str(e)}"
        }


@tool
def get_upcoming_events(hours: int = 24) -> Dict[str, Any]:
    """
    Get events coming up in the next N hours
    
    Args:
        hours (int): Number of hours to look ahead
        
    Returns:
        Dict: Upcoming events
    """
    try:
        now = datetime.now()
        future_time = now + timedelta(hours=hours)
        
        calendar_manager = _get_calendar_manager()
        all_events = list(calendar_manager.events.values())
        
        upcoming_events = []
        for event in all_events:
            event_start = datetime.fromisoformat(event.start_time.replace('Z', '+00:00'))
            if now <= event_start <= future_time:
                upcoming_events.append(event)
        
        # Sort by start time
        upcoming_events.sort(key=lambda e: e.start_time)
        
        # Convert to dict format
        events_list = [asdict(event) for event in upcoming_events]
        
        # Add time until event
        for event_dict in events_list:
            event_start = datetime.fromisoformat(event_dict['start_time'].replace('Z', '+00:00'))
            time_until = event_start - now
            event_dict['minutes_until'] = int(time_until.total_seconds() / 60)
            event_dict['time_until_formatted'] = str(time_until).split('.')[0]
        
        return {
            "success": True,
            "hours_ahead": hours,
            "total_events": len(events_list),
            "events": events_list,
            "current_time": now.isoformat(),
            "search_until": future_time.isoformat(),
            "message": f"Found {len(events_list)} upcoming events in the next {hours} hours"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting upcoming events: {str(e)}"
        }


def set_reminder(event_id: str, minutes_before: int, notification_type: str = "system") -> Dict[str, Any]:
    """
    Set a reminder for an event
    
    Args:
        event_id (str): Event ID
        minutes_before (int): Minutes before event to remind
        notification_type (str): Type of notification ("system", "email", "popup")
        
    Returns:
        Dict: Reminder setup result
    """
    try:
        calendar_manager = _get_calendar_manager()
        
        if event_id not in calendar_manager.events:
            return {
                "success": False,
                "event_id": event_id,
                "error": "Event not found"
            }
        
        event = calendar_manager.events[event_id]
        
        # Add reminder to event
        if minutes_before not in event.reminder_minutes:
            event.reminder_minutes.append(minutes_before)
            event.modified = datetime.now().isoformat()
            calendar_manager._save_events()
        
        # Calculate reminder time
        event_start = datetime.fromisoformat(event.start_time.replace('Z', '+00:00'))
        reminder_time = event_start - timedelta(minutes=minutes_before)
        
        return {
            "success": True,
            "event_id": event_id,
            "event_title": event.title,
            "reminder_time": reminder_time.isoformat(),
            "minutes_before": minutes_before,
            "notification_type": notification_type,
            "total_reminders": len(event.reminder_minutes),
            "message": f"Reminder set for {minutes_before} minutes before: {event.title}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "event_id": event_id,
            "error": f"Error setting reminder: {str(e)}"
        }


def get_calendar_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get a summary of calendar for the next N days
    
    Args:
        days (int): Number of days to summarize
        
    Returns:
        Dict: Calendar summary
    """
    try:
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        calendar_manager = _get_calendar_manager()
        events = calendar_manager.get_events(start_date, end_date)
        
        # Group by date
        events_by_date = {}
        category_counts = {}
        total_duration = timedelta()
        
        for event in events:
            # By date
            date = event.start_time.split('T')[0]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(asdict(event))
            
            # By category
            if event.category not in category_counts:
                category_counts[event.category] = 0
            category_counts[event.category] += 1
            
            # Total duration
            try:
                start = datetime.fromisoformat(event.start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(event.end_time.replace('Z', '+00:00'))
                total_duration += (end - start)
            except:
                pass
        
        # Find busiest day
        busiest_day = None
        max_events = 0
        for date, day_events in events_by_date.items():
            if len(day_events) > max_events:
                max_events = len(day_events)
                busiest_day = date
        
        # Find free days
        all_dates = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
        free_days = [date for date in all_dates if date not in events_by_date]
        
        return {
            "success": True,
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "total_events": len(events),
            "events_by_date": events_by_date,
            "category_counts": category_counts,
            "statistics": {
                "total_duration_hours": round(total_duration.total_seconds() / 3600, 1),
                "average_events_per_day": round(len(events) / days, 1),
                "busiest_day": {
                    "date": busiest_day,
                    "events": max_events
                } if busiest_day else None,
                "free_days": free_days,
                "free_days_count": len(free_days)
            },
            "message": f"Calendar summary for {days} days: {len(events)} events, {len(free_days)} free days"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error generating calendar summary: {str(e)}"
        }


def find_free_time(date: str, duration_minutes: int, 
                  start_hour: int = 9, end_hour: int = 17) -> Dict[str, Any]:
    """
    Find free time slots on a given date
    
    Args:
        date (str): Date to search (YYYY-MM-DD)
        duration_minutes (int): Required duration in minutes
        start_hour (int): Search start hour (24h format)
        end_hour (int): Search end hour (24h format)
        
    Returns:
        Dict: Available time slots
    """
    try:
        # Get events for the date
        calendar_manager = _get_calendar_manager()
        events = calendar_manager.get_events(date, date)
        
        # Create time slots for the day
        search_start = datetime.fromisoformat(f"{date}T{start_hour:02d}:00:00")
        search_end = datetime.fromisoformat(f"{date}T{end_hour:02d}:00:00")
        
        # Collect busy periods
        busy_periods = []
        for event in events:
            event_start = datetime.fromisoformat(event.start_time.replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event.end_time.replace('Z', '+00:00'))
            
            # Only consider events within search window
            if event_end > search_start and event_start < search_end:
                busy_periods.append((
                    max(event_start, search_start),
                    min(event_end, search_end)
                ))
        
        # Sort busy periods by start time
        busy_periods.sort()
        
        # Find free slots
        free_slots = []
        current_time = search_start
        
        for busy_start, busy_end in busy_periods:
            # Check if there's a gap before this busy period
            if current_time < busy_start:
                gap_duration = busy_start - current_time
                if gap_duration.total_seconds() >= duration_minutes * 60:
                    free_slots.append({
                        "start": current_time.isoformat(),
                        "end": busy_start.isoformat(),
                        "duration_minutes": int(gap_duration.total_seconds() / 60)
                    })
            
            current_time = max(current_time, busy_end)
        
        # Check for time after the last event
        if current_time < search_end:
            final_gap = search_end - current_time
            if final_gap.total_seconds() >= duration_minutes * 60:
                free_slots.append({
                    "start": current_time.isoformat(),
                    "end": search_end.isoformat(),
                    "duration_minutes": int(final_gap.total_seconds() / 60)
                })
        
        # Filter slots that are long enough
        suitable_slots = [slot for slot in free_slots if slot["duration_minutes"] >= duration_minutes]
        
        return {
            "success": True,
            "search_criteria": {
                "date": date,
                "required_duration_minutes": duration_minutes,
                "search_window": f"{start_hour:02d}:00 - {end_hour:02d}:00"
            },
            "total_events": len(events),
            "free_slots_found": len(suitable_slots),
            "free_slots": suitable_slots,
            "all_free_periods": free_slots,
            "message": f"Found {len(suitable_slots)} free slots of {duration_minutes}+ minutes on {date}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "date": date,
            "error": f"Error finding free time: {str(e)}"
        }


if __name__ == "__main__":
    # Test the calendar tools
    print("=== Calendar Tools Test ===")
    
    # Test event creation
    print("\n1. Testing event creation:")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    create_result = create_event(
        title="Test Meeting",
        start_time=f"{tomorrow}T10:00:00",
        end_time=f"{tomorrow}T11:00:00",
        description="A test meeting",
        location="Conference Room A",
        reminder_minutes=[15, 60],
        category="work"
    )
    if create_result['success']:
        print(f"Event created: {create_result['event']['title']}")
        print(f"Event ID: {create_result['event_id']}")
        
        # Test getting events
        print("\n2. Testing get events:")
        events_result = get_events()
        if events_result['success']:
            print(f"Found {events_result['total_events']} events")
        else:
            print(f"Get events error: {events_result['error']}")
        
        # Test upcoming events
        print("\n3. Testing upcoming events:")
        upcoming_result = get_upcoming_events(48)
        if upcoming_result['success']:
            print(f"Found {upcoming_result['total_events']} upcoming events")
        else:
            print(f"Upcoming events error: {upcoming_result['error']}")
        
        # Test free time finding
        print("\n4. Testing free time search:")
        free_time_result = find_free_time(tomorrow, 30)
        if free_time_result['success']:
            print(f"Found {free_time_result['free_slots_found']} free slots")
        else:
            print(f"Free time error: {free_time_result['error']}")
        
        # Test calendar summary
        print("\n5. Testing calendar summary:")
        summary_result = get_calendar_summary(7)
        if summary_result['success']:
            print(f"Summary: {summary_result['total_events']} events in 7 days")
            print(f"Free days: {summary_result['statistics']['free_days_count']}")
        else:
            print(f"Summary error: {summary_result['error']}")
        
        # Clean up - delete test event
        delete_result = delete_event(create_result['event_id'])
        if delete_result['success']:
            print(f"\nTest event cleaned up: {delete_result['message']}")
        
    else:
        print(f"Event creation error: {create_result['error']}")
    
    print("\n=== Calendar Tools Test Complete ===")