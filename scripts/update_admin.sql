-- Update admin credentials
-- Generated: 2026-05-15
-- bcrypt hash of password: Maks.26091991

UPDATE users
SET
    phone        = '+79955426099',
    email        = 'maksim.prokopiew@gmail.com',
    password_hash = '$2b$12$EkJQNMBzFxSQRfqX19Cxi.BYEQJZo9QNHotz2QagcS2CMLiLDLtIy'
WHERE role = 'admin';
