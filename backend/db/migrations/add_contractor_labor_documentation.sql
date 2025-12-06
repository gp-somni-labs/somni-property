-- ============================================================================
-- COMPREHENSIVE CONTRACTOR LABOR DOCUMENTATION SYSTEM
-- ============================================================================
-- Enhances quote labor items with contractor assignment, photo documentation,
-- time tracking, and detailed work notes
-- ============================================================================

-- ============================================================================
-- 1. ENHANCE QUOTE_LABOR_ITEMS TABLE
-- ============================================================================

-- Add contractor assignment and tracking fields
ALTER TABLE quote_labor_items
ADD COLUMN IF NOT EXISTS assigned_contractor_id UUID REFERENCES contractors(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS contractor_assigned_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS contractor_assigned_by VARCHAR(255),

-- Work status tracking
ADD COLUMN IF NOT EXISTS work_status VARCHAR(50) DEFAULT 'pending',  -- pending, assigned, in_progress, completed, on_hold, cancelled
ADD COLUMN IF NOT EXISTS work_started_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS work_completed_at TIMESTAMP,

-- Actual time tracking (vs estimated)
ADD COLUMN IF NOT EXISTS actual_hours NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS actual_labor_cost NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS actual_materials_cost NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS actual_total_cost NUMERIC(10,2),

-- Variance tracking
ADD COLUMN IF NOT EXISTS hours_variance NUMERIC(10,2),  -- actual - estimated
ADD COLUMN IF NOT EXISTS cost_variance NUMERIC(10,2),   -- actual - estimated

-- Customer approval
ADD COLUMN IF NOT EXISTS requires_customer_approval BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS customer_approved BOOLEAN,
ADD COLUMN IF NOT EXISTS customer_approved_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS customer_approval_notes TEXT,

-- Quality control
ADD COLUMN IF NOT EXISTS qc_passed BOOLEAN,
ADD COLUMN IF NOT EXISTS qc_performed_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS qc_performed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS qc_notes TEXT,

-- Location tracking (for mobile crews)
ADD COLUMN IF NOT EXISTS work_location_coords POINT,  -- GPS coordinates
ADD COLUMN IF NOT EXISTS work_location_address TEXT,

-- Equipment/tools used
ADD COLUMN IF NOT EXISTS equipment_used JSONB DEFAULT '[]'::jsonb,  -- [{"name": "Drill", "serial": "12345"}]

-- Additional metadata
ADD COLUMN IF NOT EXISTS weather_conditions TEXT,  -- For outdoor work
ADD COLUMN IF NOT EXISTS access_notes TEXT,  -- How to access site, gate codes, etc.
ADD COLUMN IF NOT EXISTS safety_notes TEXT;  -- Safety precautions taken

-- Add constraints
ALTER TABLE quote_labor_items
ADD CONSTRAINT valid_work_status CHECK (work_status IN ('pending', 'assigned', 'in_progress', 'completed', 'on_hold', 'cancelled', 'needs_review'));

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_quote_labor_contractor ON quote_labor_items(assigned_contractor_id);
CREATE INDEX IF NOT EXISTS idx_quote_labor_status ON quote_labor_items(work_status);
CREATE INDEX IF NOT EXISTS idx_quote_labor_dates ON quote_labor_items(work_started_at, work_completed_at);

COMMENT ON COLUMN quote_labor_items.assigned_contractor_id IS 'Contractor assigned to perform this labor task';
COMMENT ON COLUMN quote_labor_items.work_status IS 'Current status of the work: pending, assigned, in_progress, completed, on_hold, cancelled';
COMMENT ON COLUMN quote_labor_items.actual_hours IS 'Actual hours worked (tracked via contractor updates)';
COMMENT ON COLUMN quote_labor_items.hours_variance IS 'Difference between actual and estimated hours (positive = over estimate)';


-- ============================================================================
-- 2. LABOR ITEM PHOTOS & ATTACHMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS quote_labor_item_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    labor_item_id UUID NOT NULL REFERENCES quote_labor_items(id) ON DELETE CASCADE,

    -- Photo metadata
    photo_type VARCHAR(50) NOT NULL,  -- before, after, progress, example, issue, completed, safety, equipment
    file_url TEXT NOT NULL,
    file_path TEXT,
    file_size INTEGER,
    mime_type VARCHAR(100),

    -- Photo details
    caption TEXT,
    description TEXT,
    photo_taken_at TIMESTAMP DEFAULT NOW(),
    photo_taken_by VARCHAR(255),  -- Contractor name or staff
    photographer_type VARCHAR(50),  -- contractor, staff, customer

    -- Location metadata
    gps_coordinates POINT,
    location_notes TEXT,

    -- Categorization
    tags JSONB DEFAULT '[]'::jsonb,  -- ['plumbing', 'leak', 'before-repair']
    related_task VARCHAR(255),  -- Which specific task this photo documents

    -- Analysis/annotations
    annotations JSONB DEFAULT '[]'::jsonb,  -- Image annotations/markup
    ai_analysis JSONB,  -- AI-generated insights about the photo

    -- Display settings
    display_order INTEGER DEFAULT 0,
    show_to_customer BOOLEAN DEFAULT true,
    show_in_pdf BOOLEAN DEFAULT true,
    is_thumbnail BOOLEAN DEFAULT false,

    -- Quality/review
    approved_for_display BOOLEAN DEFAULT true,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_labor_photos_item_id ON quote_labor_item_photos(labor_item_id);
CREATE INDEX idx_labor_photos_type ON quote_labor_item_photos(photo_type);
CREATE INDEX idx_labor_photos_taken_at ON quote_labor_item_photos(photo_taken_at);
CREATE INDEX idx_labor_photos_display_order ON quote_labor_item_photos(labor_item_id, display_order);

COMMENT ON TABLE quote_labor_item_photos IS 'Photo documentation for labor tasks (before/after, progress, examples)';
COMMENT ON COLUMN quote_labor_item_photos.photo_type IS 'Type: before, after, progress, example, issue, completed, safety, equipment';
COMMENT ON COLUMN quote_labor_item_photos.annotations IS 'Image markup/annotations showing specific areas of interest';


-- ============================================================================
-- 3. CONTRACTOR NOTES & UPDATES
-- ============================================================================

CREATE TABLE IF NOT EXISTS quote_labor_item_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    labor_item_id UUID NOT NULL REFERENCES quote_labor_items(id) ON DELETE CASCADE,

    -- Note content
    note_type VARCHAR(50) NOT NULL,  -- progress_update, issue, material_request, question, completion, customer_feedback
    note_text TEXT NOT NULL,
    note_title VARCHAR(255),

    -- Attribution
    created_by VARCHAR(255) NOT NULL,
    created_by_type VARCHAR(50) NOT NULL,  -- contractor, staff, customer, system
    created_by_id UUID,  -- contractor_id or staff_id

    -- Visibility
    is_internal BOOLEAN DEFAULT false,  -- Hidden from customer
    show_to_customer BOOLEAN DEFAULT true,
    requires_response BOOLEAN DEFAULT false,

    -- Response/resolution
    responded_to BOOLEAN DEFAULT false,
    responded_by VARCHAR(255),
    responded_at TIMESTAMP,
    response_text TEXT,

    -- Categorization
    priority VARCHAR(20),  -- low, normal, high, urgent
    tags JSONB DEFAULT '[]'::jsonb,

    -- Attachments (references to photos or documents)
    attached_photo_ids JSONB DEFAULT '[]'::jsonb,  -- [uuid1, uuid2, ...]
    attached_files JSONB DEFAULT '[]'::jsonb,

    -- Time tracking (if note includes time update)
    hours_worked NUMERIC(10,2),
    work_date DATE,

    -- Location
    location_coords POINT,
    location_name TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_labor_notes_item_id ON quote_labor_item_notes(labor_item_id);
CREATE INDEX idx_labor_notes_type ON quote_labor_item_notes(note_type);
CREATE INDEX idx_labor_notes_created_at ON quote_labor_item_notes(created_at);
CREATE INDEX idx_labor_notes_requires_response ON quote_labor_item_notes(requires_response) WHERE requires_response = true;

COMMENT ON TABLE quote_labor_item_notes IS 'Contractor notes, updates, and communication thread for labor tasks';
COMMENT ON COLUMN quote_labor_item_notes.note_type IS 'Type: progress_update, issue, material_request, question, completion, customer_feedback';
COMMENT ON COLUMN quote_labor_item_notes.is_internal IS 'Internal notes hidden from customer (for staff/contractor coordination)';


-- ============================================================================
-- 4. TIME TRACKING ENTRIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS quote_labor_time_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    labor_item_id UUID NOT NULL REFERENCES quote_labor_items(id) ON DELETE CASCADE,

    -- Time details
    work_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    duration_hours NUMERIC(10,2) NOT NULL,

    -- Worker info
    contractor_id UUID REFERENCES contractors(id) ON DELETE SET NULL,
    worker_name VARCHAR(255) NOT NULL,
    worker_role VARCHAR(100),  -- lead_tech, assistant, apprentice

    -- Work performed
    work_description TEXT,
    tasks_completed JSONB DEFAULT '[]'::jsonb,  -- ["Installed 3 locks", "Ran wiring"]

    -- Billing
    hourly_rate NUMERIC(10,2),
    total_cost NUMERIC(10,2),
    billable BOOLEAN DEFAULT true,
    approved BOOLEAN DEFAULT false,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,

    -- Location verification
    clock_in_location POINT,
    clock_out_location POINT,
    verified BOOLEAN DEFAULT false,

    -- Break time
    break_duration_hours NUMERIC(10,2) DEFAULT 0,

    -- Notes
    notes TEXT,
    issues_encountered TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_labor_time_item_id ON quote_labor_time_entries(labor_item_id);
CREATE INDEX idx_labor_time_contractor ON quote_labor_time_entries(contractor_id);
CREATE INDEX idx_labor_time_date ON quote_labor_time_entries(work_date);
CREATE INDEX idx_labor_time_approved ON quote_labor_time_entries(approved);

COMMENT ON TABLE quote_labor_time_entries IS 'Detailed time tracking for labor tasks with clock-in/out and verification';
COMMENT ON COLUMN quote_labor_time_entries.duration_hours IS 'Total billable hours (excluding breaks)';


-- ============================================================================
-- 5. MATERIAL USAGE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS quote_labor_materials_used (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    labor_item_id UUID NOT NULL REFERENCES quote_labor_items(id) ON DELETE CASCADE,

    -- Material details
    material_name VARCHAR(255) NOT NULL,
    material_category VARCHAR(100),  -- cable, mounting, electrical, plumbing, etc.
    quantity_used NUMERIC(10,2) NOT NULL,
    unit_type VARCHAR(50) NOT NULL,  -- ft, ea, box, roll, etc.

    -- Pricing
    unit_cost NUMERIC(10,2),
    total_cost NUMERIC(10,2),

    -- Vendor/source
    vendor_name VARCHAR(255),
    purchase_order_number VARCHAR(100),
    receipt_photo_url TEXT,

    -- Tracking
    used_date DATE,
    recorded_by VARCHAR(255),  -- Contractor or staff who recorded usage

    -- Comparison to estimate
    was_estimated BOOLEAN DEFAULT false,
    estimated_quantity NUMERIC(10,2),
    quantity_variance NUMERIC(10,2),  -- actual - estimated

    -- Notes
    notes TEXT,
    reason_for_variance TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_labor_materials_item_id ON quote_labor_materials_used(labor_item_id);
CREATE INDEX idx_labor_materials_category ON quote_labor_materials_used(material_category);
CREATE INDEX idx_labor_materials_date ON quote_labor_materials_used(used_date);

COMMENT ON TABLE quote_labor_materials_used IS 'Actual materials used vs estimated for cost tracking';


-- ============================================================================
-- 6. WORK ORDER STATUS HISTORY
-- ============================================================================

CREATE TABLE IF NOT EXISTS quote_labor_item_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    labor_item_id UUID NOT NULL REFERENCES quote_labor_items(id) ON DELETE CASCADE,

    -- Change tracking
    change_type VARCHAR(50) NOT NULL,  -- status_change, contractor_assigned, time_logged, cost_updated, photo_added, note_added
    old_value TEXT,
    new_value TEXT,

    -- Change details
    changed_by VARCHAR(255),
    changed_by_type VARCHAR(50),  -- contractor, staff, customer, system
    change_reason TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,  -- Additional context about the change

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_labor_history_item_id ON quote_labor_item_history(labor_item_id);
CREATE INDEX idx_labor_history_type ON quote_labor_item_history(change_type);
CREATE INDEX idx_labor_history_created_at ON quote_labor_item_history(created_at);

COMMENT ON TABLE quote_labor_item_history IS 'Audit trail of all changes to labor items';


-- ============================================================================
-- 7. BEFORE/AFTER PHOTO PAIRS
-- ============================================================================

CREATE TABLE IF NOT EXISTS quote_labor_before_after_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    labor_item_id UUID NOT NULL REFERENCES quote_labor_items(id) ON DELETE CASCADE,

    -- Photo references
    before_photo_id UUID REFERENCES quote_labor_item_photos(id) ON DELETE SET NULL,
    after_photo_id UUID REFERENCES quote_labor_item_photos(id) ON DELETE SET NULL,

    -- Comparison details
    pair_title VARCHAR(255),
    pair_description TEXT,
    work_performed TEXT,  -- What work was done between these photos

    -- Metrics/measurements (if applicable)
    before_measurement NUMERIC(10,2),
    after_measurement NUMERIC(10,2),
    improvement_percentage NUMERIC(5,2),
    measurement_unit VARCHAR(50),

    -- Display
    display_order INTEGER DEFAULT 0,
    show_to_customer BOOLEAN DEFAULT true,
    featured BOOLEAN DEFAULT false,  -- Highlight this comparison

    -- Annotations
    before_annotations JSONB,
    after_annotations JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_before_after_item_id ON quote_labor_before_after_pairs(labor_item_id);
CREATE INDEX idx_before_after_display_order ON quote_labor_before_after_pairs(labor_item_id, display_order);

COMMENT ON TABLE quote_labor_before_after_pairs IS 'Paired before/after photos showing work completion and quality';


-- ============================================================================
-- 8. EXAMPLE WORK PHOTOS (Reference Library)
-- ============================================================================

CREATE TABLE IF NOT EXISTS contractor_work_examples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contractor_id UUID REFERENCES contractors(id) ON DELETE CASCADE,

    -- Example details
    example_title VARCHAR(255) NOT NULL,
    example_description TEXT,
    work_category VARCHAR(100),  -- plumbing, electrical, installation, etc.
    difficulty_level VARCHAR(50),  -- simple, moderate, complex

    -- Photos
    primary_photo_url TEXT NOT NULL,
    additional_photos JSONB DEFAULT '[]'::jsonb,  -- [{"url": "...", "caption": "..."}]

    -- Project details
    project_type VARCHAR(100),
    completion_date DATE,
    duration_days INTEGER,
    total_cost NUMERIC(10,2),

    -- Skills showcased
    skills_demonstrated JSONB DEFAULT '[]'::jsonb,  -- ['smart lock install', 'network cabling']
    equipment_used JSONB DEFAULT '[]'::jsonb,

    -- Customer info (anonymized)
    customer_satisfaction_rating INTEGER,  -- 1-5
    customer_testimonial TEXT,

    -- Display settings
    is_public BOOLEAN DEFAULT true,
    show_in_portfolio BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,

    -- Quality
    approved BOOLEAN DEFAULT false,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_work_examples_contractor ON contractor_work_examples(contractor_id);
CREATE INDEX idx_work_examples_category ON contractor_work_examples(work_category);
CREATE INDEX idx_work_examples_public ON contractor_work_examples(is_public) WHERE is_public = true;

COMMENT ON TABLE contractor_work_examples IS 'Portfolio of example work by contractors to show customers';


-- ============================================================================
-- 9. CREATE VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Labor items with contractor and photo counts
CREATE OR REPLACE VIEW v_labor_items_summary AS
SELECT
    li.*,
    c.company_name AS contractor_name,
    c.email AS contractor_email,
    c.phone AS contractor_phone,
    (SELECT COUNT(*) FROM quote_labor_item_photos WHERE labor_item_id = li.id) AS photo_count,
    (SELECT COUNT(*) FROM quote_labor_item_photos WHERE labor_item_id = li.id AND photo_type = 'before') AS before_photo_count,
    (SELECT COUNT(*) FROM quote_labor_item_photos WHERE labor_item_id = li.id AND photo_type = 'after') AS after_photo_count,
    (SELECT COUNT(*) FROM quote_labor_item_notes WHERE labor_item_id = li.id) AS note_count,
    (SELECT COUNT(*) FROM quote_labor_time_entries WHERE labor_item_id = li.id) AS time_entry_count,
    (SELECT SUM(duration_hours) FROM quote_labor_time_entries WHERE labor_item_id = li.id) AS total_actual_hours
FROM quote_labor_items li
LEFT JOIN contractors c ON li.assigned_contractor_id = c.id;

COMMENT ON VIEW v_labor_items_summary IS 'Comprehensive view of labor items with contractor info and documentation counts';


-- View: Active work for contractors
CREATE OR REPLACE VIEW v_contractor_active_work AS
SELECT
    c.id AS contractor_id,
    c.company_name,
    li.id AS labor_item_id,
    li.quote_id,
    li.task_name,
    li.work_status,
    li.estimated_hours,
    li.actual_hours,
    li.work_started_at,
    q.quote_number,
    q.customer_name,
    q.customer_phone,
    q.customer_email
FROM contractors c
JOIN quote_labor_items li ON li.assigned_contractor_id = c.id
JOIN quotes q ON li.quote_id = q.id
WHERE li.work_status IN ('assigned', 'in_progress')
ORDER BY li.work_started_at DESC NULLS LAST;

COMMENT ON VIEW v_contractor_active_work IS 'Current active work assigned to contractors';


-- ============================================================================
-- GRANT PERMISSIONS (adjust as needed for your auth system)
-- ============================================================================

-- Grant SELECT to authenticated users
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated_users;

-- Grant INSERT, UPDATE, DELETE to contractors on their own data
-- GRANT INSERT, UPDATE, DELETE ON quote_labor_item_photos, quote_labor_item_notes, quote_labor_time_entries TO contractors;
