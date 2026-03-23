-- Migration: Add exchange rate table and admin flag to users
-- Date: 2026-02-12

-- Add is_admin column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- Update default currency to UZS
ALTER TABLE users ALTER COLUMN default_currency SET DEFAULT 'UZS';
ALTER TABLE transactions ALTER COLUMN currency SET DEFAULT 'UZS';
ALTER TABLE transfers ALTER COLUMN currency SET DEFAULT 'UZS';
ALTER TABLE balances ALTER COLUMN currency SET DEFAULT 'UZS';

-- Create exchange_rates table
CREATE TABLE IF NOT EXISTS exchange_rates ( 
    id SERIAL PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate NUMERIC(15, 6) NOT NULL CHECK (rate > 0),
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_exchange_pair UNIQUE (from_currency, to_currency)
);

-- Create index on exchange_rates
CREATE INDEX IF NOT EXISTS idx_exchange_rates_from_currency ON exchange_rates(from_currency);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_to_currency ON exchange_rates(to_currency);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_updated_at ON exchange_rates(updated_at);

-- Insert default exchange rate USD to UZS
INSERT INTO exchange_rates (from_currency, to_currency, rate)
VALUES ('USD', 'UZS', 12300)
ON CONFLICT (from_currency, to_currency) DO NOTHING;

-- Insert reverse rate UZS to USD
INSERT INTO exchange_rates (from_currency, to_currency, rate)
VALUES ('UZS', 'USD', 1.0 / 12300)
ON CONFLICT (from_currency, to_currency) DO NOTHING;

-- Comment
COMMENT ON TABLE exchange_rates IS 'Valyuta kurslari';
COMMENT ON COLUMN exchange_rates.from_currency IS 'Qaysi valyutadan';
COMMENT ON COLUMN exchange_rates.to_currency IS 'Qaysi valyutaga';
COMMENT ON COLUMN exchange_rates.rate IS 'Kurs qiymati';
COMMENT ON COLUMN exchange_rates.updated_by IS 'Yangilagan admin ID';
