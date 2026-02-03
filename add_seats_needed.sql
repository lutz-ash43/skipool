-- Add seats_needed column to ride_requests table
-- Run this in your GCP Cloud SQL console or via psql

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'seats_needed'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN seats_needed INTEGER DEFAULT 1;
    END IF;
END $$;
