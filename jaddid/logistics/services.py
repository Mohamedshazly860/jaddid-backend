import math
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import Courier, CourierAssignment, LiveTracking
from orders.models import Order

class CourierService:
    """Service class for courier-related operations"""

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """calculate distance between two points using Haversine formula
        returns distance in kilometers"""
        
        R=6371 #Earth Radius in kilometers

        lat1_rad=math.radians(lat1)
        lat2_rad=math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
                    math.cos(lat1_rad) * math.cos(lat2_rad) *
                    math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                
        distance = R * c
        return distance
    
    @staticmethod
    def find_nearest_courier(order_lat, order_lng):
        """Find the nearest available courier
        Returns: Courier Object or None"""
        available_couriers=Courier.objects.filter(
            is_active=True,
            current_lat__isnull=False,
            current_lng__isnull=False
        )

        if not available_couriers.exists():
            return None
        
        #calculate the distance and find the nearest
        nearest_courier=None
        min_distance=float('inf')

        for courier in available_couriers:
            distance=CourierService.calculate_distance(
                courier.current_lat,
                courier.current_lng,
                order_lat,
                order_lng
            )

            if distance < min_distance:
                min_distance=distance
                nearest_courier=courier
        
        return nearest_courier
    

    @staticmethod
    def assign_courier_to_order(order):
        """Automatically assign nearest available courier to order
        Returns: CourierAssignment or None"""
        order_lat = 30.0444  # Cairo latitude (example)
        order_lng = 31.2357  # Cairo longitude (example)

        #find the nearest courier
        courier=CourierService.find_nearest_courier(order_lat, order_lng)

        if not courier:
            return None
        
        #create assignment
        assignment=CourierAssignment.objects.create(
            order=order,
            courier=courier,
            accepted=True,
            accepted_at=timezone.now()
        )

        #mark courier as busy
        courier.is_active= True
        courier.save()

        #update order status
        order.status='in progress'
        order.save()

        return assignment
    

    @staticmethod
    def simulate_delivery_route(assignment, destination_lat, destination_lng):
        """Simulate courier movement from current location to destination
        Creates tracking logs along the route"""
        courier=assignment.courier

        #starting point
        start_lat=courier.current_lat
        start_lng=courier.current_lng

        steps = 10

        #calculate increment per step
        lat_increment=(destination_lat-start_lat) / steps
        lng_increment=(destination_lng-start_lng) / steps

        #create tracking logs
        for step in range(steps+1):
            current_lat=start_lat + (lat_increment * steps)
            current_lng=start_lng + (lng_increment * steps)

            distance=CourierService.calculate_distance(current_lat, current_lng, destination_lat, destination_lng)
            
            # Estimate time (assuming 30 km/h average speed)
            estimated_time=int((distance/30) * 60) #in minutes

            #create tracking log
            LiveTracking.objects.create(
                order=assignment.order,
                courier=courier,
                latitude=current_lat,
                longitude=current_lng,
                distance_to_destination=distance,
                estimated_time=estimated_time
            )

            #update courier current location
            courier.current_lat=current_lat
            courier.current_lng=current_lng
            courier.save()

        #mark delivery as complete
        assignment.completed_at=timezone.now()
        assignment.save()

        #update order status
        assignment.order.status='Delivered'
        assignment.order.save()

        #mark courier available again
        courier.is_active= True
        courier.save()

        return True
    
    
