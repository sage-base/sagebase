-- Add role_name_mappings column to minutes table
-- This column stores the mapping between roles and names extracted from meeting minutes
-- Format: JSON object like {"議長": "伊藤条一", "副議長": "梶谷大志"}

ALTER TABLE minutes
ADD COLUMN IF NOT EXISTS role_name_mappings JSONB;

-- Add comment to the column
COMMENT ON COLUMN minutes.role_name_mappings IS '議事録冒頭の出席者情報から抽出した役職-人名マッピング (例: {"議長": "伊藤条一"})';
