import React, { useState, useEffect } from 'react';
import { View, Text, Button, FlatList, TouchableOpacity } from 'react-native';

const API_URL = "https://your-ngrok-url.app"; // The URL from ngrok

export default function App() {
  const [hubs, setHubs] = useState([]);
  const [matches, setMatches] = useState([]);

  // Fetch Hubs on load
  useEffect(() => {
    fetch(`${API_URL}/hubs/`)
      .then(res => res.json())
      .then(data => setHubs(Object.entries(data)));
  }, []);

  const findRides = (hubId) => {
    fetch(`${API_URL}/search/?hub_id=${hubId}`)
      .then(res => res.json())
      .then(data => setMatches(data));
  };

  return (
    <View style={{ flex: 1, paddingTop: 50, paddingHorizontal: 20 }}>
      <Text style={{ fontSize: 24, fontWeight: 'bold' }}>Find a Carpool</Text>
      
      <Text>Select a Pickup Hub:</Text>
      {hubs.map(([id, hub]) => (
        <TouchableOpacity key={id} onPress={() => findRides(id)} style={{ padding: 10, backgroundColor: '#eee', marginVertical: 5 }}>
          <Text>{hub.name}</Text>
        </TouchableOpacity>
      ))}

      <FlatList
        data={matches}
        keyExtractor={item => item.id.toString()}
        renderItem={({ item }) => (
          <View style={{ padding: 15, borderBottomWidth: 1 }}>
            <Text>{item.driver_name} is going to {item.destination}</Text>
            <Button title="Join Carpool" onPress={() => alert("Request Sent!")} />
          </View>
        )}
      />
    </View>
  );
}