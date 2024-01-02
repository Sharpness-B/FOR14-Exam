#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# In[4]:


# A car object holds information about the car and has a method to list it's reservations
class Car:
    def __init__(self, car_id, model_id, location_id, car_number, icon_url):
        self.car_id      = car_id # with car_id, each object can be linked to car.csv
        self.model_id    = model_id
        self.location_id = location_id
        self.car_number  = car_number
        self.icon_url    = icon_url
        
        # get information about the car model from the model dataframe
        model_row = model_raw[model_raw['model_id'] == model_id]
        
        # some models are missing in model.csv
        if not model_row.empty:
            self.model_name  = model_row['model_name'].iloc[0]
            self.seats       = model_row['seats'].iloc[0]

            self.category_id = model_row['category_id'].iloc[0]
            # get information about the car's category from the categoty dataframe
            category_row = car_category_raw[car_category_raw['category_id'] == self.category_id]

            self.category_name = category_row['category_name'].iloc[0]
            
            
    
    # lists the car's reservations. Inputs: the schedule object and a specification to use the schedule beofre or after reshuffling 
    def list_reservations(self, schedule, specified_schedule="trips"):
        car_id = self.car_id
        
        # get bookings from the original schedule if this is specified
        if specified_schedule=="trips":
            # if the car has andy bookings
            if car_id in schedule.trips:
                bookings = schedule.trips[car_id]
            # else, the car is not booked
            else:
                bookings = []
                
        # get bookings from the reshuffled schedule if this is specified  
        elif specified_schedule=="reshuffled_trips":
            # if the car has andy bookings
            if car_id in schedule.reshuffled_trips:
                bookings = schedule.reshuffled_trips[car_id]
            # else, the car is not booked
            else:
                bookings = []
            
        # print information about each booking
        for b in bookings:
            print("Reservation ID", b.trip_id, "Start:", b.start_ts, "End", b.ends_ts)
            
        return bookings
    

    
# A fleet object holds car objects and has the ability to create a subset of cars with the same number of seats
class Fleet:
    def __init__(self):
        self.cars = {}

    def add_car(self, id, car):
        self.cars[id] = car
        
    # returns a subset of cars with the same nubmer of seats. Input: x=number of seats, sort_by=proerty to sort the subset on
    def get_cars_by_seats(self, x, sort_by=None):
        # List to hold cars with x number of seats
        cars_with_x_seats = []

        # Iterate through all cars in the fleet
        for car_id, car in self.cars.items():
            # Check if the car has x seats
            if hasattr(car, 'seats') and car.seats == x:
                cars_with_x_seats.append(car)

        # Sort the list if a sort_by property is provided
        if sort_by is not None:
            cars_with_x_seats.sort(key=lambda car: getattr(car, sort_by))

        return cars_with_x_seats
        


# A reservation object contains information about a reservation
class Reservation:
    def __init__(self, trip_id, driven_km, start_ts, ends_ts, car_id):
        # store inputs
        self.trip_id = trip_id # with trip_id, each reservation can be linked to trips.csv
        self.driven_km = driven_km
        self.start_ts = start_ts
        self.ends_ts = ends_ts
        self.car_id = car_id
        
        # calculate duration in hours
        self.duration_hours = (ends_ts - start_ts).total_seconds() / 3600
        
         # add number of seats
        # none of the bookings are of the cars that are missing information about the car model. Therefore, no if/else or try/catch is needed
        self.seats         = fleet.cars[car_id].seats
        self.category_id   = fleet.cars[car_id].category_id
        self.category_name = fleet.cars[car_id].category_name
    
    

