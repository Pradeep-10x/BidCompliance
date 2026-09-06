-- ====================================================================
-- CPCL Bid Compliance & Statutory Verification Database Schema
-- Optimized for PostgreSQL with pg_trgm for high-speed entity resolution
-- ====================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. MCA Master Data Snapshot
CREATE TABLE IF NOT EXISTS mca_companies (
    cin VARCHAR(21) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255),
    roc_code VARCHAR(50),
    registration_number VARCHAR(50),
    company_category VARCHAR(100),
    class_of_company VARCHAR(50),
    date_of_incorporation DATE,
    authorized_capital NUMERIC(18, 2),
    paidup_capital NUMERIC(18, 2),
    company_status VARCHAR(50) DEFAULT 'Active',
    registered_address TEXT,
    email VARCHAR(150),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mca_normalized_name ON mca_companies USING gin (normalized_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_mca_status ON mca_companies (company_status);

-- 2. MSME / Udyam Registered Enterprises
CREATE TABLE IF NOT EXISTS msme_enterprises (
    udyam_registration_number VARCHAR(30) PRIMARY KEY,
    enterprise_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255),
    enterprise_type VARCHAR(50), -- Micro, Small, Medium
    major_activity VARCHAR(50),   -- Manufacturing, Services, Trading
    nic_2digit_code VARCHAR(10),
    nic_4digit_code VARCHAR(10),
    state VARCHAR(100),
    district VARCHAR(100),
    date_of_registration DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_msme_normalized_name ON msme_enterprises USING gin (normalized_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_msme_activity ON msme_enterprises (major_activity);

-- 3. CPCL Official Debarment / Holiday List
CREATE TABLE IF NOT EXISTS cpcl_debarment_records (
    id SERIAL PRIMARY KEY,
    bidder_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    pan_masked VARCHAR(20),       -- e.g. xxxxxxxx2Q from CPCL portal
    pan_full VARCHAR(10),         -- 10-char PAN if known
    login_id VARCHAR(150),
    organisation_chain TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    active_status BOOLEAN DEFAULT TRUE,
    source_reference VARCHAR(100) DEFAULT 'CPCL e-Procurement Portal (cpcletenders.nic.in)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_debarment_normalized_name ON cpcl_debarment_records USING gin (normalized_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_debarment_pan_masked ON cpcl_debarment_records (pan_masked);
CREATE INDEX IF NOT EXISTS idx_debarment_pan_full ON cpcl_debarment_records (pan_full);
CREATE INDEX IF NOT EXISTS idx_debarment_dates ON cpcl_debarment_records (start_date, end_date);

-- 4. Bid Evaluation Dossiers
CREATE TABLE IF NOT EXISTS bid_evaluations (
    bid_id VARCHAR(64) PRIMARY KEY,
    tender_number VARCHAR(100),
    bidder_name VARCHAR(255),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    classification_summary JSONB,
    extracted_fields JSONB,
    contradictions JSONB,
    statutory_verifications JSONB,
    recommendation_status VARCHAR(50), -- officer_review_ready, clarification_required, manual_review_required
    recommendation_narrative TEXT
);

-- 5. Immutable Officer Audit Log
CREATE TABLE IF NOT EXISTS officer_audit_log (
    id SERIAL PRIMARY KEY,
    bid_id VARCHAR(64) REFERENCES bid_evaluations(bid_id) ON DELETE CASCADE,
    officer_id VARCHAR(100) NOT NULL,
    officer_name VARCHAR(150),
    decision VARCHAR(50) NOT NULL, -- QUALIFY, DISQUALIFY, CLARIFICATION_REQUIRED, MANUAL_REVIEW
    reason_narrative TEXT NOT NULL,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_bid_id ON officer_audit_log (bid_id);
