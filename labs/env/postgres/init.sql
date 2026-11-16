CREATE SCHEMA crm;
CREATE TABLE crm.customers (customer_id int PRIMARY KEY, name text, region text, segment text, email text);
INSERT INTO crm.customers
SELECT g, 'Customer ' || g,
       (ARRAY['NA','EMEA','APJ','LATAM'])[1 + g % 4],
       (ARRAY['Enterprise','Mid-market','SMB'])[1 + g % 3],
       'customer' || g || '@example.com'
FROM generate_series(1, 1000) g;
