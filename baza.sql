-- Kreiranje tabele za stranke
CREATE TABLE stranke (
    id SERIAL PRIMARY KEY,
    ime VARCHAR(100) NOT NULL,
    priimek VARCHAR(100) NOT NULL,
    naslov TEXT,
    email VARCHAR(100),
    telefon VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Kreiranje tabele za lokacije/merilna mesta
CREATE TABLE lokacije (
    id SERIAL PRIMARY KEY,
    stranka_id INTEGER REFERENCES stranke(id),
    naziv VARCHAR(100) NOT NULL,
    naslov TEXT,
    merilna_stevilka VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Kreiranje tabele za meritve porabe
CREATE TABLE meritve (
    id SERIAL PRIMARY KEY,
    lokacija_id INTEGER REFERENCES lokacije(id),
    casovni_zig TIMESTAMP NOT NULL,
    poraba_kwh DECIMAL(10,4) NOT NULL,
    dinamicna_cena_eur_kwh DECIMAL(8,5) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lokacija_id, casovni_zig)
);

-- Kreiranje tabele za račune
CREATE TABLE racuni (
    id SERIAL PRIMARY KEY,
    lokacija_id INTEGER REFERENCES lokacije(id),
    stevilka_racuna VARCHAR(50) UNIQUE NOT NULL,
    datum_od DATE NOT NULL,
    datum_do DATE NOT NULL,
    skupni_znesek DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'USTVARJEN',
    datum_izdaje TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pdf_pot TEXT
);

-- Kreiranje tabele za postavke računa
CREATE TABLE postavke_racuna (
    id SERIAL PRIMARY KEY,
    racun_id INTEGER REFERENCES racuni(id),
    meritev_id INTEGER REFERENCES meritve(id),
    poraba_kwh DECIMAL(10,4) NOT NULL,
    cena_eur_kwh DECIMAL(8,5) NOT NULL,
    znesek DECIMAL(10,2) NOT NULL
);

-- Dodajanje testnih strank
INSERT INTO stranke (ime, priimek, naslov, email, telefon) VALUES
('Janez', 'Novak', 'Ljubljanska cesta 1, 1000 Ljubljana', 'janez.novak@email.com', '031234567'),
('Marija', 'Kovač', 'Celovška cesta 2, 1000 Ljubljana', 'marija.kovac@email.com', '031234568'),
('Petra', 'Zorec', 'Dunajska cesta 3, 1000 Ljubljana', 'petra.zorec@email.com', '031234569');

-- Dodajanje testnih lokacij
INSERT INTO lokacije (stranka_id, naziv, naslov, merilna_stevilka) VALUES
(1, 'Lokacija 1', 'Ljubljanska cesta 1, 1000 Ljubljana', 'SI-001'),
(2, 'Lokacija 2', 'Celovška cesta 2, 1000 Ljubljana', 'SI-002'),
(3, 'Lokacija 3', 'Dunajska cesta 3, 1000 Ljubljana', 'SI-003');

-- Kreiranje indeksov za boljšo optimizacijo
CREATE INDEX idx_meritve_lokacija_cas ON meritve(lokacija_id, casovni_zig);
CREATE INDEX idx_racuni_lokacija ON racuni(lokacija_id);
CREATE INDEX idx_postavke_racun ON postavke_racuna(racun_id);
