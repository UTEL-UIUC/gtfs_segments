import partridge as ptg

def get_bus_feed(path):
    """
    It reads the gtfs file and returns the busiest day and the feed object
    
    Args:
      path: The path to the GTFS file
    
    Returns:
      The busiest day and the feed object
    """
    _date, service_ids = ptg.read_busiest_date(path)
    view = {
        'routes.txt': {'route_type':3}, # Only bus routes
        'trips.txt': {'service_id': service_ids} # Busiest day only
    }
    feed = ptg.load_geo_feed(path,view=view)
#     return feed.routes, feed.stops, feed.stop_times, feed.trips, feed.shapes
    return _date,feed