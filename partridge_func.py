from .partridge_mod import partridge as ptg

def ptg_read_file(path):
    """Use Partridge library to read the gtfs file and get the busiest day. Also filter bus routes

    Args:
        path (_type_): _description_
    """
    _date, service_ids = ptg.read_busiest_date(path)
    view = {
        'routes.txt': {'route_type':3}, # Only bus routes
        'trips.txt': {'service_id': service_ids} # Busiest day only
    }
    feed = ptg.load_geo_feed(path,view=view)
#     return feed.routes, feed.stops, feed.stop_times, feed.trips, feed.shapes
    return _date,feed