# A Schedule object is able to calculate the necessary metrics to analyze usage after reshuffling
# it it also implements the reshuffling algorithm
class Schedule:
    def __init__(self, earliestStart, latestEnd):
        self.earliestStart = earliestStart 
        self.latestEnd     = latestEnd
        
        # to store the original schedule
        self.trips = {} # {car_id: [reservation]}
        
        # to store the reshuffled schedule and leftover reservations
        self.initialize_reshuffled_trips()
        
    def initialize_reshuffled_trips(self):
        # to store the reshuffled schedule
        self.reshuffled_trips = {}
        # to store reservations that does not fit the schedule of any applicable car after reshuffling
        self.leftover_trips = []
        
    # Returns the productive time before or after the bookings have been reshuffled, depending on input
    # inputs are a car object and the specified schedule
    def calculate_productive_time(self, car, specified_schedule="trips"):     
        car_id = car.car_id
        
        # Make it possible to calculate the metric before and after reshuffling
        if specified_schedule=="trips":
            bookings = self.trips[car_id]
        elif specified_schedule=="reshuffled_trips":
            bookings = self.reshuffled_trips[car_id]

        productive_time = 0
        # add all occupied time
        for i in range(len(bookings)):
            productive_time += bookings[i].duration_hours
        
        return productive_time
    
        
        
    # Returns the unusable time before or after the bookings have been reshuffled, depending on input  
    # inputs are a car object and the specified schedule
    def calculate_unusable_time(self, car, specified_schedule="trips"):
        car_id = car.car_id    

        # bookings = the specified schedule
        if specified_schedule=="trips":
            bookings = self.trips[car_id]
        elif specified_schedule=="reshuffled_trips":
            bookings = self.reshuffled_trips[car_id]    
            

        unusable_time = 0
        
        # add unusable time time between bookings
        for i in range(len(bookings)-1):    
            time_clearance_hours = (bookings[i+1].start_ts - bookings[i].ends_ts).total_seconds() / 3600
            # add 30 minutes or the time between the bookings if the time clearance is less than 0.5 hours
            unusable_time += min(0.5, time_clearance_hours)
            
        return unusable_time
        
    #Returns the idle time before or after the bookings have been reshuffled, depending on input
    # inputs are a car object and the specified schedule
    def calculate_idle_time(self, car, specified_schedule="trips"):
        car_id = car.car_id    

        # bookings = the specified schedule
        if specified_schedule=="trips":
            bookings = self.trips[car_id]
        elif specified_schedule=="reshuffled_trips":
            bookings = self.reshuffled_trips[car_id]

        # sort bookings by start_ts to calculate the time between bookings
        bookings.sort(key=lambda reservation: reservation.start_ts)

        # calculate the time between the first and last booking of the fleet
        total_period_hours = (self.latestEnd - self.earliestStart).total_seconds() / 3600
        
        total_idle_time = total_period_hours
        # subtract actuall occupied time
        total_idle_time -= self.calculate_productive_time(car, specified_schedule=specified_schedule)
        # subtract unusable time between bookings
        total_idle_time -= self.calculate_unusable_time(car, specified_schedule=specified_schedule)
            
        return total_idle_time
    
    
    #Returns the wasted time before or after the bookings have been reshuffled, depending on input
    # inputs are a car object and the specified schedule
    def calculate_wasted_time(self, car, specified_schedule="trips"):
        car_id = car.car_id 
        
        # bookings = the specified schedule
        if specified_schedule=="trips":
            bookings = self.trips[car_id]
        elif specified_schedule=="reshuffled_trips":
            bookings = self.reshuffled_trips[car_id]
            
        wasted_time = 0
        
        # for each booking, if the duratio is lees than 30 minutes, add the duration to wasted time
        for i in range(len(bookings)):
            duration = bookings[i].duration_hours
            if duration < 0.5:
                wasted_time += duration
                
        return wasted_time
    
    
    # Returns the utilization of the cars in terms of percentage of total available hours
    # inputs are a car object and the specified schedule
    def calculate_utilization(self, car, specified_schedule="trips"):
        # utilization = (productive time + unusable time) / total time period
        
        # calculate productive time
        productive_time = self.calculate_productive_time(car, specified_schedule=specified_schedule)
        # calculate unusable time
        unusable_time   = self.calculate_unusable_time(car, specified_schedule=specified_schedule)
        
        # calculate total time period
        total_period_hours = (self.latestEnd - self.earliestStart).total_seconds() / 3600
        
        # calculate utilization
        return (productive_time + unusable_time) / total_period_hours

        
    #Adds a new reservation to designated schedule. Input: a new reservation and the specified schedule 
    def add_reservation(self, reservation, specified_schedule="trips"):        
        car_id = reservation.car_id
        
        # Add the reservation to the specified schedule
        # if the chosen schedule is the standard one
        if specified_schedule=="trips":
            # if the car alread has at least one booking
            if car_id in self.trips:
                self.trips[car_id].append(reservation)
            # if this is the first booking of the car
            else:
                self.trips[car_id] = [reservation]
            
        # if the chosen schedule is the new reshuffled one
        elif specified_schedule=="reshuffled_trips":
            # if the car alread has at least one booking
            if car_id in self.reshuffled_trips:
                self.reshuffled_trips[car_id].append(reservation)
            # if this is the first booking of the car
            else:
                self.reshuffled_trips[car_id] = [reservation]
                
                
    # Checks what car can fit a specific booking in ints schedule  
    # inputs, the new reservation, the car object, and intended pause between each booking
    def can_accommodate_reservation(self, reservation, car, minutes_pause=0):      
        # Calculate adjusted start time
        adj_start = reservation.start_ts  - timedelta(minutes=minutes_pause)
        adj_end   = reservation.ends_ts   + timedelta(minutes=minutes_pause)
        car_id    = car.car_id
        
        # if the car_id has not been added to the schedule
        if car_id not in self.reshuffled_trips:
            return True
        
        # for each existing reservation of the car
        for booking in self.reshuffled_trips[car_id]:
            # return false if the booking overlaps
            if ((adj_start >  booking.start_ts) and (adj_start <  booking.ends_ts) or
                (adj_end   >  booking.start_ts) and (adj_end   <  booking.ends_ts) or
                (adj_start <= booking.start_ts) and (adj_end   >= booking.ends_ts)):
                
                return False
            
        # no overlapping bookings if the function has not retruned False yet
        return True
            
            
    #Reshuffles the bookings into a more optimal schedule. Input: the intended pause between each booking      
    def reshuffle(self, minutes_pause=0):  
        #################################################
        # sort by duration and group by number of seats #
        #################################################
        # Flatten the dictionary into one long list, and add any leftover reservations
        flattened_list = [reservation for sublist in self.trips.values() for reservation in sublist]
        
        # initialize the reshuffled schedule
        self.initialize_reshuffled_trips()

        # Sort the flattened list by duration_hours
        flattened_list.sort(key=lambda x: x.duration_hours, reverse=True)

        # Group the sorted list by reservation.seats
        grouped_reservations = {} # {seats: [reservation]}
        for reservation in flattened_list:
            if reservation.seats in grouped_reservations:
                grouped_reservations[reservation.seats].append(reservation)
            else:
                grouped_reservations[reservation.seats] = [reservation]
                
        
        #############
        # RESHUFLLE #
        #############
        # for each group of reservations with the same number of seats (each set of of interchangeable reservations)
        for seats, reservations in grouped_reservations.items():
        
            # find a list of cars that can accommodate the reservations (cars with the correct number of seats)
            applicable_cars = fleet.get_cars_by_seats(seats, sort_by="category_id") # sort the cars by cheapest first
                   
            # iterate through the cars and fill as densely in the first cars as possible
            for booking in reservations:
                allocated = False
                # Find the first car that can accommodate this booking
                for car in applicable_cars:                    
                    if self.can_accommodate_reservation(booking, car, minutes_pause=minutes_pause):
                        # change the car id
                        booking.car_id = car.car_id
                        # Add the booking to this car
                        self.add_reservation(booking, specified_schedule="reshuffled_trips")
                        allocated = True
                        break

                # handle leftover bookings
                if not allocated:
                    self.leftover_trips.append(booking)
                    print("added leftover booking")
                    
                    
                    
                    
    # Provides a report of key metrics to evaluate the effectiveness of reshuffling method. Input: the intended pause between each booking              
    def report(self, specified_schedule="trips"):
        # bookings = the specified schedule
        if specified_schedule=="trips":
            bookings = self.trips
        elif specified_schedule=="reshuffled_trips":
            bookings = self.reshuffled_trips
            
        # initialize empty dataframe to store statstics about the cars. one row per car
        statsDF = pd.DataFrame({
            "Car ID": [],
            "Number of reservations": [],
            "Idle time": [],
            "Productive time": [],
            "Unusable time": [],
            "Wasted time": [],
            "Utilization": []    
        })

        # for each car and the car's reservations
        for car_id, reservations in bookings.items():

            # add a new row to the statistics dataframe
            new_index = len(statsDF)
            statsDF.loc[new_index] = {
                "Car ID":                 car_id,
                "Number of reservations": len(reservations),
                "Idle time":        self.calculate_idle_time      (fleet.cars[car_id], specified_schedule=specified_schedule), # calculate idle time
                "Productive time":  self.calculate_productive_time(fleet.cars[car_id], specified_schedule=specified_schedule), # calculate productive time
                "Unusable time":    self.calculate_unusable_time  (fleet.cars[car_id], specified_schedule=specified_schedule), # calculate unusable time
                "Wasted time":      self.calculate_wasted_time    (fleet.cars[car_id], specified_schedule=specified_schedule), # calculate wasted time
                "Utilization":   f"{self.calculate_utilization    (fleet.cars[car_id], specified_schedule=specified_schedule)*100:.2f}%" # calculate utilization % and format it as a string
            }


        # Rounding all numeric columns to two decimals
        statsDF = statsDF.round(2)

        # Sorting by 'Utilization' in descending order
        statsDF = statsDF.sort_values(by='Productive time', ascending=False)
        statsDF.set_index("Car ID", inplace=True)
        
        return statsDF

            
        


