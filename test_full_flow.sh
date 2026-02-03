#!/bin/bash
# Full flow test script - creates data and simulates driver movement (Ride Now)
# Ride Now: passengers are at pickup; we only simulate driver movement.

echo "🧪 SkiPool Full Flow Test"
echo "=========================="
echo ""

echo "1️⃣  Creating test data..."
python create_test_data.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to create test data"
    exit 1
fi

echo ""
echo "2️⃣  Waiting 3 seconds for data to settle..."
sleep 3

echo ""
echo "3️⃣  Simulating driver movement (Ride Now to Alta)..."
echo "   - Driver 1 will move along route; passenger 1 is at pickup (no simulation)."
echo ""

python simulate_location.py --trip-id 1 --steps 15 --delay 3.0

echo ""
echo "✅ Test complete!"
echo ""
echo "💡 Next steps:"
echo "   1. Open iOS Simulator"
echo "   2. Test as driver or passenger"
echo "   3. Watch matches appear; driver navigates to pickup (passenger waiting there)"
