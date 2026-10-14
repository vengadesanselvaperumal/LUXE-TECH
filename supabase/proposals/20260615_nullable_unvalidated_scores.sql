-- Proposal only. Review and deploy through the approved database process.
-- These values are absent when the relevant metric is undefined or uncalibrated.
ALTER TABLE forecasts
    ALTER COLUMN confidence DROP NOT NULL;

ALTER TABLE prophecy
    ALTER COLUMN confidence DROP NOT NULL;