# In[5]:


# Provides a series of statistics to analyze the improvement in utilization. Input: arrays of utilization percentages of each car in the the fleet, before and after reshuffling
def calculateImprovementStatistics(utilization_before, utilization_after):
    # Calculate sum of utilization and standard deviation before and after reshuffling
    std_deviation_before = np.std(utilization_before)
    std_deviation_after  = np.std(utilization_after)
    # Find the change in standard deviation within the fleet
    std_deviation_change = std_deviation_after / std_deviation_before
    
    return std_deviation_change


# In[2]:


#############
# Read data #
#############

# read car data
model_raw        = pd.read_csv("data/model.csv", sep=";")
car_category_raw = pd.read_csv("data/car_category.csv", sep=";")
car_raw          = pd.read_csv("data/car.csv", sep=";")

# Read the trips CSV file
trips_raw = pd.read_csv("data/trips.csv", sep=";")

# convert all time-stamps to uct
trips_raw['start_ts'] = pd.to_datetime(trips_raw['start_ts'], utc=True)
trips_raw['ends_ts']  = pd.to_datetime(trips_raw['ends_ts'],  utc=True)

# keep only the first 5 000 bookings for testing purposes
trips_raw = trips_raw.sort_values(by='start_ts')
trips_raw = trips_raw.head(5000)


