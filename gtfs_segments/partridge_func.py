import partridge as ptg

def get_bus_feed(path, agency_name=None):
  """
  This function retrieves the bus feed data from a specified path and returns the date and feed
  information, with the option to filter by agency name.
  
  Args:
    path: The path to the directory containing the GTFS files. GTFS (General Transit Feed
  Specification) is a standard format for public transportation schedules and related geographic data.
    agency_name: The name of the transit agency for which you want to retrieve the bus feed. If this
  parameter is not provided, the function will retrieve the bus feed for all transit agencies.
  
  Returns:
    a tuple containing the busiest date and a GTFS feed object. The GTFS feed object contains
  information about routes, stops, stop times, trips, and shapes for a transit agency's schedule.
  """
  _date, service_ids = ptg.read_busiest_date(path)
  route_types = [3,700,702,703,704,705] ##701 is regional
  if agency_name is not None:
      view = {
          'routes.txt': {'route_type':route_types}, # Only bus routes
          'trips.txt': {'service_id': service_ids}, # Busiest day only
          'agency.txt': {'agency_name': agency_name} # Eg: 'Société de transport de Montréal
      }
  else:
      view = {
          'routes.txt': {'route_type':route_types}, # Only bus routes
          'trips.txt': {'service_id': service_ids}, # Busiest day only
      }
  feed = ptg.load_geo_feed(path,view=view)
  #     return feed.routes, feed.stops, feed.stop_times, feed.trips, feed.shapes
  return _date,feed