import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

st.title("🚗 Python Carpool MVP")

role = st.sidebar.radio("Select Role", ["Driver", "Passenger"])

# Fetch Hubs from Backend
hubs_data = requests.get(f"{BACKEND_URL}/hubs/").json()
hub_options = {v['name']: k for k, v in hubs_data.items()}

if role == "Driver":
    st.header("Post a Trip")
    name = st.text_input("Your Name")
    dest = st.text_input("Destination")
    seats = st.number_input("Available Seats", min_value=1, max_value=4)
    
    selected_names = st.multiselect("Which hubs will you pass along the way?", list(hub_options.keys()))
    selected_ids = [hub_options[name] for name in selected_names]

    if st.button("Post Trip"):
        payload = {
            "driver_name": name,
            "destination": dest,
            "selected_hub_ids": selected_ids,
            "available_seats": seats
        }
        res = requests.post(f"{BACKEND_URL}/trips/", json=payload)
        if res.status_code == 200:
            st.success("Trip posted successfully!")

else:
    st.header("Find a Ride")
    search_hub_name = st.selectbox("Where are you located?", list(hub_options.keys()))
    search_hub_id = hub_options[search_hub_name]

    if st.button("Find Drivers"):
        res = requests.get(f"{BACKEND_URL}/search/", params={"hub_id": search_hub_id})
        matches = res.json()

        if matches:
            for trip in matches:
                st.write(f"**Driver:** {trip['driver_name']} | **Going to:** {trip['destination']}")
                st.button(f"Request Seat from {trip['driver_name']}", key=trip['id'])
        else:
            st.warning("No drivers found passing this hub.")