# In[6]:


########################################
# Initialize the fleet and car objects #
########################################

# Create a list to hold the car objects
fleet = Fleet()

# Loop through each row in the dataframe and create a Car object
for _, row in car_raw.iterrows():
    if not np.isnan(row['car_id']):
        car = Car(row['car_id'], row['model_id'], row['location_id'], row['car_number'], row['icon_url'])
        fleet.add_car(row['car_id'], car)
        


# In[7]:


###################################################
# Initialize the schedule and reservation objects #
###################################################

# record the earliest start and the latest end
earliestStart = trips_raw['start_ts'].min()
latestEnd     = trips_raw['ends_ts'].max()

# Create a schedule dictionary
schedule = Schedule(earliestStart, latestEnd)

# Iterate over the DataFrame and create Reservation objects
for index, row in trips_raw.iterrows():
    reservation = Reservation(row['trip_id'], row['driven_km'], row['start_ts'], row['ends_ts'], row['car_id'])
    schedule.add_reservation(reservation)


# In[8]:


#########################################
# Reshufling and performance evaluation #
#########################################

print("reshuffling...")
schedule.reshuffle(minutes_pause=30)

# generate report based on the schdule before reshuffling
report_before_reshuffling = schedule.report(specified_schedule="trips")
number_of_utilized_cars_before = len(report_before_reshuffling)

# generate report based on the schdule after reshuffling
report_after_reshuffling = schedule.report(specified_schedule="reshuffled_trips")
number_of_utilized_cars_after = len(report_after_reshuffling)

# calculate improvement statistics
utilization_before_list_str = list(report_before_reshuffling["Utilization"])
utilization_before = [float(u.strip('%')) / 100 for u in utilization_before_list_str]

utilization_after_list_str = list(report_after_reshuffling["Utilization"])
utilization_after = [float(u.strip('%')) / 100 for u in utilization_after_list_str]

std_deviation_change = calculateImprovementStatistics(utilization_before, utilization_after)

# presentation
print("=============================")
print("STATISTICS BEFORE RESHUFFLING")
print("=============================")
print(report_before_reshuffling)

print("============================")
print("STATISTICS AFTER RESHUFFLING")
print("============================")
print(report_after_reshuffling)

print("======================")
print("IMPROVEMENT STATISTICS")
print("======================")

print(f"Number of leftover bookings:    {len(schedule.leftover_trips)}")
print(f"Reduction of utilized cars:     {number_of_utilized_cars_before - number_of_utilized_cars_after} cars")
print(f"Reduction of utilized cars:     {(number_of_utilized_cars_before/number_of_utilized_cars_after - 1)*100:.1f}%")
print(f"Increase in fleet utilizatin standard deviation: {std_deviation_change:.1f}x")

