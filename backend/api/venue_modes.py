"""Resolve legacy events without changing their bookings or historical programme."""
def mode(db,event):
 if event.venue_mode:return event.venue_mode
 if event.venue_experience_type!='auditorium':return 'standard'
 from .venue_rentals import booking
 return 'grand_arena' if (event.programme or {}).get('arena_booking_required') or booking(db,event.id) else 'virtual_auditorium'
