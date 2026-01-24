-- Quick fix for missing columns
-- Run this directly in your database to add the missing columns

-- Add start_location_text to trips table
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'start_location_text'
    ) THEN
        ALTER TABLE trips ADD COLUMN start_location_text VARCHAR;
        RAISE NOTICE 'Added start_location_text column to trips table';
    ELSE
        RAISE NOTICE 'start_location_text column already exists';
    END IF;
END $$;

-- Add pickup_address to ride_requests table
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'pickup_address'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN pickup_address VARCHAR;
        RAISE NOTICE 'Added pickup_address column to ride_requests table';
    ELSE
        RAISE NOTICE 'pickup_address column already exists';
    END IF;
END $$;

-- Verify columns were added
SELECT 
    'trips' as table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'trips' 
AND column_name IN ('start_location_text')
ORDER BY column_name;

SELECT 
    'ride_requests' as table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'ride_requests' 
AND column_name IN ('pickup_address')
ORDER BY column_name;
